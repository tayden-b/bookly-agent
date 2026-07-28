"""Bookly business tools (mocked) + code-enforced gates.

The core design rule: the LLM proposes, Python disposes. Customer-impacting
actions (create_return) are gated on facts in session slots that ONLY real
tool executions can set. A prompt cannot set them, so a prompt cannot bypass
them.
"""
import json
from datetime import date
from pathlib import Path
from typing import Any

from memory import Session

DATA_DIR = Path(__file__).parent / "data"
RETURN_WINDOW_DAYS = 30
# Frozen "today" so the demo and evals are deterministic.
TODAY = date(2026, 7, 27)


class GateBlocked(Exception):
    """Raised when a code-level gate refuses an action the model requested."""


def _load_orders() -> dict[str, Any]:
    return json.loads((DATA_DIR / "orders.json").read_text())


# ---------------------------------------------------------------- tools

def lookup_orders(session: Session, email: str) -> dict[str, Any]:
    email = email.strip().lower()
    for customer in _load_orders()["customers"]:
        if customer["email"] == email:
            session.slots["email"] = email
            session.slots["customer_name"] = customer["name"]
            orders = [
                {k: o[k] for k in ("order_id", "placed", "status", "eta")}
                | {"items": [i["title"] for i in o["items"]]}
                for o in customer["orders"]
            ]
            return {"found": True, "orders": orders}
    return {"found": False, "orders": []}


def get_order(session: Session, order_id: str) -> dict[str, Any]:
    for customer in _load_orders()["customers"]:
        for order in customer["orders"]:
            if order["order_id"] == order_id:
                session.slots["order_id"] = order_id
                return {"found": True, "order": order}
    return {"found": False}


def get_policy(session: Session, topic: str) -> dict[str, Any]:
    path = DATA_DIR / "policies" / f"{topic}.md"
    if not path.exists():
        return {"found": False, "available": ["shipping", "returns", "refunds"]}
    return {"found": True, "policy": path.read_text()}


def check_return_eligibility(session: Session, order_id: str, item_id: str) -> dict[str, Any]:
    result = get_order(session, order_id)
    if not result["found"]:
        return {"eligible": False, "reason": "order_not_found"}
    order = result["order"]
    if item_id not in {i["item_id"] for i in order["items"]}:
        return {"eligible": False, "reason": "item_not_in_order"}

    age_days = (TODAY - date.fromisoformat(order["placed"])).days
    eligible = age_days <= RETURN_WINDOW_DAYS
    verdict = {
        "eligible": eligible,
        "order_age_days": age_days,
        "window_days": RETURN_WINDOW_DAYS,
        "reason": "within_window" if eligible else "outside_30_day_window",
    }
    # THE GATE FACT: only this real execution can set it. Not the model.
    # `turn` is recorded so create_return can require a real customer round-trip.
    session.slots["eligibility"] = {
        "order_id": order_id, "item_id": item_id, "turn": session.turn, **verdict
    }
    return verdict


def create_return(
    session: Session, order_id: str, item_id: str, reason: str, confirmed: bool = False
) -> dict[str, Any]:
    elig = session.slots.get("eligibility")
    if not elig or elig["order_id"] != order_id or elig["item_id"] != item_id:
        raise GateBlocked(
            "Return refused: eligibility has not been checked for this order/item "
            "in this session. Run check_return_eligibility first."
        )
    if not elig["eligible"]:
        raise GateBlocked(
            f"Return refused: item is not eligible ({elig['reason']}). "
            "Offer escalation to a human specialist instead."
        )
    # Structural consent check. `confirmed` is asserted by the model, so on its own
    # it can be short-circuited: the model can check eligibility and claim consent in
    # the same turn, before the customer has been told the refund terms. Requiring a
    # later turn forces a real round-trip. The model cannot fabricate a customer turn.
    if session.turn <= elig["turn"]:
        raise GateBlocked(
            "Return refused: eligibility was established during this same turn, so the "
            "customer has not been told the terms and asked yet. Summarize the refund "
            "terms, ask them to confirm, and create the return after they reply."
        )
    if not confirmed:
        raise GateBlocked(
            "Return refused: the customer has not explicitly confirmed. "
            "Ask for confirmation, then retry with confirmed=true."
        )
    rma = f"RMA-{order_id}-{item_id}"
    session.slots["return_created"] = rma
    return {
        "created": True,
        "rma": rma,
        "refund": "original payment method, 5-7 business days after warehouse receipt",
    }


def escalate(session: Session, reason: str, summary: str) -> dict[str, Any]:
    ticket = f"ESC-{session.session_id[:6].upper()}"
    session.slots["escalated"] = {"ticket": ticket, "reason": reason}
    return {
        "ticket": ticket,
        "handoff_summary": summary,
        "sla": "a human specialist will reply within 4 business hours",
    }


# ------------------------------------------------- registry & dispatch

TOOL_FUNCTIONS = {
    "lookup_orders": lookup_orders,
    "get_order": get_order,
    "get_policy": get_policy,
    "check_return_eligibility": check_return_eligibility,
    "create_return": create_return,
    "escalate": escalate,
}

TOOL_SPECS = [
    {
        "name": "lookup_orders",
        "description": "Look up all orders for a customer by email address.",
        "input_schema": {
            "type": "object",
            "properties": {"email": {"type": "string"}},
            "required": ["email"],
        },
    },
    {
        "name": "get_order",
        "description": "Fetch full detail for one order (status, carrier, tracking, ETA, items).",
        "input_schema": {
            "type": "object",
            "properties": {"order_id": {"type": "string"}},
            "required": ["order_id"],
        },
    },
    {
        "name": "get_policy",
        "description": "Fetch a Bookly policy document. Topics: shipping, returns, refunds.",
        "input_schema": {
            "type": "object",
            "properties": {"topic": {"type": "string", "enum": ["shipping", "returns", "refunds"]}},
            "required": ["topic"],
        },
    },
    {
        "name": "check_return_eligibility",
        "description": "Check whether an item on an order is eligible for return. MUST be run before create_return.",
        "input_schema": {
            "type": "object",
            "properties": {"order_id": {"type": "string"}, "item_id": {"type": "string"}},
            "required": ["order_id", "item_id"],
        },
    },
    {
        "name": "create_return",
        "description": "Create a return (RMA). Requires prior eligibility check AND explicit customer confirmation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string"},
                "item_id": {"type": "string"},
                "reason": {"type": "string"},
                "confirmed": {"type": "boolean", "description": "true only after the customer explicitly confirms"},
            },
            "required": ["order_id", "item_id", "reason", "confirmed"],
        },
    },
    {
        "name": "escalate",
        "description": "Hand off to a human specialist with a structured summary of the conversation so far.",
        "input_schema": {
            "type": "object",
            "properties": {"reason": {"type": "string"}, "summary": {"type": "string"}},
            "required": ["reason", "summary"],
        },
    },
]


def execute(session: Session, name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Dispatch a model-requested tool call. Raises GateBlocked when a gate refuses."""
    fn = TOOL_FUNCTIONS.get(name)
    if fn is None:
        return {"error": f"unknown tool: {name}"}
    return fn(session, **args)
