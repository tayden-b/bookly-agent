// One session at a time. The backend keys memory off this id. "New conversation"
// swaps the id instead of reloading, so the rest of the platform keeps its state
// and the finished conversation stays visible in the Conversations view.
let sessionId = crypto.randomUUID();

export function newSession() {
  sessionId = crypto.randomUUID();
  return sessionId;
}

async function getJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

async function send(url, method, body) {
  const res = await fetch(url, {
    method,
    headers: body ? { "content-type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

export async function sendMessage(message) {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message }),
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body.slice(0, 200)}`);
  }
  return res.json(); // { reply, trace, state }
}

export async function resetSession() {
  await fetch(`/api/reset/${sessionId}`, { method: "POST" });
}

// ---------------- procedures (Build) ----------------

export const getProcedures = () => getJSON("/api/procedures");
export const saveProcedure = (name, content) => send(`/api/procedures/${name}`, "PUT", { content });
export const resetProcedure = (name) => send(`/api/procedures/${name}/reset`, "POST");

// ---------------- platform views ----------------

export const getMetrics = () => getJSON("/api/metrics");
export const getConversations = () => getJSON("/api/conversations");
export const getConversation = (id) => getJSON(`/api/conversations/${id}`);
export const getWatchtower = () => getJSON("/api/watchtower");
export const saveWatchtower = (id, criteria) => send(`/api/watchtower/${id}`, "PUT", { criteria });
export const resetWatchtower = (id) => send(`/api/watchtower/${id}/reset`, "POST");
export const runWatchtower = () => send("/api/watchtower/run", "POST");
export const getKnowledge = () => getJSON("/api/knowledge");
export const getTools = () => getJSON("/api/tools");
