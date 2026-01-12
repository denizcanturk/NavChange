import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# 1. VERİ YÜKLEME VE ÖN İŞLEME
df = pd.read_csv('DetailToAnalyse.csv')
df.columns = [col.strip().replace('"', '') for col in df.columns]

# Analiz edilecek ana sütunlar
core_cols = [
    "VelocityX", "VelocityY", "VelocityZ", 
    "PlatformAzimuth", "RollAngle", "PitchAngle", 
    "PresentTrueHeading", "PresentMagneticHeading",
    "GreatCircleSteeringError", "ComputedCourseDeviation"
]

# Açısal dönüşüm (Birim tespiti için burayı true/false yaparak test edebilirsin)
USE_DEGREE = True
angle_cols = ["PlatformAzimuth", "RollAngle", "PitchAngle", "PresentTrueHeading", 
              "PresentMagneticHeading", "GreatCircleSteeringError", "ComputedCourseDeviation"]

for col in core_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        if USE_DEGREE and col in angle_cols:
            df[col] = df[col] * (180.0 / np.pi)
        # Yumuşatma filtresi
        df[col] = df[col].rolling(window=10, min_periods=1, center=True).mean()

# --- FARK (DELTA) HESAPLAMALARI ---
# Bu kısımlar uyumsuzluğun nedenini açıklayacak
df['Diff_Azimuth_True'] = df['PlatformAzimuth'] - df['PresentTrueHeading']
df['Diff_True_Mag'] = df['PresentTrueHeading'] - df['PresentMagneticHeading']

# Grafik listesine farkları da ekleyelim
plot_cols = core_cols + ['Diff_Azimuth_True', 'Diff_True_Mag']

df = df.fillna(method='ffill').fillna(0)

# 2. GRAFİK KURULUMU (6 satır, 2 sütun)
fig, axes = plt.subplots(nrows=6, ncols=2, figsize=(16, 22))
fig.suptitle("Navigasyon Sistemi Uyum ve Hata Analizi", fontsize=16, fontweight='bold')
axes = axes.flatten()
lines = []

for i, col in enumerate(plot_cols):
    # Renklendirme mantığı
    if 'Diff' in col:
        color = 'tab:green' # Karşılaştırma grafikleri yeşil
    elif 'Error' in col or 'Deviation' in col:
        color = 'tab:orange' # Hata grafikleri turuncu
    else:
        color = '#1f77b4' # Standart veriler mavi
        
    line, = axes[i].plot([], [], label=col, color=color, lw=2)
    axes[i].set_title(f"{col}")
    axes[i].grid(True, alpha=0.3)
    lines.append(line)

# 3. ANİMASYON FONKSİYONU
WINDOW_SIZE = 200 
STEP = 10          

def update(frame):
    start = max(0, frame - WINDOW_SIZE)
    end = frame
    subset = df.iloc[start:end]
    
    if not subset.empty:
        for i, col in enumerate(plot_cols):
            y_data = subset[col].values
            x_data = np.arange(len(y_data))
            lines[i].set_data(x_data, y_data)
            
            # Dinamik Ölçekleme
            y_min, y_max = np.min(y_data), np.max(y_data)
            diff = y_max - y_min
            
            # Değişim çok azsa ekseni kilitleme, en az 2 birimlik fark göster
            margin = max(diff * 0.15, 1.0)
            axes[i].set_ylim(y_min - margin, y_max + margin)
            axes[i].set_xlim(0, WINDOW_SIZE)
                
    return lines

ani = FuncAnimation(fig, update, frames=range(STEP, len(df), STEP), 
                    interval=250, blit=False, repeat=False)

plt.tight_layout(rect=[0, 0.03, 1, 0.97])
plt.show()