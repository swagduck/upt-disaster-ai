// --- MAIN LOGIC MODULE (v29.0 - SENTIENT OBSERVER) ---
// Features: Zero Mock AI, Real-time Distance, Sonar Radar, Real Data

// 1. Biến toàn cục & Cấu hình
const strategicLocations = {
  // Châu Á
  vietnam: { lat: 14.0, lng: 108.0, alt: 0.8, msg: "Home Base" },
  hanoi: { lat: 21.0, lng: 105.8, alt: 0.4, msg: "Capital Sector" },
  saigon: { lat: 10.8, lng: 106.6, alt: 0.4, msg: "Southern Hub" },
  japan: { lat: 36.0, lng: 138.0, alt: 0.7, msg: "Seismic Hotspot" },
  tokyo: { lat: 35.6, lng: 139.6, alt: 0.3, msg: "High Density Zone" },
  china: { lat: 35.0, lng: 105.0, alt: 1.0, msg: "Mainland Monitoring" },
  indonesia: { lat: -5.0, lng: 120.0, alt: 0.8, msg: "Ring of Fire" },
  india: { lat: 20.0, lng: 77.0, alt: 1.0, msg: "Subcontinent" },

  // Âu - Mỹ
  usa: { lat: 37.0, lng: -95.0, alt: 1.0, msg: "Western Hemisphere" },
  california: { lat: 36.7, lng: -119.4, alt: 0.5, msg: "San Andreas Fault" },
  europe: { lat: 54.0, lng: 15.0, alt: 1.2, msg: "EU Sector" },
  russia: { lat: 60.0, lng: 100.0, alt: 1.2, msg: "Northern Territory" },
  ukraine: { lat: 48.3, lng: 31.1, alt: 0.6, msg: "Conflict Zone" },

  // Điểm nóng đặc biệt
  chernobyl: { lat: 51.27, lng: 30.22, alt: 0.2, msg: "☢️ RADIATION ZONE ☢️" },
  fukushima: {
    lat: 37.42,
    lng: 141.03,
    alt: 0.2,
    msg: "☢️ REACTOR FALLOUT ☢️",
  },
  mariana: { lat: 11.3, lng: 142.2, alt: 0.3, msg: "Deepest Point" },
  everest: { lat: 27.98, lng: 86.92, alt: 0.1, msg: "Highest Point" },
  bermuda: { lat: 25.0, lng: -71.0, alt: 0.5, msg: "Anomaly Detected?" },

  // Tổng quan
  global: { lat: 0, lng: 0, alt: 2.5, msg: "Global Overwatch" },
  north: { lat: 90, lng: 0, alt: 2.0, msg: "Arctic Circle" },
  south: { lat: -90, lng: 0, alt: 2.0, msg: "Antarctica" },
};

let socket = null;
let isLive = false;
let fetchTimer = null;
let currentDefcon = 5;
let currentNodeCount = 0;
let allEventsCache = [];
let predictionEvents = []; // Cache cho dự báo AI
let isTraining = false;

let activeFilters = {
  QUAKE: true,
  VOLCANO: true,
  STORM: true,
  FIRE: true,
  OTHER: true,
  NUKE: true,
  PREDICT: false,
};

let userLat = null;
let userLng = null;
let userEventMarker = null;
let radarInterval = null; // Biến lưu vòng lặp Radar

// 2. Audio System (ADVANCED SONAR EDITION)
class AudioSynth {
  constructor() {
    this.ctx = new (window.AudioContext || window.webkitAudioContext)();
    this.muted = false;

    // Master Gain để kiểm soát âm lượng tổng
    this.masterGain = this.ctx.createGain();
    this.masterGain.gain.value = 0.5;
    this.masterGain.connect(this.ctx.destination);
  }

  playTone(freq, type, duration, vol = 0.1) {
    if (this.muted) return;
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, this.ctx.currentTime);
    gain.gain.setValueAtTime(vol, this.ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(
      0.01,
      this.ctx.currentTime + duration
    );
    osc.connect(gain);
    gain.connect(this.masterGain);
    osc.start();
    osc.stop(this.ctx.currentTime + duration);
    osc.onended = () => {
      osc.disconnect();
      gain.disconnect();
    };
  }

  playBeep() {
    this.playTone(800, "sine", 0.1, 0.05);
  }
  playPredict() {
    this.playTone(600, "triangle", 0.3, 0.05);
  }

  playAlarm() {
    if (this.muted) return;
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();
    osc.type = "sawtooth";
    osc.frequency.setValueAtTime(400, this.ctx.currentTime);
    osc.frequency.linearRampToValueAtTime(600, this.ctx.currentTime + 0.3);
    gain.gain.value = 0.1;
    osc.connect(gain);
    gain.connect(this.masterGain);
    osc.start();
    osc.stop(this.ctx.currentTime + 0.5);
    osc.onended = () => {
      osc.disconnect();
      gain.disconnect();
    };
  }

  // --- SONAR RADAR SOUND ---
  playSonar() {
    if (this.muted) return;
    const t = this.ctx.currentTime;

    // 1. Oscillator chính (Tiếng Ping)
    const osc = this.ctx.createOscillator();
    const gain = this.ctx.createGain();

    osc.type = "sine";
    osc.frequency.setValueAtTime(1200, t);
    osc.frequency.exponentialRampToValueAtTime(600, t + 0.2); // Pitch drop

    gain.gain.setValueAtTime(0, t);
    gain.gain.linearRampToValueAtTime(0.05, t + 0.02); // Attack
    gain.gain.exponentialRampToValueAtTime(0.001, t + 1.5); // Decay dài (Echo)

    osc.connect(gain);
    gain.connect(this.masterGain);

    osc.start(t);
    osc.stop(t + 1.5);

    // 2. Noise (Tiếng nhiễu nền khi quét)
    const bufferSize = this.ctx.sampleRate * 0.5;
    const buffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
    const data = buffer.getChannelData(0);
    for (let i = 0; i < bufferSize; i++) {
      data[i] = Math.random() * 2 - 1;
    }

    const noise = this.ctx.createBufferSource();
    noise.buffer = buffer;
    const noiseGain = this.ctx.createGain();
    const filter = this.ctx.createBiquadFilter();
    filter.type = "lowpass";
    filter.frequency.value = 800;

    noiseGain.gain.setValueAtTime(0.015, t);
    noiseGain.gain.exponentialRampToValueAtTime(0.001, t + 0.3);

    noise.connect(filter);
    filter.connect(noiseGain);
    noiseGain.connect(this.masterGain);

    noise.start(t);
    noise.stop(t + 1.5);

    osc.onended = () => {
      osc.disconnect();
      gain.disconnect();
    };
    noise.onended = () => {
      noise.disconnect();
      filter.disconnect();
      noiseGain.disconnect();
    };
  }
}
window.sfx = new AudioSynth();

// 3. Helper Functions & UI
const termOut = document.getElementById("term-output");
const MAX_TERM_LINES = 60;
function printTerm(msg, type = "") {
  const div = document.createElement("div");
  div.className = `term-line ${type}`;
  div.innerText = `> ${msg}`;
  termOut.appendChild(div);
  // Cap terminal lines to prevent DOM bloat
  while (termOut.childElementCount > MAX_TERM_LINES) {
    termOut.removeChild(termOut.firstChild);
  }
  termOut.scrollTop = termOut.scrollHeight;
}

function getDistance(lat1, lon1, lat2, lon2) {
  const R = 6371; // Bán kính Trái đất (km)
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function calcNearestThreat() {
  if (userLat === null || allEventsCache.length === 0) return;
  let minDist = 999999;
  let nearestEvent = null;
  allEventsCache.forEach((e) => {
    if (e.type === "USER_LOC") return;
    const dist = getDistance(userLat, userLng, e.lat, e.lng);
    if (dist < minDist) {
      minDist = dist;
      nearestEvent = e;
    }
  });
  if (nearestEvent) {
    document.getElementById("val-prob").innerText =
      Math.round(minDist).toLocaleString();
    document.getElementById(
      "nearest-name"
    ).innerText = `${nearestEvent.type} - ${nearestEvent.place}`;
  }
}

function applyFilters() {
  let filteredData = allEventsCache.filter((d) => {
    // 1. Luôn hiển thị vị trí người dùng (User Location)
    if (d.type === "USER_LOC") return true;

    // 2. Kiểm tra từng loại thiên tai cụ thể
    if (d.type.includes("QUAKE")) return activeFilters["QUAKE"];
    if (d.type.includes("VOLCANO")) return activeFilters["VOLCANO"];
    if (d.type.includes("STORM")) return activeFilters["STORM"]; // Bỏ điều kiện màu để bắt tất cả bão
    if (d.type.includes("WILDFIRE")) return activeFilters["FIRE"];
    if (d.type.includes("NUCLEAR")) return activeFilters["NUKE"];

    // 3. QUAN TRỌNG: Tất cả các loại còn lại (SOLAR, FLOOD, TSUNAMI...)
    // sẽ được gộp vào bộ lọc "OTHER".
    // Nếu activeFilters["OTHER"] bật -> hiện. Tắt -> ẩn.
    if (!activeFilters["OTHER"]) return false;

    return true;
  });

  // Lọc theo thời gian (Time-frame Filtering)
  if (globalTimeFilter > 0) {
    const cutoff = Date.now() - (globalTimeFilter * 60 * 60 * 1000);
    filteredData = filteredData.filter(d => d.timestamp >= cutoff);
  }

  // Gộp thêm dự báo AI nếu đang bật
  if (activeFilters["PREDICT"]) {
    filteredData = filteredData.concat(predictionEvents);
  }
  // Thêm marker người dùng
  if (userEventMarker) filteredData.push(userEventMarker);

  // Cập nhật lên quả cầu
  if (window.world) {
    window.world.customLayerData(filteredData);
  }
  
  // Debounce proximity list — only recalculate if GPS is set
  if (userLat !== null && userLng !== null) {
    clearTimeout(window._proximityDebounce);
    window._proximityDebounce = setTimeout(() => updateProximityList(filteredData), 300);
  } else {
    updateProximityList(filteredData);
  }
}

// 4. Backend Data Loop (ZERO MOCK)
async function fetchAllDataLoop() {
  if (!isLive) return;

  let nextDelay = 60000;
  try {
    const response = await fetch(`/api/v1/disasters/live?t=${Date.now()}`);
    const json = await response.json();

    if (json.data && json.data.length > 0) {
      processBackendData(json.data);
      nextDelay = 60000;
      trainModel(); // Auto-train with real data
    } else {
      printTerm("Scanning... Retrying in 3s...", "sys");
      nextDelay = 3000;
      document.getElementById("status-model").innerText = "SCANNING...";
      document.getElementById("status-model").style.color =
        "var(--neon-orange)";
    }
  } catch (e) {
    console.error(e);
    printTerm("Uplink lost. Retrying...", "err");
    nextDelay = 5000;
  }

  if (isLive) {
    clearTimeout(fetchTimer);
    fetchTimer = setTimeout(fetchAllDataLoop, nextDelay);
  }
}

let lastEventsHash = 0;
let currentCounts = { QUAKE: 0, FIRE: 0, VOLCANO: 0, STORM: 0, OTHER: 0, NUKE: 0 };

// Fast numeric hash — avoids JSON.stringify on large arrays every 60s
function fastHash(events) {
  let h = events.length;
  for (let i = 0; i < Math.min(events.length, 20); i++) {
    const e = events[i];
    h = (h * 31 + (e.lat * 1000 | 0) + (e.raw_val * 100 | 0)) >>> 0;
  }
  return h;
}

function processBackendData(events) {
  const currentHash = fastHash(events);
  const isFirstLoad = lastEventsHash === 0;
  if (currentHash === lastEventsHash) {
    return; // Silently skip if no new events
  }
  lastEventsHash = currentHash;

  let combinedEvents = [];
  let counts = { QUAKE: 0, FIRE: 0, VOLCANO: 0, STORM: 0, ICE: 0, OTHER: 0, NUKE: 0 };

  events.forEach((e) => {
    let color = "#aaaaaa";
    let maxR = 0;
    let type = e.type;

    if (type.includes("EARTHQUAKE")) {
      counts.QUAKE++;
      const mag = e.raw_val;
      color = mag > 7 ? "#ff003c" : mag > 5 ? "#ffd700" : "#00f3ff";
      maxR = mag > 5 ? mag * 5 : 0;
      type = `QUAKE (M${mag.toFixed(1)})`;
    } else if (type.includes("WILDFIRE")) {
      counts.FIRE++;
      color = "#ff6600";
    } else if (type.includes("VOLCANO")) {
      counts.VOLCANO++;
      color = "#ff00cc";
    } else if (type.includes("STORM")) {
      counts.STORM++;
      color = "#bd00ff";
    } else if (type.includes("SOLAR")) {
      color = "#ffffff";
      maxR = 50;
    } else {
      counts.OTHER++;
    }

    combinedEvents.push({
      lat: e.lat,
      lng: e.lon,
      alt: e.energy_level * 0.5,
      color: color,
      type: type,
      place: e.place,
      value: e.raw_val,
      maxR: maxR,
      propagationSpeed: 5,
      repeatPeriod: 800,
      timestamp: e.timestamp || 0,
      _uid: `${e.lat}_${e.lon}_${e.type}`,
    });
  });

  // Add Nuclear Plants
  if (window.nuclearPlants) {
    window.nuclearPlants.forEach((n) => {
      counts.NUKE++;
      combinedEvents.push({
        lat: n.lat,
        lng: n.lng,
        alt: 0.1,
        color: "#ccff00",
        type: "NUCLEAR PLANT",
        place: n.name,
        value: 10,
        maxR: 20,
        propagationSpeed: 1,
        repeatPeriod: 3000,
        _uid: `NUKE_${n.lat}_${n.lng}`,
      });
    });
  }

  allEventsCache = combinedEvents;
  currentNodeCount = combinedEvents.length;
  currentCounts = counts;

  const countEl = document.getElementById("val-prob");
  if (countEl) countEl.innerText = combinedEvents.length;

  if (window.radarChart && window.radarChart.data) {
    window.radarChart.data.datasets[0].data = [
      counts.QUAKE,
      counts.FIRE,
      counts.VOLCANO,
      counts.STORM,
      counts.OTHER,
    ];
    window.radarChart.update('none');
  }

  applyFilters();
  updateFilterButtons();

  if (isFirstLoad) {
    printTerm(`Initial sync: ${combinedEvents.length} global threats loaded.`, "sys");
  } else {
    printTerm(`ALERT: New threat data detected! Synchronized ${combinedEvents.length} active threats.`, "err");
    window.sfx.playBeep();

    // Fire browser notifications for notable events
    combinedEvents.forEach(ev => {
      const val = parseFloat(ev.value) || 0;
      const isNotableQuake    = ev.type && ev.type.includes('QUAKE')    && val >= 5.5;
      const isNotableVolcano  = ev.type && ev.type.includes('VOLCANO');
      const isNotableStorm    = ev.type && ev.type.includes('STORM')    && val >= 6;
      if (isNotableQuake || isNotableVolcano || isNotableStorm) {
        sendDisasterAlert(ev);
      }
    });
  }
}

// 5. AI Functions (REAL DATA LOGIC)
async function trainModel() {
  if (isTraining) return;
  isTraining = true;
  try {
    const res = await fetch("/api/v1/predict/train", { method: "POST" });
    const json = await res.json();
    if (json.total_events_learned > 0) {
      printTerm(
        `Neural Core updated. Knowledge: ${json.total_events_learned}`,
        "sys"
      );
    }
    const statusModel = document.getElementById("status-model");
    if (statusModel) {
      statusModel.innerText = "ONLINE (AI ACTIVE)";
      statusModel.style.color = "var(--neon-green)";
    }
  } catch (e) {
    console.warn("AI Train Fail:", e);
  } finally {
    isTraining = false;
  }
}

async function runNeuralPrediction() {
  if (!activeFilters["PREDICT"]) return;
  printTerm("=== GUARDIAN GLOBAL SCAN INITIATED ===", "ai");
  printTerm("Scanning 20 major fault lines & hotspots...", "sys");
  window.sfx.playPredict();

  try {
    const res = await fetch("/api/v1/predict/global-scan");
    const data = await res.json();

    if (!data.data || data.data.length === 0) {
      printTerm("No scan data returned.", "err");
      return;
    }

    const criticalZones = data.data.filter(r => r.alert_level === "CRITICAL");
    const warningZones  = data.data.filter(r => r.alert_level === "WARNING");

    printTerm(`Scan complete: ${data.count} regions analyzed.`, "sys");
    printTerm(`CRITICAL: ${criticalZones.length} | WARNING: ${warningZones.length}`, criticalZones.length > 0 ? "err" : "sys");

    if (criticalZones.length > 0) {
      criticalZones.forEach(r => {
        printTerm(`>> [CRITICAL] ${r.name} - Risk: ${(r.risk_score * 100).toFixed(1)}%`, "err");
      });
    }

    // Chuyển đổi dữ liệu quét thành các điểm vẽ trên quả cầu 3D
    predictionEvents = data.data.map((r, idx) => {
      const isCrit = r.alert_level === "CRITICAL";
      const isWarn = r.alert_level === "WARNING";
      const color  = isCrit ? "#ff003c" : (isWarn ? "#ffaa00" : "#00ff88");
      return {
        _uid: `pred_${idx}`,
        lat: r.lat,
        lng: r.lon,
        alt: Math.max(r.risk_score * 0.3, 0.05),
        color: color,
        type: "AI PREDICTION",
        place: `${r.name} — Risk: ${(r.risk_score * 100).toFixed(1)}% [${r.alert_level}]`,
        maxR: isCrit ? 12 : (isWarn ? 6 : 2),
        propagationSpeed: 2,
      };
    });

    applyFilters();
  } catch (e) {
    console.error(e);
    printTerm("Neural Uplink Failed.", "err");
  }
}

// 6. COMMAND SYSTEM
window.processCommand = async function (cmd) {
  cmd = cmd.trim().toLowerCase();

  // System
  if (cmd.includes("scan") || cmd === "refresh") {
    printTerm("Initiating Manual Scan...", "sys");
    fetchAllDataLoop();
    return;
  }
  if (cmd.includes("train") || cmd === "learn") {
    printTerm("Force Retraining Neural Core...", "tf");
    trainModel();
    return;
  }
  if (cmd.includes("locate") || cmd.includes("gps") || cmd === "me") {
    locateUser();
    return;
  }
  if (cmd === "status" || cmd === "report") {
    printTerm(`--- SITUATION REPORT ---`, "sys");
    printTerm(
      `DEFCON LEVEL: ${currentDefcon}`,
      currentDefcon <= 2 ? "err" : "sys"
    );
    printTerm(`ACTIVE THREATS: ${currentNodeCount}`, "sys");
    printTerm(`NEURAL STATUS: ${isTraining ? "TRAINING" : "ONLINE"}`, "ai");
    if (userLat !== null)
      printTerm(
        `OPERATOR LOC: ${userLat.toFixed(2)}, ${userLng.toFixed(2)}`,
        "sys"
      );
    return;
  }
  if (cmd === "eval" || cmd === "metrics") {
    printTerm("Querying AI Accuracy Metrics...", "ai");
    fetch("/api/v1/predict/evaluation")
      .then(res => res.json())
      .then(data => {
        if(data.status === "EVALUATED") {
          printTerm(`--- AI ACCURACY REPORT ---`, "sys");
          printTerm(`Tolerance Accuracy: ${data.metrics.tolerance_accuracy}%`, "tf");
          printTerm(`MSE: ${data.metrics.mse} | MAE: ${data.metrics.mae}`, "sys");
        } else {
          printTerm(`AI Evaluation: ${data.message}`, "err");
        }
      })
      .catch(e => printTerm("Evaluation Failed.", "err"));
    return;
  }

  // Reactor
  if (cmd === "scram" || cmd === "shutdown") {
    printTerm("!!! EMERGENCY SCRAM INITIATED !!!", "err");
    window.sfx.playAlarm();
    try {
      await fetch("/api/v1/reactor/scram", { method: "POST" });
      printTerm("CONTROL RODS DROPPED. FLUX ZERO.", "sys");
    } catch (e) {
      printTerm("SCRAM FAILED: Uplink Error.", "err");
    }
    return;
  }

  // Visual/Audio
  if (cmd.includes("predict") || cmd === "ai") {
    togglePrediction();
    return;
  }
  if (cmd === "mute" || cmd === "silent") {
    window.sfx.muted = true;
    printTerm("Audio Muted.", "sys");
    return;
  }
  if (cmd === "unmute" || cmd === "sound") {
    window.sfx.muted = false;
    printTerm("Audio Enabled.", "sys");
    return;
  }

  // Navigation
  for (const [key, val] of Object.entries(strategicLocations)) {
    if (cmd.includes(key)) {
      if (window.world) {
        window.world.pointOfView(
          { lat: val.lat, lng: val.lng, altitude: val.alt },
          2000
        );
        window.world.controls().autoRotate = false;
      }
      printTerm(`Moving to ${key.toUpperCase()}...`, "sys");
      window.sfx.playBeep();
      return;
    }
  }

  if (cmd === "help")
    printTerm(
      "Commands: scan, locate, train, predict, eval, scram, mute, [location]...",
      "sys"
    );
  else printTerm("Command not recognized.", "err");
};



function setAllFilters(state) {
  // ... (Logic giữ nguyên, lược bỏ để gọn vì không thay đổi logic) ...
  ["QUAKE", "VOLCANO", "STORM", "FIRE", "OTHER", "NUKE"].forEach((type) => {
    activeFilters[type] = state;
    // ... Cập nhật nút bấm ...
  });
  applyFilters();
}

// 7. Interaction & Listeners
document.addEventListener("keydown", (e) => {
  const termIn = document.getElementById("term-input");
  if (document.activeElement === termIn) {
    if (e.key === "Enter") {
      const cmd = termIn.value.trim().toLowerCase();
      printTerm(cmd, "cmd");
      window.processCommand(cmd);
      termIn.value = "";
      window.sfx.playBeep();
    }
  }
});

// RADAR LOOP INIT
function startRadarSweep() {
  if (radarInterval) clearInterval(radarInterval);
  radarInterval = setInterval(() => {
    if (!window.sfx.muted) window.sfx.playSonar();
  }, 4000); // 4 giây quét 1 lần
}

// Click to unlock Audio Context
document.addEventListener(
  "click",
  () => {
    if (window.sfx.ctx.state === "suspended") {
      window.sfx.ctx.resume();
    }
    if (!radarInterval) {
      startRadarSweep();
      printTerm("AUDIO SYSTEM ONLINE. RADAR ACTIVE.", "sys");
    }
  },
  { once: true }
);

// ─── BROWSER NOTIFICATION SYSTEM ─────────────────────────────────────────────
let notificationsEnabled = false;
const notifiedEvents = new Set(); // Track already-notified events to avoid spam

window.toggleNotifications = async () => {
  const btn = document.getElementById('btn-notify');

  if (notificationsEnabled) {
    // Turn off
    notificationsEnabled = false;
    btn.innerText = '🔔 ALERTS: OFF';
    btn.style.borderColor = 'var(--neon-gold)';
    btn.style.color = 'var(--neon-gold)';
    btn.style.background = 'transparent';
    printTerm('Alert notifications disabled.', 'sys');
    return;
  }

  // Request permission
  if (!('Notification' in window)) {
    printTerm('Browser does not support notifications.', 'err');
    return;
  }

  let permission = Notification.permission;
  if (permission === 'default') {
    permission = await Notification.requestPermission();
  }

  if (permission === 'granted') {
    notificationsEnabled = true;
    btn.innerText = '🔔 ALERTS: ON';
    btn.style.borderColor = 'var(--neon-green)';
    btn.style.color = 'var(--neon-green)';
    btn.style.background = 'rgba(0,255,100,0.1)';
    printTerm('Alert notifications ENABLED. Major threats will trigger alerts.', 'sys');

    // Send a welcome test notification
    new Notification('☢ UPT Guardian System', {
      body: 'Alert system online. You will be notified of major disaster events.',
      icon: 'data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>☢️</text></svg>',
      badge: 'data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>☢️</text></svg>',
      silent: false
    });
  } else {
    printTerm('Notification permission denied. Please allow in browser settings.', 'err');
  }
};

function sendDisasterAlert(event) {
  if (!notificationsEnabled || Notification.permission !== 'granted') return;

  // Build a unique key so we don't spam the same event
  const key = `${event.type}-${(event.lat || 0).toFixed(1)}-${(event.lng || 0).toFixed(1)}`;
  if (notifiedEvents.has(key)) return;
  notifiedEvents.add(key);

  // Clear old keys if set gets too large
  if (notifiedEvents.size > 200) notifiedEvents.clear();

  const mag = event.value ? `M${parseFloat(event.value).toFixed(1)}` : '';
  const loc  = event.place || 'Unknown Location';
  let title, body, icon;

  if (event.type && event.type.includes('QUAKE')) {
    title = `🌍 MAJOR EARTHQUAKE DETECTED`;
    body  = `${mag} — ${loc}`;
    icon  = 'data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🌍</text></svg>';
  } else if (event.type && event.type.includes('WILDFIRE')) {
    title = `🔥 WILDFIRE ALERT`;
    body  = loc;
    icon  = 'data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🔥</text></svg>';
  } else if (event.type && event.type.includes('VOLCANO')) {
    title = `🌋 VOLCANO ACTIVITY`;
    body  = loc;
    icon  = 'data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🌋</text></svg>';
  } else {
    title = `⚠ DISASTER ALERT`;
    body  = `${event.type} — ${loc}`;
    icon  = 'data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>⚠️</text></svg>';
  }

  const notif = new Notification(title, {
    body,
    icon,
    tag: key,         // Prevents duplicate popups for same event
    renotify: false,
  });

  // Click notification → open app and fly to event
  notif.onclick = () => {
    window.focus();
    if (window.world && event.lat !== undefined) {
      window.world.pointOfView({ lat: event.lat, lng: event.lng, altitude: 1.2 }, 2000);
    }
  };
}

// ─── END NOTIFICATION SYSTEM ─────────────────────────────────────────────────

// UI Buttons
let globalTimeFilter = 0;

window.setTimeFilter = (hours) => {
  globalTimeFilter = hours;
  [1, 12, 24, 0].forEach(h => {
    const btn = document.getElementById(h === 0 ? 'btn-time-all' : `btn-time-${h}h`);
    if (btn) {
      if (h === hours) btn.classList.add('active');
      else btn.classList.remove('active');
    }
  });
  window.sfx.playBeep();
  applyFilters();
};

window.exportCSV = () => {
  if (allEventsCache.length === 0) return;
  const headers = "Type,Place,Latitude,Longitude,Magnitude,Timestamp\n";
  const rows = allEventsCache.map(d => `${d.type},"${d.place}",${d.lat},${d.lng},${d.value},${d.timestamp}`).join("\n");
  const blob = new Blob([headers + rows], { type: 'text/csv' });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.setAttribute('href', url);
  a.setAttribute('download', `disaster_report_${Date.now()}.csv`);
  document.body.appendChild(a);
  a.click();
  a.remove();
  printTerm("CSV Data Exported Successfully.", "sys");
};

window.updateFilterButtons = () => {
  const map = {
    QUAKE: { id: 'btn-quake', label: 'QUAKES' },
    VOLCANO: { id: 'btn-volcano', label: 'VOLCANO' },
    STORM: { id: 'btn-storm', label: 'STORMS' },
    FIRE: { id: 'btn-fire', label: 'FIRES' },
    OTHER: { id: 'btn-other', label: 'OTHERS' },
    NUKE: { id: 'btn-nuke', label: 'NUKES' }
  };
  for (const [type, config] of Object.entries(map)) {
    const btn = document.getElementById(config.id);
    if (btn) {
      const count = currentCounts[type] || 0;
      btn.innerText = activeFilters[type] ? `[x] ${config.label} (${count})` : `[ ] ${config.label} (${count})`;
      if (activeFilters[type]) btn.classList.add("active");
      else btn.classList.remove("active");
    }
  }
};

window.togglePrediction = () => {
  activeFilters["PREDICT"] = !activeFilters["PREDICT"];
  const btn = document.getElementById("btn-predict");
  if (activeFilters["PREDICT"]) {
    btn.innerText = "[x] NEURAL AI";
    btn.classList.add("active");
    runNeuralPrediction();
  } else {
    btn.innerText = "[ ] NEURAL AI";
    btn.classList.remove("active");
    predictionEvents = [];
    applyFilters();
  }
};

window.toggleFilter = (type, btn) => {
  if (window.world) window.world.controls().autoRotate = false;
  activeFilters[type] = !activeFilters[type];
  updateFilterButtons();
  window.sfx.playBeep();
  applyFilters();
};

window.locateUser = async () => {
  const btn = document.getElementById("btn-gps");
  const statusLoc = document.getElementById("status-loc");
  
  printTerm("Triangulating IP Coordinates...", "sys");
  btn.innerText = "[...] LOCATING";

  try {
    const res = await fetch("https://get.geojs.io/v1/ip/geo.json");
    if (!res.ok) throw new Error("Network response was not ok");
    const data = await res.json();
    
    userLat = parseFloat(data.latitude);
    userLng = parseFloat(data.longitude);
    
    btn.innerText = "[x] LOC LOCKED";
    btn.classList.add("active");
    statusLoc.innerText = `${userLat.toFixed(2)},${userLng.toFixed(2)}`;
    statusLoc.style.color = "var(--neon-blue)";
    printTerm(`IP LOC: ${userLat.toFixed(4)}, ${userLng.toFixed(4)} (${data.city || 'Unknown'})`, "sys");
    window.sfx.playBeep();

    userEventMarker = {
      lat: userLat,
      lng: userLng,
      alt: 0.02,
      color: "#00f3ff",
      type: "USER_LOC",
      place: "HOME BASE",
      value: 0,
      maxR: 5,
    };
    if (window.world) {
      window.world.pointOfView({ lat: userLat, lng: userLng, altitude: 1.5 }, 2000);
    }
    applyFilters();
    if (activeFilters["PREDICT"]) runNeuralPrediction();

  } catch (error) {
    console.warn("IP Geo Error:", error);
    printTerm("IP Scan failed, falling back to satellite...", "err");
    
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          userLat = position.coords.latitude;
          userLng = position.coords.longitude;
          btn.innerText = "[x] GPS LOCKED";
          btn.classList.add("active");
          statusLoc.innerText = `${userLat.toFixed(2)},${userLng.toFixed(2)}`;
          statusLoc.style.color = "var(--neon-blue)";
          printTerm(`GPS: ${userLat.toFixed(4)}, ${userLng.toFixed(4)}`, "sys");
          window.sfx.playBeep();
  
          userEventMarker = {
            lat: userLat,
            lng: userLng,
            alt: 0.02,
            color: "#00f3ff",
            type: "USER_LOC",
            place: "HOME BASE",
            value: 0,
            maxR: 5,
          };
          if (window.world)
            window.world.pointOfView({ lat: userLat, lng: userLng, altitude: 1.5 }, 2000);
          applyFilters();
          if (activeFilters["PREDICT"]) runNeuralPrediction();
        },
        (gpsError) => {
          console.warn("GPS Error:", gpsError);
          printTerm("GPS Failed: " + (gpsError.message || "Timeout"), "err");
          btn.innerText = "[!] LOC FAIL";
        },
        { enableHighAccuracy: false, timeout: 10000, maximumAge: 0 }
      );
    } else {
      printTerm("Geolocation totally failed.", "err");
      btn.innerText = "[!] LOC FAIL";
    }
  }
};

window.showInspector = (d) => {
  document.getElementById("inspector").classList.add("active");

  let distanceHtml = "";
  if (
    userLat !== null &&
    userLng !== null &&
    d.lat !== undefined &&
    d.lng !== undefined
  ) {
    const dist = getDistance(userLat, userLng, d.lat, d.lng);
    let distColor = "#00f3ff";
    if (dist < 500) distColor = "#ff003c";
    else if (dist < 2000) distColor = "#ffcc00";

    distanceHtml = `
        <div class="insp-row" style="border-top: 1px dashed #333; margin-top: 5px; padding-top: 5px;">
            <span class="insp-lbl">DISTANCE</span> 
            <span class="insp-val" style="color:${distColor}; font-weight:bold;">${Math.round(dist).toLocaleString()} KM</span>
        </div>`;
  } else if (userLat === null) {
    distanceHtml = `<div class="insp-row" style="margin-top:5px; opacity:0.5; font-style:italic;"><span class="insp-lbl">DIST</span> <span class="insp-val">LOCATE ME FIRST</span></div>`;
  }

  const timeStr = d.timestamp ? new Date(d.timestamp).toLocaleString() : "Unknown";

  document.getElementById("inspector-content").innerHTML = `
      <div class="insp-row"><span class="insp-lbl">TYPE</span> <span class="insp-val" style="color:${d.color}">${d.type}</span></div>
      <div class="insp-row"><span class="insp-lbl">PLACE</span> <span class="insp-val" style="font-size:0.8rem">${d.place || "Unknown"}</span></div>
      <div class="insp-row"><span class="insp-lbl">LATITUDE</span> <span class="insp-val">${(d.lat || 0).toFixed(4)}</span></div>
      <div class="insp-row"><span class="insp-lbl">LONGITUDE</span> <span class="insp-val">${(d.lng || 0).toFixed(4)}</span></div>
      <div class="insp-row"><span class="insp-lbl">MAGNITUDE</span> <span class="insp-val">${(d.value || 0).toFixed(2)}</span></div>
      <div class="insp-row"><span class="insp-lbl">TIME</span> <span class="insp-val" style="font-size:0.75rem">${timeStr}</span></div>
      ${distanceHtml}
  `;
};

window.updateProximityList = (data) => {
  const container = document.getElementById("proximity-list");
  if (!container) return;

  if (userLat === null || userLng === null) {
    container.innerHTML = `<div style="text-align: center; color: #888; font-size: 0.8rem; margin-top: 20px;">
      <div style="font-size: 2rem; color: #00f3ff; font-family: var(--tech-font); margin-bottom: 5px;">${data.length}</div>
      TOTAL THREATS<br/>(AWAITING GPS)
    </div>`;
    return;
  }

  let threats = [];
  data.forEach(d => {
    if (d.type !== "USER_LOC" && d.lat !== undefined && d.lng !== undefined) {
      const dist = getDistance(userLat, userLng, d.lat, d.lng);
      threats.push({ ...d, dist });
    }
  });

  threats.sort((a, b) => a.dist - b.dist);
  const topThreats = threats.slice(0, 3);

  if (topThreats.length === 0) {
    container.innerHTML = `<div style="text-align: center; color: var(--neon-green); font-size: 0.8rem; margin-top: 20px;">NO THREATS DETECTED</div>`;
    return;
  }

  let html = "";
  topThreats.forEach(t => {
    let distColor = "#00f3ff";
    if (t.dist < 500) distColor = "#ff003c";
    else if (t.dist < 2000) distColor = "#ffcc00";

    html += `
      <div style="background: rgba(0,0,0,0.5); padding: 5px; border-left: 2px solid ${t.color}; display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
        <div style="display: flex; flex-direction: column; overflow: hidden; white-space: nowrap; text-overflow: ellipsis; max-width: 65%;">
          <span style="color: ${t.color}; font-size: 0.7rem; font-weight: bold;">${t.type}</span>
          <span style="color: #ccc; font-size: 0.6rem; overflow: hidden; text-overflow: ellipsis;">${t.place}</span>
        </div>
        <div style="color: ${distColor}; font-family: var(--code-font); font-size: 1rem;">
          ${Math.round(t.dist).toLocaleString()}KM
        </div>
      </div>
    `;
  });
  container.innerHTML = html;
};

window.closeInspector = () => {
  document.getElementById("inspector").classList.remove("active");
  // Bỏ highlight của cột đã chọn
  if (window.clearSelectedHighlight) window.clearSelectedHighlight();
  if (window.world) {
    window.world.controls().autoRotate = true;
    window.world.pointOfView({ altitude: 2.5 }, 2000);
  }
};

// 8. WebSocket Connection
document.getElementById("btn-link").addEventListener("click", () => {
  const btn = document.getElementById("btn-link");
  isLive = !isLive;

  if (isLive) {
    btn.classList.add("active");
    btn.innerText = "LINK ESTABLISHED";
    printTerm("Initializing Quantum Uplink (WebSocket)...");
    window.sfx.playBeep();
    fetchAllDataLoop();
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/api/v1/reactor/ws/status`;

    socket = new WebSocket(wsUrl);
    socket.onopen = () => printTerm("WebSocket Connected.", "sys");
    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (document.getElementById("val-flux"))
          document.getElementById("val-flux").innerText = data.neutron_flux;
        if (document.getElementById("val-temp"))
          document.getElementById("val-temp").innerText = data.core_temp + " K";
        if (window.waveChart && window.waveChart.data) {
          window.waveChart.data.datasets[0].data.push(data.k_eff);
          window.waveChart.data.datasets[0].data.shift();
          window.waveChart.update('none');
        }
        if (data.core_temp > 2000) window.sfx.playAlarm();
      } catch (e) {}
    };
    socket.onclose = () => {
      printTerm("WebSocket Disconnected.", "err");
      document.getElementById("status-model").innerText = "OFFLINE";
    };
  } else {
    btn.classList.remove("active");
    btn.innerText = "ACTIVATE REACTOR LINK";
    clearTimeout(fetchTimer);
    if (socket) socket.close();
    printTerm("Uplink Terminated.");
    document.getElementById("status-model").innerText = "OFFLINE";
  }
});

printTerm("Guardian Kernel v29.0 loaded.");
printTerm("Modules: SONAR + DISTANCE TRACKING + ZERO MOCK AI.");
