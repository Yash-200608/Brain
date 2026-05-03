const API = window.location.origin.replace(":5173", ":8000") || "http://localhost:8000";
let sessionId = null;

const $msgs = document.getElementById("messages");
const $form = document.getElementById("composer");
const $input = document.getElementById("prompt");
const $memory = document.getElementById("memory-list");
const $goals = document.getElementById("goals-list");

function append(role, text) {
  const div = document.createElement("div");
  div.className = role === "user" ? "msg-user" : "msg-jarvis";
  div.textContent = (role === "user" ? "you: " : "jarvis: ") + text;
  $msgs.appendChild(div);
  $msgs.scrollTop = $msgs.scrollHeight;
}

async function send(query) {
  append("user", query);
  const r = await fetch(`${API}/api/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, session_id: sessionId }),
  });
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
    const r = await fetch(`${API}/api/goals/`);
    const goals = await r.json();
    $goals.innerHTML = "";
    goals.forEach((g) => {
      const li = document.createElement("li");
      li.textContent = `${g.description} [${g.status}]`;
      $goals.appendChild(li);
    });
  } catch (e) { /* offline */ }
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
