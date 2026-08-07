import { useEffect, useState } from "react";
import { getConversations, getConversation } from "../api.js";

export function timeAgo(iso) {
  const mins = Math.max(Math.round((Date.now() - new Date(iso).getTime()) / 60000), 0);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

const KIND_LABEL = {
  tool_call: "Tool call",
  tool_result: "Tool result",
  gate_blocked: "Gate blocked",
  escalation: "Escalation",
  note: "Note",
};

function AuditEvent({ event }) {
  return (
    <div className={`event ${event.kind}`}>
      <div className="event-head">
        <span className="event-kind">{KIND_LABEL[event.kind] ?? "Note"}</span>
        <span className="event-label">{event.label}</span>
      </div>
      {event.detail && (
        <details>
          <summary>payload</summary>
          <pre>{JSON.stringify(event.detail, null, 2)}</pre>
        </details>
      )}
    </div>
  );
}

function Detail({ conv, onBack }) {
  const grouped = [];
  for (const e of conv.trace ?? []) {
    const last = grouped.at(-1);
    if (last && last.turn === (e.turn ?? 1)) last.events.push(e);
    else grouped.push({ turn: e.turn ?? 1, events: [e] });
  }

  return (
    <div className="conv-detail">
      <div className="conv-transcript">
        <div className="conv-detail-head">
          <button className="proc-back" onClick={onBack}>&larr; All conversations</button>
          <span className="conv-customer">{conv.customer ?? "visitor"}</span>
        </div>
        <div className="conv-messages">
          {(conv.messages ?? []).map((m, i) => (
            <div key={i} className={`conv-bubble ${m.role}`}>{m.text}</div>
          ))}
        </div>
      </div>
      <aside className="conv-side">
        <h3>Overview</h3>
        {conv.summary && (
          <>
            <div className="side-label">Summary</div>
            <p className="side-text">{conv.summary}</p>
          </>
        )}
        {conv.resolution && (
          <>
            <div className="side-label">Resolution</div>
            <p className="side-text">{conv.resolution}</p>
          </>
        )}
        {!conv.summary && (
          <p className="side-text">
            Live conversation from the Agent Preview. The audit log below is the
            real execution record for this session.
          </p>
        )}
        <div className="side-label">Tags</div>
        <div className="tag-row">
          <span className={`status-chip ${conv.status}`}>{conv.status}</span>
          {(conv.tags ?? []).map((t) => <span key={t} className="tag-chip">{t}</span>)}
        </div>
        {conv.csat != null && (
          <>
            <div className="side-label">CSAT</div>
            <p className="side-text">{"★".repeat(conv.csat)}{"☆".repeat(5 - conv.csat)} ({conv.csat}/5)</p>
          </>
        )}
        {(conv.flags ?? []).length > 0 && (
          <>
            <div className="side-label">Watchtower flags</div>
            {conv.flags.map((f, i) => (
              <div key={i} className="flag-note">
                <span className="flag-name">{f.watchtower.replaceAll("-", " ")}</span>
                <p>{f.reasoning}</p>
              </div>
            ))}
          </>
        )}
        <h3 className="audit-title">Audit log</h3>
        <p className="trace-hint">Every tool call, result, and gate decision behind this conversation.</p>
        {grouped.length === 0 && <p className="trace-empty">No tool activity recorded.</p>}
        {grouped.map((g) => (
          <div key={g.turn} className="turn">
            <div className="turn-label">Turn {g.turn}</div>
            {g.events.map((e, i) => <AuditEvent key={i} event={e} />)}
          </div>
        ))}
      </aside>
    </div>
  );
}

export default function ConversationsPage({ filterTag, onClearFilter, focusId, onFocusHandled }) {
  const [list, setList] = useState(null);
  const [error, setError] = useState(null);
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(null);

  useEffect(() => {
    getConversations().then(setList).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    if (!focusId) return;
    getConversation(focusId).then(setOpen).catch((e) => setError(e.message));
    onFocusHandled?.();
  }, [focusId]);

  if (error) return <div className="page-pad"><p className="proc-error">{error}</p></div>;
  if (!list) return <div className="page-pad"><p className="proc-loading">Loading conversations...</p></div>;

  if (open) return <div className="page-pad wide"><Detail conv={open} onBack={() => setOpen(null)} /></div>;

  const q = query.trim().toLowerCase();
  const shown = list.filter((c) => {
    if (filterTag && !c.tags.includes(filterTag)) return false;
    if (!q) return true;
    return (
      c.customer.toLowerCase().includes(q) ||
      c.preview.toLowerCase().includes(q) ||
      c.tags.some((t) => t.toLowerCase().includes(q))
    );
  });

  return (
    <div className="page-pad">
      <div className="page-head">
        <h1>Conversations</h1>
        <span className="page-note">
          Showing {shown.length} recent in full. Aggregates on Home cover the whole 30 day window.
        </span>
      </div>
      <div className="conv-toolbar">
        <input
          className="conv-search"
          placeholder="Search by customer, text, or tag"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        {filterTag && (
          <button className="filter-chip" onClick={onClearFilter}>
            {filterTag} &times;
          </button>
        )}
      </div>
      <div className="conv-list">
        {shown.map((c) => (
          <button
            key={c.id}
            className="conv-row"
            onClick={() => getConversation(c.id).then(setOpen).catch((e) => setError(e.message))}
          >
            <div className="conv-row-main">
              <span className="conv-customer">{c.customer}</span>
              <span className="conv-preview">{c.preview}</span>
            </div>
            <div className="conv-row-meta">
              {c.source === "live" && <span className="live-chip">live</span>}
              {c.flag_count > 0 && <span className="flag-chip">{c.flag_count} flag{c.flag_count > 1 ? "s" : ""}</span>}
              <span className={`status-chip ${c.status}`}>{c.status}</span>
              {c.tags.slice(0, 2).map((t) => <span key={t} className="tag-chip">{t}</span>)}
              <span className="conv-time">{timeAgo(c.at)}</span>
            </div>
          </button>
        ))}
        {shown.length === 0 && <p className="trace-empty">No conversations match.</p>}
      </div>
    </div>
  );
}
