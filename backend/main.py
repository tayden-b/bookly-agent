"""FastAPI app: /api/chat + serves the built frontend (or a minimal fallback page)."""
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

import conversations
import llm_client
import orchestrator
import tools
import watchtower
from memory import get_session, reset_session
from schemas import ChatRequest, ChatResponse, ProcedureUpdate, TraceEvent, WatchtowerUpdate

log = logging.getLogger("bookly")

app = FastAPI(title="Bookly Support Agent")

FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"

# Originals captured at startup so a live edit is always one click from clean.
# Also acts as the whitelist: only files that existed at boot can be edited,
# so the write endpoint can never create files or touch anything else.
_ORIGINAL_PROCEDURES = {
    p.name: p.read_text() for p in sorted(orchestrator.PROCEDURES_DIR.glob("*.md"))
}


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    try:
        resp = orchestrator.handle_message(req.session_id, req.message)
        conversations.record_turn(req.session_id, req.message, resp)
        return resp
    except Exception:
        # Everything below the gates is unguarded: a rate limit or overload from
        # the model API, or a tool called with an argument it does not accept,
        # would otherwise reach the customer as a bare 500. Degrade to a reply
        # they can act on, and put it in the trace so it is not invisible.
        # Deliberately not caught here: GateBlocked, which the orchestrator
        # handles as a normal part of a turn rather than as a failure.
        log.exception("chat failed, session=%s", req.session_id)
        resp = ChatResponse(
            reply="Sorry, something went wrong on my end. Could you send that again?",
            trace=[TraceEvent(
                kind="note",
                label="request failed",
                detail={"handled": "returned a reply instead of a 500"},
            )],
            state=get_session(req.session_id).snapshot(),
        )
        conversations.record_turn(req.session_id, req.message, resp)
        return resp


@app.post("/api/reset/{session_id}")
def reset(session_id: str) -> dict:
    reset_session(session_id)
    return {"ok": True}


@app.get("/api/procedures")
def list_procedures() -> list[dict]:
    out = []
    for name, original in _ORIGINAL_PROCEDURES.items():
        content = (orchestrator.PROCEDURES_DIR / name).read_text()
        out.append({"name": name, "content": content, "modified": content != original})
    return out


@app.put("/api/procedures/{name}")
def update_procedure(name: str, req: ProcedureUpdate) -> dict:
    if name not in _ORIGINAL_PROCEDURES:
        raise HTTPException(404, f"unknown procedure: {name}")
    (orchestrator.PROCEDURES_DIR / name).write_text(req.content)
    return {"ok": True}


@app.post("/api/procedures/{name}/reset")
def reset_procedure(name: str) -> dict:
    if name not in _ORIGINAL_PROCEDURES:
        raise HTTPException(404, f"unknown procedure: {name}")
    original = _ORIGINAL_PROCEDURES[name]
    (orchestrator.PROCEDURES_DIR / name).write_text(original)
    return {"ok": True, "content": original}


# ------------------------------------------------ platform views
# Everything below is read-side plumbing for the admin UI (Home, Conversations,
# Watchtower, Insights, Build). None of it touches the agent's control path.

# Gate summaries surfaced on the Build > Tools page. Kept here rather than in
# tools.py so the enforcement code stays free of presentation concerns.
_TOOL_GATES = {
    "get_order": "Requires a verified customer identity. Blocked unless the order belongs to the customer set by a real lookup_orders result.",
    "check_return_eligibility": "Requires a verified customer identity for the order being checked.",
    "create_return": "Triple gated: a tool-written eligibility fact, a later turn than that check, and explicit customer confirmation.",
}


@app.get("/api/conversations")
def list_conversations() -> list[dict]:
    return conversations.summaries()


@app.get("/api/conversations/{conv_id}")
def get_conversation(conv_id: str) -> dict:
    conv = conversations.get_conversation(conv_id)
    if conv is None:
        raise HTTPException(404, f"unknown conversation: {conv_id}")
    return conv


@app.get("/api/metrics")
def metrics() -> dict:
    return conversations.metrics()


@app.get("/api/watchtower")
def watchtower_state() -> dict:
    return watchtower.state()


@app.put("/api/watchtower/{wt_id}")
def update_watchtower(wt_id: str, req: WatchtowerUpdate) -> dict:
    if watchtower.find(wt_id) is None:
        raise HTTPException(404, f"unknown watchtower: {wt_id}")
    watchtower.update_criteria(wt_id, req.criteria)
    return {"ok": True}


@app.post("/api/watchtower/{wt_id}/reset")
def reset_watchtower(wt_id: str) -> dict:
    if watchtower.find(wt_id) is None:
        raise HTTPException(404, f"unknown watchtower: {wt_id}")
    return {"ok": True, "criteria": watchtower.reset_criteria(wt_id)}


@app.post("/api/watchtower/run")
def run_watchtower() -> dict:
    return watchtower.run_scan()


@app.get("/api/knowledge")
def knowledge() -> list[dict]:
    out = []
    for path in sorted((tools.DATA_DIR / "policies").glob("*.md")):
        content = path.read_text()
        title = next(
            (l.removeprefix("# ").strip() for l in content.splitlines() if l.startswith("# ")),
            path.stem.replace("_", " ").title(),
        )
        out.append({"name": path.name, "title": title, "content": content})
    return out


@app.get("/api/tools")
def list_tools() -> list[dict]:
    return [
        {
            "name": spec["name"],
            "description": spec["description"],
            "params": [
                {"name": p, "type": s.get("type", "string"), "required": p in spec["input_schema"].get("required", [])}
                for p, s in spec["input_schema"].get("properties", {}).items()
            ],
            "gate": _TOOL_GATES.get(spec["name"]),
        }
        for spec in tools.TOOL_SPECS
    ]


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
