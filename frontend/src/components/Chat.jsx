import { useEffect, useRef, useState } from "react";

// The model writes light markdown, so bold and bullets need rendering or the
// raw ** shows up in the chat. This builds React elements rather than setting
// innerHTML, so model output can never turn into markup.
function inline(text, key) {
  return text.split(/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g).map((part, i) => {
    const k = `${key}-${i}`;
    if (part.startsWith("**") && part.endsWith("**") && part.length > 4)
      return <strong key={k}>{part.slice(2, -2)}</strong>;
    if (part.startsWith("`") && part.endsWith("`") && part.length > 2)
      return <code key={k}>{part.slice(1, -1)}</code>;
    if (part.startsWith("*") && part.endsWith("*") && part.length > 2)
      return <em key={k}>{part.slice(1, -1)}</em>;
    return part;
  });
}

function Markdown({ text }) {
  return text.split("\n").map((line, i) => {
    const bullet = line.startsWith("- ");
    return (
      <div key={i} className={bullet ? "md-bullet" : "md-line"}>
        {inline(bullet ? line.slice(2) : line, i)}
      </div>
    );
  });
}

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
            {m.role === "agent" ? <Markdown text={m.text} /> : m.text}
          </div>
        ))}
        {loading && (
          <div className="bubble agent typing">
            <span /><span /><span />
          </div>
        )}
        {error && <div className="bubble error">{error}</div>}
        <div ref={bottomRef} />
      </div>
      <form className="composer" onSubmit={submit}>
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Ask about an order, a return, or a policy…"
          autoFocus
        />
        <button aria-label="Send" disabled={loading || !draft.trim()}>↑</button>
      </form>
    </section>
  );
}
