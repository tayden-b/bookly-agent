import { useState } from "react";
import Sidebar from "./components/Sidebar.jsx";
import HomePage from "./components/HomePage.jsx";
import ConversationsPage from "./components/ConversationsPage.jsx";
import WatchtowerPage from "./components/WatchtowerPage.jsx";
import InsightsPage from "./components/InsightsPage.jsx";
import BuildPage from "./components/BuildPage.jsx";
import PreviewPage from "./components/PreviewPage.jsx";
import { sendMessage, resetSession, newSession } from "./api.js";

const GREETING = {
  role: "agent",
  text: "Hi! I'm the Bookly support agent. I can check an order, help with a return or refund, or answer questions about our policies. What can I do for you?",
};

export default function App() {
  const [page, setPage] = useState("home");

  // Chat state lives here so the conversation survives navigating the platform.
  const [messages, setMessages] = useState([GREETING]);
  const [turns, setTurns] = useState([]); // one entry per agent turn: {trace, state}
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [traceOpen, setTraceOpen] = useState(true);

  // Cross-page intents: Insights and Watchtower deep-link into Conversations.
  const [convFilter, setConvFilter] = useState(null);
  const [convFocus, setConvFocus] = useState(null);

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

  function handleNewConversation() {
    resetSession();
    newSession();
    setMessages([GREETING]);
    setTurns([]);
    setError(null);
  }

  function openCategory(tag) {
    setConvFilter(tag);
    setConvFocus(null);
    setPage("conversations");
  }

  function openConversation(id) {
    setConvFocus(id);
    setPage("conversations");
  }

  return (
    <div className="platform">
      <Sidebar page={page} onNavigate={setPage} />
      <main className="page">
        {page === "home" && <HomePage />}
        {page === "conversations" && (
          <ConversationsPage
            filterTag={convFilter}
            onClearFilter={() => setConvFilter(null)}
            focusId={convFocus}
            onFocusHandled={() => setConvFocus(null)}
          />
        )}
        {page === "watchtower" && <WatchtowerPage onOpenConversation={openConversation} />}
        {page === "insights" && <InsightsPage onOpenCategory={openCategory} />}
        {page === "build" && <BuildPage />}
        {page === "preview" && (
          <PreviewPage
            messages={messages}
            turns={turns}
            loading={loading}
            error={error}
            traceOpen={traceOpen}
            onSend={handleSend}
            onToggleTrace={() => setTraceOpen((o) => !o)}
            onNewConversation={handleNewConversation}
          />
        )}
      </main>
    </div>
  );
}
