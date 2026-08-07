import { useEffect, useState } from "react";
import { getWatchtower, saveWatchtower, resetWatchtower, runWatchtower } from "../api.js";
import { timeAgo } from "./ConversationsPage.jsx";

function WatchtowerCard({ wt, onChanged, onOpenConversation }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(wt.criteria);
  const [error, setError] = useState(null);

  async function handleSave() {
    try {
      await saveWatchtower(wt.id, draft);
      setEditing(false);
      onChanged();
    } catch (e) {
      setError(e.message);
    }
  }

  async function handleReset() {
    try {
      await resetWatchtower(wt.id);
      setEditing(false);
      onChanged();
    } catch (e) {
      setError(e.message);
    }
  }

  return (
    <div className="card wt-card">
      <div className="card-head">
        <h2>{wt.name} {wt.modified && <span className="proc-flag">edited</span>}</h2>
        <div className="proc-actions">
          {!editing && (
            <button className="proc-btn" onClick={() => { setDraft(wt.criteria); setEditing(true); }}>
              Edit criteria
            </button>
          )}
          {wt.modified && !editing && (
            <button className="proc-btn subtle" onClick={handleReset}>Reset</button>
          )}
        </div>
      </div>

      <div className="wt-stats">
        <div><div className="mini-value">{wt.analyzed.toLocaleString()}</div><div className="mini-label">Conversations analyzed</div></div>
        <div><div className="mini-value">{wt.flagged_rate}%</div><div className="mini-label">Flagged rate</div></div>
        <div><div className="mini-value">{wt.flagged.toLocaleString()}</div><div className="mini-label">Flagged</div></div>
      </div>

      {editing ? (
        <div className="proc-editor">
          <textarea value={draft} onChange={(e) => setDraft(e.target.value)} spellCheck={false} rows={4} />
          <div className="proc-actions">
            <button className="proc-btn primary" onClick={handleSave}>Save</button>
            <button className="proc-btn subtle" onClick={() => setEditing(false)}>Cancel</button>
          </div>
          <p className="proc-hint">
            Plain English. Applied to every conversation the next time a scan runs.
          </p>
        </div>
      ) : (
        <p className="wt-criteria">{wt.criteria}</p>
      )}
      {error && <p className="proc-error">{error}</p>}

      {wt.examples.length > 0 && (
        <div className="wt-examples">
          <div className="side-label">Flagged conversations in the sample</div>
          {wt.examples.map((ex, i) => (
            <button key={i} className="wt-example" onClick={() => onOpenConversation(ex.conversation)}>
              <div className="wt-example-head">
                <span className="conv-customer">{ex.customer}</span>
                {ex.source === "live" && <span className="live-chip">live</span>}
                <span className="conv-time">{timeAgo(ex.at)}</span>
              </div>
              <p>{ex.reasoning}</p>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function WatchtowerPage({ onOpenConversation }) {
  const [state, setState] = useState(null);
  const [error, setError] = useState(null);
  const [running, setRunning] = useState(false);
  const [notice, setNotice] = useState(null);

  async function refresh() {
    try {
      setState(await getWatchtower());
      setError(null);
    } catch (e) {
      setError(e.message);
    }
  }

  useEffect(() => { refresh(); }, []);

  async function handleRun() {
    setRunning(true);
    setNotice(null);
    try {
      const result = await runWatchtower();
      const flags = result.new_flags.length;
      setNotice(
        result.scanned === 0
          ? "Nothing new to scan. Have a conversation in the Agent Preview first."
          : `Scanned ${result.scanned} conversation${result.scanned > 1 ? "s" : ""}, ${flags} new flag${flags === 1 ? "" : "s"}.`
      );
      await refresh();
    } catch (e) {
      setError(e.message);
    } finally {
      setRunning(false);
    }
  }

  if (error && !state) return <div className="page-pad"><p className="proc-error">{error}</p></div>;
  if (!state) return <div className="page-pad"><p className="proc-loading">Loading watchtowers...</p></div>;

  return (
    <div className="page-pad">
      <div className="page-head">
        <h1>Watchtower</h1>
        <button className="proc-btn primary" onClick={handleRun} disabled={running}>
          {running ? "Scanning..." : state.pending_live > 0
            ? `Scan ${state.pending_live} new conversation${state.pending_live > 1 ? "s" : ""}`
            : "Run scan"}
        </button>
      </div>
      <p className="page-sub">
        Always-on QA over every conversation. Each watchtower is a plain-English
        rule; the model reviews each conversation's transcript and execution trace
        against it and explains every flag. Live sessions from the Agent Preview
        are scanned on demand.
      </p>
      {notice && <div className="proc-notice">{notice}</div>}
      {error && <p className="proc-error">{error}</p>}
      {state.watchtowers.map((wt) => (
        <WatchtowerCard key={wt.id} wt={wt} onChanged={refresh} onOpenConversation={onOpenConversation} />
      ))}
    </div>
  );
}
