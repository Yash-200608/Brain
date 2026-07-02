const API = window.location.origin.replace(":5173", ":8000") || "http://localhost:8000";
let sessionId = null;

const $msgs = document.getElementById("messages");
const $form = document.getElementById("composer");
const $input = document.getElementById("prompt");
const $memory = document.getElementById("memory-list");
const $goals = document.getElementById("goals-list");
const $status = document.getElementById("status");

// Brain's auth is fail-closed (Priority #1 / Ecosystem Architecture §6.1):
// every /api/* request needs a Bearer token that resolves to a configured
// key (JARVIS_API_KEYS on the server). The dashboard has no build step and
// no server-side templating, so the key can't be injected at build time --
// it's entered once and kept only in this browser's localStorage, never
// committed to source.
const API_KEY_STORAGE_KEY = "jarvis_brain_api_key";

function getApiKey() {
  let key = localStorage.getItem(API_KEY_STORAGE_KEY);
  if (!key) {
    key = (window.prompt(
      "Brain API key required (server rejects unauthenticated requests).\n" +
      "Ask whoever configured JARVIS_API_KEYS for a token, or generate one " +
      "yourself and register it server-side. Stored only in this browser."
    ) || "").trim();
    if (key) localStorage.setItem(API_KEY_STORAGE_KEY, key);
  }
  return key;
}

function setConnectionStatus(ok, title) {
  $status.className = ok ? "dot dot-ok" : "dot dot-bad";
  $status.title = title || (ok ? "connected" : "unauthorized");
}

async function authenticatedFetch(url, options = {}) {
  const key = getApiKey();
  const headers = { ...(options.headers || {}) };
  if (key) headers["Authorization"] = `Bearer ${key}`;
  const r = await fetch(url, { ...options, headers });
  if (r.status === 401) {
    // The stored key is missing, wrong, or revoked -- drop it so the next
    // request re-prompts instead of retrying the same bad key forever.
    localStorage.removeItem(API_KEY_STORAGE_KEY);
    setConnectionStatus(false, "unauthorized -- API key rejected, will re-prompt on next request");
  }
  return r;
}

function append(role, text) {
  const div = document.createElement("div");
  div.className = role === "user" ? "msg-user" : "msg-jarvis";
  div.textContent = (role === "user" ? "you: " : "jarvis: ") + text;
  $msgs.appendChild(div);
  $msgs.scrollTop = $msgs.scrollHeight;
}

async function send(query) {
  append("user", query);
  const r = await authenticatedFetch(`${API}/api/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, session_id: sessionId }),
  });
  if (!r.ok) {
    append("jarvis", r.status === 401
      ? "error: unauthorized -- re-enter your API key and try again"
      : `error: request failed (${r.status})`);
    return;
  }
  setConnectionStatus(true);
  const data = await r.json();
  sessionId = data.session_id;
  append("jarvis", data.response || "(empty)");
  renderMemory(data.memory_used || []);
}

function renderMemory(ids) {
  $memory.innerHTML = "";
  ids.forEach((id) => {
    const li = document.createElement("li");
    li.textContent = id;
    $memory.appendChild(li);
  });
}

async function loadGoals() {
  try {
    const r = await authenticatedFetch(`${API}/api/goals/`);
    if (!r.ok) return;
    setConnectionStatus(true);
    const goals = await r.json();
    $goals.innerHTML = "";
    goals.forEach((g) => {
      const li = document.createElement("li");
      li.textContent = `${g.description} [${g.status}]`;
      $goals.appendChild(li);
    });
  } catch (e) { setConnectionStatus(false, "offline"); }
}

$form.addEventListener("submit", (e) => {
  e.preventDefault();
  const q = $input.value.trim();
  if (!q) return;
  $input.value = "";
  send(q).catch((err) => append("jarvis", `error: ${err}`));
});

loadGoals();
setInterval(loadGoals, 30000);
