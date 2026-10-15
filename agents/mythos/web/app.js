const LEVELS = {
  1: "1 — ask before every tool",
  2: "2 — confirm writes and shell",
  3: "3 — safe auto, confirm destructive",
  4: "4 — auto except irreversible",
  5: "5 — full auto + post-action report",
};

const autonomy = document.getElementById("autonomy");
const autonomyLabel = document.getElementById("autonomyLabel");
const meta = document.getElementById("meta");
const rootEl = document.getElementById("root");
const llmEl = document.getElementById("llm");
const logEl = document.getElementById("log");
const planEl = document.getElementById("plan");
const agentsEl = document.getElementById("agents");
const improvementsEl = document.getElementById("improvements");
const pending = document.getElementById("pending");
const pendingText = document.getElementById("pendingText");
const runBtn = document.getElementById("runBtn");
const taskEl = document.getElementById("task");

let since = 0;

function text(el, value) {
  el.textContent = value;
}

function addLog(kind, title, body) {
  const li = document.createElement("li");
  li.className = kind;
  li.textContent = body ? `${title}\n${body}` : title;
  logEl.prepend(li);
}

async function api(path, opts) {
  const res = await fetch(path, opts);
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || res.statusText);
  return data;
}

async function refreshHealth() {
  const s = await api("/api/health");
  autonomy.value = String(s.autonomy);
  autonomyLabel.textContent = LEVELS[s.autonomy] || String(s.autonomy);
  text(meta, s.busy ? "running" : "idle");
  text(rootEl, `root ${s.root}`);
  text(
    llmEl,
    s.has_llm
      ? `${s.provider} · ${s.model}${s.bills_xai ? "" : " · no xAI charges"}`
      : "local Ollama not running — LLM loop disabled (no paid API fallback)"
  );
  if (s.pending) showPending(s.pending);
  else pending.classList.add("hidden");
  runBtn.disabled = Boolean(s.busy);
}

function showPending(p) {
  pending.classList.remove("hidden");
  pendingText.textContent = `[${p.risk}] ${p.reason}\n${p.tool} ${JSON.stringify(p.args || {}).slice(0, 400)}`;
}

async function refreshAgents() {
  const data = await api("/api/agents");
  agentsEl.innerHTML = "";
  for (const agent of data.agents || []) {
    const li = document.createElement("li");
    li.textContent = `${agent.name}: ${agent.role || ""}`;
    agentsEl.appendChild(li);
  }
}

async function refreshImprovements() {
  const data = await api("/api/improvements");
  improvementsEl.innerHTML = "";
  for (const row of data.improvements || []) {
    const li = document.createElement("li");
    li.textContent = `${row.area}: ${row.note}`;
    improvementsEl.appendChild(li);
  }
}

async function poll() {
  try {
    const data = await api(`/api/events?since=${since}`);
    for (const ev of data.events || []) {
      since = Math.max(since, ev.id);
      handle(ev);
    }
    runBtn.disabled = Boolean(data.busy);
    meta.textContent = data.busy ? "running" : "idle";
  } catch (err) {
    meta.textContent = String(err.message || err);
  }
}

function handle(ev) {
  const d = ev.data || {};
  if (ev.type === "plan" && d.subgoals) {
    planEl.innerHTML = "";
    for (const g of d.subgoals) {
      const li = document.createElement("li");
      li.textContent = `${g.id}: ${g.title}`;
      planEl.appendChild(li);
    }
  }
  if (ev.type === "tool") addLog("", `tool ${d.name}`, JSON.stringify(d.args || {}));
  if (ev.type === "tool_result") addLog(d.ok ? "ok" : "bad", `${d.name}`, (d.output || "").slice(0, 800));
  if (ev.type === "model") addLog("", "model", d.text);
  if (ev.type === "confirm") {
    showPending(d);
    addLog("warn", "confirmation required", d.reason);
  }
  if (ev.type === "done") {
    pending.classList.add("hidden");
    addLog(d.ok ? "ok" : "bad", "report", d.report);
    refreshImprovements();
  }
  if (ev.type === "error") addLog("bad", "error", d.message);
}

autonomy.addEventListener("change", async () => {
  const level = Number(autonomy.value);
  autonomyLabel.textContent = LEVELS[level];
  await api("/api/autonomy", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ level }),
  });
});

document.getElementById("runForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const task = taskEl.value.trim();
  if (!task) return;
  logEl.innerHTML = "";
  await api("/api/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ task, autonomy: Number(autonomy.value) }),
  });
});

document.getElementById("improveForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const path = document.getElementById("improvePath").value.trim();
  if (!path) return;
  try {
    const report = await api("/api/improve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path, apply: false }),
    });
    addLog(report.fails ? "warn" : "ok", `scan ${report.name} ${report.score}`, JSON.stringify(report.checks, null, 2).slice(0, 2000));
  } catch (err) {
    addLog("bad", "improve scan failed", String(err.message || err));
  }
});

document.getElementById("spawnForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const body = Object.fromEntries(fd.entries());
  try {
    const result = await api("/api/spawn", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    addLog("ok", "spawned", result.run);
    refreshAgents();
  } catch (err) {
    addLog("bad", "spawn failed", String(err.message || err));
  }
});

document.getElementById("approve").addEventListener("click", () =>
  api("/api/confirm", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ approve: true }) })
);
document.getElementById("deny").addEventListener("click", () =>
  api("/api/confirm", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ approve: false }) })
);

refreshHealth();
refreshAgents();
refreshImprovements();
setInterval(poll, 700);
setInterval(refreshHealth, 4000);
