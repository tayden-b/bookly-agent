import Chat from "./Chat.jsx";
import TracePanel from "./TracePanel.jsx";

// The agent, framed the way a customer would meet it: a chat window, with the
// internal execution trace alongside for the builder's view.
export default function PreviewPage({
  messages, turns, loading, error, traceOpen,
  onSend, onToggleTrace, onNewConversation,
}) {
  return (
    <div className="preview-page">
      <div className="preview-head">
        <div>
          <h1>Agent Preview</h1>
          <p className="page-sub slim">
            Test the live agent. Every conversation here is recorded to
            Conversations with its full audit log, and Watchtower can scan it.
          </p>
        </div>
        <button className="reset" onClick={onNewConversation}>New conversation</button>
      </div>
      <div className={traceOpen ? "preview-body" : "preview-body trace-collapsed"}>
        <div className="agent-window">
          <div className="agent-window-bar">
            <span className="dot red" /><span className="dot yellow" /><span className="dot green" />
            <span className="agent-window-title">Chat with Bookly</span>
          </div>
          <Chat messages={messages} loading={loading} error={error} onSend={onSend} />
        </div>
        <TracePanel turns={turns} open={traceOpen} onToggle={onToggleTrace} />
      </div>
    </div>
  );
}
