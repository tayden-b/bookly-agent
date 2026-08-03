"""FastAPI app: /api/chat + serves the built frontend (or a minimal fallback page)."""
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

import llm_client
import orchestrator
from memory import get_session, reset_session
from schemas import ChatRequest, ChatResponse, TraceEvent

log = logging.getLogger("bookly")

app = FastAPI(title="Bookly Support Agent")

FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    try:
        return orchestrator.handle_message(req.session_id, req.message)
    except Exception:
        # Everything below the gates is unguarded: a rate limit or overload from
        # the model API, or a tool called with an argument it does not accept,
        # would otherwise reach the customer as a bare 500. Degrade to a reply
        # they can act on, and put it in the trace so it is not invisible.
        # Deliberately not caught here: GateBlocked, which the orchestrator
        # handles as a normal part of a turn rather than as a failure.
        log.exception("chat failed, session=%s", req.session_id)
        return ChatResponse(
            reply="Sorry, something went wrong on my end. Could you send that again?",
            trace=[TraceEvent(
                kind="note",
                label="request failed",
                detail={"handled": "returned a reply instead of a 500"},
            )],
            state=get_session(req.session_id).snapshot(),
        )


@app.post("/api/reset/{session_id}")
def reset(session_id: str) -> dict:
    reset_session(session_id)
    return {"ok": True}


@app.get("/api/health")
def health() -> dict:
    """Cheap liveness check. Reports the model so a deploy can be verified
    without spending a request on the API."""
    return {"ok": True, "model": llm_client.MODEL}


if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
else:
    @app.get("/", response_class=HTMLResponse)
    def fallback() -> str:
        return """<!doctype html><meta charset='utf-8'><title>Bookly Agent</title>
<body style='font-family:system-ui;background:#0b1020;color:#e7ecff;display:grid;place-items:center;height:100vh'>
<div style='max-width:34rem'>
<h1>Bookly Support Agent</h1>
<p>Backend is running. The React frontend hasn't been built yet - run
<code>cd frontend && npm install && npm run build</code>, then restart.</p>
<p>Or try the API directly:</p>
<pre style='background:#161d35;padding:1rem;border-radius:8px;overflow:auto'>curl -s localhost:8000/api/chat -H 'content-type: application/json' \\
  -d '{"session_id":"demo","message":"Where is my order?"}'</pre>
</div></body>"""
