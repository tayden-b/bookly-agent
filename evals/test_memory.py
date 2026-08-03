"""Regression test for the history cap.

Unlike run_evals.py this makes no model calls, so it runs instantly and for free.

The bug it pins down: tool results are appended with role "user", same as real
customer messages. The old trim only checked the role, so once a long
conversation passed the cap it could leave a tool_result as the first message,
orphaned from the tool_use it answers. The API rejects that with a 400, which
surfaced as a 500.

Usage:  python evals/test_memory.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from memory import MAX_HISTORY_MESSAGES, Session  # noqa: E402

GREEN, RED, END = "\033[92m", "\033[91m", "\033[0m"


def build(tool_rounds_per_turn: list[int]) -> Session:
    """Replay a conversation shaped like a real one: a customer message, then
    N rounds of tool_use/tool_result, then the final text reply."""
    session = Session(session_id="test")
    for rounds in tool_rounds_per_turn:
        session.turn += 1
        session.add("user", "customer message")
        for i in range(rounds):
            call_id = f"tu{session.turn}_{i}"
            session.add("assistant", [{"type": "tool_use", "id": call_id, "name": "get_order", "input": {}}])
            session.add("user", [{"type": "tool_result", "tool_use_id": call_id, "content": "{}"}])
        session.add("assistant", [{"type": "text", "text": "reply"}])
    return session


def orphaned_tool_result(session: Session) -> str | None:
    """A tool_result whose tool_use is no longer in the history. The API 400s on this."""
    seen: set[str] = set()
    for message in session.history:
        content = message["content"]
        if not isinstance(content, list):
            continue
        for block in content:
            if block.get("type") == "tool_use":
                seen.add(block["id"])
            elif block.get("type") == "tool_result" and block["tool_use_id"] not in seen:
                return block["tool_use_id"]
    return None


def check(session: Session, label: str) -> bool:
    failures = []
    if len(session.history) > MAX_HISTORY_MESSAGES:
        failures.append(f"history is {len(session.history)}, over the {MAX_HISTORY_MESSAGES} cap")
    orphan = orphaned_tool_result(session)
    if orphan:
        failures.append(f"orphaned tool_result {orphan}, the API rejects this")
    if session.history:
        first = session.history[0]
        content = first["content"]
        is_tool_result = isinstance(content, list) and any(
            b.get("type") == "tool_result" for b in content
        )
        if first["role"] != "user" or is_tool_result:
            failures.append("history does not open on a real customer message")

    if failures:
        print(f"{RED}FAIL{END}  {label}")
        for f in failures:
            print(f"      - {f}")
        return False
    print(f"{GREEN}PASS{END}  {label}  (len={len(session.history)})")
    return True


def main() -> int:
    # Turn shapes taken from the real demo: a vague opener with no tools, a
    # lookup, a return with several tool rounds, a confirmation, and so on.
    shapes = [0, 1, 3, 1, 1, 2, 1, 1, 3, 1, 2, 2, 1, 3, 1]
    passed = 0
    total = 0
    for n in range(1, len(shapes) + 1):
        total += 1
        passed += check(build(shapes[:n]), f"{n} turn conversation")

    print(f"\n{passed}/{total} passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
