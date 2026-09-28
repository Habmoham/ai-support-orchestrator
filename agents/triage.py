"""
Triage Agent: the first node in the graph.

Reads the customer's message and classifies it into a category + urgency,
with a confidence score. This confidence score is what the orchestrator
later uses to decide whether to trust an automated resolution or escalate
to a human.
"""

import json
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from state import TicketState

TRIAGE_SYSTEM_PROMPT = """You are a support ticket triage classifier.
Given a customer message, respond with ONLY a JSON object (no markdown, no preamble):

{
  "category": "billing" | "technical" | "refund" | "other",
  "urgency": "low" | "medium" | "high",
  "confidence": <float between 0.0 and 1.0>
}

confidence should reflect how clearly the message fits the category —
lower it if the message is ambiguous, vague, or could fit multiple categories.
"""

llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0)


def triage_node(state: TicketState) -> TicketState:
    messages = [
        SystemMessage(content=TRIAGE_SYSTEM_PROMPT),
        HumanMessage(content=state["customer_message"]),
    ]
    response = llm.invoke(messages)

    try:
        parsed = json.loads(response.content)
    except json.JSONDecodeError:
        # Fallback if the model doesn't return clean JSON
        parsed = {"category": "other", "urgency": "medium", "confidence": 0.3}

    return {
        **state,
        "category": parsed.get("category", "other"),
        "urgency": parsed.get("urgency", "medium"),
        "triage_confidence": float(parsed.get("confidence", 0.3)),
    }