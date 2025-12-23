// --- MAIN LOGIC MODULE (V28.0 - AI BACKEND INTEGRATION) ---

// 1. Biến toàn cục
let socket = null;
let isLive = false;
let fetchTimer = null;
let currentDefcon = 5;
let currentNodeCount = 0;
let allEventsCache = [];
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
let predictionEvents = []; // Cache cho các điểm dự báo AI
let isTraining = false; // Cờ trạng thái training

// 2. Audio System (Giữ nguyên)
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
  } // Âm thanh mới cho AI
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

// 3. Helper Functions (Giữ nguyên)
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

  // Thêm dữ liệu dự báo AI nếu bật
  if (activeFilters["PREDICT"]) {
    filteredData = filteredData.concat(predictionEvents);
  }

  if (userEventMarker) filteredData.push(userEventMarker);

  if (window.world) {
    window.world.pointsData(filteredData);
    window.world.ringsData(filteredData.filter((d) => d.maxR > 0));
  }
}

// 4. Data Processing (Smart Loop)
async function fetchAllDataLoop() {
  if (!isLive) return;

  let nextDelay = 60000;
  try {
    const response = await fetch(`/api/v1/disasters/live?t=${Date.now()}`);
    const json = await response.json();

    if (json.data && json.data.length > 0) {
      processBackendData(json.data);
      nextDelay = 60000;

      // Sau khi lấy dữ liệu mới, tự động train AI
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
  printTerm(`Synced ${combinedEvents.length} threats.`);
}

// 5. AI FUNCTIONS (NEW & IMPROVED)
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

  // Dùng vị trí người dùng hoặc mặc định (Nhật Bản - Vùng hay có động đất)
  const targetLat = userLat || 36.2;
  const targetLon = userLng || 138.2;

  try {
    const res = await fetch("/api/v1/predict/forecast", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        lat: targetLat,
        lon: targetLon,
        simulated_energy: 0.7, // Giả lập mức năng lượng cao
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

    // Vẽ vòng tròn cảnh báo lên bản đồ
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

// 6. Interaction & WebSocket
window.toggleFilter = (type, btn) => {
  if (window.world) window.world.controls().autoRotate = false;
  activeFilters[type] = !activeFilters[type];
  btn.innerText = activeFilters[type] ? `[x] ${type}S` : `[ ] ${type}S`;
  btn.classList.toggle("active");
  window.sfx.playBeep();
  applyFilters();
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
    printTerm("Neural Viz deactivated.", "sys");
  }
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

        // Nếu AI đang bật, dự báo lại cho vị trí mới
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

        if (
          window.waveChart &&
          window.waveChart.data &&
          window.waveChart.data.datasets
        ) {
          window.waveChart.data.datasets[0].data.push(data.k_eff);
          window.waveChart.data.datasets[0].data.shift();
          window.waveChart.update();
        }

        if (data.core_temp > 2000) {
          window.sfx.playAlarm();
        }
      } catch (e) {
        console.warn("WS Error:", e);
      }
    };
    socket.onclose = () => {
      printTerm("WebSocket Disconnected.", "err");
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

printTerm("Guardian Kernel v28.0 loaded.");
printTerm("Modules: AI Neural Core (Scikit-Learn) Ready.");
