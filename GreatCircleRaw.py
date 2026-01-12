import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# 1. VERİ YÜKLEME
df = pd.read_csv('DetailToAnalyse.csv')
df.columns = [col.strip().replace('"', '') for col in df.columns]

# Analiz edilecek genişletilmiş liste (10 Sütun)
columns_to_show = [
    "VelocityX", "VelocityY", "VelocityZ", 
    "PlatformAzimuth", "RollAngle", "PitchAngle", 
    "PresentTrueHeading", "PresentMagneticHeading",
    "GreatCircleSteeringError", "ComputedCourseDeviation"
]

# Açısal/Hata sütunları (Radyan şüphesi olanlar)
angle_cols = [
    "PlatformAzimuth", "RollAngle", "PitchAngle", 
    "PresentTrueHeading", "PresentMagneticHeading",
    "GreatCircleSteeringError", "ComputedCourseDeviation"
]

# Birim Dönüşüm Kontrolü (İstediğinde buradan kapatabilirsin)
USE_DEGREE_CONVERSION = True 

for col in columns_to_show:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        
        if USE_DEGREE_CONVERSION and col in angle_cols:
            df[col] = df[col] * (180.0 / np.pi)
        
        # Gürültü filtreleme
        df[col] = df[col].rolling(window=10, min_periods=1, center=True).mean()

df = df.fillna(method='ffill').fillna(0)

# 2. GRAFİK KURULUMU (5 satır, 2 sütun)
fig, axes = plt.subplots(nrows=5, ncols=2, figsize=(16, 18))
fig.suptitle("Kapsamlı Navigasyon ve Hata Analiz Paneli", fontsize=16)
axes = axes.flatten()
lines = []

for i, col in enumerate(columns_to_show):
    color = 'tab:orange' if "Error" in col or "Deviation" in col else '#1f77b4'
    line, = axes[i].plot([], [], label=col, color=color, lw=2)
    axes[i].set_title(f"{col}")
    axes[i].grid(True, alpha=0.3)
    unit = "deg" if col in angle_cols else "unit"
    axes[i].set_ylabel(unit)
    lines.append(line)

# 3. ANİMASYON AYARLARI
WINDOW_SIZE = 150 
STEP = 10          

def update(frame):
    start = max(0, frame - WINDOW_SIZE)
    end = frame
    subset = df.iloc[start:end]
    
    if not subset.empty:
        for i, col in enumerate(columns_to_show):
            y_data = subset[col].values
            x_data = np.arange(len(y_data))
            lines[i].set_data(x_data, y_data)
            
            # Dinamik Ölçekleme
            y_min, y_max = np.min(y_data), np.max(y_data)
            diff = y_max - y_min
            
            # Görsel netlik için minimum 2 derecelik/birimlik bir pencere bırak
            margin = max(diff * 0.15, 1.0)
            axes[i].set_ylim(y_min - margin, y_max + margin)
            axes[i].set_xlim(0, WINDOW_SIZE)
                
    return lines

ani = FuncAnimation(fig, update, frames=range(STEP, len(df), STEP), 
                    interval=200, blit=False, repeat=False)

plt.tight_layout(rect=[0, 0.03, 1, 0.95])
plt.show()