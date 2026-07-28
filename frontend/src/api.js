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
