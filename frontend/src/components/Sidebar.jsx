// Left navigation for the platform shell. Icons are inline SVG so the build
// stays dependency-free.

const ICONS = {
  home: <path d="M3 10.5 12 3l9 7.5M5.5 9.5V20h13V9.5" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />,
  conversations: <path d="M4 5.5h16v10.5H9.5L5.5 19v-3H4z" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />,
  watchtower: (
    <>
      <path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
      <circle cx="12" cy="12" r="3" fill="none" stroke="currentColor" strokeWidth="1.7" />
    </>
  ),
  insights: (
    <>
      <path d="M12 3.5a8.5 8.5 0 1 0 8.5 8.5H12z" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
      <path d="M15 3.9a8.5 8.5 0 0 1 5.1 5.1H15z" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinejoin="round" />
    </>
  ),
  build: <path d="M4 6.5h16M4 12h16M4 17.5h10" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />,
  preview: (
    <>
      <circle cx="12" cy="12" r="8.5" fill="none" stroke="currentColor" strokeWidth="1.7" />
      <path d="M10 8.8v6.4L15.2 12z" fill="currentColor" />
    </>
  ),
};

const NAV = [
  { id: "home", label: "Home" },
  { id: "conversations", label: "Conversations" },
  { id: "watchtower", label: "Watchtower" },
  { id: "insights", label: "Insights" },
  { id: "build", label: "Build" },
  { id: "preview", label: "Agent Preview" },
];

export default function Sidebar({ page, onNavigate }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <span className="brand-mark">B</span>
        <div>
          <div className="brand-name">Bookly</div>
          <div className="brand-sub">Agent workspace</div>
        </div>
      </div>
      <nav className="sidebar-nav">
        {NAV.map((item) => (
          <button
            key={item.id}
            className={page === item.id ? "nav-item active" : "nav-item"}
            onClick={() => onNavigate(item.id)}
          >
            <svg viewBox="0 0 24 24" aria-hidden="true">{ICONS[item.id]}</svg>
            {item.label}
          </button>
        ))}
      </nav>
      <div className="sidebar-foot">
        Demo workspace
        <br />
        Seeded history + live sessions
      </div>
    </aside>
  );
}
