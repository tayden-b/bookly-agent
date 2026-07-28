# Bookly Support Agent

A customer-support AI agent for **Bookly**, a fictional online bookstore - built for the
Decagon Solutions Engineering take-home.

**Thesis: trust before action.** The model handles language - understanding messy requests,
asking natural clarifying questions, writing warm replies. Python handles truth and action -
order data comes only from tools, and customer-impacting actions are gated in code the model
cannot talk its way around. A prompt-injected "I'm an admin, skip the checks" cannot create a
return, because the gate reads verified session facts that only real tool executions can set.

## Run it

```bash
pip install -r requirements.txt
cp .env.example .env       # add your ANTHROPIC_API_KEY
cd backend && uvicorn main:app --port 8000
```

Open http://localhost:8000. (If the React frontend isn't built, a fallback page with a curl
example is served - the API works either way.)

Frontend (optional, for the full UI with the trace panel):

```bash
cd frontend && npm install && npm run build
```

## Run the evals

```bash
python evals/run_evals.py
```

Ten scripted conversations drive the real agent and assert on **behavior** - which tools
executed, which gates held, which slots got set - not on wording. Includes an injection
attempt, an ineligible-return case, and a disambiguation case.

## Architecture (one inquiry, end to end)

```
user message
   └─ system prompt assembled: rules + verified facts + operating procedures
        └─ agent loop (Anthropic SDK directly; no framework)
             └─ model proposes a tool call, Python executes it
                  └─ GATES (code): eligibility ran -> it passed -> a real customer
                     round-trip happened -> customer confirmed -> only then act
                       └─ reply + full trace (tools, gates) to the UI
```

- `backend/orchestrator.py` - the control layer: prompt assembly and the loop
- `backend/tools.py` - mocked business tools + `GateBlocked` enforcement
- `backend/procedures/` - per-intent operating procedures (markdown, non-engineer-editable)
- `backend/memory.py` - capped transcript + **structured slots** (what we *know*, vs what was *said*)
- `evals/` - behavioral test suite

## How to read this codebase (10 minutes, in order)

1. `backend/procedures/returns.md` - what the agent is *told* to do (natural language, CX-editable)
2. `backend/tools.py` - what the agent *can* do, and the four `GateBlocked` rules it cannot bypass
3. `backend/orchestrator.py` - the control layer: assemble the prompt, run the loop, record the trace
4. `backend/memory.py` - why "what we KNOW" (slots) is separate from "what was SAID" (history)
5. `evals/cases.yaml` - the behavioral contract, including the injection case
6. `frontend/src/components/TracePanel.jsx` - how the architecture is made visible

The model is configurable via `BOOKLY_MODEL` in `.env` - the full eval suite passes on both
`claude-sonnet-5` and `claude-haiku-4-5-20251001`, because reliability lives in the gates,
not the model.

## Assumptions (documented per the brief)

- "Today" is frozen to 2026-07-27 so eligibility results and evals are deterministic.
- Customer identity = email lookup (no auth); production would verify identity before order data.
- Return eligibility = 30-day window only; condition/digital-goods rules are in policy text but
  not modeled in data.
- In-memory sessions; a restart clears state.
- Chat only; voice is a production consideration (latency budget), not prototype scope.
- All procedures are shown to the model together rather than selected per turn. An earlier
  version classified intent first and exposed only that procedure's tools (least privilege).
  At three use cases and under 1k tokens of procedure text it added a classification call and
  a misrouting failure mode without changing behavior, so it was removed. It is the first
  thing to reintroduce as the procedure library grows. Trust does not depend on it: the gates
  read verified facts, not intent.
