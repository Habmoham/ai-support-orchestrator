"""
Refund Agent: a specialist node that handles refund-category tickets.

Checks the customer's order against mock policy data to decide approve/
deny/escalate — this is the agent most likely to need human escalation,
since refund decisions often carry real financial and policy weight.
"""

import json
import os
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from state import TicketState

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "mock_data", "orders.json")

REFUND_SYSTEM_PROMPT = """You are a refund support agent. You are given:
1. The customer's message
2. Their order data and refund eligibility
3. The company refund policy

Decide whether to approve, deny, or escalate the refund request, and draft
a clear response explaining the decision using ONLY the data provided.

Then respond with ONLY a JSON object (no markdown, no preamble):

{
  "response": "<your drafted reply to the customer>",
  "confidence": <float 0.0-1.0>,
  "tool_used": "refund_check"
}

Lower confidence (below 0.6) if the case is borderline, involves an amount
over $100, or the eligibility data conflicts with what the customer is
requesting — these should escalate to a human rather than auto-resolve.
"""

llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0)


def _lookup_order(email: str) -> dict | None:
    """Mock order/refund-eligibility lookup tool."""
    with open(DATA_PATH, "r") as f:
        data = json.load(f)
    for order in data["orders"]:
        if order["customer_email"].lower() == (email or "").lower():
            return {"order": order, "policy": data["refund_policy"]}
    return None


def refund_node(state: TicketState) -> TicketState:
    result = _lookup_order(state.get("customer_email", ""))

    if result is None:
        return {
            **state,
            "agent_response": "Could not locate an order for the provided email.",
            "agent_confidence": 0.0,
            "agent_used_tool": "refund_check",
            "last_error": "order_not_found",
        }

    context = json.dumps(result, indent=2)
    messages = [
        SystemMessage(content=REFUND_SYSTEM_PROMPT),
        HumanMessage(
            content=f"Customer message: {state['customer_message']}\n\nOrder & policy data:\n{context}"
        ),
    ]
    response = llm.invoke(messages)

    try:
        parsed = json.loads(response.content)
    except json.JSONDecodeError:
        parsed = {"response": response.content, "confidence": 0.4, "tool_used": "refund_check"}

    confidence = float(parsed.get("confidence", 0.4))

    # Deterministic guardrail: don't trust the LLM's self-reported confidence
    # alone for a policy-sensitive decision. If the order data says the
    # refund isn't eligible, force low confidence regardless of what the
    # model claims - this is a rule check, not a judgment call.
    order = result["order"]
    if not order.get("refund_eligible", False):
        confidence = min(confidence, 0.3)

    return {
        **state,
        "agent_response": parsed.get("response", ""),
        "agent_confidence": confidence,
        "agent_used_tool": "refund_check",
    }
