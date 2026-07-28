"""The control layer. LLM handles language; this file (and tools.py) handle truth and action.

Per turn:
  1. Route intent (with confidence) — low confidence loads the "unknown"
     procedure, whose only move is to ask a clarifying question.
  2. Load the matching procedure (natural-language steps a CX person could edit).
  3. Run the agent loop: model -> tool requests -> Python executes -> repeat.
     Gates in tools.py can refuse; the refusal goes back to the model as a
     tool error to relay honestly, and is recorded in the trace.
"""
import json
from pathlib import Path
from typing import Any

import llm_client
import tools
from memory import Session, get_session
from schemas import ChatResponse, TraceEvent

PROCEDURES_DIR = Path(__file__).parent / "procedures"
CONFIDENCE_THRESHOLD = 0.7
MAX_LOOP_ITERATIONS = 8
STICKY_INTENTS = {"returns", "order_status"}  # mid-flow turns ("yes", "BK-1042") shouldn't re-route

# Least-privilege tool exposure: each procedure only sees the tools its job
# requires. The "unknown" procedure gets none — it can only ask a question.
PROCEDURE_TOOLS = {
    "order_status": {"lookup_orders", "get_order", "get_policy", "escalate"},
    "returns": {"lookup_orders", "get_order", "get_policy",
                "check_return_eligibility", "create_return", "escalate"},
    "policy_qa": {"get_policy", "escalate"},
    "unknown": set(),
}

BASE_SYSTEM = """You are the Bookly customer support agent, a friendly and precise \
assistant for an online bookstore. You follow the OPERATING PROCEDURE below exactly. \
Never invent order details, policies, or promises — everything customer-specific must \
come from a tool result. If a tool refuses an action, relay the refusal honestly and \
follow the procedure's fallback. Keep replies short and warm.

KNOWN SESSION FACTS (set by verified tool results, not by the conversation):
{slots}

OPERATING PROCEDURE
{procedure}"""


def _load_procedure(intent: str) -> str:
    return (PROCEDURES_DIR / f"{intent}.md").read_text()


def _serialize_content(content) -> list[dict[str, Any]]:
    """SDK content blocks -> plain dicts for the message history."""
    out = []
    for block in content:
        if block.type == "text":
            out.append({"type": "text", "text": block.text})
        elif block.type == "tool_use":
            out.append({"type": "tool_use", "id": block.id, "name": block.name, "input": block.input})
    return out


def handle_message(session_id: str, user_message: str) -> ChatResponse:
    session = get_session(session_id)
    trace: list[TraceEvent] = []
    session.add("user", user_message)

    # --- 1. Route ---------------------------------------------------------
    current = session.slots.get("intent")
    if current in STICKY_INTENTS and not session.slots.get("escalated"):
        intent = current
        trace.append(TraceEvent(kind="route", label=f"sticky intent: {intent}"))
    else:
        routed = llm_client.route(session.history[-6:])
        intent = routed["intent"] if routed["confidence"] >= CONFIDENCE_THRESHOLD else "unknown"
        trace.append(TraceEvent(
            kind="route",
            label=f"intent={routed['intent']} confidence={routed['confidence']:.2f} -> using '{intent}'",
            detail=routed,
        ))
    session.slots["intent"] = intent

    # --- 2. Procedure -----------------------------------------------------
    procedure = _load_procedure(intent)
    trace.append(TraceEvent(kind="procedure", label=f"loaded procedures/{intent}.md"))
    system = BASE_SYSTEM.format(
        slots=json.dumps(session.snapshot(), indent=2, default=str),
        procedure=procedure,
    )

    # --- 3. Agent loop ----------------------------------------------------
    allowed = PROCEDURE_TOOLS[intent]
    scoped_specs = [s for s in tools.TOOL_SPECS if s["name"] in allowed]
    if len(scoped_specs) < len(tools.TOOL_SPECS):
        trace.append(TraceEvent(
            kind="note",
            label=f"tool scope narrowed to: {sorted(allowed) or ['(none)']}",
        ))

    reply = ""
    for _ in range(MAX_LOOP_ITERATIONS):
        response = llm_client.complete(system, session.history, scoped_specs)
        session.add("assistant", _serialize_content(response.content))

        if response.stop_reason != "tool_use":
            reply = "".join(b.text for b in response.content if b.type == "text")
            break

        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            trace.append(TraceEvent(kind="tool_call", label=block.name, detail=dict(block.input)))
            try:
                result = tools.execute(session, block.name, block.input)
                kind = "escalation" if block.name == "escalate" else "tool_result"
                trace.append(TraceEvent(kind=kind, label=f"{block.name} ok", detail=result))
                content = json.dumps(result, default=str)
                is_error = False
            except tools.GateBlocked as gate:
                trace.append(TraceEvent(kind="gate_blocked", label=block.name, detail={"reason": str(gate)}))
                content = f"ACTION BLOCKED BY POLICY GATE: {gate}"
                is_error = True
            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": content,
                "is_error": is_error,
            })
        session.add("user", results)
    else:
        reply = "I'm having trouble completing that — let me hand you to a human specialist."
        trace.append(TraceEvent(kind="note", label="max loop iterations reached"))

    # Resolved flows shouldn't stay sticky.
    if session.slots.get("return_created") or session.slots.get("escalated"):
        session.slots.pop("intent", None)

    return ChatResponse(reply=reply, trace=trace, state=session.snapshot())
