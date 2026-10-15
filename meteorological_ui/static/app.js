const $ = (id) => document.getElementById(id);

function showError(msg) {
  const el = $("error");
  if (!msg) {
    el.classList.add("hidden");
    el.textContent = "";
    return;
  }
  el.classList.remove("hidden");
  el.textContent = msg;
}

function drawLineChart(canvas, values, opts = {}) {
  const ctx = canvas.getContext("2d");
  const w = canvas.width;
  const h = canvas.height;
  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = "#0a101c";
  ctx.fillRect(0, 0, w, h);

  if (!values.length) {
    ctx.fillStyle = "#9aa8c7";
    ctx.font = "16px sans-serif";
    ctx.fillText("No data", 24, h / 2);
    return;
  }

  const pad = 36;
  const nums = values.map((v) => Number(v));
  const min = Math.min(...nums);
  const max = Math.max(...nums);
  const span = max - min || 1;

  ctx.strokeStyle = "#243149";
  ctx.beginPath();
  ctx.moveTo(pad, pad);
  ctx.lineTo(pad, h - pad);
  ctx.lineTo(w - pad, h - pad);
  ctx.stroke();

  ctx.fillStyle = "#9aa8c7";
  ctx.font = "12px sans-serif";
  ctx.fillText(String(max), 6, pad + 4);
  ctx.fillText(String(min), 6, h - pad);

  ctx.strokeStyle = opts.color || "#4da3ff";
  ctx.lineWidth = 2;
  ctx.beginPath();
  nums.forEach((n, i) => {
    const x = pad + (i * (w - 2 * pad)) / Math.max(nums.length - 1, 1);
    const y = h - pad - ((n - min) / span) * (h - 2 * pad);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();
}

function renderPeriods(periods) {
  const root = $("periods");
  root.innerHTML = "";
  periods.slice(0, 12).forEach((p) => {
    const div = document.createElement("div");
    div.className = "period";
    div.innerHTML = `<strong>${p.name || ""}</strong>
      <div class="temp">${p.temperature ?? "—"}°${p.temperatureUnit || "F"}</div>
      <div>${p.windDirection || ""} ${p.windSpeed || ""}</div>
      <div>${p.shortForecast || ""}</div>`;
    root.appendChild(div);
  });
}

function renderAlerts(alerts) {
  const root = $("alerts");
  if (!alerts || !alerts.length) {
    root.textContent = "None active for this point.";
    return;
  }
  root.innerHTML = "";
  alerts.forEach((a) => {
    const div = document.createElement("div");
    div.className = "alert";
    div.innerHTML = `<strong>${a.event || "Alert"}</strong><div>${a.headline || ""}</div>`;
    root.appendChild(div);
  });
}

function setupMaps(maps) {
  const pick = $("mapPick");
  pick.innerHTML = "";
  Object.entries(maps).forEach(([key, meta]) => {
    const opt = document.createElement("option");
    opt.value = key;
    opt.textContent = meta.label;
    pick.appendChild(opt);
  });
  const apply = () => {
    const meta = maps[pick.value];
    if (!meta) return;
    $("mapLabel").textContent = meta.label + " · " + meta.url;
    $("mapImg").src = meta.url + (meta.url.includes("?") ? "&" : "?") + "t=" + Date.now();
  };
  pick.onchange = apply;
  apply();
}

async function loadForecast(query) {
  showError("");
  $("go").disabled = true;
  $("status").textContent = "fetching NWS…";
  try {
    const url = "/api/forecast?q=" + encodeURIComponent(query);
    const res = await fetch(url);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || res.statusText);

    $("place").textContent = `${data.place || query} · ${data.lat.toFixed(3)}, ${data.lon.toFixed(3)} · office ${data.office || "?"}`;
    $("status").textContent = "live · free data";

    const temps = (data.hourly || []).map((h) => h.temperature).filter((v) => v != null);
    const pops = (data.hourly || []).map((h) => h.probabilityOfPrecipitation ?? 0);
    drawLineChart($("tempChart"), temps, { color: "#ffb020" });
    drawLineChart($("popChart"), pops, { color: "#4da3ff" });
    renderPeriods(data.periods || []);
    renderAlerts(data.alerts || []);
    setupMaps(data.maps || {});
  } catch (err) {
    showError(String(err.message || err));
    $("status").textContent = "error";
  } finally {
    $("go").disabled = false;
  }
}

async function boot() {
  try {
    const health = await fetch("/api/health").then((r) => r.json());
    $("status").textContent = health.ok ? "ready · no charges" : "degraded";
  } catch {
    $("status").textContent = "server issue";
  }

  const presets = await fetch("/api/presets").then((r) => r.json()).catch(() => ({ presets: [] }));
  const sel = $("preset");
  (presets.presets || []).forEach((name) => {
    const opt = document.createElement("option");
    opt.value = name;
    opt.textContent = name;
    sel.appendChild(opt);
  });
  sel.onchange = () => {
    if (sel.value) {
      $("q").value = sel.value;
      loadForecast(sel.value);
    }
  };

  $("lookup").onsubmit = (e) => {
    e.preventDefault();
    loadForecast($("q").value.trim());
  };

  loadForecast($("q").value.trim() || "Buffalo");
}

boot();
