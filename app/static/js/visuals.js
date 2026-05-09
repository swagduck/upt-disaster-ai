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

// Map từ _uid -> Three.js Group, để highlight trực tiếp khi event bắn
const _uidToGroup = new Map();
let _hoveredUid = null;
let _selectedUid = null;
let _inspectorOpen = false;

function _applyHighlight(group, mode, d) {
  const col = group && group.userData && group.userData.column;
  if (!col) return;
  const baseOpacity = col.material._baseOpacity || 0.6;
  if (mode === 'selected') {
    col.scale.set(1.8, 1.8, 1.8);
    col.material.opacity = 1.0;
    col.material.color.set(0xffffff);
  } else if (mode === 'hover') {
    col.scale.set(1.4, 1.4, 1.4);
    col.material.opacity = 1.0;
    col.material.color.set(0xffff00);
  } else {
    col.scale.set(1, 1, 1);
    col.material.opacity = baseOpacity;
    col.material.color.set(d && d.color ? d.color : '#aaaaaa');
  }
}

window.clearSelectedHighlight = () => {
  if (_selectedUid) {
    const obj = _uidToGroup.get(_selectedUid);
    const d = obj && obj.__data;
    _applyHighlight(obj, 'none', d);
    _selectedUid = null;
  }
  _inspectorOpen = false;
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
        colMat._baseOpacity = isAI ? 0.8 : 0.6;
        // FIX: gắn __data vào cả mesh con để Globe.gl tìm được datum khi raycast trúng cylinder
        column.__data = d;
        group.add(column);

        // --- 2. Vẽ Vòng Sóng (Wave Ring) ---
        const ringGeo = new THREE.RingGeometry(1.4, 1.5, 32);
        const ringMat = new THREE.MeshBasicMaterial({
          color: d.color,
          transparent: true,
          opacity: 0.8,
          side: THREE.DoubleSide,
          blending: THREE.AdditiveBlending,
          depthWrite: false
        });
        const ring = new THREE.Mesh(ringGeo, ringMat);
        ring.rotation.x = -Math.PI / 2;
        ring.raycast = function() {}; // Tắt raycast vòng sóng, không cản click vào cột
        ring.__data = d; // safety

        if (d.maxR > 0) {
            group.add(ring);
        }

        group.userData = {
          ring: ring,
          column: column,
          maxR: d.maxR || 0,
          speed: (d.propagationSpeed || 2) * 0.005,
          animOffset: Math.random(),
          isAI: isAI,
          oriented: false
        };

        group.__data = d;
        // Đăng ký vào map để event handler có thể tìm và highlight trực tiếp
        if (d._uid) _uidToGroup.set(d._uid, group);
        return group;
      })
      .customLayerLabel(d => d.place || d.type) // Kích hoạt tương tác Hover/Click cho Custom Layer
      .customThreeObjectUpdate((obj, d) => {
        Object.assign(obj.position, window.world.getCoords(d.lat, d.lng, 0));

        // FIX: chỉ orient lần đầu, tránh rotateX tích lũy mỗi frame
        if (!obj.userData.oriented) {
            const lookDir = obj.position.clone().multiplyScalar(2);
            obj.lookAt(lookDir);
            obj.rotateX(Math.PI / 2);
            obj.userData.oriented = true;
        }

        // Chạy Animation cho Vòng sóng độc lập (Không bị giật khi Filter)
        if (obj.userData.maxR > 0) {
            obj.userData.animOffset += obj.userData.speed;
            if (obj.userData.animOffset > 1) obj.userData.animOffset = 0;
            const t = obj.userData.animOffset;
            obj.userData.ring.scale.set(1 + t * obj.userData.maxR * 2, 1 + t * obj.userData.maxR * 2, 1);
            obj.userData.ring.material.opacity = (1 - Math.pow(t, 2)) * 0.8;
        }

        // Xoay khối cầu AI
        if (obj.userData.isAI) {
            obj.userData.column.rotation.y += 0.05;
            obj.userData.column.rotation.z += 0.02;
        }
      })
      .onCustomLayerHover((d, prevD) => {
        // Bỏ highlight hover cũ
        if (_hoveredUid && _hoveredUid !== _selectedUid) {
            const prevGroup = _uidToGroup.get(_hoveredUid);
            _applyHighlight(prevGroup, 'none', prevGroup && prevGroup.__data);
        }
        _hoveredUid = d ? (d._uid || null) : null;
        // Áp highlight hover mới trực tiếp
        if (_hoveredUid && _hoveredUid !== _selectedUid) {
            const group = _uidToGroup.get(_hoveredUid);
            _applyHighlight(group, 'hover', d);
        }
        if (window.world && !_inspectorOpen) {
            window.world.controls().autoRotate = !d;
        }
        document.getElementById("globe-viz").style.cursor = d ? 'pointer' : 'default';
      })
      .onCustomLayerClick((d) => {
        if (!d) return;
        // Bỏ highlight selected cũ
        if (_selectedUid) {
            const prevGroup = _uidToGroup.get(_selectedUid);
            _applyHighlight(prevGroup, 'none', prevGroup && prevGroup.__data);
        }
        _selectedUid = d._uid || null;
        _inspectorOpen = true;
        // Áp highlight selected trực tiếp
        const selGroup = _uidToGroup.get(_selectedUid);
        _applyHighlight(selGroup, 'selected', d);
        if (window.sfx) window.sfx.playBeep();
        if (window.world) window.world.controls().autoRotate = false;
        window.world.pointOfView({ lat: d.lat, lng: d.lng, altitude: 1.2 }, 1500);
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
