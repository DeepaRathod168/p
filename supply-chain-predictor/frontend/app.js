/* ════════════════════════════════════════════════════════════
   ChainPredictAI v2.0 — app.js
   Real-time logistics intelligence frontend
   ════════════════════════════════════════════════════════════ */

const API_BASE = "http://localhost:5000";

// ── App State ────────────────────────────────────────────────
const state = {
  weather:     "",         // selected or auto-detected
  traffic:     "",         // selected or auto-detected
  vehicle_type: "",        // selected
  charts:      {},         // Chart.js instances keyed by canvas id
  map:         null,       // Leaflet map instance
  mapMarkers:  [],         // Leaflet marker array
  mapLine:     null,       // Leaflet polyline
  routeData:   null,       // last /route response
  allHistory:  [],         // full history array for filtering
  prevDelayProb: null,     // for change-detection notifications

  // ── Tracking ──────────────────────────────────────────────
  trk: {
    vehicle:     "Van",    // vehicle selection in new-shipment form
    activeId:    null,     // shipment ID currently being tracked
    prevStatus:  null,     // last known status (for change alerts)
    pollTimer:   null,     // setInterval handle for live polling
    trkMap:      null,     // Leaflet map in tracking tab
    truckMarker: null,     // animated truck Leaflet marker
    srcMarker:   null,     // source city marker
    dstMarker:   null,     // destination city marker
    routeLine:   null,     // dashed route polyline
    lastLat:     null,     // for smooth truck animation
    lastLon:     null,
    animFrame:   null,     // requestAnimationFrame handle
  },
};

// ═══════════════════════════════════════════════════════════
//  Initialization
// ═══════════════════════════════════════════════════════════
window.addEventListener("DOMContentLoaded", () => {
  checkHealth();
  fetchTrafficNow();
  setInterval(checkHealth, 30_000);   // health ping every 30 s

  // Auto-resolve when both city inputs are filled (on blur)
  const autoResolve = debounce(() => {
    const src = document.getElementById("source").value.trim();
    const dst = document.getElementById("destination").value.trim();
    if (src && dst) autoResolveRoute();
  }, 600);

  document.getElementById("source").addEventListener("blur", autoResolve);
  document.getElementById("destination").addEventListener("blur", autoResolve);

  // Distance: update pin label when typed
  document.getElementById("distance").addEventListener("input", e => {
    const v = parseFloat(e.target.value) || 0;
    document.getElementById("distance-pin").textContent = v ? `${v} km` : "— km";
  });
});

// ═══════════════════════════════════════════════════════════
//  Utilities
// ═══════════════════════════════════════════════════════════
function debounce(fn, ms) {
  let timer;
  return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), ms); };
}

function vehicleEmoji(v) {
  return { Bike: "🏍️", Van: "🚐", Truck: "🚚" }[v] || "🚗";
}

function weatherEmoji(w) {
  return { Sunny: "☀️", Rainy: "🌧️", Storm: "⛈️" }[w] || "🌡️";
}

function trafficEmoji(t) {
  return { Low: "🟢", Medium: "🟡", High: "🔴" }[t] || "🚦";
}

function fmtTime(mins) {
  if (mins >= 60) return `${Math.floor(mins / 60)}h ${mins % 60}m`;
  return `${mins}m`;
}

// Smooth number counter animation
function animateNumber(elId, from, to, suffix = "", decimals = 1, durationMs = 800) {
  const el = document.getElementById(elId);
  if (!el) return;
  const start = performance.now();
  const update = (now) => {
    const t = Math.min((now - start) / durationMs, 1);
    const ease = 1 - Math.pow(1 - t, 3);
    const val = from + (to - from) * ease;
    el.textContent = `${val.toFixed(decimals)}${suffix}`;
    if (t < 1) requestAnimationFrame(update);
  };
  requestAnimationFrame(update);
}

// Integer counter (for KPI cards)
function animateCount(elId, target) {
  const el = document.getElementById(elId);
  if (!el) return;
  let cur = 0;
  const step = Math.max(1, Math.ceil(target / 30));
  const t = setInterval(() => {
    cur = Math.min(cur + step, target);
    el.textContent = cur;
    if (cur >= target) clearInterval(t);
  }, 20);
}

// ═══════════════════════════════════════════════════════════
//  Health Check
// ═══════════════════════════════════════════════════════════
async function checkHealth() {
  const dot   = document.getElementById("status-dot");
  const label = document.getElementById("status-label");
  try {
    const res  = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(4000) });
    const data = await res.json();
    if (data.status === "ok") {
      dot.className     = "status-dot online";
      label.textContent = data.model_ready ? "Model Ready" : "No Model";
    } else throw new Error();
  } catch {
    dot.className     = "status-dot offline";
    label.textContent = "Offline";
  }
}

// ═══════════════════════════════════════════════════════════
//  Traffic Auto-detection
// ═══════════════════════════════════════════════════════════
async function fetchTrafficNow() {
  try {
    const res  = await fetch(`${API_BASE}/traffic`, { signal: AbortSignal.timeout(5000) });
    const data = await res.json();
    applyTrafficStatus(data.level, data.reason);
    if (!state.traffic) {
      state.traffic = data.level;
      document.getElementById("traffic").value = data.level;
    }
  } catch {
    applyTrafficStatus("Medium", "Could not detect");
  }
}

function applyTrafficStatus(level, reason) {
  const icons = { Low: "🟢", Medium: "🟡", High: "🔴" };
  document.getElementById("tr-icon").textContent  = icons[level] || "🚦";
  document.getElementById("tr-label").textContent = `${level} Traffic`;
  document.getElementById("tr-sub").textContent   = reason;
  document.getElementById("traffic-badge").classList.add("loaded");
}

// ═══════════════════════════════════════════════════════════
//  Auto-resolve Route (geocoding + weather)
// ═══════════════════════════════════════════════════════════
async function autoResolveRoute() {
  const source = document.getElementById("source").value.trim();
  const dest   = document.getElementById("destination").value.trim();
  if (!source || !dest) { showError("Enter both source and destination first."); return; }
  clearError();

  // Button loading state
  const btn     = document.getElementById("resolve-btn");
  const btnText = document.getElementById("resolve-text");
  const btnIcon = document.getElementById("resolve-icon");
  btn.disabled  = true;
  btnIcon.textContent = "⟳";
  btnIcon.classList.add("spinner");
  btnText.textContent = "Detecting route, weather & traffic…";

  // Show weather loading
  document.getElementById("wx-label").textContent = "Fetching…";
  document.getElementById("wx-sub").textContent   = "";
  document.getElementById("weather-badge").classList.remove("loaded");
  document.getElementById("weather-badge").classList.add("loading-pulse");

  try {
    const [routeRes, weatherRes, trafficRes] = await Promise.all([
      fetch(`${API_BASE}/route?source=${encodeURIComponent(source)}&destination=${encodeURIComponent(dest)}`,   { signal: AbortSignal.timeout(14000) }),
      fetch(`${API_BASE}/weather?city=${encodeURIComponent(source)}`,                                           { signal: AbortSignal.timeout(8000)  }),
      fetch(`${API_BASE}/traffic`,                                                                               { signal: AbortSignal.timeout(5000)  }),
    ]);

    // ── Route ──────────────────────────────────────────────
    if (routeRes.ok) {
      const rd = await routeRes.json();
      state.routeData = rd;
      const km = rd.estimated_road_km;
      document.getElementById("distance").value          = km;
      document.getElementById("distance-pin").textContent = `${km} km`;
      showMap(rd);
      showToast(`✅ Route detected: ${km} km`);
    } else {
      const err = await routeRes.json();
      showError(`Route: ${err.error || "unknown error"}. Enter distance manually.`);
    }

    // ── Weather ────────────────────────────────────────────
    if (weatherRes.ok) {
      const wd = await weatherRes.json();
      document.getElementById("wx-icon").textContent  = wd.icon || "🌡️";
      document.getElementById("wx-label").textContent = `${wd.condition}${wd.temperature !== undefined ? ` · ${wd.temperature}°C` : ""}`;
      document.getElementById("wx-sub").textContent   = `${wd.description}${wd.source === "simulated" ? " (simulated)" : ""}`;
      document.getElementById("weather-badge").classList.add("loaded");

      // Auto-select weather button if not overridden
      if (!state.weather) {
        const wBtn = document.querySelector(`[data-group="weather"][data-value="${wd.condition}"]`);
        if (wBtn) selectOption(wBtn);
      }
    }

    // ── Traffic ────────────────────────────────────────────
    if (trafficRes.ok) {
      const td = await trafficRes.json();
      applyTrafficStatus(td.level, td.reason);
      if (!state.traffic) {
        state.traffic = td.level;
        document.getElementById("traffic").value = td.level;
        const tBtn = document.querySelector(`[data-group="traffic"][data-value="${td.level}"]`);
        if (tBtn) selectOption(tBtn);
      }
    }

  } catch (err) {
    showError("Failed to fetch data. Check connection, or enter values manually.");
    document.getElementById("wx-label").textContent = "Could not fetch";
  } finally {
    document.getElementById("weather-badge").classList.remove("loading-pulse");
    btn.disabled = false;
    btnIcon.textContent = "🛰️";
    btnIcon.classList.remove("spinner");
    btnText.textContent = "Auto-detect Distance, Weather & Traffic";
  }
}

// ═══════════════════════════════════════════════════════════
//  Leaflet Map
// ═══════════════════════════════════════════════════════════
function showMap(routeData) {
  const container   = document.getElementById("map-container");
  const placeholder = document.getElementById("map-placeholder");
  container.classList.remove("hidden");
  placeholder.classList.add("hidden");

  const src = routeData.source;
  const dst = routeData.destination;

  document.getElementById("map-meta").textContent =
    `${routeData.straight_line_km} km straight · ${routeData.estimated_road_km} km road est.`;

  if (!state.map) {
    state.map = L.map("map-container", { zoomControl: true });
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      maxZoom: 18,
    }).addTo(state.map);
  }

  // Clear previous
  state.mapMarkers.forEach(m => state.map.removeLayer(m));
  if (state.mapLine) state.map.removeLayer(state.mapLine);
  state.mapMarkers = [];

  // Custom pin icons
  const makePin = (color, label) => L.divIcon({
    html: `<div style="
      background:${color};width:32px;height:32px;border-radius:50% 50% 50% 0;
      transform:rotate(-45deg);border:2.5px solid #fff;
      box-shadow:0 2px 10px rgba(0,0,0,0.25);
      display:flex;align-items:center;justify-content:center;
    "><span style="transform:rotate(45deg);font-size:12px;font-weight:700;color:#fff;">${label}</span></div>`,
    iconSize: [32, 32], iconAnchor: [16, 32], className: "",
  });

  const srcLatLng = [src.lat, src.lon];
  const dstLatLng = [dst.lat, dst.lon];

  const m1 = L.marker(srcLatLng, { icon: makePin("#4F46E5", "A") })
    .addTo(state.map)
    .bindPopup(`<strong>📍 From:</strong> ${src.name}`);
  const m2 = L.marker(dstLatLng, { icon: makePin("#EF4444", "B") })
    .addTo(state.map)
    .bindPopup(`<strong>🎯 To:</strong> ${dst.name}`);
  state.mapMarkers.push(m1, m2);

  state.mapLine = L.polyline([srcLatLng, dstLatLng], {
    color: "#4F46E5", weight: 3, opacity: 0.75, dashArray: "10 7",
  }).addTo(state.map);

  state.map.fitBounds(L.latLngBounds([srcLatLng, dstLatLng]), { padding: [50, 50] });
  setTimeout(() => state.map.invalidateSize(), 120);
}

function updateMapLineColor(isDelayed) {
  if (state.mapLine) {
    state.mapLine.setStyle({ color: isDelayed ? "#EF4444" : "#10B981" });
  }
}

// ═══════════════════════════════════════════════════════════
//  Tab Switching
// ═══════════════════════════════════════════════════════════
function switchTab(name) {
  document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
  document.querySelectorAll(".nav-tab").forEach(t => t.classList.remove("active"));
  document.getElementById(`panel-${name}`).classList.add("active");
  document.getElementById(`tab-${name}`).classList.add("active");
  if (name === "dashboard") loadDashboard();
  if (name === "history")   loadHistory();
  if (name === "predict" && state.map) setTimeout(() => state.map.invalidateSize(), 120);
}

// ═══════════════════════════════════════════════════════════
//  Option Button Selection
// ═══════════════════════════════════════════════════════════
function selectOption(btn) {
  const group = btn.dataset.group;
  const value = btn.dataset.value;
  document.querySelectorAll(`[data-group="${group}"]`).forEach(b => b.classList.remove("selected"));
  btn.classList.add("selected");
  state[group] = value;
  const hidden = document.getElementById(group);
  if (hidden) hidden.value = value;
}

// ═══════════════════════════════════════════════════════════
//  Prediction Submit
// ═══════════════════════════════════════════════════════════
async function submitPrediction(e) {
  e.preventDefault();
  clearError();

  const source = document.getElementById("source").value.trim();
  const dest   = document.getElementById("destination").value.trim();
  if (!source || !dest) { showError("Enter source and destination cities."); return; }

  const distVal = document.getElementById("distance").value;
  const body    = {
    source,
    destination:  dest,
    vehicle_type: state.vehicle_type || "Van",
  };

  if (distVal)       body.distance     = parseFloat(distVal);
  if (state.weather) body.weather      = state.weather;
  if (state.traffic) body.traffic      = state.traffic;

  // Pass known coordinates to skip re-geocoding on backend
  if (state.routeData) {
    body.lat_src = state.routeData.source.lat;
    body.lon_src = state.routeData.source.lon;
    body.lat_dst = state.routeData.destination.lat;
    body.lon_dst = state.routeData.destination.lon;
  }

  setLoading(true);

  try {
    const res  = await fetch(`${API_BASE}/predict`, {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify(body),
      signal:  AbortSignal.timeout(18_000),
    });
    const data = await res.json();

    if (!res.ok) { showError(data.error || "Prediction failed."); return; }

    // Detect change from previous prediction
    if (state.prevDelayProb !== null) {
      const delta = data.delay_probability - state.prevDelayProb;
      if (Math.abs(delta) >= 10) showNotification(delta);
    }
    state.prevDelayProb = data.delay_probability;

    displayResult(data);
    updateMapLineColor(data.prediction === "Delayed");
    showToast(`${data.prediction === "Delayed" ? "⏰" : "✅"} ${data.prediction}!`);

    // If we now have coordinates and didn't have a map yet, draw it
    if (!state.routeData && data.lat_src != null && data.lat_dst != null) {
      const synth = {
        source:      { name: source, lat: data.lat_src, lon: data.lon_src, display_name: source },
        destination: { name: dest,   lat: data.lat_dst, lon: data.lon_dst, display_name: dest   },
        straight_line_km:  data.distance,
        estimated_road_km: data.distance,
      };
      state.routeData = synth;
      showMap(synth);
    }

  } catch (err) {
    showError("Cannot reach backend. Make sure Flask is running on port 5000.");
  } finally {
    setLoading(false);
  }
}

// ═══════════════════════════════════════════════════════════
//  Display Result
// ═══════════════════════════════════════════════════════════
function displayResult(d) {
  document.getElementById("result-placeholder").classList.add("hidden");
  const content = document.getElementById("result-content");
  content.classList.remove("hidden");
  content.classList.add("anim-in");

  const isDelayed = d.prediction === "Delayed";

  // Verdict
  const banner = document.getElementById("verdict-banner");
  banner.className = `verdict-banner ${isDelayed ? "delayed" : "on-time"}`;
  document.getElementById("verdict-emoji").textContent =  isDelayed ? "⏰" : "✅";
  const lbl = document.getElementById("verdict-label");
  lbl.className = `verdict-label ${isDelayed ? "delayed" : "on-time"}`;
  lbl.textContent = d.prediction;
  document.getElementById("verdict-sub").textContent = `${d.source} → ${d.destination}`;

  // Probabilities (animated)
  animateNumber("prob-ontime", 0, d.ontime_probability, "%");
  animateNumber("prob-delay",  0, d.delay_probability,  "%");
  setTimeout(() => {
    document.getElementById("bar-ontime").style.width = `${d.ontime_probability}%`;
    document.getElementById("bar-delay").style.width  = `${d.delay_probability}%`;
  }, 80);

  // ETA chips
  document.getElementById("eta-dist").textContent    = `${d.distance} km`;
  document.getElementById("eta-time").textContent    = fmtTime(d.eta_minutes || 0);
  document.getElementById("eta-vehicle").textContent = `${vehicleEmoji(d.vehicle_type)} ${d.vehicle_type}`;
  document.getElementById("eta-weather").textContent = `${weatherEmoji(d.weather)} ${d.weather}`;

  // AI explanation
  document.getElementById("ai-text").textContent = d.delay_reason || "";

  // Suggestions
  const list = document.getElementById("sugg-list");
  list.innerHTML = "";
  (d.suggestions || []).forEach((s, i) => {
    const el = document.createElement("div");
    el.className = "sugg-item";
    el.style.animationDelay = `${i * 55}ms`;
    el.innerHTML = `
      <span class="sugg-icon">${s.icon}</span>
      <div>
        <div class="sugg-name">${s.title}</div>
        <div class="sugg-desc">${s.reason}</div>
      </div>`;
    list.appendChild(el);
  });
}

// ═══════════════════════════════════════════════════════════
//  Notification Banner (live change detection)
// ═══════════════════════════════════════════════════════════
function showNotification(delta) {
  const el = document.getElementById("notif-banner");
  el.className = "notif-banner " + (delta > 0 ? "warn" : "info");
  el.textContent = delta > 0
    ? `⚠️ Delay risk increased by ${delta.toFixed(1)}% since last check!`
    : `📉 Delay risk decreased by ${Math.abs(delta).toFixed(1)}% — conditions improving.`;
  el.classList.remove("hidden");
  setTimeout(() => el.classList.add("hidden"), 6000);
}

// ═══════════════════════════════════════════════════════════
//  Form Helpers
// ═══════════════════════════════════════════════════════════
function showError(msg) {
  const el = document.getElementById("form-error");
  el.textContent = msg;
  el.classList.remove("hidden");
}
function clearError() {
  document.getElementById("form-error").classList.add("hidden");
}
function setLoading(on) {
  const btn     = document.getElementById("predict-btn");
  const text    = document.getElementById("btn-text");
  const spinner = document.getElementById("btn-spinner");
  btn.disabled          = on;
  text.textContent      = on ? "Predicting…" : "🔮 Predict Delay";
  spinner.classList.toggle("hidden", !on);
}

// ═══════════════════════════════════════════════════════════
//  Toast
// ═══════════════════════════════════════════════════════════
let _toastTimer;
function showToast(msg) {
  const el = document.getElementById("toast");
  el.textContent = msg;
  el.classList.add("show");
  clearTimeout(_toastTimer);
  _toastTimer = setTimeout(() => el.classList.remove("show"), 3500);
}

// ═══════════════════════════════════════════════════════════
//  Dashboard
// ═══════════════════════════════════════════════════════════
async function loadDashboard() {
  const btn = document.getElementById("refresh-btn");
  if (btn) { btn.textContent = "↻ Loading…"; btn.disabled = true; }

  try {
    const res  = await fetch(`${API_BASE}/dashboard`, { signal: AbortSignal.timeout(8000) });
    const data = await res.json();
    renderDashboard(data);
  } catch {
    showToast("⚠️ Could not load dashboard.");
  } finally {
    if (btn) { btn.textContent = "↻ Refresh"; btn.disabled = false; }
  }
}

function renderDashboard(d) {
  const empty  = document.getElementById("empty-dashboard");
  const kpiG   = document.getElementById("kpi-grid");
  const chartG = document.getElementById("charts-grid");

  if (d.total === 0) {
    empty.classList.remove("hidden");
    kpiG.style.display   = "none";
    chartG.style.display = "none";
    return;
  }
  empty.classList.add("hidden");
  kpiG.style.display   = "";
  chartG.style.display = "";

  // KPIs
  animateCount("kpi-total",   d.total);
  animateCount("kpi-ontime",  d.on_time);
  animateCount("kpi-delayed", d.delayed);
  document.getElementById("kpi-rate").textContent = `${d.on_time_pct}%`;

  const C = { success:"#10B981", danger:"#EF4444", primary:"#4F46E5", warning:"#F59E0B", info:"#3B82F6", amber:"#D97706", violet:"#7C3AED" };
  const BASE_OPTS = {
    responsive: true, maintainAspectRatio: false,
    animation: { duration: 700, easing: "easeInOutQuart" },
    plugins: { legend: { labels: { color: "#475569", font: { family: "Inter", size: 12 } } } },
  };

  // Donut
  buildOrUpdate("donut-chart", "doughnut", {
    labels: ["On Time", "Delayed"],
    datasets: [{ data: [d.on_time, d.delayed], backgroundColor: [C.success, C.danger], borderColor: ["#fff"], borderWidth: 3, hoverOffset: 8 }],
  }, { ...BASE_OPTS, cutout: "68%" });

  // Weather bar
  buildOrUpdate("weather-chart", "bar", {
    labels: Object.keys(d.weather_breakdown),
    datasets: [{ label: "Shipments", data: Object.values(d.weather_breakdown), backgroundColor: [C.warning, C.info, C.violet], borderRadius: 8 }],
  }, {
    ...BASE_OPTS,
    plugins: { ...BASE_OPTS.plugins, legend: { display: false } },
    scales: {
      x: { ticks: { color: "#94A3B8" }, grid: { display: false } },
      y: { ticks: { color: "#94A3B8" }, grid: { color: "rgba(0,0,0,0.05)" }, beginAtZero: true },
    },
  });

  // Traffic bar
  buildOrUpdate("traffic-chart", "bar", {
    labels: Object.keys(d.traffic_breakdown),
    datasets: [{ label: "Shipments", data: Object.values(d.traffic_breakdown), backgroundColor: [C.success, C.warning, C.danger], borderRadius: 8 }],
  }, {
    ...BASE_OPTS,
    plugins: { ...BASE_OPTS.plugins, legend: { display: false } },
    scales: {
      x: { ticks: { color: "#94A3B8" }, grid: { display: false } },
      y: { ticks: { color: "#94A3B8" }, grid: { color: "rgba(0,0,0,0.05)" }, beginAtZero: true },
    },
  });

  // Daily trend line
  buildOrUpdate("trend-chart", "line", {
    labels: d.trend.map(t => t.date),
    datasets: [
      { label: "On Time",  data: d.trend.map(t => t.on_time),  borderColor: C.success, backgroundColor: "rgba(16,185,129,0.08)",  fill: true, tension: 0.4, pointBackgroundColor: C.success, pointRadius: 4 },
      { label: "Delayed",  data: d.trend.map(t => t.delayed),  borderColor: C.danger,  backgroundColor: "rgba(239,68,68,0.08)",    fill: true, tension: 0.4, pointBackgroundColor: C.danger,  pointRadius: 4 },
    ],
  }, {
    ...BASE_OPTS,
    scales: {
      x: { ticks: { color: "#94A3B8" }, grid: { color: "rgba(0,0,0,0.04)" } },
      y: { ticks: { color: "#94A3B8" }, grid: { color: "rgba(0,0,0,0.04)" }, beginAtZero: true },
    },
  });
}

function buildOrUpdate(id, type, data, opts) {
  if (state.charts[id]) {
    state.charts[id].data    = data;
    state.charts[id].options = opts;
    state.charts[id].update();
    return;
  }
  const ctx = document.getElementById(id)?.getContext("2d");
  if (!ctx) return;
  state.charts[id] = new Chart(ctx, { type, data, options: opts });
}

// ═══════════════════════════════════════════════════════════
//  History
// ═══════════════════════════════════════════════════════════
async function loadHistory() {
  const list  = document.getElementById("history-list");
  const empty = document.getElementById("empty-history");
  list.innerHTML = "";

  try {
    const res   = await fetch(`${API_BASE}/history?limit=20`, { signal: AbortSignal.timeout(8000) });
    const items = await res.json();
    state.allHistory = items;
    renderHistory(items);
  } catch {
    showToast("⚠️ Could not load history.");
  }
}

function filterHistory(filter, btn) {
  document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
  btn.classList.add("active");
  let filtered = state.allHistory;
  if (filter === "on-time") filtered = state.allHistory.filter(r => r.prediction === "On Time");
  if (filter === "delayed") filtered = state.allHistory.filter(r => r.prediction === "Delayed");
  renderHistory(filtered);
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
    el.style.animationDelay = `${i * 40}ms`;
    el.innerHTML = `
      <div class="hist-icon">${isDelayed ? "⏰" : "✅"}</div>
      <div class="hist-body">
        <div class="hist-route">${r.source} → ${r.destination}</div>
        <div class="hist-meta">
          ${r.timestamp} &nbsp;·&nbsp; ${r.distance ?? "—"} km
          &nbsp;·&nbsp; ${r.weather ? weatherEmoji(r.weather) + " " + r.weather : "—"}
          &nbsp;·&nbsp; ${r.traffic ? trafficEmoji(r.traffic) + " " + r.traffic : "—"}
          &nbsp;·&nbsp; ${r.vehicle_type ? vehicleEmoji(r.vehicle_type) + " " + r.vehicle_type : "—"}
        </div>
        ${r.delay_reason ? `<div class="hist-reason">${r.delay_reason}</div>` : ""}
      </div>
      <div class="hist-right">
        <span class="hist-badge ${isDelayed ? "delayed" : "on-time"}">${r.prediction}</span>
        <div class="hist-prob">Delay ${r.delay_probability}%</div>
      </div>`;
    list.appendChild(el);
  });
}
