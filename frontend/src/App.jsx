import { useState } from "react";
import Chat from "./components/Chat.jsx";
import TracePanel from "./components/TracePanel.jsx";
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
        <button className="reset" onClick={handleReset}>New conversation</button>
      </header>
      <main className="panes">
        <Chat messages={messages} loading={loading} error={error} onSend={handleSend} />
        <TracePanel turns={turns} />
      </main>
    </div>
  );
}
