"""Session memory.

Two kinds of state, deliberately separated:
- `history`: raw conversation messages (what was said) — capped.
- `slots`: structured facts the orchestrator has verified (what we KNOW).

Gates in tools.py read `slots`, never the transcript. The model can say
anything; only slots set by real tool results unlock actions.
"""
from dataclasses import dataclass, field
from typing import Any

MAX_HISTORY_MESSAGES = 30


@dataclass
class Session:
    session_id: str
    history: list[dict[str, Any]] = field(default_factory=list)
    slots: dict[str, Any] = field(default_factory=dict)

    def add(self, role: str, content: Any) -> None:
        self.history.append({"role": role, "content": content})
        if len(self.history) > MAX_HISTORY_MESSAGES:
            # Drop oldest turns; keep structure valid (must start with a user msg).
            self.history = self.history[-MAX_HISTORY_MESSAGES:]
            while self.history and self.history[0]["role"] != "user":
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
