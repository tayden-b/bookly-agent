import { useState } from "react";
import Chat from "./components/Chat.jsx";
import TracePanel from "./components/TracePanel.jsx";
import ProceduresPanel from "./components/ProceduresPanel.jsx";
import { sendMessage, resetSession } from "./api.js";

export default function App() {
  const [messages, setMessages] = useState([
    {
      role: "agent",
      text: "Hi! I'm the Bookly support agent. I can check an order, help with a return or refund, or answer questions about our policies. What can I do for you?",
    },
  ]);
  const [turns, setTurns] = useState([]); // one entry per agent turn: {trace, state}
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [view, setView] = useState("chat"); // "chat" | "procedures"
  const [traceOpen, setTraceOpen] = useState(true);

  async function handleSend(text) {
    setMessages((m) => [...m, { role: "user", text }]);
    setLoading(true);
    setError(null);
    try {
      const { reply, trace, state } = await sendMessage(text);
      setMessages((m) => [...m, { role: "agent", text: reply }]);
      setTurns((t) => [...t, { trace, state }]);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  function handleReset() {
    resetSession();
    window.location.reload();
  }

  return (
    <div className="app">
      <header className="header">
        <div>
          <span className="logo">Bookly</span>
          <span className="tagline">Support Agent</span>
        </div>
        <nav className="views">
          <button
            className={view === "chat" ? "view-tab active" : "view-tab"}
            onClick={() => setView("chat")}
          >
            Chat
          </button>
          <button
            className={view === "procedures" ? "view-tab active" : "view-tab"}
            onClick={() => setView("procedures")}
          >
            Procedures
          </button>
        </nav>
        <button className="reset" onClick={handleReset}>New conversation</button>
      </header>
      {view === "chat" ? (
        <main className={traceOpen ? "panes" : "panes trace-collapsed"}>
          <Chat messages={messages} loading={loading} error={error} onSend={handleSend} />
          <TracePanel turns={turns} open={traceOpen} onToggle={() => setTraceOpen((o) => !o)} />
        </main>
      ) : (
        <main className="panes single">
          <ProceduresPanel />
        </main>
      )}
    </div>
  );
}
