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
const highlightColor = 0xffffff;

// --- Emoji Cache ---
const emojiCache = {};
function getEmojiSprite(emoji, scale = 1.0) {
    if (!emojiCache[emoji]) {
        const canvas = document.createElement('canvas');
        canvas.width = 128;
        canvas.height = 128;
        const ctx = canvas.getContext('2d');
        ctx.font = '80px sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        // Thêm hiệu ứng phát sáng cho Emoji
        ctx.shadowColor = '#00ffff';
        ctx.shadowBlur = 15;
        ctx.fillText(emoji, 64, 64);
        emojiCache[emoji] = new THREE.CanvasTexture(canvas);
        emojiCache[emoji].needsUpdate = true;
    }
    const material = new THREE.SpriteMaterial({ map: emojiCache[emoji], transparent: true, depthTest: true });
    const sprite = new THREE.Sprite(material);
    sprite.scale.set(1.5 * scale, 1.5 * scale, 1.5 * scale); // Thu nhỏ icon lại để không bị đè nhau
    return sprite;
}

let _hoveredUid = null;
let _selectedUid = null;
let _inspectorOpen = false;

window.gcUidToGroup = function(validData) {
  const validUids = new Set(validData.map(d => d._uid));
  for (const uid of _uidToGroup.keys()) {
    if (!validUids.has(uid)) {
      _uidToGroup.delete(uid);
    }
  }
};

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

// (Removed Canvas Texture block to save memory)
function initGlobe() {
  try {
    window.world = Globe()(document.getElementById("globe-viz"))
      .globeImageUrl("//unpkg.com/three-globe/example/img/earth-night.jpg")
      .bumpImageUrl("//unpkg.com/three-globe/example/img/earth-topology.png")
      .backgroundImageUrl("//unpkg.com/three-globe/example/img/night-sky.png")
      .atmosphereColor("#002244")
      .atmosphereAltitude(0.15)

      // Cấu hình Sóng Xung Kích ôm sát bề mặt Trái Đất (Hiệu ứng gợn sóng mượt)
      .ringColor(d => d.color)
      .ringMaxRadius(d => (d.maxR || 0) / 10) // Bán kính
      .ringPropagationSpeed(d => (d.propagationSpeed || 1) * 0.3) // Làm chậm tốc độ lan truyền (slow ripple)
      .ringRepeatPeriod(d => (d.maxR > 0) ? 700 : 0) // Tần suất sóng liên tục (dưới 1s)

      // --- Cấu hình Hexagon Heatmap cho AI Risk ---
      .hexBinPointWeight('alt')
      .hexBinResolution(4) // Tăng độ phân giải để các ô nhỏ lại, mịn hơn
      .hexMargin(0) // Không có khoảng cách giữa các ô -> tạo thành mảng liên tục
      .hexAltitude(0.005) // Dát mỏng, ôm sát mặt đất như bản đồ nhiệt
      .hexBinMerge(true)
      .hexTransitionDuration(1000)
      .hexTopColor(d => d.sumWeight > 0.3 ? '#ff003c' : '#ffaa00')
      .hexSideColor(d => d.sumWeight > 0.3 ? '#880020' : '#885500')

    // Cấu hình Custom Layer cho Hình thù đặc trưng
      .customThreeObject((d) => {
        const group = new THREE.Group();
        const isNuclear = d.type === "NUCLEAR PLANT";
        const isAI = d.type && d.type.includes("AI");

        // --- 1. Vẽ Cột Năng Lượng (Laser Beam) ---
        const colHeight = Math.max((d.alt || 0) * 12, isNuclear ? 3.5 : 1.5);
        
        // Sử dụng chung 1 khối trụ (Cylinder) cho tất cả. Bán kính 0.4 để đủ to dễ bấm chuột, nhưng không bị lấn sang nhau
        const colGeo = new THREE.CylinderGeometry(0.4, 0.4, colHeight, 8);
        colGeo.translate(0, colHeight / 2, 0);

        const colMat = new THREE.MeshStandardMaterial({
          color: d.color,
          transparent: true,
          opacity: isAI ? 0.9 : 0.8,
          wireframe: false, // Tắt wireframe để laser luôn nhìn thấy rõ
          emissive: d.color,
          emissiveIntensity: isAI ? 2.0 : 0.8, // Tăng cường độ sáng cho AI
        });
        if (isAI) {
            colMat.blending = THREE.AdditiveBlending; 
        }
        
        // Tạo Mesh chính (cột laser)
        const column = new THREE.Mesh(colGeo, colMat);
        column.__data = d;
        
        // --- 2. Thêm Emoji Trực Quan Lên Đỉnh Cột ---
        let emoji = '🔴'; // Mặc định
        let scale = 1.0;
        if (isAI) { emoji = '👁️'; scale = 1.5; }
        else if (isNuclear) { emoji = '☢️'; scale = 1.5; }
        else if (d.type && d.type.includes("WILDFIRE")) emoji = '🔥';
        else if (d.type && d.type.includes("STORM")) emoji = '🌀';
        else if (d.type && d.type.includes("QUAKE")) emoji = '💥';
        else if (d.type && d.type.includes("VOLCANO")) emoji = '🌋';
        else if (d.type && d.type.includes("FLOOD")) emoji = '🌊';
        else if (d.type && d.type.includes("DROUGHT")) emoji = '🏜️';

        const sprite = getEmojiSprite(emoji, scale);
        // Đặt Emoji nằm trên đỉnh cột
        sprite.position.set(0, colHeight + 0.5, 0);
        sprite.raycast = function() {}; // Vô hiệu hoá raycast
        column.add(sprite); // Add sprite as child of column

        // Luôn luôn vẽ hình thù 3D (column)
        group.add(column);
        
        // Đã xóa HitBox tàng hình và Heatmap 3D tự chế vì bị lỗi render

        group.userData = {
          column: column, // Dùng lại biểu tượng 3D làm gốc highlight cho đồng bộ
          isAI: isAI,
          type: d.type || "UNKNOWN",
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

        // Các hiệu ứng xoay (Rotation) đặc thù cho từng loại thiên tai
        const typeStr = obj.userData.type || "";
        if (obj.userData.isAI) {
            obj.userData.column.rotation.y += 0.05;
            obj.userData.column.rotation.z += 0.02;
        } else if (typeStr.includes("STORM")) {
            // Bão xoáy tròn
            obj.userData.column.rotation.y -= 0.08;
            obj.userData.column.rotation.x += 0.01;
        } else if (typeStr.includes("WILDFIRE")) {
            // Lửa bập bùng (Scale nhấp nháy)
            const pulse = 1 + Math.sin(Date.now() * 0.01) * 0.2;
            obj.userData.column.scale.set(1, pulse, 1);
        } else if (typeStr.includes("QUAKE")) {
            // Động đất đập thình thịch
            const pulse = 1 + Math.sin(Date.now() * 0.02) * 0.15;
            obj.userData.column.scale.set(pulse, pulse, pulse);
        }
      })
      .onCustomLayerHover((d, prevD) => {
        if (!d && !prevD) return; // Early return nếu di chuyển chuột trong vùng trống
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

    // --- LỚP PHỦ MÂY VỆ TINH (CLOUDS) ---
    const CLOUDS_IMG_URL = '/static/img/clouds.png';
    const CLOUDS_ALT = 0.008; // Nâng lên một chút để không bị che
    const CLOUDS_ROTATION_SPEED = -0.005; // deg/frame

    const textureLoader = new THREE.TextureLoader();
    textureLoader.crossOrigin = 'Anonymous';
    textureLoader.load(
      CLOUDS_IMG_URL,
      cloudsTexture => {
        const clouds = new THREE.Mesh(
          new THREE.SphereGeometry(window.world.getGlobeRadius() * (1 + CLOUDS_ALT), 75, 75),
          new THREE.MeshLambertMaterial({ map: cloudsTexture, transparent: true, opacity: 0.8 })
        );
        // Vô hiệu hóa bắt sự kiện chuột trên lớp mây để không chặn click xuống quả cầu
        clouds.raycast = function() {}; 
        window.world.scene().add(clouds);

        (function rotateClouds() {
          clouds.rotation.y += CLOUDS_ROTATION_SPEED * Math.PI / 180;
          requestAnimationFrame(rotateClouds);
        })();
      },
      undefined,
      err => console.error("Failed to load clouds:", err)
    );

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
