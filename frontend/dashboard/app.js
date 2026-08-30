const API = window.location.origin.replace(":5173", ":8000") || "http://localhost:8000";
let sessionId = null;

const $msgs = document.getElementById("messages");
const $form = document.getElementById("composer");
const $input = document.getElementById("prompt");
const $memory = document.getElementById("memory-list");
const $goals = document.getElementById("goals-list");
const $devices = document.getElementById("devices-list");
const $approvals = document.getElementById("approvals-list");
const $audit = document.getElementById("audit-list");
const $trial = document.getElementById("trial-summary");
const $status = document.getElementById("status");

// Brain's auth is fail-closed (Priority #1 / Ecosystem Architecture §6.1):
// every /api/* request needs a Bearer token that resolves to a configured
// key (JARVIS_API_KEYS on the server). The dashboard has no build step and
// no server-side templating, so the key can't be injected at build time --
// it's entered once and kept only in this browser's localStorage, never
// committed to source.
const API_KEY_STORAGE_KEY = "jarvis_brain_api_key";
// NP-7: approving is a distinct privilege (devices.approve) -- stored
// separately from the ordinary requester key so the same browser session
// can drive both roles without conflating principals.
const APPROVER_KEY_STORAGE_KEY = "jarvis_brain_approver_key";

// Default params for common skills when the operator invokes from the
// dashboard console (editable in the prompt before dispatch).
const DEFAULT_SKILL_PARAMS = {
  "phone.tts": { text: "hello" },
  "phone.sms.send": { recipient: "Mom", message: "test" },
  "phone.whatsapp.send": { recipient: "Mom", message: "hi", auto_send: true },
  "phone.notify": { title: "Test", content: "message" },
  "phone.app.open": { app: "Settings" },
  "phone.torch": { on: true },
  "phone.vibrate": { ms: 200 },
  "phone.ring": { seconds: 1 },
  "pc.media.control": { command: "volume_up" },
  "pc.shell.run": { command: "echo hello", confirmed: true },
};

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

function getApproverKey() {
  let key = localStorage.getItem(APPROVER_KEY_STORAGE_KEY);
  if (!key) {
    key = (window.prompt(
      "Approver API key required for approve/deny actions.\n" +
      "Use a token from JARVIS_APPROVER_KEYS (devices.approve scope). " +
      "Stored only in this browser."
    ) || "").trim();
    if (key) localStorage.setItem(APPROVER_KEY_STORAGE_KEY, key);
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
    localStorage.removeItem(API_KEY_STORAGE_KEY);
    setConnectionStatus(false, "unauthorized -- API key rejected, will re-prompt on next request");
  }
  return r;
}

async function approverFetch(url, options = {}) {
  const key = getApproverKey();
  const headers = { ...(options.headers || {}) };
  if (key) headers["Authorization"] = `Bearer ${key}`;
  const r = await fetch(url, { ...options, headers });
  if (r.status === 401 || r.status === 403) {
    localStorage.removeItem(APPROVER_KEY_STORAGE_KEY);
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

const lastPingResult = new Map();
const lastInvokeResult = new Map();

function setStickyResult(map, key, className, text, el) {
  map.set(key, { className, text });
  if (el && document.body.contains(el)) {
    el.className = className;
    el.textContent = text;
  }
}

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

    const pingResultEl = document.createElement("div");
    const pingKey = `${d.node}:ping`;
    const lastPing = lastPingResult.get(pingKey);
    pingResultEl.className = lastPing ? lastPing.className : "device-result";
    pingResultEl.textContent = lastPing ? lastPing.text : "";

    const pingBtn = document.createElement("button");
    pingBtn.className = "ping-btn";
    pingBtn.type = "button";
    pingBtn.textContent = "Ping";
    pingBtn.addEventListener("click", () => pingDevice(d.node, pingBtn, pingResultEl, pingKey));
    row.appendChild(pingBtn);

    li.appendChild(row);
    li.appendChild(pingResultEl);

    if (d.state && Object.keys(d.state).length > 0) {
      const state = document.createElement("div");
      state.className = "device-state";
      state.textContent = JSON.stringify(d.state);
      li.appendChild(state);
    }

    if (d.skills && d.skills.length > 0) {
      const skillsWrap = document.createElement("div");
      skillsWrap.className = "device-skills";
      d.skills.forEach((skill) => {
        const skillRow = document.createElement("div");
        skillRow.className = "skill-row";
        const code = document.createElement("code");
        code.textContent = skill;
        skillRow.appendChild(code);

        const invokeResultEl = document.createElement("div");
        const invokeKey = `${d.node}:${skill}`;
        const lastInvoke = lastInvokeResult.get(invokeKey);
        invokeResultEl.className = lastInvoke ? lastInvoke.className : "device-result";
        invokeResultEl.textContent = lastInvoke ? lastInvoke.text : "";

        const invokeBtn = document.createElement("button");
        invokeBtn.className = "skill-invoke-btn";
        invokeBtn.type = "button";
        invokeBtn.textContent = "Invoke";
        invokeBtn.addEventListener("click", () =>
          invokeSkill(d.node, skill, invokeBtn, invokeResultEl, invokeKey)
        );
        skillRow.appendChild(invokeBtn);
        skillsWrap.appendChild(skillRow);
        skillsWrap.appendChild(invokeResultEl);
      });
      li.appendChild(skillsWrap);
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

async function pingDevice(node, buttonEl, resultEl, resultKey) {
  buttonEl.disabled = true;
  setStickyResult(lastPingResult, resultKey, "device-result", "pinging…", resultEl);
  try {
    const r = await authenticatedFetch(
      `${API}/api/devices/${encodeURIComponent(node)}/ping`,
      { method: "POST" }
    );
    const body = await r.json().catch(() => ({}));
    if (r.ok) {
      setStickyResult(
        lastPingResult, resultKey, "device-result result-ok",
        `ping ok: ${JSON.stringify(body.result)}`, resultEl
      );
    } else {
      setStickyResult(
        lastPingResult, resultKey, "device-result result-bad",
        `ping failed (${r.status}): ${body.detail || r.statusText}`, resultEl
      );
    }
  } catch (e) {
    setStickyResult(lastPingResult, resultKey, "device-result result-bad", `ping error: ${e}`, resultEl);
  } finally {
    if (document.body.contains(buttonEl)) buttonEl.disabled = false;
  }
}

function formatSkillResult(result) {
  if (!result || typeof result !== "object") return String(result ?? "");
  if (result.ok === false) return result.error || "failed";

  const contact = result.resolved_contact;
  const to = contact?.name
    ? `${contact.name} (${contact.number || result.phone})`
    : result.phone;

  if (to && (result.message || result.note || result.sent != null)) {
    const parts = [];
    if (to) parts.push(`To ${to}`);
    if (result.sent === true) parts.push("WhatsApp sent");
    else if (result.note) parts.push(result.note);
    else if (result.sent == null && result.phone) parts.push("SMS sent");
    if (contact?.alternates?.length) {
      const nums = contact.alternates.map((a) => a.number).join(", ");
      parts.push(`other numbers: ${nums}`);
    }
    return parts.join(" · ");
  }

  if (result.battery?.level != null) {
    const pct = result.battery.level;
    const ch = result.battery.charging ? ", charging" : "";
    return `Battery ${pct}%${ch}`;
  }

  const { ok, exit_code, stdout, stderr, ...rest } = result;
  const compact = JSON.stringify(rest);
  return compact === "{}" ? "Done" : compact;
}

async function invokeSkill(node, skill, buttonEl, resultEl, resultKey) {
  const defaults = DEFAULT_SKILL_PARAMS[skill] || {};
  const input = window.prompt(`Params JSON for ${skill}:`, JSON.stringify(defaults));
  if (input === null) return;

  let params = {};
  try {
    params = JSON.parse(input || "{}");
  } catch (e) {
    setStickyResult(
      lastInvokeResult, resultKey, "device-result result-bad",
      `invalid JSON: ${e}`, resultEl
    );
    return;
  }

  buttonEl.disabled = true;
  setStickyResult(lastInvokeResult, resultKey, "device-result", "invoking…", resultEl);
  try {
    const r = await authenticatedFetch(
      `${API}/api/devices/${encodeURIComponent(node)}/invoke`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ skill, params }),
      }
    );
    const body = await r.json().catch(() => ({}));
    if (r.ok && body.status === "approval_required") {
      setStickyResult(
        lastInvokeResult, resultKey, "device-result result-ok",
        `approval required (risk ${body.risk}): ${body.approval_id}`, resultEl
      );
      loadApprovals();
      loadAudit();
    } else if (r.ok) {
      const skillOk = body.result?.ok !== false;
      setStickyResult(
        lastInvokeResult, resultKey,
        skillOk ? "device-result result-ok" : "device-result result-bad",
        skillOk
          ? formatSkillResult(body.result)
          : formatSkillResult(body.result) || `skill failed: ${JSON.stringify(body.result)}`,
        resultEl
      );
      loadAudit();
    } else {
      setStickyResult(
        lastInvokeResult, resultKey, "device-result result-bad",
        `invoke failed (${r.status}): ${body.detail || r.statusText}`, resultEl
      );
    }
  } catch (e) {
    setStickyResult(lastInvokeResult, resultKey, "device-result result-bad", `invoke error: ${e}`, resultEl);
  } finally {
    if (document.body.contains(buttonEl)) buttonEl.disabled = false;
  }
}

function renderApprovals(items) {
  $approvals.innerHTML = "";
  if (!items.length) {
    const li = document.createElement("li");
    li.className = "console-empty";
    li.textContent = "no pending approvals";
    $approvals.appendChild(li);
    return;
  }
  items.forEach((a) => {
    const li = document.createElement("li");
    li.className = "approval-item";
    const meta = document.createElement("div");
    meta.className = "approval-meta";
    meta.textContent = `${a.skill} on ${a.node} (risk ${a.risk})`;
    li.appendChild(meta);

    const detail = document.createElement("div");
    detail.textContent = `id: ${a.id} · params: ${JSON.stringify(a.params)}`;
    li.appendChild(detail);

    const resultEl = document.createElement("div");
    resultEl.className = "approval-result";
    li.appendChild(resultEl);

    const actions = document.createElement("div");
    actions.className = "approval-actions";
    const approveBtn = document.createElement("button");
    approveBtn.className = "console-btn";
    approveBtn.type = "button";
    approveBtn.textContent = "Approve";
    approveBtn.addEventListener("click", () => approvePending(a.id, approveBtn, resultEl));
    const denyBtn = document.createElement("button");
    denyBtn.className = "console-btn deny";
    denyBtn.type = "button";
    denyBtn.textContent = "Deny";
    denyBtn.addEventListener("click", () => denyPending(a.id, denyBtn, resultEl));
    actions.appendChild(approveBtn);
    actions.appendChild(denyBtn);
    li.appendChild(actions);
    $approvals.appendChild(li);
  });
}

async function loadApprovals() {
  try {
    const r = await authenticatedFetch(`${API}/api/devices/approvals`);
    if (!r.ok) return;
    renderApprovals(await r.json());
  } catch (e) { /* offline */ }
}

async function approvePending(approvalId, buttonEl, resultEl) {
  buttonEl.disabled = true;
  resultEl.textContent = "approving…";
  try {
    const r = await approverFetch(
      `${API}/api/devices/approvals/${encodeURIComponent(approvalId)}/approve`,
      { method: "POST" }
    );
    const body = await r.json().catch(() => ({}));
    if (r.ok) {
      resultEl.className = "approval-result result-ok";
      resultEl.textContent = `approved: ${JSON.stringify(body.result)}`;
      loadApprovals();
      loadAudit();
    } else {
      resultEl.className = "approval-result result-bad";
      resultEl.textContent = `approve failed (${r.status}): ${body.detail || r.statusText}`;
    }
  } catch (e) {
    resultEl.className = "approval-result result-bad";
    resultEl.textContent = `approve error: ${e}`;
  } finally {
    if (document.body.contains(buttonEl)) buttonEl.disabled = false;
  }
}

async function denyPending(approvalId, buttonEl, resultEl) {
  buttonEl.disabled = true;
  resultEl.textContent = "denying…";
  try {
    const r = await approverFetch(
      `${API}/api/devices/approvals/${encodeURIComponent(approvalId)}/deny`,
      { method: "POST" }
    );
    const body = await r.json().catch(() => ({}));
    if (r.ok) {
      resultEl.className = "approval-result result-ok";
      resultEl.textContent = `denied: ${body.denied || approvalId}`;
      loadApprovals();
    } else {
      resultEl.className = "approval-result result-bad";
      resultEl.textContent = `deny failed (${r.status}): ${body.detail || r.statusText}`;
    }
  } catch (e) {
    resultEl.className = "approval-result result-bad";
    resultEl.textContent = `deny error: ${e}`;
  } finally {
    if (document.body.contains(buttonEl)) buttonEl.disabled = false;
  }
}

function renderAudit(rows) {
  $audit.innerHTML = "";
  if (!rows.length) {
    const li = document.createElement("li");
    li.className = "console-empty";
    li.textContent = "no dispatch events yet";
    $audit.appendChild(li);
    return;
  }
  rows.forEach((row) => {
    const li = document.createElement("li");
    li.className = "audit-item";
    li.textContent = `${row.outcome} · ${row.skill} @ ${row.node} · risk ${row.risk}`;
    if (row.approval_id) li.textContent += ` · approval ${row.approval_id}`;
    if (row.result) li.textContent += ` · ${JSON.stringify(row.result)}`;
    $audit.appendChild(li);
  });
}

async function loadAudit() {
  try {
    const r = await authenticatedFetch(`${API}/api/devices/audit?limit=30`);
    if (!r.ok) return;
    renderAudit(await r.json());
  } catch (e) { /* offline */ }
}

function renderTrial(report) {
  $trial.innerHTML = "";
  if (!report) return;
  const cov = report.criteria?.command_coverage;
  const leg = report.criteria?.legacy_zero_for_covered;
  const items = [
    `coverage: ${cov ? "ok" : "incomplete"}`,
    `legacy zero: ${leg ? "ok" : "violations or missing log"}`,
    `spine events: ${report.spine?.total_events ?? 0}`,
    `legacy invocations: ${report.legacy?.total_invocations ?? 0}`,
  ];
  items.forEach((text) => {
    const li = document.createElement("li");
    li.className = "trial-item";
    li.textContent = text;
    $trial.appendChild(li);
  });
  if (report.confirmed_classes) {
    Object.entries(report.confirmed_classes).forEach(([cls, row]) => {
      const li = document.createElement("li");
      li.className = "trial-item";
      li.textContent = `${cls}: spine ${row.spine_success}/${row.spine_any} · legacy ${row.legacy}`;
      $trial.appendChild(li);
    });
  }
}

async function loadTrial() {
  try {
    const r = await authenticatedFetch(`${API}/api/devices/trial-report`);
    if (!r.ok) return;
    renderTrial(await r.json());
  } catch (e) { /* offline */ }
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
  loadApprovals();
  loadAudit();
  loadTrial();
}

refresh();
setInterval(refresh, 30000);
