"""
Orchestration graph definition.

STEP 4 scope: this is now the full orchestration loop.

  triage -> [billing | technical | refund] -> confidence_gate
                                                  |
                              +-------------------+-------------------+
                              |                   |                   |
                          retry (max 1)      auto_resolve         human_handoff

The confidence_gate and terminal nodes are pure Python logic, not LLM
calls - the orchestrator is making decisions about the agents' output,
which is the core thing this project demonstrates.
"""

from dotenv import load_dotenv
load_dotenv()

from langgraph.graph import StateGraph, END
from state import TicketState
from agents.triage import triage_node
from agents.billing import billing_node
from agents.technical import technical_node
from agents.refund import refund_node
from agents.confidence_gate import confidence_gate, route_after_gate
from agents.terminal_nodes import auto_resolve_node, human_handoff_node
from tracing_setup import get_langfuse_handler


def route_after_triage(state: TicketState) -> str:
    category = state.get("category", "other")
    if category in ("billing", "technical", "refund"):
        return category
    return "unhandled"


def build_graph():
    graph = StateGraph(TicketState)

    graph.add_node("triage", triage_node)
    graph.add_node("billing", billing_node)
    graph.add_node("technical", technical_node)
    graph.add_node("refund", refund_node)
    graph.add_node("confidence_gate", confidence_gate)
    graph.add_node("auto_resolve", auto_resolve_node)
    graph.add_node("human_handoff", human_handoff_node)

    graph.set_entry_point("triage")

    graph.add_conditional_edges(
        "triage",
        route_after_triage,
        {
            "billing": "billing",
            "technical": "technical",
            "refund": "refund",
            "unhandled": END,
        },
    )

    # Every specialist agent's output goes through the confidence gate -
    # nothing resolves or escalates without passing through this check.
    graph.add_edge("billing", "confidence_gate")
    graph.add_edge("technical", "confidence_gate")
    graph.add_edge("refund", "confidence_gate")

    graph.add_conditional_edges(
        "confidence_gate",
        route_after_gate,
        {
            "retry_billing": "billing",
            "retry_technical": "technical",
            "retry_refund": "refund",
            "human_handoff": "human_handoff",
            "auto_resolve": "auto_resolve",
        },
    )

    graph.add_edge("auto_resolve", END)
    graph.add_edge("human_handoff", END)

    return graph.compile()


def run_ticket(app, ticket: TicketState, langfuse_handler=None):
    config = {}
    if langfuse_handler:
        config = {
            "callbacks": [langfuse_handler],
            "run_name": f"ticket-{ticket['ticket_id']}",
            "metadata": {"ticket_id": ticket["ticket_id"]},
            "tags": ["support-orchestrator"],
        }

    result = app.invoke(ticket, config=config)
    print(f"\n=== Ticket {ticket['ticket_id']} ===")
    print(f"Message:    {ticket['customer_message']}")
    print(f"Category:   {result.get('category')} (confidence: {result.get('triage_confidence')})")
    print(f"Retries:    {result.get('retry_count', 0)}")
    print(f"Status:     {result.get('final_status')}")
    print(f"Summary:\n{result.get('resolution_summary')}")
    return result


if __name__ == "__main__":
    app = build_graph()
    langfuse_handler = get_langfuse_handler()
    if langfuse_handler:
        print("Langfuse tracing enabled - check your dashboard after this run.\n")
    else:
        print("Langfuse keys not set - running without tracing.\n")

    test_tickets: list[TicketState] = [
        {
            "ticket_id": "T-001",
            "customer_message": "I was charged twice for my subscription last month, can you fix this?",
            "customer_email": "sarah.chen@example.com",
        },
        {
            "ticket_id": "T-002",
            "customer_message": "The app keeps crashing every time I open it on my phone.",
            "customer_email": "james.okafor@example.com",
        },
        {
            # Deliberately unknown email - should retry once, then escalate.
            "ticket_id": "T-003",
            "customer_message": "I need a refund, this app isn't working for me at all.",
            "customer_email": "unknown.person@example.com",
        },
        {
            # Priya's order is NOT refund-eligible per the mock data and
            # is a $299.99 order - should push confidence low and escalate.
            "ticket_id": "T-004",
            "customer_message": "I'd like a full refund on my annual plan please.",
            "customer_email": "priya.nair@example.com",
        },
    ]

    for ticket in test_tickets:
        run_ticket(app, ticket, langfuse_handler)
