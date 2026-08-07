import { useEffect, useState } from "react";
import { getMetrics } from "../api.js";
import { Donut } from "./charts.jsx";

const COLORS = [
  "#6d5ef2", "#f2703e", "#3ec48a", "#f2b93e", "#5eb0f2", "#e05e8f", "#9aa0ae",
];

export default function InsightsPage({ onOpenCategory }) {
  const [metrics, setMetrics] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    getMetrics().then(setMetrics).catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="page-pad"><p className="proc-error">{error}</p></div>;
  if (!metrics) return <div className="page-pad"><p className="proc-loading">Loading insights...</p></div>;

  const entries = Object.entries(metrics.categories).sort((a, b) => b[1] - a[1]);
  const slices = entries.map(([label, value], i) => ({ label, value, color: COLORS[i % COLORS.length] }));
  const total = entries.reduce((a, [, v]) => a + v, 0);

  return (
    <div className="page-pad">
      <div className="page-head">
        <h1>Insights</h1>
        <span className="page-note">AI-labeled categories across the last {metrics.window_days} days</span>
      </div>

      <div className="card">
        <div className="card-head"><h2>What are customers asking?</h2></div>
        <p className="card-hint">Click a segment or category to open the matching conversations.</p>
        <div className="insights-body">
          <Donut slices={slices} onSlice={onOpenCategory} />
          <div className="insights-legend">
            {slices.map((s) => (
              <button key={s.label} className="insight-row" onClick={() => onOpenCategory(s.label)}>
                <i style={{ background: s.color }} />
                <span className="insight-label">{s.label}</span>
                <span className="insight-count">{s.value.toLocaleString()}</span>
                <span className="insight-pct">{Math.round((s.value / total) * 100)}%</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-head"><h2>Resolution split</h2></div>
        <div className="split-bar">
          <div
            className="split-deflected"
            style={{ width: `${metrics.deflection_rate}%` }}
            title={`Deflected ${metrics.deflection_rate}%`}
          />
        </div>
        <div className="split-legend">
          <span className="legend-item"><i style={{ background: "var(--brand)" }} /> Resolved by the agent ({metrics.deflection_rate}%)</span>
          <span className="legend-item"><i style={{ background: "#e8e6f8" }} /> Escalated to a human ({metrics.escalations.toLocaleString()})</span>
        </div>
        <p className="card-hint">
          Escalation is a designed outcome, not a failure: unsupported requests and
          out-of-policy exceptions hand off with a structured summary and an SLA.
        </p>
      </div>
    </div>
  );
}
