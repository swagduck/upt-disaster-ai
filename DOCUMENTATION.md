# UPT DISASTER AI — DOCUMENTATION ĐẦY ĐỦ

> **Version:** 28.2.0 | **Stack:** FastAPI · Python 3.11 · MongoDB Atlas · Scikit-Learn · Globe.gl · Chart.js  
> **Deploy:** Render.com (Free Tier) | **Repo:** https://github.com/swagduck/upt-disaster-ai

---

## 1. TỔNG QUAN HỆ THỐNG

UPT Disaster AI là một hệ thống **Giám sát Thiên tai Toàn cầu và Dự báo Rủi ro Thời gian Thực**. Hệ thống kết hợp:

- Dữ liệu động đất từ **USGS** và thảm họa từ **NASA EONET/DONKI**
- Mô hình AI **HistGradientBoostingRegressor** (Scikit-Learn) để dự báo rủi ro
- Giao diện **Globe.gl 3D** tương tác trực quan trên trình duyệt
- Mô phỏng lò phản ứng lượng tử **UPT-RC** phản ứng theo thiên tai thực tế
- Trang **Analytics Dashboard** phân tích dữ liệu lịch sử

---

## 2. KIẾN TRÚC HỆ THỐNG

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT (Browser)                         │
│  ┌─────────────────┐        ┌───────────────────────────────┐   │
│  │ index.html      │        │ dashboard.html (Analytics)    │   │
│  │ Globe.gl 3D     │        │ Chart.js · KPI · AI Scan Panel│   │
│  │ Terminal CMD    │        └───────────────────────────────┘   │
│  │ Reactor HUD     │                                            │
│  └────────┬────────┘                                            │
└───────────┼─────────────────────────────────────────────────────┘
            │ HTTP / WebSocket
┌───────────▼─────────────────────────────────────────────────────┐
│                     FASTAPI BACKEND (Render.com)                 │
│                                                                  │
│  ┌──────────────┐  ┌─────────────────┐  ┌────────────────────┐  │
│  │ /api/v1      │  │ /api/v1/reactor │  │ /api/v1/predict    │  │
│  │ (stats/data) │  │ (Reactor Core)  │  │ (AI Prediction)    │  │
│  └──────┬───────┘  └───────┬─────────┘  └────────┬───────────┘  │
│         │                  │                      │              │
│  ┌──────▼──────────────────▼──────────────────────▼───────────┐  │
│  │                    CORE SERVICES                            │  │
│  │  DisasterService  │  UPTReactorCore  │  DeepGuardian (AI)  │  │
│  └──────┬────────────┴──────────────────┴──────────┬──────────┘  │
└─────────┼────────────────────────────────────────────┼───────────┘
          │                                            │
┌─────────▼────────────┐                  ┌───────────▼────────────┐
│   EXTERNAL APIs      │                  │     MONGODB ATLAS       │
│  • USGS GeoJSON      │                  │  Collection: raw_logs   │
│  • NASA EONET v3     │                  │  Collection: alerts_subs│
│  • NASA DONKI (Solar)│                  │  (Disaster Snapshots)   │
└──────────────────────┘                  └────────────────────────┘
```

---

## 3. CẤU TRÚC THƯ MỤC

```
upt-disaster-ai/
├── app/
│   ├── main.py                    # FastAPI entry point, lifespan, router mounting
│   ├── core/
│   │   ├── config.py              # Pydantic Settings (đọc .env)
│   │   ├── database.py            # MongoDB singleton connection
│   │   ├── logger.py              # Structured logging
│   │   ├── limiter.py             # SlowAPI rate limiting
│   │   └── security.py            # X-API-Key authentication dependency
│   ├── api/
│   │   └── v1/
│   │       └── endpoints/
│   │           ├── router.py      # /api/v1/disasters, /api/v1/stats
│   │           ├── reactor.py     # /api/v1/reactor/*
│   │           └── prediction.py  # /api/v1/predict/*
│   ├── upt_engine/
│   │   ├── deep_core.py           # DeepGuardian AI (HistGradientBoosting)
│   │   ├── reactor_core.py        # UPT-RC Physics Simulation
│   │   └── formulas.py            # UPTMath (geomagnetic coupling, etc.)
│   ├── services/
│   │   ├── earthquake_service.py  # Data fetching từ USGS + NASA
│   │   └── alert_service.py       # Twilio SMS alert service
│   ├── models/                    # Pydantic DB models
│   ├── schemas/                   # Pydantic request/response schemas
│   └── static/
│       ├── index.html             # Trang chủ (Globe 3D + Terminal)
│       ├── dashboard.html         # Trang Analytics
│       ├── style.css              # CSS cyberpunk theme
│       ├── manifest.json          # PWA manifest
│       └── js/
│           ├── main.js            # Logic chính (AI, commands, filters)
│           └── visuals.js         # Globe.gl 3D rendering
├── tests/
│   ├── test_api_endpoints.py
│   ├── test_earthquake_service.py
│   ├── test_reactor_core.py
│   └── test_upt_math.py
├── .github/workflows/ci.yml       # GitHub Actions CI
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── DOCUMENTATION.md               # File này
```

---

## 4. LUỒNG DỮ LIỆU (DATA FLOW)

### 4.1 Thu thập dữ liệu thời gian thực

```
[STARTUP / APScheduler mỗi N phút]
        │
        ▼
DisasterService.fetch_all_realtime()
        │
        ├─── GET USGS GeoJSON ──► Lọc động đất mag >= 1.0
        │                         Tính energy_level = mag / 9.0
        │
        ├─── GET NASA EONET ───► Wildfires, Volcanoes, Storms, Icebergs
        │                        energy_level cố định theo loại thảm họa
        │
        └─── GET NASA DONKI ───► Solar Flares (B/C/M/X class)
                                  Tính total_cosmic_energy
                                  → Inject vào UPT Reactor
                                  
        │
        ▼
sensors = [{type, place, lat, lon, energy_level, anomaly_score, raw_val}]
        │
        ├─── DisasterService.LATEST_DATA = sensors   (In-memory cache)
        │
        ├─── guardian_brain.update_realtime_state(sensors)
        │      └── Cập nhật realtime_buffer (deque, kích thước = look_back)
        │
        └─── MongoDB.raw_logs.insert({timestamp, total_events, max_magnitude, sensors_data})
```

### 4.2 Luồng AI Prediction

```
[User bấm NEURAL AI hoặc gọi API /global-scan]
        │
        ▼
runNeuralPrediction() [Frontend JS]
        │
        ▼
GET /api/v1/predict/global-scan
        │
        ├── Lấy live_events từ DisasterService.LATEST_DATA
        │
        ├── Với mỗi trong 20 HOTSPOTS:
        │     ├── _calc_local_energy(lat, lon, live_events, radius=800km)
        │     │     └── Tính tổng năng lượng từ các thiên tai trong bán kính 800km
        │     │         log1p(total) / log1p(10) [tránh bão hòa]
        │     │
        │     └── guardian_brain.predict_risk(lat, lon, local_energy, local_anomaly)
        │           ├── Nếu chưa có đủ dữ liệu: trả về local_energy * 0.7 + local_anomaly * 0.3
        │           └── Nếu đã train:
        │                 ├── Lấy 20 snapshot gần nhất từ realtime_buffer
        │                 ├── MinMaxScaler.transform(raw_seq)
        │                 ├── model.predict(input_flattened) → global_instability
        │                 └── final_risk = global_instability*0.7 + local_energy*0.3
        │
        ▼
Response: [{name, lat, lon, risk_score, local_energy, alert_level}]
        │
        ▼
Frontend vẽ Icosahedron 3D lên Globe (đỏ=CRITICAL, vàng=WARNING, xanh=NORMAL)
```

### 4.3 Luồng Training AI

```
[STARTUP hoặc User gõ "train" / POST /predict/train]
        │
        ▼
guardian_brain.initialize() / train_from_memory()
        │
        ├── Truy vấn MongoDB raw_logs (200 snapshot gần nhất)
        │
        ├── Tạo Feature Matrix:
        │     Dataset = [total_events, max_magnitude, max_anomaly] (theo thời gian)
        │     MinMaxScaler.fit_transform(dataset)
        │
        ├── Sliding Window (look_back=20, forecast_horizon=5):
        │     X[i] = 20 snapshots liên tiếp (flattened)
        │     y[i] = risk tại snapshot thứ (i + 5) trong tương lai
        │
        ├── Chronological Split 80/20:
        │     X_train = X[:80%]   → Model học
        │     X_test  = X[80%:]   → Đánh giá độ chính xác thực tế
        │
        ├── HistGradientBoostingRegressor.fit(X_train, y_train)
        │
        └── evaluate_accuracy(X_test, y_test)
              ├── MSE, MAE
              └── accuracy_score = (1 - MAE) * 100%
              → Lưu vào guardian_brain.metrics
```

### 4.4 Luồng Reactor Physics

```
[Mỗi frame của simulation loop]
        │
        ├── Tính neutron_flux, k_eff, core_temp dựa trên:
        │     CONST_C_GEO=0.911, CONST_TAU_ION=0.080, CONST_RES_FREQ=2.148
        │
        ├── Khi có động đất >= 6.0 Richter:
        │     upt_reactor.update_external_stress(energy) → Tăng entropy
        │
        ├── Khi có Solar Flare mạnh (M/X class):
        │     upt_reactor.inject_cosmic_interference(coupling_factor)
        │     → Tăng geomagnetic_residual và phase_noise
        │
        └── User bấm SCRAM:
              trigger_phase_detuning() → status = "SCRAM"
              Reactor ngừng hoạt động
```

---

## 5. API ENDPOINTS ĐẦY ĐỦ

### 5.1 Data & Stats — `/api/v1/`

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| `GET` | `/disasters/live` | Trả về danh sách thiên tai đang xảy ra (từ in-memory cache) |
| `GET` | `/stats/summary` | KPI tổng hợp: tổng sự kiện, magnitude cao nhất, snapshot 24h |
| `GET` | `/stats/trend?hours=24` | Chuỗi thời gian để vẽ biểu đồ xu hướng (6H/24H/3D/7D) |

### 5.2 Reactor — `/api/v1/reactor/`

| Method | Endpoint | Mô tả | Auth |
|--------|----------|-------|------|
| `GET` | `/status` | Trạng thái hiện tại của lò phản ứng | — |
| `POST` | `/start` | Kích hoạt lò phản ứng | ✅ X-API-Key |
| `POST` | `/scram` | Dừng khẩn cấp (SCRAM) | ✅ X-API-Key |
| `POST` | `/inject-event` | Inject sự kiện thủ công vào reactor | ✅ X-API-Key |

### 5.3 AI Prediction — `/api/v1/predict/`

| Method | Endpoint | Mô tả | Auth |
|--------|----------|-------|------|
| `GET` | `/status` | Trạng thái AI model (ONLINE/INITIALIZING) | — |
| `GET` | `/evaluation` | Độ chính xác AI (MSE, MAE, Tolerance Accuracy %) | — |
| `GET` | `/global-scan` | Quét rủi ro tại 20 điểm nóng toàn cầu | — |
| `POST` | `/forecast` | Dự báo rủi ro tại toạ độ bất kỳ | ✅ X-API-Key |
| `POST` | `/train` | Kích hoạt huấn luyện AI từ MongoDB | ✅ X-API-Key |
| `POST` | `/predict` | Dự báo nhanh (legacy endpoint) | — |

---

## 6. MÔ HÌNH AI — DeepGuardian

### Thuật toán
- **Model:** `HistGradientBoostingRegressor` (Scikit-Learn)
- **Lý do chọn:** Cực kỳ tiết kiệm RAM (~50MB), không cần TensorFlow/PyTorch, phù hợp Render Free Tier (512MB RAM)
- **Input:** Feature vector từ 20 snapshot lịch sử (Sliding Window)
- **Output:** Giá trị rủi ro trong khoảng [0.0, 1.0]

### Features (3 chiều × 20 timesteps = 60 features)
| Feature | Mô tả |
|---------|-------|
| `total_events` | Tổng số thiên tai được ghi nhận trong snapshot |
| `max_magnitude` | Độ richter cao nhất trong snapshot |
| `max_anomaly_score` | Điểm bất thường cao nhất (0-1) |

### Training Strategy
- **Chronological Split:** 80% dữ liệu cũ nhất để train, 20% mới nhất để test
- **Forecast Horizon = 5:** Dự đoán rủi ro tại thời điểm **5 nhịp sau** (không phải nhịp kế tiếp ngay)
- **Thang đo:** MinMaxScaler fit trên toàn bộ dữ liệu trước khi split

### Công thức Predict Risk
```python
global_instability = model.predict(window_of_20_snapshots)
final_risk = global_instability * 0.7 + local_energy * 0.3
```

### Tính Local Energy (hàm `_calc_local_energy`)
```python
for each event in live_events:
    dist = haversine(hotspot, event)
    if dist < 800km:
        impact = event.energy_level * (1 - dist / 800)
        total += impact

local_energy = log1p(total) / log1p(10)  # Tránh bão hòa 100%
```

---

## 7. GIAO DIỆN NGƯỜI DÙNG

### 7.1 Trang chủ (`/`) — Globe 3D

| Thành phần | Mô tả |
|-----------|-------|
| **Quả cầu 3D** | Globe.gl + Three.js. Hiển thị thiên tai dưới dạng cột neon có vòng sóng |
| **Terminal** | Dòng lệnh kiểu cyberpunk để tương tác với hệ thống |
| **DEFCON Bar** | Thanh trạng thái cảnh báo toàn cầu (DEFCON 5 → 1) |
| **HUD Panels** | Proximity Alerts · Reactor Chart · Hazard Distribution · Tactical Ops |
| **AI Ticker** | Dải tin chạy ngang màn hình với cảnh báo thiên tai mới nhất |

**Màu sắc thiên tai:**
| Loại | Màu |
|------|-----|
| Động đất (EARTHQUAKE) | 🔵 Xanh neon (`#00f3ff`) |
| Cháy rừng (WILDFIRE) | 🟠 Cam (`#ff6600`) |
| Núi lửa (VOLCANO) | 🟣 Tím hồng (`#ff00cc`) |
| Bão (STORM) | 💜 Tím (`#bd00ff`) |
| Bức xạ hạt nhân (NUCLEAR PLANT) | 🟡 Toxic Yellow (`#ccff00`) |
| Dự báo AI (AI PREDICTION) | ⚪ Xanh/Vàng/Đỏ theo mức rủi ro |

### 7.2 Terminal Commands

| Lệnh | Chức năng |
|------|-----------|
| `scan` | Refresh dữ liệu thiên tai |
| `locate` | Xác định vị trí GPS của người dùng |
| `train` | Kích hoạt huấn luyện AI từ MongoDB |
| `predict` | Dự báo rủi ro tại vị trí hiện tại |
| `eval` / `metrics` | Hiển thị độ chính xác AI (MSE, MAE, Tolerance Accuracy %) |
| `scram` / `shutdown` | Dừng khẩn cấp lò phản ứng |
| `mute` | Tắt âm thanh |
| `vietnam` | Di chuyển camera đến Việt Nam |
| `global` | Reset camera về view toàn cầu |
| `help` | Hiển thị danh sách lệnh |

### 7.3 Nút Tactical Ops

| Nút | Chức năng |
|-----|-----------|
| `[ ] LOCATE ME (GPS)` | Lấy vị trí GPS thực tế |
| `[x] QUAKES/VOLCANO/STORMS/FIRES/OTHERS/NUKES` | Bộ lọc hiển thị loại thảm họa |
| `[ ] NEURAL AI` | Bật quét AI toàn cầu (20 hotspots) |
| `[ EXPORT CSV ]` | Xuất dữ liệu thiên tai hiện tại ra file CSV |
| `🔔 ALERTS: OFF` | Bật/tắt thông báo trình duyệt |
| `ACTIVATE REACTOR LINK` | Kết nối WebSocket với lò phản ứng |

### 7.4 Trang Analytics (`/dashboard`)

| Thành phần | Mô tả |
|-----------|-------|
| **KPI Cards** | Total Events · Max Magnitude · Snapshots 24H · Active Now |
| **Trend Chart** | Biểu đồ đường tổng sự kiện theo thời gian (6H/24H/3D/7D) |
| **Donut Chart** | Phân bổ loại thảm họa |
| **Magnitude Chart** | Biểu đồ magnitude tối đa theo thời gian |
| **Top Snapshots Table** | 20 snapshot có magnitude cao nhất |
| **AI Risk Assessment Panel** | Bảng xếp hạng 20 khu vực rủi ro với thanh progress bar |

---

# 8. CẤU HÌNH & BIẾN MÔI TRƯỜNG

File `.env` (xem `.env.example` để tham khảo):

```env
# Database
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/
DB_NAME=upt_guardian

# NASA API
NASA_API_KEY=DEMO_KEY          # Lấy tại api.nasa.gov

# Telegram Alerts (tuỳ chọn)
TELEGRAM_TOKEN=                # Token từ @BotFather
TELEGRAM_CHAT_ID=              # Chat ID nhận alert

# Security
ALLOWED_ORIGINS=https://your-app.onrender.com,http://localhost:8000
API_SECRET_KEY=your_super_secret_key_here

# Server
HOST=0.0.0.0
PORT=8000
```

---

## 9. BẢO MẬT

| Cơ chế | Chi tiết |
|--------|----------|
| **API Key Auth** | Header `X-API-Key` bắt buộc cho các endpoint nhạy cảm (train, forecast, scram, inject-event). Nếu `API_SECRET_KEY` không được set → Dev mode, bỏ qua auth |
| **Rate Limiting** | SlowAPI: 5 req/phút cho train, 10 req/phút cho forecast, 5 req/phút cho global-scan |
| **CORS** | Chỉ cho phép các origin được liệt kê trong `ALLOWED_ORIGINS` |
| **Input Validation** | Tất cả request body được validate bởi Pydantic schemas |

---

## 10. DATABASE — MongoDB Atlas

### Collection: `raw_logs`
Mỗi document là một **snapshot dữ liệu thiên tai** tại một thời điểm:

```json
{
  "timestamp": "2026-05-13T10:00:00Z",
  "total_events": 307,
  "max_magnitude": 6.2,
  "sensors_data": [
    {
      "type": "EARTHQUAKE",
      "place": "10km NW of Ferndale, CA",
      "lat": 40.6,
      "lon": -124.3,
      "energy_level": 0.47,
      "anomaly_score": 0.23,
      "raw_val": 4.2,
      "timestamp": 1747130000000
    }
  ]
}
```

---

## 11. CI/CD & DEPLOYMENT

### GitHub Actions (`.github/workflows/ci.yml`)
- Chạy tự động khi push lên nhánh `main`
- **Python 3.11** + cài dependencies từ `requirements.txt`
- Chạy toàn bộ test suite: `pytest tests/`
- **68 test cases** bao gồm:
  - `test_api_endpoints.py` — Kiểm tra tất cả HTTP endpoints
  - `test_earthquake_service.py` — Kiểm tra data fetching
  - `test_reactor_core.py` — Kiểm tra physics simulation
  - `test_upt_math.py` — Kiểm tra công thức toán học

### Render.com Deployment
- **Free Tier** (512MB RAM, cold start sau 15 phút idle)
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Environment Variables: Cấu hình trong phần **Environment** của Render dashboard

### Docker (Tuỳ chọn)
```bash
docker-compose up --build
```

---

## 12. DEPENDENCIES CHÍNH

```
fastapi==0.109.0          # Web framework
uvicorn[standard]==0.27.0 # ASGI server
pydantic==2.6.0           # Data validation
pydantic-settings==2.2.1  # Env config
pymongo                    # MongoDB driver
scikit-learn               # AI (HistGradientBoosting, MinMaxScaler, metrics)
numpy                      # Numerical computing
apscheduler==3.10.4        # Task scheduling
slowapi==0.1.9             # Rate limiting
fastapi-cache2             # In-memory caching
python-telegram-bot        # Telegram alerts
twilio                     # SMS alerts
httpx                      # Async HTTP client
pytest + pytest-asyncio    # Testing
```

---

## 13. ROADMAP & TÍNH NĂNG CÓ THỂ PHÁT TRIỂN

| Tính năng | Mô tả | Độ phức tạp |
|-----------|-------|-------------|
| Email Alerts (SendGrid) | Gửi alert qua email miễn phí | 🟢 Dễ |
| Export PDF Report | Xuất báo cáo AI scan ra PDF | 🟢 Dễ |
| Historical Playback | Thanh timeline để tua lại lịch sử thiên tai | 🟡 Trung bình |
| Crowdsourced Reports | Người dùng báo cáo thiên tai trực tiếp trên bản đồ | 🟡 Trung bình |
| IoT Sensor API | Nhận dữ liệu từ cảm biến Raspberry Pi/Arduino | 🔴 Nâng cao |
| Long-term AI Training | Train AI trên dữ liệu lịch sử hàng tháng/năm | 🔴 Nâng cao |

---

## 14. GHI CHÚ PHÁT TRIỂN

### Về Độ Chính Xác AI
- Với dữ liệu được thu thập theo chu kỳ ngắn (vài phút/lần), thiên tai ít thay đổi nhanh. Thay vì dùng classification accuracy, dự án sử dụng **Tolerance Accuracy** tính bằng `max(0, 1 - MAE) * 100` để đo lường tỷ lệ chênh lệch tuyệt đối so với biên độ rủi ro (0-1).
- Vấn đề **Data Leakage** đã được fix bằng cách chia dữ liệu theo dạng Chronological (train/test split) **trước khi** tiến hành fit biến đổi `MinMaxScaler`.
- Sau khi hệ thống chạy **1-3 tháng** và thu thập đủ dữ liệu lịch sử, model sẽ học được các quy luật dài hạn thực sự.
- **Forecast Horizon = 5** giúp tránh "học vẹt" bằng cách bắt AI dự đoán xa hơn vào tương lai.

### Về Local Energy Calculation
- Sử dụng công thức **Haversine** để tính khoảng cách địa lý chính xác trên mặt cầu
- Bán kính quét **800km** được chọn để bao phủ đủ sự kiện mà không quá rộng
- **log1p normalization** ngăn các khu vực như California (rất nhiều động đất nhỏ) bị bão hòa 100%

### Về Render Free Tier
- App sẽ "ngủ" (cold start) sau 15 phút không có request, mất ~30-60 giây để khởi động lại
- RAM tối đa 512MB — đây là lý do chọn HistGradientBoosting thay vì TensorFlow/LSTM
- Dữ liệu in-memory sẽ bị reset mỗi khi app khởi động lại

---

*Tài liệu được tạo ngày 2026-05-13. Cập nhật cùng với các thay đổi của dự án.*
