"""The control layer. The LLM handles language; this file (and tools.py) handle
truth and action.

Per turn:
  1. Assemble the system prompt: fixed rules + verified session facts + the
     operating procedures (natural-language markdown a CX person could edit).
  2. Run the agent loop: model proposes a tool call -> Python executes it ->
     result goes back to the model -> repeat until it writes a customer reply.
  3. Gates in tools.py can refuse an action. A refusal is returned to the model
     as a tool error it must relay honestly, and is recorded in the trace.

Design note: guidance lives in the procedure text, which the model may interpret
loosely. Enforcement lives in tools.py, which the model cannot argue with.
"""
import json
from pathlib import Path
from typing import Any

import llm_client
import tools
from memory import Session, get_session
from schemas import ChatResponse, TraceEvent

PROCEDURES_DIR = Path(__file__).parent / "procedures"
MAX_LOOP_ITERATIONS = 8

# All procedures are shown to the model together. They total well under 1.5k
# tokens, so selecting one per turn would add a classification call and a
# misrouting failure mode without buying anything at this scale.
# Read fresh each turn (not once at import) so edits made through the
# procedures UI take effect on the customer's next message.
def load_procedures() -> str:
    return "\n\n---\n\n".join(
        p.read_text().strip() for p in sorted(PROCEDURES_DIR.glob("*.md"))
    )

BASE_SYSTEM = """You are the Bookly customer support agent, a friendly and precise \
assistant for an online bookstore. Follow the OPERATING PROCEDURES below exactly, \
using whichever one matches what the customer needs.

Core rules:
- Never invent order details, policies, or promises. Everything customer-specific \
must come from a tool result.
- If you are not sure what the customer needs, ask one short clarifying question. \
Do not guess and do not call tools on a guess.
- If a tool refuses an action, relay the refusal honestly and follow the \
procedure's fallback. Do not try to work around it.
- If the customer asks for something no procedure covers and no tool supports, \
such as cancelling an order, changing an address, or editing payment details, \
say plainly that you cannot do it yourself and offer to `escalate` to a human \
specialist. Never improvise a workaround, and never imply you have done \
something you have not.
- If the request has nothing to do with Bookly support, say what you can help \
with instead. Do not call a tool on it.
- Keep replies short and warm. Write plainly, and use commas or hyphens rather \
than dashes.

KNOWN SESSION FACTS (set by verified tool results, not by the conversation):
{slots}

OPERATING PROCEDURES
{procedures}"""


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
    session.turn += 1
    session.add("user", user_message)

    system = BASE_SYSTEM.format(
        slots=json.dumps(session.snapshot(), indent=2, default=str),
        procedures=load_procedures(),
    )

    reply = ""
    for _ in range(MAX_LOOP_ITERATIONS):
        response = llm_client.complete(system, session.history, tools.TOOL_SPECS)
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
        reply = "I'm having trouble completing that. Let me hand you to a human specialist."
        trace.append(TraceEvent(kind="note", label="max loop iterations reached"))

    # A turn that touches no tools would otherwise render as an empty trace,
    # which reads as a failure. Choosing not to act is a decision worth showing:
    # it is what a clarifying question looks like from the outside.
    if not any(e.kind == "tool_call" for e in trace):
        trace.insert(0, TraceEvent(
            kind="note",
            label="no tool calls this turn",
            detail={
                "reason": "the model asked a clarifying question or answered "
                          "from the conversation, so no tool was needed",
                "tools_available": len(tools.TOOL_SPECS),
            },
        ))

    return ChatResponse(reply=reply, trace=trace, state=session.snapshot())
