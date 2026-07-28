import { useEffect, useRef, useState } from "react";

export default function Chat({ messages, loading, error, onSend }) {
  const [draft, setDraft] = useState("");
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  function submit(e) {
    e.preventDefault();
    const text = draft.trim();
    if (!text || loading) return;
    setDraft("");
    onSend(text);
  }

  return (
    <section className="chat">
      <div className="messages">
        {messages.map((m, i) => (
          <div key={i} className={`bubble ${m.role}`}>
            {m.text}
          </div>
        ))}
        {loading && (
          <div className="bubble agent typing">
            <span /><span /><span />
          </div>
        )}
        {error && <div className="bubble error">⚠️ {error}</div>}
        <div ref={bottomRef} />
      </div>
      <form className="composer" onSubmit={submit}>
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && submit(e)}
          placeholder="Ask about an order, a return, or a policy…"
          autoFocus
        />
        <button aria-label="Send" disabled={loading || !draft.trim()}>↑</button>
      </form>
    </section>
  );
}
