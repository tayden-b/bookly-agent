"""Thin wrapper around the Anthropic SDK. No framework - the loop lives in orchestrator.py."""
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
