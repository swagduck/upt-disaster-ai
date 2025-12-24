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
  }
}
window.sfx = new AudioSynth();

// 3. Helper Functions & UI
const termOut = document.getElementById("term-output");
function printTerm(msg, type = "") {
  const div = document.createElement("div");
  div.className = `term-line ${type}`;
  div.innerText = `> ${msg}`;
  termOut.appendChild(div);
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
    if (d.type.includes("USER_LOC")) return true;
    if (d.type.includes("QUAKE")) return activeFilters["QUAKE"];
    if (d.type.includes("VOLCANO")) return activeFilters["VOLCANO"];
    if (d.type.includes("STORM") && d.color === "#bd00ff")
      return activeFilters["STORM"];
    if (d.type.includes("WILDFIRE")) return activeFilters["FIRE"];
    if (d.type.includes("NUCLEAR")) return activeFilters["NUKE"];
    if (d.type.includes("OTHER EVENT")) return activeFilters["OTHER"];
    return false;
  });

  if (activeFilters["PREDICT"]) {
    filteredData = filteredData.concat(predictionEvents);
  }
  if (userEventMarker) filteredData.push(userEventMarker);

  if (window.world) {
    window.world.pointsData(filteredData);
    window.world.ringsData(filteredData.filter((d) => d.maxR > 0));
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

function processBackendData(events) {
  let combinedEvents = [];
  let counts = { QUAKE: 0, FIRE: 0, VOLCANO: 0, STORM: 0, ICE: 0, OTHER: 0 };

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
    });
  });

  // Add Nuclear Plants
  if (window.nuclearPlants) {
    window.nuclearPlants.forEach((n) => {
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
      });
    });
  }

  allEventsCache = combinedEvents;
  currentNodeCount = combinedEvents.length;

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
    window.radarChart.update();
  }

  applyFilters();
  printTerm(`Synced ${combinedEvents.length} threats via UPT-CACHE.`);
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
  printTerm("Querying Guardian AI...", "ai");
  window.sfx.playPredict();

  let targetLat = 36.2;
  let targetLon = 138.2;

  if (userLat !== null && userLng !== null) {
    targetLat = userLat;
    targetLon = userLng;
  } else if (window.world) {
    const pov = window.world.pointOfView();
    targetLat = pov.lat;
    targetLon = pov.lng;
  }

  // --- REAL LOCAL CALCULATION ---
  let localEnergySum = 0.0;
  let eventCount = 0;
  const SCAN_RADIUS_KM = 800;

  if (allEventsCache && allEventsCache.length > 0) {
    allEventsCache.forEach((e) => {
      if (e.type === "USER_LOC" || e.type.includes("SOLAR")) return;
      const dist = getDistance(targetLat, targetLon, e.lat, e.lng);
      if (dist < SCAN_RADIUS_KM) {
        const impact = e.alt * 2 * (1 - dist / SCAN_RADIUS_KM);
        localEnergySum += Math.max(0, impact);
        eventCount++;
      }
    });
  }

  const realLocalEnergy = Math.min(localEnergySum / 2.0, 1.0);
  printTerm(
    `Analyzing Local Vector: ${eventCount} events. Density: ${realLocalEnergy.toFixed(
      2
    )}`,
    "sys"
  );

  try {
    const res = await fetch("/api/v1/predict/forecast", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        lat: targetLat,
        lon: targetLon,
        simulated_energy: realLocalEnergy,
      }),
    });
    const data = await res.json();
    const isCritical = data.alert_level === "CRITICAL";
    const typeStr = isCritical ? "err" : "sys";

    printTerm(
      `AI FORECAST @ [${targetLat.toFixed(1)}, ${targetLon.toFixed(1)}]:`,
      "ai"
    );
    printTerm(
      `RISK LEVEL: ${(data.predicted_risk * 100).toFixed(1)}% [${
        data.alert_level
      }]`,
      typeStr
    );

    if (data.predicted_risk > 0.8)
      printTerm(">> REASON: GLOBAL INSTABILITY + LOCAL THREAT", "err");

    if (data.predicted_risk > 0.0) {
      predictionEvents = [
        {
          lat: targetLat,
          lng: targetLon,
          alt: 0.1,
          color: isCritical ? "#ff0000" : "#ffffff",
          type: "AI PREDICTION",
          place: `RISK ZONE (${data.alert_level})`,
          value: data.predicted_risk * 10,
          maxR: isCritical ? 15 : 8,
          propagationSpeed: 2,
          repeatPeriod: 1000,
        },
      ];
    } else {
      predictionEvents = [];
    }
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
      "Commands: scan, locate, train, predict, scram, mute, [location]...",
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

// UI Buttons
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
  btn.innerText = activeFilters[type] ? `[x] ${type}S` : `[ ] ${type}S`;
  btn.classList.toggle("active");
  window.sfx.playBeep();
  applyFilters();
};

window.locateUser = () => {
  const btn = document.getElementById("btn-gps");
  const statusLoc = document.getElementById("status-loc");
  if (navigator.geolocation) {
    printTerm("Triangulating...", "sys");
    btn.innerText = "[...] LOCATING";
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
          window.world.pointOfView(
            { lat: userLat, lng: userLng, altitude: 1.5 },
            2000
          );
        applyFilters();
        calcNearestThreat();
        if (activeFilters["PREDICT"]) runNeuralPrediction();
      },
      () => {
        printTerm("GPS Failed.", "err");
        btn.innerText = "[!] GPS FAIL";
      }
    );
  } else {
    printTerm("Geolocation not supported.", "err");
  }
};

// --- INSPECTOR WITH DISTANCE ---
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
            <span class="insp-val" style="color:${distColor}; font-weight:bold;">${Math.round(
      dist
    ).toLocaleString()} KM</span>
        </div>`;
  } else if (userLat === null) {
    distanceHtml = `<div class="insp-row" style="margin-top:5px; opacity:0.5; font-style:italic;"><span class="insp-lbl">DIST</span> <span class="insp-val">LOCATE ME FIRST</span></div>`;
  }

  document.getElementById("inspector-content").innerHTML = `
        <div class="insp-row"><span class="insp-lbl">CLASS</span> <strong style="color:${
          d.color
        }">${d.type}</strong></div>
        <div class="insp-row"><span class="insp-lbl">LOC</span> <span class="insp-val" style="font-size:0.8rem;">${
          d.place
        }</span></div>
        <div class="insp-row"><span class="insp-lbl">VAL</span> <span class="insp-val" style="color:${
          d.color
        }">${d.value.toFixed(1)}</span></div>
        ${distanceHtml}
    `;
};

window.closeInspector = () => {
  document.getElementById("inspector").classList.remove("active");
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
          window.waveChart.update();
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
