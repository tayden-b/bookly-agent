"""FastAPI app: /api/chat + serves the built frontend (or a minimal fallback page)."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

import llm_client
import orchestrator
from memory import reset_session
from schemas import ChatRequest, ChatResponse

app = FastAPI(title="Bookly Support Agent")

FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    return orchestrator.handle_message(req.session_id, req.message)


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
