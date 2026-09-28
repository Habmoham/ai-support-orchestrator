"""
Terminal nodes for the orchestration graph.

Both are deliberately NOT LLM calls - by this point the specialist agent
has already drafted a response. These nodes just decide how the ticket
gets closed out and format the final record accordingly.
"""

from state import TicketState


def auto_resolve_node(state: TicketState) -> TicketState:
    return {
        **state,
        "final_status": "auto_resolved",
        "resolution_summary": (
            f"Auto-resolved by {state.get('agent_used_tool')} "
            f"(confidence: {state.get('agent_confidence')})."
        ),
    }


def human_handoff_node(state: TicketState) -> TicketState:
    """
    Produces a clean handoff summary - this is what a real support agent
    would read to pick up the ticket. Deliberately plain-text/structured
    rather than another LLM call: at handoff time, reliability matters
    more than eloquence.
    """
    reason = state.get("last_error") or f"low confidence ({state.get('agent_confidence')})"

    summary_lines = [
        f"Ticket: {state.get('ticket_id')}",
        f"Category: {state.get('category')} | Urgency: {state.get('urgency')}",
        f"Customer message: {state.get('customer_message')}",
        f"Escalation reason: {reason}",
        f"Retries attempted: {state.get('retry_count', 0)}",
    ]
    if state.get("agent_response"):
        summary_lines.append(f"Draft response attempted: {state['agent_response']}")

    return {
        **state,
        "final_status": "escalated",
        "resolution_summary": "\n".join(summary_lines),
    }
