# %% [markdown]
# # 🔬 Phòng Thí nghiệm Dữ liệu (UPT Guardian Data Lab)
# Chào mừng bạn đến với môi trường Jupyter Notebook.
# Đây là nơi chúng ta sẽ load dữ liệu từ file CSV vừa trích xuất và thực hiện phân tích thăm dò (EDA).
# 
# **HƯỚNG DẪN:** Trong VS Code, bạn có thể click vào nút `Run Cell` xuất hiện phía trên các ô lệnh `# %%` để chạy code tương tác.

# %%
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Cấu hình phong cách biểu đồ (Dark mode cho hợp vibe Cyberpunk)
plt.style.use('dark_background')
plt.rcParams['figure.figsize'] = (10, 6)

# Khởi tạo đường dẫn dữ liệu
data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dataset', 'sensors.csv')

df = pd.DataFrame()
if os.path.exists(data_path):
    try:
        df = pd.read_csv(data_path)
        # Chuyển đổi timestamp sang dạng Datetime
        df['log_timestamp'] = pd.to_datetime(df['log_timestamp'])
        print(f"✅ Đã tải thành công {len(df)} bản ghi dữ liệu thiên tai!")
        # Hiển thị 5 dòng đầu tiên (dùng print để tương thích cả chạy script thường và Jupyter)
        print(df.head())
    except Exception as e:
        print(f"❌ Lỗi khi tải file CSV: {e}")
else:
    print(f"❌ Không tìm thấy file {data_path}! Bạn vui lòng chạy script export_dataset.py trước nhé.")

# %% [markdown]
# ## 1. Thống kê Phân bổ các loại Thiên tai (Hazard Distribution)
# Trực quan hóa tỷ lệ các loại thiên tai mà hệ thống đã ghi nhận được.

# %%
if not df.empty:
    plt.figure(figsize=(8, 8))
    event_counts = df['event_type'].value_counts()
    
    # Vẽ biểu đồ tròn
    plt.pie(event_counts, labels=event_counts.index, autopct='%1.1f%%', 
            colors=sns.color_palette('pastel', len(event_counts)), 
            startangle=140, explode=[0.05]*len(event_counts))
    plt.title("Tỷ lệ phân bổ các loại Thảm họa Toàn cầu", fontsize=14, fontweight='bold', color='cyan')
    plt.show()

# %% [markdown]
# ## 2. Phân phối Cường độ Động đất (Earthquake Magnitude Histogram)
# Xem xét đồ thị phân phối để biết cường độ động đất trung bình thường tập trung ở mức nào.

# %%
if not df.empty:
    quakes = df[df['event_type'] == 'EARTHQUAKE'].copy()
    # Loại bỏ các trận động đất không có giá trị (raw_val = 0 hoặc NaN)
    quakes = quakes[quakes['raw_val'] > 0]
    
    if not quakes.empty:
        plt.figure(figsize=(12, 6))
        sns.histplot(quakes['raw_val'], bins=30, kde=True, color='cyan')
        plt.title('Đồ thị Phân phối Độ lớn Động Đất (Richter)', fontsize=14, color='cyan')
        plt.xlabel('Cường độ (Độ Richter)', fontsize=12)
        plt.ylabel('Tần suất (Số vụ)', fontsize=12)
        plt.grid(axis='y', alpha=0.3)
        plt.show()
    else:
        print("Cảnh báo: Không có dữ liệu Động đất hợp lệ để phân tích.")

# %% [markdown]
# ## 3. Định hướng nghiên cứu tiếp theo: Kiểm định Chuỗi thời gian (Time-series)
# Tại cell dưới đây, bạn có thể tự mình thực hành viết code phân tích xem:
# **Số vụ động đất có tăng vọt trong vòng 48 giờ sau khi xảy ra Bão mặt trời (Solar Flares) cường độ lớn hay không?**
# 
# *Gợi ý: Dùng `df.groupby()` kết hợp thời gian (log_timestamp) để phân tích.*

# %%
# Code phân tích tương quan:
if not df.empty and 'SOLAR_FLARE' in df['event_type'].values:
    # 1. Trích xuất phần Ngày (Date) từ log_timestamp
    df['date'] = df['log_timestamp'].dt.date
    
    # 2. Gom nhóm số lượng sự kiện theo Ngày và Loại thảm họa
    daily_events = df.groupby(['date', 'event_type']).size().unstack(fill_value=0)
    
    if 'EARTHQUAKE' in daily_events.columns and 'SOLAR_FLARE' in daily_events.columns:
        # 3. Vẽ biểu đồ Hai Trục Tung (Dual Y-axis)
        fig, ax1 = plt.subplots(figsize=(14, 6))
        
        color1 = 'cyan'
        ax1.set_xlabel('Ngày (Date)', fontsize=12)
        ax1.set_ylabel('Số vụ Động đất', color=color1, fontweight='bold', fontsize=12)
        ax1.plot(daily_events.index, daily_events['EARTHQUAKE'], color=color1, marker='o', linewidth=2, label='Động đất')
        ax1.tick_params(axis='y', labelcolor=color1)
        ax1.grid(alpha=0.2)
        
        ax2 = ax1.twinx()  # Khởi tạo trục Y thứ hai
        color2 = 'orange'
        ax2.set_ylabel('Số vụ Bão Mặt Trời', color=color2, fontweight='bold', fontsize=12)
        ax2.plot(daily_events.index, daily_events['SOLAR_FLARE'], color=color2, marker='x', linestyle='--', linewidth=2, label='Bão Mặt Trời')
        ax2.tick_params(axis='y', labelcolor=color2)
        
        plt.title('Biểu đồ Chuỗi thời gian: Tần suất Động Đất vs Bão Mặt Trời', fontsize=16, color='white', pad=20)
        fig.tight_layout()
        plt.show()
        
        # 4. Tính toán hệ số tương quan (Pearson Correlation)
        correlation = daily_events['EARTHQUAKE'].corr(daily_events['SOLAR_FLARE'])
        print(f"\n⚡ Hệ số tương quan (Pearson Correlation): {correlation:.3f}")
        
        if correlation > 0.5:
            print("=> KẾT LUẬN: Tương quan thuận MẠNH! Có dấu hiệu Bão mặt trời bùng nổ đi kèm với sự gia tăng động đất.")
        elif correlation > 0:
            print("=> KẾT LUẬN: Tương quan thuận NHẸ. Có sự đồng biến nhưng chưa đủ mạnh, cần thu thập thêm dữ liệu dài hạn (vài tháng) để kết luận.")
        elif correlation < 0:
            print("=> KẾT LUẬN: Tương quan NGHỊCH. Khi Bão mặt trời tăng thì động đất lại giảm.")
        else:
            print("=> KẾT LUẬN: Không có sự tương quan (Độc lập thống kê).")
    else:
        print("Không đủ dữ liệu của Động đất và Bão mặt trời để so sánh.")
else:
    print("Dữ liệu không chứa Bão Mặt Trời (SOLAR_FLARE) để làm phân tích.")

# %% [markdown]
# ## 4. Trí tuệ Nhân tạo Phân cụm Địa lý (Geospatial Clustering - DBSCAN)
# Dùng thuật toán Học máy Không giám sát (Unsupervised ML) để tự động dò tìm
# các dải đứt gãy địa chất (Vành đai Lửa) dựa trên tọa độ động đất.

# %%
from sklearn.cluster import DBSCAN
import numpy as np

if not df.empty:
    # Lấy các trận động đất có tọa độ hợp lệ và độ lớn > 1.5 để lọc nhiễu nhẹ
    quakes_ai = df[(df['event_type'] == 'EARTHQUAKE') & (df['raw_val'] > 1.5) & (df['lat'].notna()) & (df['lng'].notna())].copy()
    
    if len(quakes_ai) > 100:
        print(f"🤖 Đang khởi động AI DBSCAN phân tích {len(quakes_ai)} chấn tâm...")
        
        # Tọa độ X=Kinh độ (lng), Y=Vĩ độ (lat)
        coords = quakes_ai[['lng', 'lat']].values
        
        # Cấu hình AI: 
        # eps=3.5 (Khoảng cách tìm hàng xóm ~350km)
        # min_samples=15 (Phải có ít nhất 15 trận tập trung mới gọi là 1 'Cụm')
        dbscan = DBSCAN(eps=3.5, min_samples=15)
        quakes_ai['cluster'] = dbscan.fit_predict(coords)
        
        # Đếm số lượng cụm (trừ nhóm -1 là nhiễu)
        num_clusters = len(set(quakes_ai['cluster'])) - (1 if -1 in quakes_ai['cluster'].values else 0)
        print(f"✅ AI đã dò tìm thành công {num_clusters} dải đứt gãy địa chất chính trên toàn cầu!")
        
        # ---- Vẽ bản đồ Scatter ----
        plt.figure(figsize=(16, 8))
        
        # 1. Vẽ các trận động đất mồ côi (Noise), cluster = -1
        noise = quakes_ai[quakes_ai['cluster'] == -1]
        plt.scatter(noise['lng'], noise['lat'], c='#333333', s=10, alpha=0.5, label='Nhiễu (Rời rạc)')
        
        # 2. Vẽ các cụm (Clusters)
        clusters = quakes_ai[quakes_ai['cluster'] != -1]
        plt.scatter(clusters['lng'], clusters['lat'], c=clusters['cluster'], cmap='gist_rainbow', s=40, alpha=0.9, edgecolors='black', linewidth=0.2)
        
        # Cấu hình hiển thị
        plt.title(f'Bản đồ Vành đai Lửa do AI (DBSCAN) phát hiện: {num_clusters} Cụm Đứt Gãy', fontsize=18, color='cyan', pad=20)
        plt.xlabel('Kinh độ (Longitude)', fontsize=12)
        plt.ylabel('Vĩ độ (Latitude)', fontsize=12)
        plt.grid(alpha=0.1)
        plt.xlim(-180, 180)
        plt.ylim(-90, 90)
        plt.legend()
        plt.show()
        
        # In ra các tọa độ dị thường (Xa vành đai lửa, nằm sâu trong lục địa hoặc giữa đại dương)
        print("\n🔍 Phân tích chuyên sâu: Các Cụm Động đất dị thường (Bất thường địa lý)")
        res = quakes_ai[quakes_ai['cluster'] != -1].groupby('cluster')[['lat', 'lng']].mean()
        
        # Lọc cụm ở Texas/Oklahoma (Fracking)
        texas = res[(res['lng'] > -110) & (res['lng'] < -90) & (res['lat'] > 25) & (res['lat'] < 45)]
        if not texas.empty:
            print(" ⚠️ Phát hiện Động đất do con người (Fracking) tại Trung tâm nước Mỹ (Texas/Oklahoma):")
            for idx, row in texas.iterrows():
                print(f"    - Cụm {idx}: Vĩ độ {row['lat']:.2f}, Kinh độ {row['lng']:.2f}")
                
        # Lọc cụm ở Hawaii (Hotspot)
        hawaii = res[(res['lng'] > -160) & (res['lng'] < -150) & (res['lat'] > 18) & (res['lat'] < 23)]
        if not hawaii.empty:
            print(" 🌋 Phát hiện Điểm nóng Núi lửa (Hotspot) tại giữa Thái Bình Dương (Hawaii):")
            for idx, row in hawaii.iterrows():
                print(f"    - Cụm {idx}: Vĩ độ {row['lat']:.2f}, Kinh độ {row['lng']:.2f}")
                
    else:
        print("Không đủ dữ liệu tọa độ động đất (>1.5 Richter) để chạy AI.")
