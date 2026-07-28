"""Behavioral eval runner: drives the real orchestrator over scripted
conversations and asserts on tool calls, gates, and slots - not wording.

Usage:  python evals/run_evals.py [case_name ...]
"""
import sys
import uuid
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import orchestrator  # noqa: E402
from memory import get_session, reset_session  # noqa: E402

GREEN, RED, DIM, END = "\033[92m", "\033[91m", "\033[2m", "\033[0m"


def run_case(case: dict) -> list[str]:
    """Returns a list of failure strings (empty = pass)."""
    session_id = f"eval-{uuid.uuid4().hex[:8]}"
    all_trace = []
    reply = ""
    for turn in case["turns"]:
        resp = orchestrator.handle_message(session_id, turn)
        all_trace.extend(resp.trace)
        reply = resp.reply

    session = get_session(session_id)
    executed = {t.label.removesuffix(" ok") for t in all_trace if t.kind in ("tool_result", "escalation")}
    blocked = {t.label for t in all_trace if t.kind == "gate_blocked"}
    kinds = {t.kind for t in all_trace}

    failures = []
    for key, expected in case["assert"].items():
        if key == "tool_called" and expected not in executed:
            failures.append(f"expected tool '{expected}' to execute; executed={sorted(executed)}")
        elif key == "tool_not_called" and expected in executed:
            failures.append(f"tool '{expected}' executed but must not")
        elif key == "gate_blocked" and expected not in blocked:
            failures.append(f"expected gate to block '{expected}'; blocked={sorted(blocked)}")
        elif key == "tool_not_called_or_gate_blocked":
            if expected in executed:
                failures.append(f"'{expected}' executed successfully but must not")
        elif key == "reply_has_question" and expected and "?" not in reply:
            failures.append(f"final reply asks no question: {reply[:120]!r}")
        elif key == "trace_has" and expected not in kinds:
            failures.append(f"trace missing event kind '{expected}'; kinds={sorted(kinds)}")
        elif key == "slot_set" and expected not in session.slots:
            failures.append(f"slot '{expected}' not set; slots={sorted(session.slots)}")
        elif key == "slot_absent" and expected in session.slots:
            failures.append(f"slot '{expected}' set but must not be")

    reset_session(session_id)
    return failures


def main() -> int:
    cases = yaml.safe_load((Path(__file__).parent / "cases.yaml").read_text())
    only = set(sys.argv[1:])
    if only:
        cases = [c for c in cases if c["name"] in only]

    passed = 0
    for case in cases:
        try:
            failures = run_case(case)
        except Exception as exc:  # a crash is a failure, not an excuse
            failures = [f"CRASHED: {type(exc).__name__}: {exc}"]
        if failures:
            print(f"{RED}FAIL{END}  {case['name']}")
            for f in failures:
                print(f"      {DIM}- {f}{END}")
        else:
            print(f"{GREEN}PASS{END}  {case['name']}")
            passed += 1

    total = len(cases)
    print(f"\n{passed}/{total} passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
