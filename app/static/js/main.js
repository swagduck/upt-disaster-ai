// --- MAIN LOGIC MODULE (V28.1 - COMMANDER & AI BACKEND) ---

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

// 2. Audio System
class AudioSynth {
  constructor() {
    this.ctx = new (window.AudioContext || window.webkitAudioContext)();
    this.muted = false;
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
    gain.connect(this.ctx.destination);
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
    gain.connect(this.ctx.destination);
    osc.start();
    osc.stop(this.ctx.currentTime + 0.5);
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
  const R = 6371;
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

  // Thêm AI Predictions vào bản đồ nếu bật
  if (activeFilters["PREDICT"]) {
    filteredData = filteredData.concat(predictionEvents);
  }

  if (userEventMarker) filteredData.push(userEventMarker);

  if (window.world) {
    window.world.pointsData(filteredData);
    window.world.ringsData(filteredData.filter((d) => d.maxR > 0));
  }
}

// 4. Backend Data Loop
async function fetchAllDataLoop() {
  if (!isLive) return;

  let nextDelay = 60000;
  try {
    const response = await fetch(`/api/v1/disasters/live?t=${Date.now()}`);
    const json = await response.json();

    if (json.data && json.data.length > 0) {
      processBackendData(json.data);
      nextDelay = 60000;

      // Auto-train AI khi có dữ liệu mới
      trainModel();
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

// 5. AI Functions (Python Backend)
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

  // --- [LOGIC MỚI] DỰ BÁO THEO TẦM NHÌN ---
  // Mặc định lấy tọa độ trung tâm màn hình (nơi bạn đang nhìn)
  let targetLat = 36.2;
  let targetLon = 138.2;

  // Nếu đã bật GPS, ưu tiên vị trí người dùng
  if (userLat !== null && userLng !== null) {
    targetLat = userLat;
    targetLon = userLng;
  }
  // Nếu chưa có GPS, lấy tọa độ camera đang chiếu tới
  else if (window.world) {
    const pov = window.world.pointOfView();
    targetLat = pov.lat;
    targetLon = pov.lng;
  }

  try {
    const res = await fetch("/api/v1/predict/forecast", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        lat: targetLat,
        lon: targetLon,
        simulated_energy: 0.7, // Giả lập năng lượng để test phản ứng AI
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

    // Vẽ vòng tròn dự báo
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

// 6. COMMAND SYSTEM (NEW)
window.processCommand = async function (cmd) {
  cmd = cmd.trim().toLowerCase();

  // --- SYSTEM COMMANDS ---
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

  // --- REACTOR COMMANDS ---
  if (cmd === "scram" || cmd === "shutdown" || cmd === "kill") {
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
  if (cmd.startsWith("defcon")) {
    const level = parseInt(cmd.split(" ")[1]);
    if (level >= 1 && level <= 5) {
      currentDefcon = level;
      const colors = {
        1: "#ff0000",
        2: "#ff4400",
        3: "#ffcc00",
        4: "#00ff66",
        5: "#0088ff",
      };
      document.getElementById("defcon-level").innerText = `DEFCON ${level}`;
      document.getElementById("defcon-level").style.color = colors[level];
      document.getElementById("defcon-bar").style.borderColor = colors[level];
      printTerm(`DEFCON LEVEL SET TO ${level}`, "sys");
      if (level === 1) window.sfx.playAlarm();
    } else {
      printTerm("Invalid DEFCON level (1-5).", "err");
    }
    return;
  }

  // --- VISUAL/AUDIO COMMANDS ---
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

  if (cmd === "matrix") {
    document.documentElement.style.setProperty("--neon-blue", "#00ff00");
    document.documentElement.style.setProperty("--neon-purple", "#00ff00");
    printTerm("ENTERING THE MATRIX...", "cmd");
    return;
  }
  if (cmd === "reset theme") {
    document.documentElement.style = "";
    printTerm("Visuals restored.", "sys");
    return;
  }

  // --- NAVIGATION COMMANDS ---
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
      printTerm(`>> ${val.msg}`, "voice");
      window.sfx.playBeep();
      return;
    }
  }

  // --- FILTER COMMANDS ---
  if (cmd === "sats") {
    const currentData = window.world.customLayerData();
    if (currentData.length > 0) {
      window.world.customLayerData([]);
      printTerm("Satellites: OFF", "sys");
    } else {
      // Cần truy cập satData từ visuals.js (scope global)
      // Nếu lỗi, đảm bảo satData được define ở scope window hoặc global
      try {
        window.world.customLayerData(satData);
        printTerm("Satellites: ON", "sys");
      } catch (e) {
        printTerm("Satellite Data Unavailable", "err");
      }
    }
    return;
  }
  if (cmd.includes("show all")) {
    setAllFilters(true);
    printTerm("All filters ENGAGED.", "sys");
    return;
  }
  if (cmd.includes("hide all")) {
    setAllFilters(false);
    printTerm("All filters DISENGAGED.", "sys");
    return;
  }

  const filterMap = {
    quake: "QUAKE",
    fire: "FIRE",
    storm: "STORM",
    volcano: "VOLCANO",
    nuke: "NUKE",
  };
  for (const [key, type] of Object.entries(filterMap)) {
    if (cmd.includes(key)) {
      const btn = document.getElementById(`btn-${key}`);
      if (btn) toggleFilter(type, btn);
      return;
    }
  }

  if (cmd === "help")
    printTerm(
      "Commands: scan, locate, train, predict, scram, defcon [1-5], [location], matrix...",
      "sys"
    );
  else printTerm("Command not recognized.", "err");
};

function setAllFilters(state) {
  ["QUAKE", "VOLCANO", "STORM", "FIRE", "OTHER", "NUKE"].forEach((type) => {
    activeFilters[type] = state;
    let btnKey = type.toLowerCase();
    if (btnKey === "quake") btnKey = "quake";
    if (btnKey === "volcano") btnKey = "volcano";
    if (btnKey === "storm") btnKey = "storm";
    if (btnKey === "fire") btnKey = "fire";
    if (btnKey === "nuke") btnKey = "nuke";
    if (btnKey === "other") btnKey = "other";

    const btn = document.getElementById(`btn-${btnKey}`);
    if (btn) {
      if (state) {
        btn.classList.add("active");
        btn.innerText = `[x] ${type}S`;
      } else {
        btn.classList.remove("active");
        btn.innerText = `[ ] ${type}S`;
      }
    }
  });
  applyFilters();
}

// 7. Interaction & Listeners
// Terminal Input Listener
document.addEventListener("keydown", (e) => {
  const termIn = document.getElementById("term-input");
  if (document.activeElement === termIn) {
    if (e.key === "Enter") {
      const cmd = termIn.value.trim().toLowerCase();
      printTerm(cmd, "cmd");
      window.processCommand(cmd); // Gọi hàm toàn cục
      termIn.value = "";
      window.sfx.playBeep();
    }
  }
});

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
    printTerm("Neural Viz deactivated.", "sys");
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
          propagationSpeed: 1,
          repeatPeriod: 2000,
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

window.showInspector = (d) => {
  document.getElementById("inspector").classList.add("active");
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
    socket.onopen = () => {
      printTerm("WebSocket Connected.", "sys");
    };
    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        const fluxEl = document.getElementById("val-flux");
        const tempEl = document.getElementById("val-temp");
        if (fluxEl) fluxEl.innerText = data.neutron_flux;
        if (tempEl) tempEl.innerText = data.core_temp + " K";

        if (window.waveChart && window.waveChart.data) {
          window.waveChart.data.datasets[0].data.push(data.k_eff);
          window.waveChart.data.datasets[0].data.shift();
          window.waveChart.update();
        }
        if (data.core_temp > 2000) window.sfx.playAlarm();
      } catch (e) {
        console.warn("WS Error:", e);
      }
    };
    socket.onclose = () => {
      printTerm("WebSocket Disconnected.", "err");
      const statusModel = document.getElementById("status-model");
      if (statusModel) {
        statusModel.innerText = "OFFLINE";
        statusModel.style.color = "#888";
      }
    };
  } else {
    btn.classList.remove("active");
    btn.innerText = "ACTIVATE REACTOR LINK";
    clearTimeout(fetchTimer);
    if (socket) socket.close();
    printTerm("Uplink Terminated.");
    const statusModel = document.getElementById("status-model");
    if (statusModel) {
      statusModel.innerText = "OFFLINE";
      statusModel.style.color = "#888";
    }
  }
});

printTerm("Guardian Kernel v28.1 loaded.");
printTerm("Modules: COMMANDER Ops + AI Backend Synced.");
