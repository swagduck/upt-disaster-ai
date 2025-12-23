// --- VISUALIZATION MODULE (Fix Crash Version) ---

// 1. Dữ liệu tĩnh
const satData = [...Array(150).keys()].map(() => ({
  lat: (Math.random() - 0.5) * 180,
  lng: (Math.random() - 0.5) * 360,
  alt: 0.6 + Math.random() * 0.3,
  velocity: Math.random() * 0.4 + 0.1,
  color: "#C8C8FF",
  type: "SATELLITE",
}));

const nuclearPlants = [
  { name: "Fukushima Daiichi", lat: 37.421, lng: 141.033, desc: "Japan" },
  { name: "Zaporizhzhia", lat: 47.512, lng: 34.586, desc: "Ukraine" },
  { name: "Kashiwazaki-Kariwa", lat: 37.429, lng: 138.596, desc: "Japan" },
  { name: "Diablo Canyon", lat: 35.211, lng: -120.855, desc: "USA" },
  {
    name: "Kori Nuclear Power Plant",
    lat: 35.316,
    lng: 129.292,
    desc: "South Korea",
  },
  { name: "Bruce Nuclear Gen", lat: 44.325, lng: -81.599, desc: "Canada" },
  { name: "Gravelines", lat: 51.015, lng: 2.136, desc: "France" },
];

window.nuclearPlants = nuclearPlants;

// Khai báo biến toàn cục
window.world = null;
window.waveChart = null;
window.radarChart = null;

// 2. Khởi tạo Globe (Đã sửa lỗi Crash)
function initGlobe() {
  try {
    window.world = Globe()(document.getElementById("globe-viz"))
      // --- GÓI ĐỒ HỌA 4K (SAFE MODE) ---

      // 1. Bề mặt Trái đất (Thành phố sáng đèn - Vẫn giữ cái này cho đẹp)
      .globeImageUrl("//unpkg.com/three-globe/example/img/earth-night.jpg")

      // 2. Bản đồ độ cao (Núi non gồ ghề)
      .bumpImageUrl("//i.imgur.com/wPZq7xO.jpg")

      // [ĐÃ XÓA DÒNG globeSpecularImageUrl GÂY LỖI]

      // 3. Hình nền vũ trụ
      .backgroundImageUrl("//unpkg.com/three-globe/example/img/night-sky.png")

      // 4. Khí quyển
      .atmosphereColor("#00f3ff")
      .atmosphereAltitude(0.25)
      // -------------------------------

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
        Object.assign(
          obj.position,
          window.world.getCoords(d.lat, d.lng, d.alt)
        );
        obj.rotation.y += 0.1;
        if (d.lng) {
          d.lng += d.velocity || 0;
          if (d.lng > 180) d.lng = -180;
        }
      })
      .onPointClick((d) => {
        if (window.sfx) window.sfx.playBeep();
        if (window.world) window.world.controls().autoRotate = false;
        window.world.pointOfView(
          { lat: d.lat, lng: d.lng, altitude: 1.2 },
          1500
        );
        if (window.showInspector) window.showInspector(d);
      });

    window.world.customThreeObject((d) => {
      const geometry =
        d.type === "NUCLEAR PLANT"
          ? new THREE.CylinderGeometry(0.5, 0.5, 2, 8)
          : new THREE.TetrahedronGeometry(1.2);
      const material = new THREE.MeshBasicMaterial({ color: d.color });
      if (d.type === "SATELLITE") {
        material.transparent = true;
        material.opacity = 0.6;
      }
      return new THREE.Mesh(geometry, material);
    });

    window.world.controls().autoRotate = true;
    window.world.controls().autoRotateSpeed = 0.15;
  } catch (e) {
    console.error("Globe Init Failed:", e);
  }
}

// 3. Khởi tạo Biểu đồ
function initCharts() {
  Chart.defaults.color = "#666";
  Chart.defaults.font.family = "Rajdhani";

  const ctxWave = document.getElementById("waveChart");
  if (ctxWave) {
    window.waveChart = new Chart(ctxWave, {
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

  const ctxRadar = document.getElementById("radarChart");
  if (ctxRadar) {
    window.radarChart = new Chart(ctxRadar, {
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

initGlobe();
initCharts();
