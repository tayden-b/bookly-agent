"""Conversation history for the platform views (Conversations, Home, Insights).

Two sources, merged everywhere they are read:
- Seeded workspace history from data/seed_conversations.json: illustrative
  volume so the dashboard reads like a live workspace. Timestamps are stored
  as offsets and resolved against the server clock at load.
- Live conversations recorded from the running agent, one record per session,
  updated turn by turn. These carry real traces from the orchestrator, which
  is the point: the audit log in the UI is the actual execution record.

Live records are in memory only, consistent with session memory itself. The
phase-two answer is the same as for sessions: Postgres.
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from schemas import ChatResponse

DATA_DIR = Path(__file__).parent / "data"

_seed = json.loads((DATA_DIR / "seed_conversations.json").read_text())
_LOADED_AT = datetime.now(timezone.utc)

SEED_TOTALS: dict[str, Any] = _seed["totals"]
CSAT_DISTRIBUTION: dict[str, int] = _seed["csat_distribution"]
CATEGORY_TOTALS: dict[str, int] = _seed["category_totals"]
DAILY_VOLUME: list[dict[str, int]] = _seed["daily_volume"]

SEED_CONVERSATIONS: list[dict[str, Any]] = []
for c in _seed["conversations"]:
    c = dict(c)
    c["at"] = (_LOADED_AT - timedelta(hours=c.pop("hours_ago"))).isoformat()
    c["source"] = "seed"
    SEED_CONVERSATIONS.append(c)

# session_id -> live conversation record
_LIVE: dict[str, dict[str, Any]] = {}


def _derive_tags(trace_labels: set[str]) -> list[str]:
    tags = []
    if {"check_return_eligibility", "create_return"} & trace_labels:
        tags.append("Returns & refunds")
    if {"lookup_orders", "get_order"} & trace_labels and not tags:
        tags.append("Order status")
    if "get_policy" in trace_labels:
        tags.append("Policy questions")
    return tags or ["Other"]


def record_turn(session_id: str, user_message: str, resp: ChatResponse) -> None:
    """Called once per chat turn. Never raises: recording is observability,
    and a bookkeeping bug must not take down the conversation itself."""
    try:
        conv = _LIVE.setdefault(session_id, {
            "id": f"live-{session_id[:8]}",
            "source": "live",
            "at": datetime.now(timezone.utc).isoformat(),
            "messages": [],
            "trace": [],
            "turns": 0,
            "csat": None,
            "summary": None,
            "resolution": None,
            "flags": [],
            "analyzed": False,
        })
        conv["turns"] += 1
        conv["updated_at"] = datetime.now(timezone.utc).isoformat()
        conv["messages"].append({"role": "user", "text": user_message})
        conv["messages"].append({"role": "agent", "text": resp.reply})
        for e in resp.trace:
            conv["trace"].append({
                "turn": conv["turns"], "kind": e.kind, "label": e.label, "detail": e.detail,
            })
        conv["analyzed"] = False  # new turns invalidate a previous watchtower pass
        labels = {e["label"].removesuffix(" ok") for e in conv["trace"]}
        conv["customer"] = resp.state.get("email", "visitor")
        conv["status"] = "escalated" if resp.state.get("escalated") else "deflected"
        conv["tags"] = _derive_tags(labels)
    except Exception:
        pass


def drop_live(session_id: str) -> None:
    _LIVE.pop(session_id, None)


def live_conversations() -> list[dict[str, Any]]:
    return sorted(_LIVE.values(), key=lambda c: c["at"], reverse=True)


def all_conversations() -> list[dict[str, Any]]:
    return live_conversations() + SEED_CONVERSATIONS


def get_conversation(conv_id: str) -> dict[str, Any] | None:
    for c in all_conversations():
        if c["id"] == conv_id:
            return c
    return None


def summaries() -> list[dict[str, Any]]:
    """List view: everything except the transcript and trace bodies."""
    out = []
    for c in all_conversations():
        out.append({
            "id": c["id"], "source": c["source"], "at": c["at"],
            "customer": c.get("customer", "visitor"),
            "status": c.get("status", "deflected"),
            "tags": c.get("tags", ["Other"]),
            "csat": c.get("csat"),
            "flag_count": len(c.get("flags", [])),
            "preview": next((m["text"] for m in c.get("messages", []) if m["role"] == "user"), ""),
        })
    return out


def metrics() -> dict[str, Any]:
    """Home dashboard aggregates: seeded history plus everything live."""
    live = live_conversations()
    live_total = len(live)
    live_deflected = sum(1 for c in live if c.get("status") != "escalated")
    total = SEED_TOTALS["conversations"] + live_total
    deflected = SEED_TOTALS["deflected"] + live_deflected

    daily = [dict(d) for d in DAILY_VOLUME]
    if daily and live_total:
        daily[-1]["total"] += live_total
        daily[-1]["deflected"] += live_deflected

    categories = dict(CATEGORY_TOTALS)
    for c in live:
        for t in c.get("tags", []):
            categories[t] = categories.get(t, 0) + 1

    gate_blocks = sum(
        1 for c in all_conversations()
        for e in c.get("trace", []) if e["kind"] == "gate_blocked"
    )

    return {
        "total_conversations": total,
        "deflection_rate": round(100 * deflected / total, 1),
        "escalations": total - deflected,
        "csat": SEED_TOTALS["csat"],
        "csat_distribution": CSAT_DISTRIBUTION,
        "daily_volume": daily,
        "categories": categories,
        "live_conversations": live_total,
        "gate_blocks_in_sample": gate_blocks,
        "window_days": len(daily),
    }
