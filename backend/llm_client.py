"""Thin wrapper around the Anthropic SDK. No framework — the loop lives in orchestrator.py."""
import json
import os
from typing import Any

import anthropic
from dotenv import load_dotenv
from pathlib import Path

# Load the repo-root .env regardless of where the server was started from.
load_dotenv(Path(__file__).parent.parent / ".env")

MODEL = os.environ.get("BOOKLY_MODEL", "claude-sonnet-5")
_client: "anthropic.Anthropic | None" = None


def _get_client() -> anthropic.Anthropic:
    # Lazy init: the server can boot (and serve the UI) without a key;
    # a missing ANTHROPIC_API_KEY only surfaces on the first chat.
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def complete(system: str, messages: list[dict], tools: list[dict] | None = None):
    """One model call. Returns the raw response; orchestrator interprets it."""
    return _get_client().messages.create(
        model=MODEL,
        max_tokens=1024,
        system=system,
        messages=messages,
        tools=tools or [],
    )


ROUTER_SYSTEM = """You classify a customer-support message for an online bookstore.
Respond with ONLY a JSON object: {"intent": "...", "confidence": 0.0-1.0}
intent must be one of: "order_status", "returns", "policy_qa", "unknown".
Use "unknown" (or low confidence) when the message is ambiguous, off-topic,
or could match multiple intents. Do not guess."""


def route(recent_messages: list[dict]) -> dict[str, Any]:
    """Cheap intent classification over the recent conversation."""
    resp = _get_client().messages.create(
        model=MODEL,
        max_tokens=100,
        system=ROUTER_SYSTEM,
        messages=recent_messages,
    )
    text = "".join(b.text for b in resp.content if b.type == "text").strip()
    try:
        start, end = text.index("{"), text.rindex("}") + 1
        parsed = json.loads(text[start:end])
        intent = parsed.get("intent", "unknown")
        confidence = float(parsed.get("confidence", 0.0))
        if intent not in {"order_status", "returns", "policy_qa", "unknown"}:
            intent = "unknown"
        return {"intent": intent, "confidence": confidence}
    except (ValueError, json.JSONDecodeError):
        return {"intent": "unknown", "confidence": 0.0}
