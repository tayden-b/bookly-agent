import { useEffect, useState } from "react";
import ProceduresPanel from "./ProceduresPanel.jsx";
import { getKnowledge, getTools } from "../api.js";

function KnowledgeTab() {
  const [docs, setDocs] = useState(null);
  const [error, setError] = useState(null);
  const [openName, setOpenName] = useState(null);

  useEffect(() => {
    getKnowledge().then(setDocs).catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="proc-error">{error}</p>;
  if (!docs) return <p className="proc-loading">Loading knowledge...</p>;

  return (
    <div>
      <p className="page-sub">
        Grounding documents the agent can retrieve with @get_policy. Answers to
        policy questions come from these, never from the model's own memory, so
        every claim has a source.
      </p>
      {docs.map((d) => {
        const open = openName === d.name;
        return (
          <div key={d.name} className="card knowledge-card">
            <button className="knowledge-head" onClick={() => setOpenName(open ? null : d.name)}>
              <div>
                <span className="proc-card-title">{d.title}</span>
                <span className="knowledge-file">{d.name}</span>
              </div>
              <span className="knowledge-toggle">{open ? "Hide" : "View"}</span>
            </button>
            {open && <pre className="knowledge-body">{d.content}</pre>}
          </div>
        );
      })}
    </div>
  );
}

function ToolsTab() {
  const [tools, setTools] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    getTools().then(setTools).catch((e) => setError(e.message));
  }, []);

  if (error) return <p className="proc-error">{error}</p>;
  if (!tools) return <p className="proc-loading">Loading tools...</p>;

  return (
    <div>
      <p className="page-sub">
        The actions the agent can request. The model only ever proposes a call;
        the orchestrator executes it, and gated tools are enforced in code, so
        no phrasing in a conversation can bypass them.
      </p>
      {tools.map((t) => (
        <div key={t.name} className="card tool-card">
          <div className="card-head">
            <h2><span className="tool-chip">{t.name}</span></h2>
            {t.gate && <span className="gate-chip">gated</span>}
          </div>
          <p className="side-text">{t.description}</p>
          <div className="tag-row">
            {t.params.map((p) => (
              <span key={p.name} className="param-chip">
                {p.name}{p.required ? "" : "?"}: {p.type}
              </span>
            ))}
          </div>
          {t.gate && <p className="gate-note">{t.gate}</p>}
        </div>
      ))}
    </div>
  );
}

const TABS = [
  { id: "procedures", label: "Procedures" },
  { id: "knowledge", label: "Knowledge" },
  { id: "tools", label: "Tools" },
];

export default function BuildPage() {
  const [tab, setTab] = useState("procedures");

  return (
    <div className={tab === "procedures" ? "build-page" : "build-page page-pad"}>
      <div className={tab === "procedures" ? "build-tabs page-pad-x" : "build-tabs"}>
        {TABS.map((t) => (
          <button
            key={t.id}
            className={tab === t.id ? "build-tab active" : "build-tab"}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>
      {tab === "procedures" && <ProceduresPanel />}
      {tab === "knowledge" && <KnowledgeTab />}
      {tab === "tools" && <ToolsTab />}
    </div>
  );
}
