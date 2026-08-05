import { useEffect, useState } from "react";
import { getProcedures, saveProcedure, resetProcedure } from "../api.js";

// Tool names the agent can call. Rendered as chips wherever a procedure
// references them with an @, mirroring how AOP editors highlight actions.
const TOOL_PATTERN = /(@[a-z_]+)/g;

// Display order: the main workflows first, escalation last since the others
// hand off to it. Files sort alphabetically by default, which buries returns.
const DISPLAY_ORDER = ["returns.md", "order_status.md", "policy_qa.md", "escalation.md"];
const rank = (name) => {
  const i = DISPLAY_ORDER.indexOf(name);
  return i === -1 ? DISPLAY_ORDER.length : i;
};

// Build React elements from one line of procedure markdown. No innerHTML.
function renderInline(text, keyBase) {
  const parts = [];
  // split on bold first, then tools inside each fragment
  text.split(/(\*\*[^*]+\*\*)/g).forEach((chunk, i) => {
    if (chunk.startsWith("**") && chunk.endsWith("**")) {
      parts.push(<strong key={`${keyBase}-b${i}`}>{renderTools(chunk.slice(2, -2), `${keyBase}-b${i}`)}</strong>);
    } else {
      parts.push(...renderTools(chunk, `${keyBase}-t${i}`));
    }
  });
  return parts;
}

function renderTools(text, keyBase) {
  return text.split(TOOL_PATTERN).map((chunk, i) =>
    chunk.startsWith("@")
      ? <span key={`${keyBase}-${i}`} className="tool-chip">{chunk.slice(1)}</span>
      : chunk
  );
}

function titleOf(proc) {
  const line = proc.content.split("\n").find((l) => l.startsWith("# "));
  return line ? line.slice(2) : proc.name;
}

function whenToUseOf(proc) {
  const line = proc.content.split("\n").find((l) => l.startsWith("**When to use:**"));
  return line ? line.replace("**When to use:**", "").trim() : "";
}

function ProcedureBody({ content }) {
  const lines = content.split("\n");
  return (
    <div className="proc-body">
      {lines.map((line, i) => {
        if (line.startsWith("# ") || line.startsWith("**When to use:**")) return null;
        const numbered = line.match(/^(\d+)\.\s+(.*)/);
        if (numbered) {
          return (
            <div key={i} className="proc-step">
              <span className="proc-step-n">{numbered[1]}</span>
              <span>{renderInline(numbered[2], i)}</span>
            </div>
          );
        }
        if (line.startsWith("- ")) {
          return <div key={i} className="proc-bullet">{renderInline(line.slice(2), i)}</div>;
        }
        if (line.trim() === "") return <div key={i} className="proc-gap" />;
        return <p key={i} className="proc-para">{renderInline(line, i)}</p>;
      })}
    </div>
  );
}

export default function ProceduresPanel() {
  const [procs, setProcs] = useState(null);
  const [openName, setOpenName] = useState(null);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [notice, setNotice] = useState(null);
  const [error, setError] = useState(null);

  async function refresh() {
    try {
      const list = await getProcedures();
      list.sort((a, b) => rank(a.name) - rank(b.name));
      setProcs(list);
      setError(null);
    } catch (e) {
      setError(e.message);
    }
  }

  useEffect(() => { refresh(); }, []);

  const open = procs?.find((p) => p.name === openName);

  async function handleSave() {
    try {
      await saveProcedure(open.name, draft);
      setEditing(false);
      setNotice("Saved. Live on the agent's next message.");
      await refresh();
      setTimeout(() => setNotice(null), 4000);
    } catch (e) {
      setError(e.message);
    }
  }

  async function handleReset() {
    try {
      await resetProcedure(open.name);
      setEditing(false);
      setNotice("Restored the original procedure.");
      await refresh();
      setTimeout(() => setNotice(null), 4000);
    } catch (e) {
      setError(e.message);
    }
  }

  if (error) return <div className="procs"><p className="proc-error">{error}</p></div>;
  if (!procs) return <div className="procs"><p className="proc-loading">Loading procedures...</p></div>;

  // detail view
  if (open) {
    return (
      <div className="procs">
        <div className="procs-inner">
          <button className="proc-back" onClick={() => { setOpenName(null); setEditing(false); }}>
            &larr; All procedures
          </button>
          <div className="proc-detail">
            <div className="proc-detail-head">
              <div>
                <h2>{titleOf(open)}</h2>
                <p className="proc-when">{whenToUseOf(open)}</p>
              </div>
              <div className="proc-actions">
                {!editing && (
                  <button className="proc-btn" onClick={() => { setDraft(open.content); setEditing(true); }}>
                    Edit
                  </button>
                )}
                {open.modified && !editing && (
                  <button className="proc-btn subtle" onClick={handleReset}>Reset to default</button>
                )}
              </div>
            </div>

            {notice && <div className="proc-notice">{notice}</div>}

            {editing ? (
              <div className="proc-editor">
                <textarea
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  spellCheck={false}
                />
                <div className="proc-actions">
                  <button className="proc-btn primary" onClick={handleSave}>Save</button>
                  <button className="proc-btn subtle" onClick={() => setEditing(false)}>Cancel</button>
                </div>
                <p className="proc-hint">
                  Plain English. Reference a tool with @, like @create_return. Changes apply on the
                  agent's next message, no restart, no deploy.
                </p>
              </div>
            ) : (
              <ProcedureBody content={open.content} />
            )}
          </div>
        </div>
      </div>
    );
  }

  // list view
  return (
    <div className="procs">
      <div className="procs-inner">
        <h2 className="procs-title">Operating procedures</h2>
        <p className="procs-sub">
          What the agent is instructed to do, in plain English. The support team owns these:
          edit one and the change is live on the next customer message.
        </p>
        {procs.map((p) => (
          <button key={p.name} className="proc-card" onClick={() => setOpenName(p.name)}>
            <div className="proc-card-head">
              <span className="proc-card-title">{titleOf(p)}</span>
              {p.modified && <span className="proc-flag">edited</span>}
            </div>
            <span className="proc-card-when">{whenToUseOf(p)}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
