"""
Confidence Gate: NOT an LLM call - this is deliberate.

This node is pure Python logic that inspects the specialist agent's output
and decides what happens next: auto-resolve, retry, or escalate to a human.
This is the orchestration-specific piece of the project - the decision
about how to use an agent's output, made by the orchestrator itself
rather than by another LLM call.
"""

from state import TicketState

CONFIDENCE_THRESHOLD = 0.6
MAX_RETRIES = 1


def confidence_gate(state: TicketState) -> TicketState:
    """
    Reads agent_confidence and last_error to decide the ticket's fate.
    Doesn't call an LLM - just applies a policy, the way a real
    orchestration layer would.
    """
    confidence = state.get("agent_confidence", 0.0)
    error = state.get("last_error")
    retry_count = state.get("retry_count", 0)

    if error and retry_count < MAX_RETRIES:
        # A tool-level failure (customer not found, no KB match, etc.)
        # gets one retry before we give up and escalate. pending_retry
        # is the explicit signal route_after_gate uses - we also clear
        # last_error here so a successful retry isn't wrongly flagged
        # by stale state from the first attempt.
        return {
            **state,
            "retry_count": retry_count + 1,
            "last_error": None,
            "pending_retry": True,
        }

    if error or confidence < CONFIDENCE_THRESHOLD:
        return {**state, "needs_human": True, "pending_retry": False}

    return {**state, "needs_human": False, "pending_retry": False}


def route_after_gate(state: TicketState) -> str:
    """
    Conditional edge from the gate: decides the next node based on what
    the gate just decided. Three outcomes: retry the same specialist,
    escalate to a human, or auto-resolve and end.
    """
    if state.get("pending_retry"):
        category = state.get("category", "other")
        if category in ("billing", "technical", "refund"):
            return f"retry_{category}"

    if state.get("needs_human"):
        return "human_handoff"

    return "auto_resolve"
