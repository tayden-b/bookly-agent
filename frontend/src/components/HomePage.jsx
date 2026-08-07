import { useEffect, useState } from "react";
import { getMetrics } from "../api.js";
import { AreaChart, HBars } from "./charts.jsx";

export default function HomePage() {
  const [metrics, setMetrics] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    getMetrics().then(setMetrics).catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="page-pad"><p className="proc-error">{error}</p></div>;
  if (!metrics) return <div className="page-pad"><p className="proc-loading">Loading metrics...</p></div>;

  const daily = metrics.daily_volume;
  const stats = [
    { label: "Total conversations", value: metrics.total_conversations.toLocaleString() },
    { label: "Deflection rate", value: `${metrics.deflection_rate}%` },
    { label: "CSAT", value: metrics.csat.toFixed(1) },
    { label: "Escalations", value: metrics.escalations.toLocaleString() },
  ];

  return (
    <div className="page-pad">
      <div className="page-head">
        <h1>Home</h1>
        <span className="page-note">Metrics over the last {metrics.window_days} days</span>
      </div>

      <div className="stat-grid">
        {stats.map((s) => (
          <div key={s.label} className="stat-card">
            <div className="stat-value">{s.value}</div>
            <div className="stat-label">{s.label}</div>
          </div>
        ))}
      </div>

      <div className="card">
        <div className="card-head">
          <h2>Conversation volume</h2>
          <div className="legend">
            <span className="legend-item"><i style={{ background: "var(--brand)" }} /> Deflected</span>
            <span className="legend-item"><i style={{ background: "var(--orange)" }} /> Total</span>
          </div>
        </div>
        <AreaChart
          series={[
            { label: "Total", color: "var(--orange)", values: daily.map((d) => d.total) },
            { label: "Deflected", color: "var(--brand)", values: daily.map((d) => d.deflected) },
          ]}
        />
      </div>

      <div className="card-row">
        <div className="card">
          <div className="card-head"><h2>Customer satisfaction</h2></div>
          <HBars rows={Object.entries(metrics.csat_distribution).map(([label, value]) => ({ label, value }))} />
        </div>
        <div className="card">
          <div className="card-head"><h2>Live this session</h2></div>
          <div className="mini-stats">
            <div>
              <div className="mini-value">{metrics.live_conversations}</div>
              <div className="mini-label">Live conversations recorded</div>
            </div>
            <div>
              <div className="mini-value">{metrics.gate_blocks_in_sample}</div>
              <div className="mini-label">Policy gate interventions in the sample</div>
            </div>
          </div>
          <p className="card-hint">
            Conversations from the Agent Preview are recorded here in real time,
            with their full execution trace. Open Conversations to audit any of them.
          </p>
        </div>
      </div>
    </div>
  );
}
