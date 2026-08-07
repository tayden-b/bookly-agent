"""Watchtower: always-on QA over conversations, defined in plain English.

Same philosophy as the procedures: the criteria are natural language a CX
person can edit, and the enforcement is code. Each scan sends a conversation's
transcript and execution trace to the model once, asking for a verdict per
watchtower with reasoning. Seeded history ships with precomputed flags; live
conversations are scanned on demand from the UI.
"""
import json
import logging
from pathlib import Path
from typing import Any

import conversations
import llm_client

log = logging.getLogger("bookly")

WATCHTOWERS_FILE = Path(__file__).parent / "data" / "watchtowers.json"

_DEFS: list[dict[str, Any]] = json.loads(WATCHTOWERS_FILE.read_text())
# Boot copy so an edit is always one click from clean, same as procedures.
_ORIGINALS: dict[str, str] = {w["id"]: w["criteria"] for w in _DEFS}

# Live-scan tallies per watchtower id.
_live_analyzed: dict[str, int] = {w["id"]: 0 for w in _DEFS}
_live_flagged: dict[str, int] = {w["id"]: 0 for w in _DEFS}

MAX_SCAN_BATCH = 6  # one model call per conversation, keep the button snappy

_SCAN_SYSTEM = """You are a QA reviewer for Bookly customer support conversations. \
You are given one conversation transcript plus the agent's execution trace \
(tool calls, tool results, and policy gate refusals).

Evaluate it against each watchtower below and reply with ONLY a JSON array, \
one object per watchtower: {{"id": "<watchtower id>", "flagged": true|false, \
"reasoning": "<one or two sentences>"}}. Reasoning is required for every \
verdict, flagged or not. No text outside the JSON.

WATCHTOWERS
{watchtowers}"""


def defs() -> list[dict[str, Any]]:
    return _DEFS


def find(wt_id: str) -> dict[str, Any] | None:
    return next((w for w in _DEFS if w["id"] == wt_id), None)


def update_criteria(wt_id: str, criteria: str) -> None:
    wt = find(wt_id)
    wt["criteria"] = criteria
    WATCHTOWERS_FILE.write_text(json.dumps(_DEFS, indent=2))
    # Changed criteria means previous live verdicts no longer apply.
    _invalidate_live()


def reset_criteria(wt_id: str) -> str:
    original = _ORIGINALS[wt_id]
    update_criteria(wt_id, original)
    return original


def _invalidate_live() -> None:
    for conv in conversations.live_conversations():
        conv["analyzed"] = False
        conv["flags"] = [f for f in conv["flags"] if f.get("source") != "scan"]
    for wt_id in _live_analyzed:
        _live_analyzed[wt_id] = 0
        _live_flagged[wt_id] = 0


def _conversation_document(conv: dict[str, Any]) -> str:
    lines = ["TRANSCRIPT"]
    for m in conv.get("messages", []):
        who = "Customer" if m["role"] == "user" else "Agent"
        lines.append(f"{who}: {m['text']}")
    lines.append("\nEXECUTION TRACE")
    for e in conv.get("trace", []):
        detail = json.dumps(e.get("detail")) if e.get("detail") else ""
        lines.append(f"[{e['kind']}] {e['label']} {detail}".strip())
    return "\n".join(lines)


def _scan_one(conv: dict[str, Any]) -> list[dict[str, Any]]:
    system = _SCAN_SYSTEM.format(watchtowers=json.dumps(
        [{"id": w["id"], "name": w["name"], "criteria": w["criteria"]} for w in _DEFS],
        indent=2,
    ))
    response = llm_client.complete(
        system, [{"role": "user", "content": _conversation_document(conv)}]
    )
    text = "".join(b.text for b in response.content if b.type == "text").strip()
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    verdicts = json.loads(text)
    known = {w["id"] for w in _DEFS}
    return [v for v in verdicts if isinstance(v, dict) and v.get("id") in known]


def run_scan() -> dict[str, Any]:
    """Scan unanalyzed live conversations. Returns what was scanned and found."""
    pending = [c for c in conversations.live_conversations() if not c["analyzed"]]
    scanned, new_flags, errors = 0, [], 0
    for conv in pending[:MAX_SCAN_BATCH]:
        try:
            verdicts = _scan_one(conv)
        except Exception:
            log.exception("watchtower scan failed for %s", conv["id"])
            errors += 1
            continue
        conv["flags"] = [f for f in conv["flags"] if f.get("source") != "scan"]
        for v in verdicts:
            _live_analyzed[v["id"]] += 1
            if v.get("flagged"):
                _live_flagged[v["id"]] += 1
                flag = {
                    "watchtower": v["id"],
                    "reasoning": str(v.get("reasoning", "")),
                    "source": "scan",
                }
                conv["flags"].append(flag)
                new_flags.append({"conversation": conv["id"], **flag})
        conv["analyzed"] = True
        scanned += 1
    return {
        "scanned": scanned,
        "pending": max(len(pending) - scanned, 0),
        "errors": errors,
        "new_flags": new_flags,
    }


def state() -> dict[str, Any]:
    """Everything the Watchtower page renders."""
    flagged_examples: dict[str, list[dict[str, Any]]] = {w["id"]: [] for w in _DEFS}
    for conv in conversations.all_conversations():
        for f in conv.get("flags", []):
            wt_id = f.get("watchtower")
            if wt_id in flagged_examples:
                flagged_examples[wt_id].append({
                    "conversation": conv["id"],
                    "customer": conv.get("customer", "visitor"),
                    "at": conv["at"],
                    "source": conv["source"],
                    "reasoning": f.get("reasoning", ""),
                })
    out = []
    for w in _DEFS:
        analyzed = w["analyzed"] + _live_analyzed[w["id"]]
        flagged = w["flagged"] + _live_flagged[w["id"]]
        out.append({
            "id": w["id"],
            "name": w["name"],
            "criteria": w["criteria"],
            "modified": w["criteria"] != _ORIGINALS[w["id"]],
            "analyzed": analyzed,
            "flagged": flagged,
            "flagged_rate": round(100 * flagged / analyzed, 1) if analyzed else 0.0,
            "examples": flagged_examples[w["id"]],
        })
    pending = sum(1 for c in conversations.live_conversations() if not c["analyzed"])
    return {"watchtowers": out, "pending_live": pending}
