### ☢️ UPT Disaster AI - Guardian System v28.1UPT Disaster AI là một hệ thống giám sát thảm họa toàn cầu thời gian thực, kết hợp giữa phân tích dữ liệu địa chấn, mô phỏng ổn định lò phản ứng lượng tử và dự báo rủi ro bằng trí tuệ nhân tạo. Dự án được xây dựng trên nền tảng phong cách Cyberpunk, mang lại trải nghiệm như một trung tâm điều hành phòng thủ thực thụ.

### 🌟 Tính năng cốt lõi📡 Giám sát đa nguồn thời gian thựcHệ thống cảm biến toàn cầu: Tự động quét dữ liệu động đất từ USGS, các sự kiện thiên tai (núi lửa, cháy rừng, bão) từ NASA EONET và bão mặt trời từ NASA DONKI mỗi 60 giây.Snapshot Database: Lưu trữ mọi biến động vào MongoDB Atlas để phục vụ việc huấn luyện AI và phân tích lịch sử.

### ⚛️ Mô phỏng Lò phản ứng (Quantum Reactor Core)Cơ chế liên kết thực tế: Các thảm họa lớn (động đất > 6.0) sẽ gây "sốc" vật lý trực tiếp lên lò phản ứng, làm biến động nhiệt độ lõi, thông lượng neutron và hệ số ổn định $K_{eff}$.Hệ thống SCRAM: Quy trình dập lò khẩn cấp tự động hoặc thủ công khi nhiệt độ vượt ngưỡng an toàn (2000K).

### 🧠 Trí tuệ nhân tạo (Guardian AI)Deep Learning (LSTM): Sử dụng mạng nơ-ron hồi quy (Long Short-Term Memory) để dự báo cường độ thảm họa trong tương lai dựa trên chuỗi dữ liệu thời gian.Neural Prediction: Dự báo mức độ rủi ro tại bất kỳ tọa độ nào trên bản đồ dựa trên kiến thức về các vành đai lửa địa chất.

### 🎮 Giao diện & Điều khiển3D Visualizer: Quả địa cầu tương tác 3D hiển thị vị trí thảm họa, nhà máy hạt nhân và vùng dự báo rủi ro.Voice Command: Hỗ trợ ra lệnh bằng giọng nói: Scan, Locate me, Status, Matrix....Tactical HUD: Bảng điều khiển cung cấp chỉ số DEFCON và biểu đồ phân bổ hiểm họa trực quan.🛠 Tech StackBackend: Python 3.11, FastAPI (Async Framework), WebSockets (Real-time stream).Frontend: HTML5/CSS3 (Cyberpunk design), Three.js, Globe.gl, Chart.js.AI/ML: TensorFlow (LSTM), Scikit-Learn (Random Forest, Scaler), NumPy.Database: MongoDB Atlas.DevOps: Docker, Shell Script.

### 🚀 Khởi động nhanh1. Cấu hình môi trườngTạo file .env tại thư mục gốc:Đoạn mãMONGO_URI=your_mongodb_uri

DB_NAME=upt_guardian
NASA_API_KEY=your_nasa_key
TELEGRAM_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
PORT=8000

### 2. Chạy với DockerBashdocker build -t upt-disaster-ai .

docker run -p 8000:8000 --env-file .env upt-disaster-ai

### 3. Cài đặt thủ côngBashpip install -r requirements.txt

python -m app.main
Hệ thống sẽ khả dụng tại: http://localhost:8000.📜 Lệnh điều khiển hệ thống (Terminal)LệnhChức năngscanQuét dữ liệu thủ công từ vệ tinh.locateXác định vị trí GPS của người vận hành.trainÉp buộc hệ thống AI học lại từ dữ liệu cache.scramDập lò phản ứng khẩn cấp.defcon [1-5]Thay đổi mức độ sẵn sàng chiến đấu.mute / unmuteĐiều khiển hệ thống âm thanh.

### 📸. Screenshot

![alt text](image-1.png)
