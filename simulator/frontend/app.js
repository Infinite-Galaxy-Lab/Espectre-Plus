const $ = (id) => document.getElementById(id);
const history = [];
const wifiHistory = [];
let current = null;
let wifiState = null;
let wifiSource = "";

async function api(path, options = {}) {
  const response = await fetch(path, options);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return response.json();
}

async function post(action, value) {
  try {
    const state = await api("/api/control", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, value }),
    });
    render(state);
  } catch (error) {
    setOffline(error.message);
  }
}

function setOffline(message) {
  $("liveText").textContent = "连接失败";
  $("liveDot").parentElement.classList.add("off");
  $("statusText").textContent = message;
}

function setText(id, value) {
  $(id).textContent = value;
}


function setSwitchVisual(input, on) {
  const root = input.closest(".switch");
  const slider = root.querySelector(".slider");
  const knob = root.querySelector(".knob");
  root.classList.toggle("is-on", on);
  slider.style.background = on ? "rgba(94,234,212,.48)" : "#25364f";
  slider.style.boxShadow = on ? "inset 0 0 0 1px #5eead4" : "none";
  knob.style.left = on ? "21px" : "3px";
  knob.style.background = on ? "#5eead4" : "#b8c7df";
}

function render(state) {
  current = state;
  $("liveText").textContent = state.demo ? "演示运行" : "已暂停";
  $("liveDot").parentElement.classList.toggle("off", !state.demo);

  const occupied = state.occupancy;
  setText("occState", occupied ? "有人" : "无人");
  setText("occNote", occupied ? "存在信号已确认" : "等待有人进入");
  $("occState").style.color = occupied ? "var(--accent)" : "var(--muted)";

  setText("modeState", state.mode.toUpperCase());
  setText("modeNote", state.mode === "auto" ? "设备内自动策略" : "手动操作优先");
  $("modeState").style.color = state.mode === "auto" ? "var(--accent)" : "var(--warm)";
  setText("luxValue", Math.round(state.lux));
  setText("statusValue", state.status);
  $("statusValue").className = "status-pill" + (state.mode === "manual" ? " manual" : "");
  setText("statusText", state.demo
    ? "演示台架正在播放房间场景。"
    : "自动演示已暂停，可用下方按钮模拟手动操作。");

  setText("totalPower", state.power.total.toFixed(1));
  setText("mainPower", `${state.power.main.toFixed(1)} W`);
  setText("auxPower", `${state.power.aux.toFixed(1)} W`);

  $("mainOn").checked = state.lights.main.on;
  $("auxOn").checked = state.lights.aux.on;
  setSwitchVisual($("mainOn"), state.lights.main.on);
  setSwitchVisual($("auxOn"), state.lights.aux.on);
  if (document.activeElement !== $("mainBrightness")) {
    $("mainBrightness").value = state.lights.main.brightness;
  }
  if (document.activeElement !== $("auxBrightness")) {
    $("auxBrightness").value = state.lights.aux.brightness;
  }
  setText("mainBrightnessValue", `${state.lights.main.brightness}%`);
  setText("auxBrightnessValue", `${state.lights.aux.brightness}%`);
  setText("lightHint", state.mode === "auto" ? "自动模式" : "手动模式");

  setText("todayEnergy", state.energy.today_kwh.toFixed(3));
  setText("monthEnergy", state.energy.month_kwh.toFixed(3));
  setText("todayCost", state.energy.today_cost.toFixed(2));
  setText("monthCost", state.energy.month_cost.toFixed(2));
  if (document.activeElement !== $("price")) {
    $("price").value = state.energy.price.toFixed(2);
  }

  $("demoBadge").textContent = state.demo ? "演示运行" : "演示暂停";
  $("demoToggle").textContent = state.demo ? "暂停演示" : "继续演示";
  setText("presenceBtn", occupied ? "模拟无人" : "模拟有人");
  if (document.activeElement !== $("luxRange")) {
    $("luxRange").value = state.lux;
  }
  setText("luxRangeValue", `${Math.round(state.lux)} lx`);
  setText("updatedAt", new Date(state.updated).toLocaleTimeString("zh-CN", { hour12: false }));

  renderEvents(state.events);
  history.push(state.power.total);
  if (history.length > 60) history.shift();
  drawChart();
}

function renderEvents(events) {
  const list = $("eventsList");
  list.replaceChildren();
  [...events].reverse().forEach((event) => {
    const item = document.createElement("li");
    const time = document.createElement("time");
    time.textContent = event.time;
    const text = document.createElement("span");
    text.textContent = event.text;
    item.append(time, text);
    list.append(item);
  });
}

function drawChart() {
  const canvas = $("powerChart");
  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  const width = Math.max(rect.width, 200);
  const height = 132;
  if (canvas.width !== Math.round(width * dpr) || canvas.height !== Math.round(height * dpr)) {
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
  }
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, width, height);

  ctx.strokeStyle = "rgba(34,54,83,.55)";
  ctx.lineWidth = 1;
  for (let i = 1; i <= 3; i += 1) {
    const y = (height / 4) * i;
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(width, y);
    ctx.stroke();
  }

  if (history.length < 2) return;
  const max = Math.max(40, ...history) * 1.12;
  const step = width / (history.length - 1);
  const points = history.map((value, index) => ({
    x: index * step,
    y: height - (value / max) * (height - 16) - 8,
  }));

  ctx.beginPath();
  ctx.moveTo(points[0].x, points[0].y);
  points.slice(1).forEach((point) => ctx.lineTo(point.x, point.y));
  ctx.strokeStyle = "#5eead4";
  ctx.lineWidth = 2;
  ctx.lineJoin = "round";
  ctx.stroke();

  ctx.lineTo(width, height);
  ctx.lineTo(0, height);
  ctx.closePath();
  const fill = ctx.createLinearGradient(0, 0, 0, height);
  fill.addColorStop(0, "rgba(94,234,212,.22)");
  fill.addColorStop(1, "rgba(94,234,212,0)");
  ctx.fillStyle = fill;
  ctx.fill();
}

function renderWifi(wifi) {
  wifiState = wifi;
  const isMock = wifi.source === "mock";
  if (wifiSource !== wifi.source) {
    wifiHistory.length = 0;
    wifiSource = wifi.source;
  }
  const label = isMock ? "模拟 CSI" : (wifi.source_label || "ESPectre CSI");
  const channel = Number.isInteger(wifi.channel) ? `CH ${wifi.channel}` : "CH --";
  const status = {
    waiting: " · 等待数据",
    offline: " · 未连接",
    stale: " · 数据中断",
  }[wifi.status] || "";
  setText("wifiSource", `${label} · ${channel}${status}`);
  setText("wifiRssi", Number.isFinite(wifi.rssi_dbm) ? `${wifi.rssi_dbm.toFixed(1)} dBm` : "--");
  setText("wifiNoise", Number.isFinite(wifi.noise_dbm) ? `${wifi.noise_dbm.toFixed(1)} dBm` : "--");
  setText("wifiInterference", Number.isFinite(wifi.interference_pct) ? `${wifi.interference_pct}%` : "--");
  setText("wifiQuality", Number.isFinite(wifi.quality_pct) ? `${wifi.quality_pct}%` : "--");
  setText("wifiMetricLabel", isMock ? "干扰强度" : "CSI 波动");
  $("wifiBurstBtn").style.display = isMock ? "" : "none";
  $("wifiFineprint").textContent = isMock
    ? "当前为模拟 CSI 波形，用于验证图表和接口；接入 ESPectre 后替换数据源，不改前端。"
    : "数据来自 ESPectre Direct API 原始 CSI 流；上方为归一化 CSI 幅值，下方为相邻帧形状变化平滑得到的 CSI 波动，用于观察信道扰动，不等同于绝对干扰功率。";
  $("footerWifi").textContent = isMock
    ? "WiFi 波形当前为模拟数据"
    : "WiFi 波形来自 ESPectre CSI（波动为派生指标）";

  if (Number.isFinite(wifi.interference_pct)) {
    wifiHistory.push(wifi.interference_pct);
    if (wifiHistory.length > 60) wifiHistory.shift();
  }
  if (Number.isFinite(wifi.interference_pct)) {
    $("wifiInterference").style.color = wifi.interference_pct >= 60 ? "var(--warm)" : "var(--text)";
  }
  if (Number.isFinite(wifi.quality_pct)) {
    $("wifiQuality").style.color = wifi.quality_pct >= 70 ? "var(--accent)" : "var(--warm)";
  }
  drawWifiChart();
}

function drawWifiChart() {
  const canvas = $("wifiChart");
  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  const width = Math.max(rect.width, 220);
  const height = 186;
  if (canvas.width !== Math.round(width * dpr) || canvas.height !== Math.round(height * dpr)) {
    canvas.width = Math.round(width * dpr);
    canvas.height = Math.round(height * dpr);
  }
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, width, height);

  const top = 8;
  const topBottom = 124;
  const bottomTop = 146;
  const bottomBottom = 180;
  ctx.strokeStyle = "rgba(34,54,83,.55)";
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i += 1) {
    const y = top + ((topBottom - top) / 4) * i;
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(width, y);
    ctx.stroke();
  }
  ctx.strokeStyle = "rgba(34,54,83,.35)";
  ctx.beginPath();
  ctx.moveTo(0, bottomTop);
  ctx.lineTo(width, bottomTop);
  ctx.stroke();

  if (!wifiState || !Array.isArray(wifiState.subcarriers) || wifiState.subcarriers.length < 2) {
    ctx.fillStyle = "#60789d";
    ctx.font = "12px 'Segoe UI', sans-serif";
    ctx.fillText("等待 CSI 数据…", 12, 68);
    return;
  }

  const values = wifiState.subcarriers;
  const step = width / (values.length - 1);
  const points = values.map((value, index) => ({
    x: index * step,
    y: top + (1 - value) * (topBottom - top - 4) + 2,
  }));
  ctx.beginPath();
  ctx.moveTo(points[0].x, points[0].y);
  points.slice(1).forEach((point) => ctx.lineTo(point.x, point.y));
  ctx.strokeStyle = "#38bdf8";
  ctx.lineWidth = 1.8;
  ctx.lineJoin = "round";
  ctx.stroke();
  ctx.lineTo(width, topBottom);
  ctx.lineTo(0, topBottom);
  ctx.closePath();
  const fill = ctx.createLinearGradient(0, top, 0, topBottom);
  fill.addColorStop(0, "rgba(56,189,248,.24)");
  fill.addColorStop(1, "rgba(56,189,248,0)");
  ctx.fillStyle = fill;
  ctx.fill();

  if (wifiHistory.length < 2) return;
  const barWidth = width / (wifiHistory.length - 1);
  const trend = wifiHistory.map((value, index) => ({
    x: index * barWidth,
    y: bottomBottom - (value / 100) * (bottomBottom - bottomTop - 4) - 2,
  }));
  ctx.beginPath();
  ctx.moveTo(trend[0].x, trend[0].y);
  trend.slice(1).forEach((point) => ctx.lineTo(point.x, point.y));
  ctx.strokeStyle = "#fbbf24";
  ctx.lineWidth = 1.5;
  ctx.stroke();
  ctx.lineTo(width, bottomBottom);
  ctx.lineTo(0, bottomBottom);
  ctx.closePath();
  const warmFill = ctx.createLinearGradient(0, bottomTop, 0, bottomBottom);
  warmFill.addColorStop(0, "rgba(251,191,36,.18)");
  warmFill.addColorStop(1, "rgba(251,191,36,0)");
  ctx.fillStyle = warmFill;
  ctx.fill();
}

async function postWifiBurst() {
  try {
    renderWifi(await api("/api/wifi/burst", { method: "POST" }));
  } catch (error) {
    setText("wifiSource", `干扰注入失败：${error.message}`);
  }
}
async function refresh() {
  const [roomResult, wifiResult] = await Promise.allSettled([api("/api/state"), api("/api/wifi")]);
  if (roomResult.status === "fulfilled") {
    render(roomResult.value);
  } else {
    setOffline(roomResult.reason.message);
  }
  if (wifiResult.status === "fulfilled") {
    renderWifi(wifiResult.value);
  } else {
    setText("wifiSource", `WiFi 数据离线：${wifiResult.reason.message}`);
  }
}

$("mainOn").addEventListener("change", () => post("toggle_main"));
$("auxOn").addEventListener("change", () => post("toggle_aux"));
$("mainBrightness").addEventListener("input", (event) => {
  setText("mainBrightnessValue", `${event.target.value}%`);
});
$("auxBrightness").addEventListener("input", (event) => {
  setText("auxBrightnessValue", `${event.target.value}%`);
});
$("mainBrightness").addEventListener("change", (event) => {
  post("set_brightness", { channel: "main", brightness: Number(event.target.value) });
});
$("auxBrightness").addEventListener("change", (event) => {
  post("set_brightness", { channel: "aux", brightness: Number(event.target.value) });
});
$("price").addEventListener("change", (event) => post("set_price", Number(event.target.value)));
$("presenceBtn").addEventListener("click", () => post("set_presence", !(current && current.occupancy)));
$("demoToggle").addEventListener("click", () => post("set_demo", !(current && current.demo)));
$("resetBtn").addEventListener("click", () => post("reset"));
$("luxRange").addEventListener("input", (event) => {
  setText("luxRangeValue", `${event.target.value} lx`);
});
$("luxRange").addEventListener("change", (event) => post("set_lux", Number(event.target.value)));
$("wifiBurstBtn").addEventListener("click", postWifiBurst);
window.addEventListener("resize", () => { drawChart(); drawWifiChart(); });
refresh();
setInterval(refresh, 1000);
