/* ═══════════════════════════════════════════════════
   ChainPredictAI — app.js
   All state management, API calls, and chart rendering
   ═══════════════════════════════════════════════════ */

const API_BASE = "http://localhost:5000";

// ── State ────────────────────────────────────────────
const state = {
  weather:      "",
  traffic:      "",
  vehicle_type: "",
  charts:       {},
};

// ── On Load ──────────────────────────────────────────
window.addEventListener("DOMContentLoaded", () => {
  checkHealth();
  setInterval(checkHealth, 30_000);
  syncDistance(100);
  document.getElementById("distance").addEventListener("input", e => {
    syncDistance(e.target.value, false);
  });
});

// ── Health Check ─────────────────────────────────────
async function checkHealth() {
  const dot   = document.getElementById("status-dot");
  const label = document.getElementById("status-label");
  try {
    const res  = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(4000) });
    const data = await res.json();
    if (data.status === "ok") {
      dot.className   = "status-dot online";
      label.textContent = data.model_ready ? "Model Ready" : "No Model";
    } else {
      throw new Error();
    }
  } catch {
    dot.className   = "status-dot offline";
    label.textContent = "Offline";
  }
}

// ── Tab Switching ─────────────────────────────────────
function switchTab(name) {
  document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
  document.querySelectorAll(".nav-tab").forEach(t => t.classList.remove("active"));
  document.getElementById(`panel-${name}`).classList.add("active");
  document.getElementById(`tab-${name}`).classList.add("active");

  if (name === "dashboard") loadDashboard();
  if (name === "history")   loadHistory();
}

// ── Option Button Selection ───────────────────────────
function selectOption(btn) {
  const group = btn.dataset.group;
  const value = btn.dataset.value;
  document.querySelectorAll(`[data-group="${group}"]`).forEach(b => b.classList.remove("selected"));
  btn.classList.add("selected");
  state[group] = value;
  document.getElementById(group).value = value;
}

// ── Distance Slider Sync ──────────────────────────────
function syncDistance(val, fromSlider = true) {
  const v = parseFloat(val) || 0;
  if (fromSlider) document.getElementById("distance").value = v;
  document.getElementById("distance-slider").value = Math.min(v, 500);
  document.getElementById("distance-badge").textContent = `${v} km`;
  // Update slider background fill
  const pct = Math.min((v / 500) * 100, 100);
  document.getElementById("distance-slider").style.background =
    `linear-gradient(to right, var(--accent) ${pct}%, rgba(255,255,255,0.1) ${pct}%)`;
}

// ── Prediction Submit ─────────────────────────────────
async function submitPrediction(e) {
  e.preventDefault();
  clearError();

  // Validate selections
  const missing = [];
  if (!state.weather)      missing.push("Weather");
  if (!state.traffic)      missing.push("Traffic");
  if (!state.vehicle_type) missing.push("Vehicle Type");
  if (missing.length) { showError(`Please select: ${missing.join(", ")}`); return; }

  const body = {
    source:       document.getElementById("source").value.trim(),
    destination:  document.getElementById("destination").value.trim(),
    distance:     parseFloat(document.getElementById("distance").value),
    weather:      state.weather,
    traffic:      state.traffic,
    vehicle_type: state.vehicle_type,
  };

  setLoading(true);

  try {
    const res  = await fetch(`${API_BASE}/predict`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(body),
      signal:  AbortSignal.timeout(10_000),
    });

    const data = await res.json();

    if (!res.ok) {
      showError(data.error || "Prediction failed. Please try again.");
      return;
    }

    displayResult(data);
    showToast("✅ Prediction complete!");
  } catch (err) {
    showError("Cannot reach the backend. Make sure Flask is running on port 5000.");
  } finally {
    setLoading(false);
  }
}

// ── Display Result ────────────────────────────────────
function displayResult(d) {
  document.getElementById("result-placeholder").classList.add("hidden");
  const content = document.getElementById("result-content");
  content.classList.remove("hidden");

  const isDelayed = d.prediction === "Delayed";

  // Verdict Banner
  const banner = document.getElementById("verdict-banner");
  banner.className = `verdict-banner ${isDelayed ? "delayed" : "on-time"}`;
  document.getElementById("verdict-icon").textContent  = isDelayed ? "⏰" : "✅";
  document.getElementById("verdict-label").textContent = d.prediction;
  document.getElementById("verdict-route").textContent = `${d.source} → ${d.destination}`;

  // Dials
  animateDial("dial-ontime-circle", d.ontime_probability, "dial-ontime-pct");
  animateDial("dial-delay-circle",  d.delay_probability,  "dial-delay-pct");

  // Stat Chips
  document.getElementById("chip-distance").textContent = `📏 ${d.distance} km`;
  document.getElementById("chip-weather").textContent  = `🌡️ ${d.weather}`;
  document.getElementById("chip-traffic").textContent  = `🚦 ${d.traffic}`;
  document.getElementById("chip-vehicle").textContent  = `🚗 ${d.vehicle_type}`;

  // Suggestions
  const list = document.getElementById("suggestions-list");
  list.innerHTML = "";
  (d.suggestions || []).forEach((s, i) => {
    const el = document.createElement("div");
    el.className = "suggestion-item";
    el.style.animationDelay = `${i * 60}ms`;
    el.innerHTML = `
      <span class="sugg-icon">${s.icon}</span>
      <div>
        <div class="sugg-title">${s.title}</div>
        <div class="sugg-reason">${s.reason}</div>
      </div>`;
    list.appendChild(el);
  });
}

// ── Dial Animation ────────────────────────────────────
function animateDial(circleId, pct, labelId) {
  const circle = document.getElementById(circleId);
  const label  = document.getElementById(labelId);
  const r = 50;
  const circ = 2 * Math.PI * r;  // ≈ 314
  const fill = (pct / 100) * circ;

  requestAnimationFrame(() => {
    circle.style.strokeDasharray = `${fill} ${circ}`;
  });
  // Animate the number
  let current = 0;
  const step  = pct / 40;
  const timer = setInterval(() => {
    current = Math.min(current + step, pct);
    label.textContent = `${current.toFixed(1)}%`;
    if (current >= pct) clearInterval(timer);
  }, 18);
}

// ── Form Helpers ──────────────────────────────────────
function showError(msg) {
  const el = document.getElementById("form-error");
  el.textContent = msg;
  el.classList.remove("hidden");
}
function clearError() {
  document.getElementById("form-error").classList.add("hidden");
}
function setLoading(on) {
  const btn    = document.getElementById("predict-btn");
  const text   = btn.querySelector(".btn-text");
  const loader = document.getElementById("btn-loader");
  btn.disabled            = on;
  text.textContent        = on ? "Predicting…" : "🔮 Predict Delay";
  loader.classList.toggle("hidden", !on);
}

// ── Toast ─────────────────────────────────────────────
let _toastTimer;
function showToast(msg) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.classList.add("show");
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => el.classList.remove("show"), 3000);
}

// ── Dashboard ─────────────────────────────────────────
async function loadDashboard() {
  const btn = document.getElementById("refresh-btn");
  if (btn) { btn.textContent = "↻ Loading…"; btn.disabled = true; }

  try {
    const res  = await fetch(`${API_BASE}/dashboard`, { signal: AbortSignal.timeout(6000) });
    const data = await res.json();
    renderDashboard(data);
  } catch {
    showToast("⚠️ Could not load dashboard. Is Flask running?");
  } finally {
    if (btn) { btn.textContent = "↻ Refresh"; btn.disabled = false; }
  }
}

function renderDashboard(d) {
  const empty = document.getElementById("empty-dashboard");
  const kpi   = document.getElementById("kpi-grid");
  const charts = document.querySelector(".charts-grid");

  if (d.total === 0) {
    empty.classList.remove("hidden");
    kpi.style.display = "none";
    charts.style.display = "none";
    return;
  }
  empty.classList.add("hidden");
  kpi.style.display    = "";
  charts.style.display = "";

  // KPI cards
  animateCount("kpi-total-val",  d.total);
  animateCount("kpi-ontime-val", d.on_time);
  animateCount("kpi-delayed-val", d.delayed);
  document.getElementById("kpi-rate-val").textContent = `${d.on_time_pct}%`;

  // Donut chart
  buildOrUpdate("donut-chart", "doughnut", {
    labels: ["On Time", "Delayed"],
    datasets: [{
      data:            [d.on_time, d.delayed],
      backgroundColor: ["#48bb78", "#fc5c7d"],
      borderColor:     ["#0a0d14"],
      borderWidth:     3,
      hoverOffset:     8,
    }],
  }, {
    plugins: {
      legend: { labels: { color: "#7d8fa8", font: { family: "Inter", size: 12 } } },
    },
    cutout: "68%",
  });

  // Weather chart
  const wLabels = Object.keys(d.weather_breakdown);
  const wData   = Object.values(d.weather_breakdown);
  buildOrUpdate("weather-chart", "bar", {
    labels: wLabels,
    datasets: [{
      label: "Shipments",
      data:  wData,
      backgroundColor: ["#f6ad55", "#63b3ed", "#7c5cfc"],
      borderRadius: 8,
    }],
  }, barOpts("Shipments"));

  // Traffic chart
  const tLabels = Object.keys(d.traffic_breakdown);
  const tData   = Object.values(d.traffic_breakdown);
  buildOrUpdate("traffic-chart", "bar", {
    labels: tLabels,
    datasets: [{
      label: "Shipments",
      data:  tData,
      backgroundColor: ["#48bb78", "#f6ad55", "#fc5c7d"],
      borderRadius: 8,
    }],
  }, barOpts("Shipments"));

  // Trend chart
  const trendLabels   = d.trend.map(t => t.date);
  const trendOntime   = d.trend.map(t => t.on_time);
  const trendDelayed  = d.trend.map(t => t.delayed);
  buildOrUpdate("trend-chart", "line", {
    labels: trendLabels,
    datasets: [
      {
        label: "On Time",
        data:  trendOntime,
        borderColor: "#48bb78",
        backgroundColor: "rgba(72,187,120,0.12)",
        fill: true,
        tension: 0.4,
        pointBackgroundColor: "#48bb78",
        pointRadius: 4,
      },
      {
        label: "Delayed",
        data:  trendDelayed,
        borderColor: "#fc5c7d",
        backgroundColor: "rgba(252,92,125,0.12)",
        fill: true,
        tension: 0.4,
        pointBackgroundColor: "#fc5c7d",
        pointRadius: 4,
      },
    ],
  }, {
    plugins: {
      legend: { labels: { color: "#7d8fa8", font: { family: "Inter", size: 12 } } },
    },
    scales: {
      x: { ticks: { color: "#7d8fa8" }, grid: { color: "rgba(255,255,255,0.04)" } },
      y: { ticks: { color: "#7d8fa8" }, grid: { color: "rgba(255,255,255,0.04)" }, beginAtZero: true },
    },
  });
}

function barOpts(label) {
  return {
    plugins: {
      legend: { display: false },
    },
    scales: {
      x: { ticks: { color: "#7d8fa8" }, grid: { display: false } },
      y: { ticks: { color: "#7d8fa8" }, grid: { color: "rgba(255,255,255,0.04)" }, beginAtZero: true },
    },
    borderRadius: 8,
  };
}

function buildOrUpdate(id, type, data, opts) {
  if (state.charts[id]) {
    state.charts[id].data = data;
    state.charts[id].options = buildChartOptions(opts);
    state.charts[id].update();
    return;
  }
  const ctx = document.getElementById(id).getContext("2d");
  state.charts[id] = new Chart(ctx, {
    type,
    data,
    options: buildChartOptions(opts),
  });
}

function buildChartOptions(extra = {}) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 800, easing: "easeInOutQuart" },
    ...extra,
  };
}

function animateCount(elId, target) {
  const el = document.getElementById(elId);
  let current = 0;
  const step  = Math.max(1, Math.ceil(target / 30));
  const timer = setInterval(() => {
    current = Math.min(current + step, target);
    el.textContent = current;
    if (current >= target) clearInterval(timer);
  }, 20);
}

// ── History ────────────────────────────────────────────
async function loadHistory() {
  try {
    const res   = await fetch(`${API_BASE}/history`, { signal: AbortSignal.timeout(6000) });
    const items = await res.json();
    renderHistory(items);
  } catch {
    showToast("⚠️ Could not load history. Is Flask running?");
  }
}

function renderHistory(items) {
  const list  = document.getElementById("history-list");
  const empty = document.getElementById("empty-history");
  list.innerHTML = "";

  if (!items || items.length === 0) {
    empty.classList.remove("hidden");
    return;
  }
  empty.classList.add("hidden");

  items.forEach((r, i) => {
    const isDelayed = r.prediction === "Delayed";
    const el = document.createElement("div");
    el.className = `history-item ${isDelayed ? "delayed" : "on-time"}`;
    el.style.animationDelay = `${i * 50}ms`;
    el.innerHTML = `
      <div class="hist-verdict">${isDelayed ? "⏰" : "✅"}</div>
      <div class="hist-body">
        <div class="hist-route">${r.source} → ${r.destination}</div>
        <div class="hist-meta">${r.timestamp} &nbsp;·&nbsp; ${r.distance} km &nbsp;·&nbsp; ${r.weather} &nbsp;·&nbsp; ${r.traffic} traffic &nbsp;·&nbsp; ${r.vehicle_type}</div>
      </div>
      <div class="hist-right">
        <span class="hist-badge ${isDelayed ? "delayed" : "on-time"}">${r.prediction}</span>
        <div class="hist-prob">Delay ${r.delay_probability}%</div>
      </div>`;
    list.appendChild(el);
  });
}
