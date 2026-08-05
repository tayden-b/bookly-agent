// One session per page load. The backend keys memory off this id.
export const SESSION_ID = crypto.randomUUID();

export async function sendMessage(message) {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ session_id: SESSION_ID, message }),
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body.slice(0, 200)}`);
  }
  return res.json(); // { reply, trace, state }
}

export async function resetSession() {
  await fetch(`/api/reset/${SESSION_ID}`, { method: "POST" });
}

export async function getProcedures() {
  const res = await fetch("/api/procedures");
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json(); // [{ name, content, modified }]
}

export async function saveProcedure(name, content) {
  const res = await fetch(`/api/procedures/${name}`, {
    method: "PUT",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ content }),
  });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

export async function resetProcedure(name) {
  const res = await fetch(`/api/procedures/${name}/reset`, { method: "POST" });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json(); // { ok, content }
}
