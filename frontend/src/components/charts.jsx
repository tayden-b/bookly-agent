// Hand-rolled SVG charts: an area chart, a donut, and horizontal bars.
// No chart library, keeping the bundle small and every pixel explainable.

export function AreaChart({ series, width = 640, height = 200 }) {
  // series: [{ label, color, values: number[] }], all the same length.
  const max = Math.max(...series.flatMap((s) => s.values), 1);
  const padX = 6;
  const padY = 12;
  const w = width - padX * 2;
  const h = height - padY * 2;
  const n = series[0].values.length;

  const pointsOf = (values) =>
    values.map((v, i) => [
      padX + (i / (n - 1)) * w,
      padY + h - (v / max) * h,
    ]);

  const linePath = (pts) =>
    pts.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");

  const areaPath = (pts) =>
    `${linePath(pts)} L${(padX + w).toFixed(1)},${padY + h} L${padX},${padY + h} Z`;

  return (
    <svg className="area-chart" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
      {[0.25, 0.5, 0.75].map((f) => (
        <line key={f} x1={padX} x2={padX + w} y1={padY + h * f} y2={padY + h * f} className="grid-line" />
      ))}
      {series.map((s) => (
        <g key={s.label}>
          <path d={areaPath(pointsOf(s.values))} fill={s.color} opacity="0.14" />
          <path d={linePath(pointsOf(s.values))} fill="none" stroke={s.color} strokeWidth="2" strokeLinejoin="round" />
        </g>
      ))}
    </svg>
  );
}

export function Donut({ slices, size = 220, thickness = 34, onSlice }) {
  // slices: [{ label, value, color }]
  const total = slices.reduce((a, s) => a + s.value, 0) || 1;
  const r = size / 2 - thickness / 2 - 2;
  const c = size / 2;
  let angle = -Math.PI / 2;

  const arcs = slices.map((s) => {
    const frac = s.value / total;
    const a0 = angle;
    const a1 = angle + frac * Math.PI * 2;
    angle = a1;
    // shrink slightly so slices read as separate segments
    const gap = 0.02;
    const b0 = a0 + gap;
    const b1 = Math.max(a1 - gap, b0 + 0.001);
    const large = b1 - b0 > Math.PI ? 1 : 0;
    const p0 = [c + r * Math.cos(b0), c + r * Math.sin(b0)];
    const p1 = [c + r * Math.cos(b1), c + r * Math.sin(b1)];
    return {
      ...s,
      frac,
      d: `M${p0[0].toFixed(2)},${p0[1].toFixed(2)} A${r},${r} 0 ${large} 1 ${p1[0].toFixed(2)},${p1[1].toFixed(2)}`,
    };
  });

  return (
    <svg viewBox={`0 0 ${size} ${size}`} className="donut">
      {arcs.map((a) => (
        <path
          key={a.label}
          d={a.d}
          fill="none"
          stroke={a.color}
          strokeWidth={thickness}
          className={onSlice ? "donut-slice clickable" : "donut-slice"}
          onClick={onSlice ? () => onSlice(a.label) : undefined}
        >
          <title>{`${a.label}: ${a.value} (${Math.round(a.frac * 100)}%)`}</title>
        </path>
      ))}
    </svg>
  );
}

export function HBars({ rows, max }) {
  // rows: [{ label, value }]
  const top = max ?? Math.max(...rows.map((r) => r.value), 1);
  return (
    <div className="hbars">
      {rows.map((r) => (
        <div key={r.label} className="hbar-row">
          <span className="hbar-label">{r.label}</span>
          <div className="hbar-track">
            <div className="hbar-fill" style={{ width: `${Math.max((r.value / top) * 100, r.value ? 2 : 0)}%` }} />
          </div>
          <span className="hbar-value">{r.value}</span>
        </div>
      ))}
    </div>
  );
}
