"""
FastAPI backend for the AI Customer Support Orchestrator.

Exposes a single endpoint that runs a ticket through the full graph and
returns the result, including the path it took (for the frontend's trace
view).
"""

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid

from graph import build_graph
from tracing_setup import get_langfuse_handler

app = FastAPI(title="AI Customer Support Orchestrator")

# Only these sites may call the API from a browser: the deployed frontend, plus
# a local static server for development (run `python -m http.server 5500`
# inside the frontend/ folder). No trailing slashes - origins must match exactly.
ALLOWED_ORIGINS = [
    "https://ai-support-orchestrator.vercel.app",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

graph_app = build_graph()
langfuse_handler = get_langfuse_handler()


class TicketRequest(BaseModel):
    customer_message: str
    customer_email: str = ""


class TicketResponse(BaseModel):
    ticket_id: str
    category: str | None
    urgency: str | None
    triage_confidence: float | None
    agent_used_tool: str | None
    agent_confidence: float | None
    retry_count: int
    final_status: str | None
    resolution_summary: str | None
    agent_response: str | None


@app.post("/tickets", response_model=TicketResponse)
def submit_ticket(req: TicketRequest):
    ticket_id = f"T-{uuid.uuid4().hex[:8]}"

    config = {}
    if langfuse_handler:
        config = {
            "callbacks": [langfuse_handler],
            "run_name": f"ticket-{ticket_id}",
            "metadata": {"ticket_id": ticket_id},
            "tags": ["support-orchestrator", "api"],
        }

    result = graph_app.invoke(
        {
            "ticket_id": ticket_id,
            "customer_message": req.customer_message,
            "customer_email": req.customer_email,
        },
        config=config,
    )

    return TicketResponse(
        ticket_id=ticket_id,
        category=result.get("category"),
        urgency=result.get("urgency"),
        triage_confidence=result.get("triage_confidence"),
        agent_used_tool=result.get("agent_used_tool"),
        agent_confidence=result.get("agent_confidence"),
        retry_count=result.get("retry_count", 0),
        final_status=result.get("final_status"),
        resolution_summary=result.get("resolution_summary"),
        agent_response=result.get("agent_response"),
    )


@app.get("/health")
def health():
    return {"status": "ok"}
