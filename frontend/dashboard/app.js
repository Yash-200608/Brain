const API = window.location.origin.replace(":5173", ":8000") || "http://localhost:8000";
let sessionId = null;

const $msgs = document.getElementById("messages");
const $form = document.getElementById("composer");
const $input = document.getElementById("prompt");
const $memory = document.getElementById("memory-list");
const $goals = document.getElementById("goals-list");
const $devices = document.getElementById("devices-list");
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

// Sticky per-node ping result, survives the periodic 30s refresh()'s
// renderDevices() rebuild -- without this, a ping's result could be wiped
// by the next poll tick before the user finishes reading it, undermining
// the dashboard's job of demonstrating the round trip actually happened.
const lastPingResult = new Map();

// Priority #3 Milestone 11: read-only view of Brain's device registry
// (GET /api/devices/, added Milestone 9) -- proves the execution spine's
// Dashboard/API -> Brain read path end-to-end.
function renderDevices(devices) {
  $devices.innerHTML = "";
  if (devices.length === 0) {
    const li = document.createElement("li");
    li.className = "device-empty";
    li.textContent = "no devices seen yet";
    $devices.appendChild(li);
    return;
  }
  devices.forEach((d) => {
    const li = document.createElement("li");
    li.className = "device-item";

    const row = document.createElement("div");
    const dot = document.createElement("span");
    dot.className = d.is_online ? "dot dot-ok" : "dot dot-bad";
    dot.title = d.is_online ? "online" : "offline";
    row.appendChild(dot);
    row.appendChild(document.createTextNode(` ${d.node} `));

    const resultEl = document.createElement("div");
    const lastResult = lastPingResult.get(d.node);
    resultEl.className = lastResult ? lastResult.className : "device-ping-result";
    resultEl.textContent = lastResult ? lastResult.text : "";

    const pingBtn = document.createElement("button");
    pingBtn.className = "ping-btn";
    pingBtn.type = "button";
    pingBtn.textContent = "Ping";
    pingBtn.addEventListener("click", () => pingDevice(d.node, pingBtn, resultEl));
    row.appendChild(pingBtn);

    li.appendChild(row);
    li.appendChild(resultEl);

    if (d.state && Object.keys(d.state).length > 0) {
      const state = document.createElement("div");
      state.className = "device-state";
      state.textContent = JSON.stringify(d.state);
      li.appendChild(state);
    }

    $devices.appendChild(li);
  });
}

async function loadDevices() {
  try {
    const r = await authenticatedFetch(`${API}/api/devices/`);
    if (!r.ok) return;
    setConnectionStatus(true);
    const devices = await r.json();
    renderDevices(devices);
  } catch (e) { setConnectionStatus(false, "offline"); }
}

// Priority #3 Milestone 12 (Execution Spine Capstone): the dashboard's
// demonstration of the complete Dashboard/API -> Brain -> MQTT -> JARVIS
// -> Response -> Brain -> Dashboard/API path via POST /api/devices/{node}/ping.
async function pingDevice(node, buttonEl, resultEl) {
  const setResult = (className, text) => {
    lastPingResult.set(node, { className, text });
    // The element may have already been replaced by a refresh() tick that
    // fired while this request was in flight -- only touch it if it's
    // still the one currently in the DOM (renderDevices() reads the map
    // fresh on every rebuild, so the result isn't lost either way).
    if (document.body.contains(resultEl)) {
      resultEl.className = className;
      resultEl.textContent = text;
    }
  };

  buttonEl.disabled = true;
  setResult("device-ping-result", "pinging…");
  try {
    const r = await authenticatedFetch(
      `${API}/api/devices/${encodeURIComponent(node)}/ping`,
      { method: "POST" }
    );
    const body = await r.json().catch(() => ({}));
    if (r.ok) {
      setResult("device-ping-result ping-ok", `ping ok: ${JSON.stringify(body.result)}`);
    } else {
      setResult("device-ping-result ping-bad", `ping failed (${r.status}): ${body.detail || r.statusText}`);
    }
  } catch (e) {
    setResult("device-ping-result ping-bad", `ping error: ${e}`);
  } finally {
    if (document.body.contains(buttonEl)) buttonEl.disabled = false;
  }
}

$form.addEventListener("submit", (e) => {
  e.preventDefault();
  const q = $input.value.trim();
  if (!q) return;
  $input.value = "";
  send(q).catch((err) => append("jarvis", `error: ${err}`));
});

function refresh() {
  loadGoals();
  loadDevices();
}

refresh();
setInterval(refresh, 30000);
