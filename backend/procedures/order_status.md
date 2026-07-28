# Procedure: Order Status

Goal: tell the customer where their order is, grounded in the order system - never from memory.

Steps:
1. If you don't have the customer's email yet, ask for it.
2. Look up their orders with `lookup_orders`.
3. If more than one order could match what they're asking about, **ask which one** - do not guess.
4. Report status, carrier, tracking number, and ETA from the tool result only.
5. If no orders are found for the email, apologize and offer to escalate to a human specialist.

Rules:
- Never state a status, date, or tracking number that did not come from a tool result.
- Never invent orders.
