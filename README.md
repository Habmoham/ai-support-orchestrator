# AI Customer Support Orchestrator

A support-ticket system built around **agentic orchestration**, not a single
chatbot. An orchestrator classifies each incoming ticket, routes it to a
specialist agent, and then a confidence gate decides whether the response is
trustworthy enough to send automatically or needs to be escalated to a
human - with retries and a deterministic policy guardrail along the way.

**Live demo:** https://ai-support-orchestrator.vercel.app/
*(backend is on a free tier and sleeps when idle - the first request can take
up to a minute to wake it up)*

## Why orchestration, not just "an agent"

Most portfolio projects show an agent calling a tool. This project is built
around the layer above that: an orchestrator that makes decisions *about*
its agents - which one to call, whether to trust what it produced, when to
retry, and when to hand off to a person. That decision layer is plain Python
logic, not another LLM call, which matters: it makes the system's behavior
predictable and auditable instead of one more thing that can hallucinate.

## How a ticket flows through the system

```
                        ┌─────────┐
                        │  Triage  │  classifies category + urgency
                        └────┬────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
         ┌─────────┐   ┌───────────┐   ┌─────────┐
         │ Billing  │   │ Technical │   │ Refund  │   specialist agents,
         │  Agent   │   │   Agent   │   │  Agent  │   each grounded in
         └────┬─────┘   └─────┬─────┘   └────┬────┘   its own mock data
              └──────────────┼──────────────┘
                             ▼
                    ┌─────────────────┐
                    │ Confidence Gate  │  pure logic, not an LLM call
                    └────────┬────────┘
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
         retry (×1)     auto-resolve    human handoff
```

- **Triage** classifies the ticket and hands off a confidence score of its own.
- **Specialist agents** (Billing, Technical, Refund) each look up real mock
  data before responding, so they can't invent account details.
- **Confidence gate** is deliberately *not* an LLM call - it's a policy check
  on the specialist's confidence and any tool errors, deciding retry vs.
  auto-resolve vs. escalate.
- **Retry logic** gives a failed lookup (e.g. account not found) one more
  attempt before giving up and escalating.
- **Human handoff** produces a clean summary of what was tried, for a real
  agent to pick up - not just a dumped error.

## A real failure I found and fixed

While testing, the Refund agent approved a $299.99 refund with 95%
self-reported confidence - even though the order data explicitly marked it
as **not eligible** for a refund. The model just didn't reliably follow the
policy instruction in its own prompt.

The fix wasn't a better prompt. It was **not trusting the LLM's self-reported
confidence for a policy decision at all**. The code now checks
`refund_eligible` directly and forces confidence down regardless of what the
model claims, which routes the ticket to a human instead of auto-approving
it. See `agents/refund.py`.

I found a related issue in the Billing agent: it would sometimes claim a
refund had "already been initiated," even though that agent only reads
data and has no tool that takes action. The prompt now explicitly forbids
claiming an action was taken - it can only describe what's in the data.

Both are small fixes, but the underlying lesson is the one worth keeping:
**an agent's own confidence score is not a reliable safety mechanism on its
own.** Deterministic checks in code are what make an orchestrated system
trustworthy enough to auto-resolve anything.

## Stack

| Layer | Tool |
|---|---|
| Orchestration | LangGraph |
| LLM inference | Groq (`openai/gpt-oss-20b`) |
| Tracing / observability | Langfuse |
| Backend | FastAPI |
| Frontend | Static HTML/JS (no build step) |
| Backend hosting | Render |
| Frontend hosting | Vercel |

## Project structure

```
support-orchestrator/
├── state.py               # Shared state schema for the graph
├── graph.py                # Graph wiring: nodes, conditional routing
├── main.py                  # FastAPI backend
├── tracing_setup.py          # Langfuse callback handler
├── agents/
│   ├── triage.py            # Classifies category + urgency
│   ├── billing.py           # Billing specialist (reads mock account data)
│   ├── technical.py         # Technical specialist (KB search)
│   ├── refund.py            # Refund specialist (policy + guardrail)
│   ├── confidence_gate.py   # Retry / escalate / resolve decision logic
│   └── terminal_nodes.py    # Auto-resolve + human handoff formatting
├── mock_data/                # Fake customers, orders, KB articles
├── frontend/
│   └── index.html            # Ticket submission UI + live pipeline trace
├── requirements.txt
└── .env.example
```

## Try it yourself

The live demo has four sample accounts wired to different outcomes, so you
can see all four paths through the graph without needing real data:

| Try this email | With a message about | You'll see |
|---|---|---|
| `sarah.chen@example.com` | a duplicate subscription charge | auto-resolved (billing) |
| a crashing app, no email needed | app crashing on startup | auto-resolved (technical) |
| `priya.nair@example.com` | a refund on an annual plan | escalated - the eligibility guardrail catches it |
| `unknown@example.com` | anything | retried once, then escalated - account not found |

## Running it locally

1. Clone the repo and create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and add your keys:
   - `GROQ_API_KEY` - free at console.groq.com
   - `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` / `LANGFUSE_BASE_URL` - free at cloud.langfuse.com (optional - the app runs fine without tracing if these are unset)

3. Run the graph directly against a few sample tickets:
   ```
   python graph.py
   ```

4. Or run the full app:
   ```
   uvicorn main:app --reload --port 8000
   ```
   Then serve `frontend/index.html` (e.g. `python -m http.server 5500` inside
   `frontend/`) and open it in your browser. Note: the deployed backend's
   CORS only allows the live Vercel URL and `localhost:5500` - update
   `ALLOWED_ORIGINS` in `main.py` if you're running against your own
   deployed backend from a different local setup.

## Possible next steps

- Swap the Technical agent's keyword search for real semantic search (FAISS,
  reusing the embeddings pipeline from an earlier project)
- Add an evaluation harness comparing the guardrail's decisions against a
  labeled test set
- Add parallel execution where agents don't depend on each other's output
