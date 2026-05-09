// --- VISUALIZATION MODULE (Custom Layer V2) ---

const nuclearPlants = [
  { name: "Fukushima Daiichi", lat: 37.421, lng: 141.033, desc: "Japan" },
  { name: "Zaporizhzhia", lat: 47.512, lng: 34.586, desc: "Ukraine" },
  { name: "Kashiwazaki-Kariwa", lat: 37.429, lng: 138.596, desc: "Japan" },
  { name: "Diablo Canyon", lat: 35.211, lng: -120.855, desc: "USA" },
  { name: "Kori Nuclear Power Plant", lat: 35.316, lng: 129.292, desc: "South Korea" },
  { name: "Bruce Nuclear Gen", lat: 44.325, lng: -81.599, desc: "Canada" },
  { name: "Gravelines", lat: 51.015, lng: 2.136, desc: "France" },
];

window.nuclearPlants = nuclearPlants;

window.world = null;
window.waveChart = null;
window.radarChart = null;

// Track các đối tượng được hover/click để highlight
let _hoveredObj = null;
let _selectedObj = null;

function _setHighlight(obj, mode) {
  if (!obj || !obj.userData || !obj.userData.column) return;
  const col = obj.userData.column;
  if (mode === 'selected') {
    col.scale.set(1.6, 1.6, 1.6);
    col.material.opacity = 1.0;
  } else if (mode === 'hover') {
    col.scale.set(1.3, 1.3, 1.3);
    col.material.opacity = 0.9;
  } else {
    col.scale.set(1, 1, 1);
    col.material.opacity = col.material._baseOpacity || 0.6;
  }
}

// Expose để closeInspector trong main.js có thể gọi để bỏ highlight selected
window.clearSelectedHighlight = () => {
  if (_selectedObj) {
    _setHighlight(_selectedObj, 'none');
    _selectedObj = null;
  }
};

function initGlobe() {
  try {
    window.world = Globe()(document.getElementById("globe-viz"))
      .globeImageUrl("//unpkg.com/three-globe/example/img/earth-night.jpg")
      .bumpImageUrl("//unpkg.com/three-globe/example/img/earth-topology.png")
      .backgroundImageUrl("//unpkg.com/three-globe/example/img/night-sky.png")
      .atmosphereColor("#00f3ff")
      .atmosphereAltitude(0.25)

      // Cấu hình Custom Layer cho Cột và Vòng sóng
      .customThreeObject((d) => {
        const group = new THREE.Group();
        const isNuclear = d.type === "NUCLEAR PLANT";
        const isAI = d.type === "AI PREDICTION";

        // --- 1. Vẽ Cột Năng Lượng (Column) ---
        const colHeight = Math.max((d.alt || 0) * 15, isNuclear ? 4 : 0.5);
        let colGeo;
        if (isAI) {
            colGeo = new THREE.IcosahedronGeometry(1.5, 0);
            colGeo.translate(0, 1.5, 0);
        } else if (isNuclear) {
            colGeo = new THREE.CylinderGeometry(0.8, 0.8, colHeight, 6);
            colGeo.translate(0, colHeight / 2, 0);
        } else {
            // Cột thiên tai lớn hơn để dễ nhìn và dễ click
            colGeo = new THREE.CylinderGeometry(0.4, 0.8, colHeight, 8);
            colGeo.translate(0, colHeight / 2, 0);
        }

        const colMat = new THREE.MeshBasicMaterial({
          color: d.color,
          transparent: true,
          opacity: isAI ? 0.8 : 0.6,
          wireframe: isAI,
          blending: THREE.AdditiveBlending,
        });
        const column = new THREE.Mesh(colGeo, colMat);
        // Lưu opacity gốc để restore khi bỏ highlight
        colMat._baseOpacity = isAI ? 0.8 : 0.6;
        group.add(column);

        // --- 2. Vẽ Vòng Sóng (Wave Ring) ---
        // Vòng sóng được thiết kế là một viền mảnh, lan tỏa ra xung quanh
        const ringGeo = new THREE.RingGeometry(1.4, 1.5, 32); // Viền mỏng
        const ringMat = new THREE.MeshBasicMaterial({
          color: d.color,
          transparent: true,
          opacity: 0.8,
          side: THREE.DoubleSide,
          blending: THREE.AdditiveBlending,
          depthWrite: false
        });
        const ring = new THREE.Mesh(ringGeo, ringMat);
        ring.rotation.x = -Math.PI / 2; // Đặt nằm ngang so với cột
        ring.raycast = function() {}; // QUAN TRỌNG: Vô hiệu hóa click vào vòng sóng để không che mất Cột
        
        if (d.maxR > 0) {
            group.add(ring);
        }

        // Lưu trữ biến state animation
        group.userData = {
          ring: ring,
          column: column,
          maxR: d.maxR || 0,
          speed: (d.propagationSpeed || 2) * 0.005,
          animOffset: Math.random(), // Chạy lệch pha nhau
          isAI: isAI
        };

        // Quan trọng: Gắn dữ liệu gốc để dùng cho sự kiện Click
        group.__data = d;
        return group;
      })
      .customLayerLabel(d => d.place || d.type) // Kích hoạt tương tác Hover/Click cho Custom Layer
      .customThreeObjectUpdate((obj, d) => {
        // Cập nhật vị trí lên bề mặt quả cầu (alt = 0)
        Object.assign(obj.position, window.world.getCoords(d.lat, d.lng, 0));
        
        // Hướng trục Y của Cụm ra ngoài không gian
        const lookDir = obj.position.clone().multiplyScalar(2);
        obj.lookAt(lookDir);
        obj.rotateX(Math.PI / 2);

        // Chạy Animation cho Vòng sóng độc lập (Không bị giật khi Filter)
        if (obj.userData.maxR > 0) {
            obj.userData.animOffset += obj.userData.speed;
            if (obj.userData.animOffset > 1) {
                obj.userData.animOffset = 0;
            }
            
            const t = obj.userData.animOffset;
            const currentScale = 1 + t * obj.userData.maxR * 2;
            
            obj.userData.ring.scale.set(currentScale, currentScale, currentScale);
            // Mờ dần về 0 khi lan rộng ra
            obj.userData.ring.material.opacity = (1 - Math.pow(t, 2)) * 0.8;
        }

        // Xoay khối cầu AI
        if (obj.userData.isAI) {
            obj.userData.column.rotation.y += 0.05;
            obj.userData.column.rotation.z += 0.02;
        }
      })
      .onCustomLayerHover((d, prevD, obj) => {
        if (window.world) {
            window.world.controls().autoRotate = !d;
            document.getElementById("globe-viz").style.cursor = d ? 'pointer' : 'default';
        }

        // Bỏ highlight hover trên đối tượng cũ (trừ khi đang được selected)
        if (_hoveredObj && _hoveredObj !== _selectedObj) {
            _setHighlight(_hoveredObj, 'none');
        }
        // Áp highlight hover lên đối tượng mới (trừ khi đang được selected)
        _hoveredObj = obj || null;
        if (_hoveredObj && _hoveredObj !== _selectedObj) {
            _setHighlight(_hoveredObj, 'hover');
        }
      })
      .onCustomLayerClick((d, obj) => {
        if (!d) return;
        if (window.sfx) window.sfx.playBeep();
        if (window.world) window.world.controls().autoRotate = false;
        window.world.pointOfView({ lat: d.lat, lng: d.lng, altitude: 1.2 }, 1500);

        // Bỏ highlight selected trên đối tượng cũ
        if (_selectedObj && _selectedObj !== obj) {
            _setHighlight(_selectedObj, 'none');
        }
        // Áp highlight selected (to hơn + sáng hơn) lên đối tượng vừa bấm
        _selectedObj = obj || null;
        if (_selectedObj) {
            _setHighlight(_selectedObj, 'selected');
        }

        if (window.showInspector) window.showInspector(d);
      });

    window.world.controls().autoRotate = true;
    window.world.controls().autoRotateSpeed = 0.15;
  } catch (e) {
    console.error("Globe Init Failed:", e);
  }
}

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
