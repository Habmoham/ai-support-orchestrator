"""
State schema for the AI Customer Support Orchestrator.

This TypedDict defines everything that flows through the LangGraph graph.
Every node reads from and writes to this shared state.
"""

from typing import TypedDict, Optional, Literal
from typing_extensions import NotRequired


class TicketState(TypedDict):
    # --- Input ---
    ticket_id: str
    customer_message: str
    customer_email: NotRequired[str]  # used by specialist agents to look up account/order data

    # --- Triage output ---
    category: NotRequired[Literal["billing", "technical", "refund", "other"]]
    urgency: NotRequired[Literal["low", "medium", "high"]]
    triage_confidence: NotRequired[float]  # 0.0 - 1.0

    # --- Specialist agent output ---
    agent_response: NotRequired[str]
    agent_confidence: NotRequired[float]
    agent_used_tool: NotRequired[str]  # which mock DB/tool was called

    # --- Retry tracking ---
    retry_count: NotRequired[int]
    last_error: NotRequired[Optional[str]]
    pending_retry: NotRequired[bool]  # internal flag set by the confidence gate

    # --- Routing / resolution ---
    needs_human: NotRequired[bool]
    final_status: NotRequired[Literal["auto_resolved", "escalated", "failed"]]
    resolution_summary: NotRequired[str]
