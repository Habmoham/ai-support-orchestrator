"""
Billing Agent: a specialist node that handles billing-category tickets.

It looks up the customer's account in the mock dataset (simulating a real
billing DB), then uses that context to draft a grounded response — instead
of hallucinating account details, which is a common failure mode for
naive support bots.
"""

import json
import os
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from state import TicketState

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "mock_data", "customers.json")

BILLING_SYSTEM_PROMPT = """You are a billing support agent. You are given:
1. The customer's message
2. Their account data (billing history, plan, etc.)

Draft a clear, helpful response addressing their billing issue using ONLY
the account data provided - never invent charges, dates, or amounts that
aren't in the data.

You can only READ account data - you cannot issue refunds, reverse charges,
or take any action. Never claim a refund has been "initiated," "processed,"
or "already flagged for review" - you have no tool that does that. If a
duplicate or incorrect charge is clearly visible in the data, point it out
factually (e.g. "I can see a duplicate charge of $X on [date]") and say a
member of the team will act on it, rather than claiming it's already done.

Then respond with ONLY a JSON object (no markdown, no preamble):

{
  "response": "<your drafted reply to the customer>",
  "confidence": <float 0.0-1.0, how confident you are this fully resolves the issue>,
  "tool_used": "billing_lookup"
}

Lower confidence if: the account wasn't found, the issue isn't clearly
explained by the data, or it seems to need a policy decision (e.g. approving
a refund) rather than just information.
"""

llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0)


def _lookup_customer(email: str) -> dict | None:
    """Mock billing DB lookup tool."""
    with open(DATA_PATH, "r") as f:
        data = json.load(f)
    for customer in data["customers"]:
        if customer["email"].lower() == (email or "").lower():
            return customer
    return None


def billing_node(state: TicketState) -> TicketState:
    customer = _lookup_customer(state.get("customer_email", ""))

    if customer is None:
        # Tool failed to find the account — this is exactly the kind of
        # failure the orchestrator's retry/escalation logic should catch.
        return {
            **state,
            "agent_response": "Could not locate a customer account for the provided email.",
            "agent_confidence": 0.0,
            "agent_used_tool": "billing_lookup",
            "last_error": "customer_not_found",
        }

    context = json.dumps(customer, indent=2)
    messages = [
        SystemMessage(content=BILLING_SYSTEM_PROMPT),
        HumanMessage(
            content=f"Customer message: {state['customer_message']}\n\nAccount data:\n{context}"
        ),
    ]
    response = llm.invoke(messages)

    try:
        parsed = json.loads(response.content)
    except json.JSONDecodeError:
        parsed = {
            "response": response.content,
            "confidence": 0.4,
            "tool_used": "billing_lookup",
        }

    return {
        **state,
        "agent_response": parsed.get("response", ""),
        "agent_confidence": float(parsed.get("confidence", 0.4)),
        "agent_used_tool": "billing_lookup",
    }
