# AI Customer Support Orchestrator

An agentic orchestration system that triages incoming support tickets and
routes them to specialist agents (Billing, Technical, Refund), escalating
to a human when confidence is low.

## Status: Step 1 — Triage node only

This is the first working slice: a single LangGraph node that classifies
a ticket. Specialist agents, conditional routing, retries, and the
confidence gate come in later steps.

## Setup

1. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env` and fill in your Groq API key:
   ```
   cp .env.example .env
   ```
   Get a free key at https://console.groq.com

4. Run the test graph:
   ```
   python graph.py
   ```

   You should see the triage classification printed for a sample ticket.

## Project structure

```
support-orchestrator/
├── state.py           # Shared state schema for the graph
├── graph.py            # Graph wiring (entry point, edges)
├── agents/
│   └── triage.py       # Triage node (classifies tickets)
├── mock_data/           # (coming in step 3) mock billing/order data
├── requirements.txt
└── .env.example
```

## Next steps

- [ ] Add Billing specialist agent + mock billing dataset
- [ ] Add conditional routing based on triage category
- [ ] Add Technical + Refund agents
- [ ] Add confidence gate (auto-resolve vs. human handoff)
- [ ] Add retry logic for failed tool calls
- [ ] Add Langfuse tracing
- [ ] Add FastAPI backend + simple frontend trace viewer
