// --- VISUALIZATION MODULE (Three.js / Globe.gl / Charts) ---

// 1. Dữ liệu tĩnh
const satData = [...Array(150).keys()].map(() => ({
  lat: (Math.random() - 0.5) * 180,
  lng: (Math.random() - 0.5) * 360,
  alt: 0.6 + Math.random() * 0.3,
  velocity: Math.random() * 0.4 + 0.1,
  color: "#C8C8FF", // Màu HEX để fix lỗi Alpha warning
  type: "SATELLITE",
}));

const nuclearPlants = [
  { name: "Fukushima Daiichi", lat: 37.421, lng: 141.033, desc: "Japan" },
  { name: "Zaporizhzhia", lat: 47.512, lng: 34.586, desc: "Ukraine" },
  { name: "Kashiwazaki-Kariwa", lat: 37.429, lng: 138.596, desc: "Japan" },
  { name: "Diablo Canyon", lat: 35.211, lng: -120.855, desc: "USA" },
];

let world;
let waveChart;
let radarChart;

// 2. Khởi tạo Globe
function initGlobe() {
  try {
    world = Globe()(document.getElementById("globe-viz"))
      .globeImageUrl("//unpkg.com/three-globe/example/img/earth-dark.jpg")
      .bumpImageUrl("//unpkg.com/three-globe/example/img/earth-topology.png")
      .backgroundImageUrl("//unpkg.com/three-globe/example/img/night-sky.png")
      .atmosphereColor("#00f3ff")
      .atmosphereAltitude(0.2)
      .pointAltitude("alt")
      .pointColor("color")
      .pointRadius(0.5)
      .pointsMerge(false)
      .ringColor("color")
      .ringMaxRadius("maxR")
      .ringPropagationSpeed("propagationSpeed")
      .ringRepeatPeriod("repeatPeriod")
      .customLayerData(satData)
      .customThreeObjectUpdate((obj, d) => {
        Object.assign(obj.position, world.getCoords(d.lat, d.lng, d.alt));
        obj.rotation.y += 0.1;
        if (d.lng) {
          d.lng += d.velocity || 0;
          if (d.lng > 180) d.lng = -180;
        }
      })
      .onPointClick((d) => {
        if (window.sfx) window.sfx.playBeep();
        // Dừng quay khi click
        if (world) world.controls().autoRotate = false;

        world.pointOfView({ lat: d.lat, lng: d.lng, altitude: 1.2 }, 1500);
        window.showInspector(d);
      });

    world.customThreeObject((d) => {
      const geometry =
        d.type === "NUCLEAR PLANT"
          ? new THREE.CylinderGeometry(0.5, 0.5, 2, 8)
          : new THREE.TetrahedronGeometry(1.2);
      const material = new THREE.MeshBasicMaterial({ color: d.color });
      // Fix Alpha Warning
      if (d.type === "SATELLITE") {
        material.transparent = true;
        material.opacity = 0.6;
      }
      return new THREE.Mesh(geometry, material);
    });

    world.controls().autoRotate = true;
    world.controls().autoRotateSpeed = 0.15; // Slow motion
  } catch (e) {
    console.error("Globe Init Failed:", e);
  }
}

// 3. Khởi tạo Biểu đồ
function initCharts() {
  Chart.defaults.color = "#666";
  Chart.defaults.font.family = "Rajdhani";

  // Wave Chart
  const ctxWave = document.getElementById("waveChart");
  if (ctxWave) {
    waveChart = new Chart(ctxWave, {
      type: "line",
      data: {
        labels: Array(30).fill(""),
        datasets: [
          {
            data: Array(30).fill(0),
            borderColor: "#00f3ff",
            borderWidth: 2,
            pointRadius: 0,
            tension: 0.5,
            fill: true,
            backgroundColor: "rgba(0,243,255,0.1)",
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { x: { display: false }, y: { display: false } },
        animation: { duration: 0 },
      },
    });
  }

  // Radar Chart
  const ctxRadar = document.getElementById("radarChart");
  if (ctxRadar) {
    radarChart = new Chart(ctxRadar, {
      type: "polarArea",
      data: {
        labels: ["Quake", "Fire", "Volcano", "Storm", "Other"],
        datasets: [
          {
            data: [0, 0, 0, 0, 0],
            backgroundColor: [
              "#00f3ff",
              "#ff6600",
              "#ffd700",
              "#bd00ff",
              "#ffffff",
            ],
            borderWidth: 1,
            borderColor: "#111",
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "right",
            labels: { color: "#ccc", boxWidth: 10, font: { size: 9 } },
          },
        },
        scales: { r: { grid: { color: "#333" }, ticks: { display: false } } },
      },
    });
  }
}

// Khởi chạy
initGlobe();
initCharts();
