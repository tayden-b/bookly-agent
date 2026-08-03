"""Session memory.

Two kinds of state, deliberately separated:
- `history`: raw conversation messages (what was said) - capped.
- `slots`: structured facts the orchestrator has verified (what we KNOW).

Gates in tools.py read `slots`, never the transcript. The model can say
anything; only slots set by real tool results unlock actions.
"""
from dataclasses import dataclass, field
from typing import Any

MAX_HISTORY_MESSAGES = 30


def _is_customer_message(msg: dict[str, Any]) -> bool:
    """True for a real customer turn, false for a tool result.

    Tool results are appended with role "user" too, so role alone cannot tell
    them apart. A tool result is meaningless without the tool_use it answers,
    and the API rejects a history that opens on one, so it can never be first.
    """
    if msg["role"] != "user":
        return False
    content = msg["content"]
    if isinstance(content, list):
        return not any(b.get("type") == "tool_result" for b in content)
    return True


@dataclass
class Session:
    session_id: str
    turn: int = 0  # increments once per customer message; gates use this
    history: list[dict[str, Any]] = field(default_factory=list)
    slots: dict[str, Any] = field(default_factory=dict)

    def add(self, role: str, content: Any) -> None:
        self.history.append({"role": role, "content": content})
        if len(self.history) > MAX_HISTORY_MESSAGES:
            # Drop oldest turns; keep structure valid. The history must open on
            # a real customer message: cutting between a tool_use and its
            # tool_result leaves an orphan the API rejects with a 400.
            self.history = self.history[-MAX_HISTORY_MESSAGES:]
            while self.history and not _is_customer_message(self.history[0]):
                self.history.pop(0)

    def snapshot(self) -> dict[str, Any]:
        """Slots snapshot for the UI / trace. Never includes raw transcript."""
        return dict(self.slots)


_SESSIONS: dict[str, Session] = {}


def get_session(session_id: str) -> Session:
    if session_id not in _SESSIONS:
        _SESSIONS[session_id] = Session(session_id=session_id)
    return _SESSIONS[session_id]


def reset_session(session_id: str) -> None:
    _SESSIONS.pop(session_id, None)
