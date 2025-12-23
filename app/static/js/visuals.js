// --- VISUALIZATION MODULE (Ultra Graphics Edition) ---

// 1. Dữ liệu tĩnh (Vệ tinh & Nhà máy hạt nhân)
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

// [QUAN TRỌNG] Gắn biến này vào window để main.js có thể đọc được
window.nuclearPlants = nuclearPlants;

// Khai báo biến toàn cục cho Globe và Chart
window.world = null;
window.waveChart = null;
window.radarChart = null;

// 2. Khởi tạo Globe (Nâng cấp đồ họa)
function initGlobe() {
  try {
    window.world = Globe()(document.getElementById("globe-viz"))
      // --- GÓI ĐỒ HỌA ULTRA DETAIL ---
      // 1. Bề mặt Trái đất (Thành phố sáng đèn ban đêm)
      .globeImageUrl("//unpkg.com/three-globe/example/img/earth-night.jpg")

      // 2. Bản đồ độ cao (Núi non gồ ghề, chi tiết cao)
      .bumpImageUrl("//i.imgur.com/wPZq7xO.jpg")

      // 3. Bản đồ phản quang (Giúp đại dương bóng loáng, phản chiếu ánh sáng)
      .globeSpecularImageUrl(
        "//unpkg.com/three-globe/example/img/earth-water.png"
      )

      // 4. Hình nền vũ trụ (Milky Way)
      .backgroundImageUrl("//unpkg.com/three-globe/example/img/night-sky.png")

      // 5. Khí quyển (Tăng độ dày và sáng)
      .atmosphereColor("#00f3ff")
      .atmosphereAltitude(0.25)
      // -------------------------------

      // Cấu hình điểm dữ liệu (Points)
      .pointAltitude("alt")
      .pointColor("color")
      .pointRadius(0.5)
      .pointsMerge(false)

      // Cấu hình vòng sóng lan truyền (Rings)
      .ringColor("color")
      .ringMaxRadius("maxR")
      .ringPropagationSpeed("propagationSpeed")
      .ringRepeatPeriod("repeatPeriod")

      // Layer Vệ tinh (Custom Data)
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

      // Sự kiện Click
      .onPointClick((d) => {
        if (window.sfx) window.sfx.playBeep();
        // Dừng tự động quay để người dùng xem chi tiết
        if (window.world) window.world.controls().autoRotate = false;

        // Bay đến điểm được click
        window.world.pointOfView(
          { lat: d.lat, lng: d.lng, altitude: 1.2 },
          1500
        );

        // Hiển thị thông tin
        if (window.showInspector) window.showInspector(d);
      });

    // Custom Objects (Vẽ nhà máy hạt nhân & Vệ tinh)
    window.world.customThreeObject((d) => {
      // Nhà máy hạt nhân: Hình trụ
      // Sự kiện khác: Hình tứ diện
      const geometry =
        d.type === "NUCLEAR PLANT"
          ? new THREE.CylinderGeometry(0.5, 0.5, 2, 8)
          : new THREE.TetrahedronGeometry(1.2);
      const material = new THREE.MeshBasicMaterial({ color: d.color });

      // Hiệu ứng trong suốt cho vệ tinh
      if (d.type === "SATELLITE") {
        material.transparent = true;
        material.opacity = 0.6;
      }
      return new THREE.Mesh(geometry, material);
    });

    // Thiết lập camera quay tự động
    window.world.controls().autoRotate = true;
    window.world.controls().autoRotateSpeed = 0.15; // Tốc độ quay chậm (Cinematic)
  } catch (e) {
    console.error("Globe Init Failed:", e);
  }
}

// 3. Khởi tạo Biểu đồ (Charts)
function initCharts() {
  Chart.defaults.color = "#666";
  Chart.defaults.font.family = "Rajdhani";

  // Biểu đồ sóng (Wave Chart) - Gắn vào window
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

  // Biểu đồ radar (Radar Chart) - Gắn vào window
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
        scales: {
          r: {
            grid: { color: "#333" },
            ticks: { display: false },
          },
        },
      },
    });
  }
}

// Khởi chạy
initGlobe();
initCharts();
