"""Pydantic schemas for the API boundary and trace events."""
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=64)
    message: str = Field(min_length=1, max_length=4000)


class ProcedureUpdate(BaseModel):
    content: str = Field(min_length=1, max_length=8000)


class WatchtowerUpdate(BaseModel):
    criteria: str = Field(min_length=1, max_length=2000)


class TraceEvent(BaseModel):
    kind: Literal[
        "tool_call",    # tool requested by the model
        "tool_result",  # tool executed successfully
        "gate_blocked", # a code-level gate refused an action
        "escalation",   # handoff to a human was created
        "note",
    ]
    label: str
    detail: Optional[dict[str, Any]] = None


class ChatResponse(BaseModel):
    reply: str
    trace: list[TraceEvent]
    state: dict[str, Any]  # snapshot of structured slots, for the UI
