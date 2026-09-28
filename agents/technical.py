"""
Technical Agent: a specialist node that handles technical-category tickets.

Uses simple keyword matching against a mock knowledge base to simulate
retrieval (this is intentionally lightweight for the orchestration demo —
your existing FAISS/embeddings pipeline from your last project would be a
natural upgrade here later).
"""

import json
import os
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from state import TicketState

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "mock_data", "knowledge_base.json")

TECHNICAL_SYSTEM_PROMPT = """You are a technical support agent. You are given:
1. The customer's message
2. One or more knowledge base articles that may be relevant

Draft a clear, step-by-step response using ONLY the knowledge base content
provided — don't invent troubleshooting steps that aren't in the articles.

Then respond with ONLY a JSON object (no markdown, no preamble):

{
  "response": "<your drafted reply to the customer>",
  "confidence": <float 0.0-1.0, how confident this resolves the issue>,
  "tool_used": "kb_search"
}

Lower confidence if: no article closely matches the issue, or the issue
sounds like it needs an engineer to investigate rather than a KB fix.
"""

llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0)


def _search_kb(query: str) -> list[dict]:
    """Mock knowledge-base search tool (keyword matching)."""
    with open(DATA_PATH, "r") as f:
        data = json.load(f)

    query_lower = query.lower()
    matches = []
    for article in data["articles"]:
        if any(keyword in query_lower for keyword in article["keywords"]):
            matches.append(article)
    return matches


def technical_node(state: TicketState) -> TicketState:
    matches = _search_kb(state["customer_message"])

    if not matches:
        return {
            **state,
            "agent_response": "No matching knowledge base article found for this issue.",
            "agent_confidence": 0.2,
            "agent_used_tool": "kb_search",
            "last_error": "no_kb_match",
        }

    context = json.dumps(matches, indent=2)
    messages = [
        SystemMessage(content=TECHNICAL_SYSTEM_PROMPT),
        HumanMessage(
            content=f"Customer message: {state['customer_message']}\n\nKnowledge base articles:\n{context}"
        ),
    ]
    response = llm.invoke(messages)

    try:
        parsed = json.loads(response.content)
    except json.JSONDecodeError:
        parsed = {"response": response.content, "confidence": 0.4, "tool_used": "kb_search"}

    return {
        **state,
        "agent_response": parsed.get("response", ""),
        "agent_confidence": float(parsed.get("confidence", 0.4)),
        "agent_used_tool": "kb_search",
    }
