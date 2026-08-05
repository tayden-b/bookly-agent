const KIND_LABEL = {
  tool_call: "Tool call",
  tool_result: "Tool result",
  gate_blocked: "Gate blocked",
  escalation: "Escalation",
  note: "Note",
};

function Event({ event }) {
  return (
    <div className={`event ${event.kind}`}>
      <div className="event-head">
        <span className="event-kind">{KIND_LABEL[event.kind] ?? "Note"}</span>
        <span className="event-label">{event.label}</span>
      </div>
      {event.detail && (
        <details>
          <summary>detail</summary>
          <pre>{JSON.stringify(event.detail, null, 2)}</pre>
        </details>
      )}
    </div>
  );
}

export default function TracePanel({ turns, open = true, onToggle }) {
  const latestState = turns.at(-1)?.state ?? {};
  if (!open) {
    return (
      <aside className="trace rail">
        <button className="trace-toggle" onClick={onToggle} title="Show the trace panel">
          &#9666;
        </button>
        <span className="rail-label">Behind the scenes</span>
      </aside>
    );
  }
  return (
    <aside className="trace">
      <div className="trace-head">
        <h2>Behind the scenes</h2>
        {onToggle && (
          <button className="trace-toggle" onClick={onToggle} title="Hide the trace panel">
            &#9656;
          </button>
        )}
      </div>
      <p className="trace-badge">Internal view, not shown to the customer</p>
      <p className="trace-hint">
        Every turn: which tools the agent called, what they returned, and where a
        code-level gate refused to act. In production this goes to the agent
        console and analytics, not to the chat widget.
      </p>
      {turns.length === 0 && <p className="trace-empty">Send a message to see the trace.</p>}
      {turns.map((turn, i) => (
        <div key={i} className="turn">
          <div className="turn-label">Turn {i + 1}</div>
          {turn.trace.map((event, j) => (
            <Event key={j} event={event} />
          ))}
        </div>
      ))}
      {Object.keys(latestState).length > 0 && (
        <div className="state">
          <h3>Verified session facts</h3>
          <p className="trace-hint">Set only by real tool executions - gates read these, never the transcript.</p>
          <pre>{JSON.stringify(latestState, null, 2)}</pre>
        </div>
      )}
    </aside>
  );
}
