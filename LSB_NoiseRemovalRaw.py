import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# 1. Veriyi Yükle
df = pd.read_csv('DetailToAnalyse.csv')
df.columns = [col.strip().replace('"', '') for col in df.columns]

columns_to_show = [
    "VelocityX", "VelocityY", "VelocityZ", 
    "PlatformAzimuth", "RollAngle", "PitchAngle", 
    "PresentTrueHeading", "PresentMagneticHeading"
]

# Sayısal veriye çevir ve hafif bir yumuşatma (Rolling Mean) uygula
# 5 örnekli bir pencere, 20Hz veride sadece 0.25 saniyelik bir gecikme yaratır 
# ama o "jitter" denilen titremeyi yok eder.
for col in columns_to_show:
    df[col] = pd.to_numeric(df[col], errors='coerce')
    df[col] = df[col].rolling(window=10, min_periods=1, center=True).mean()

# 2. Grafik Kurulumu
fig, axes = plt.subplots(nrows=4, ncols=2, figsize=(16, 12))
axes = axes.flatten()
lines = []

for i, col in enumerate(columns_to_show):
    line, = axes[i].plot([], [], label='Filtrelenmiş Veri', color='#1f77b4', lw=2)
    axes[i].set_title(f"{col}")
    axes[i].grid(True, alpha=0.3)
    lines.append(line)

WINDOW_SIZE = 150 
STEP = 2

def update(frame):
    start = max(0, frame - WINDOW_SIZE)
    end = frame
    subset = df.iloc[start:end]
    
    if not subset.empty:
        for i, col in enumerate(columns_to_show):
            y_data = subset[col].values
            x_data = np.arange(len(y_data))
            lines[i].set_data(x_data, y_data)
            
            # --- Dinamik Ölçekleme Mantığını Değiştirdik ---
            y_min, y_max = np.min(y_data), np.max(y_data)
            diff = y_max - y_min
            
            # Eğer değişim çok çok küçükse (titreme seviyesindeyse), 
            # ekseni o değere zoom yapmaya zorlamıyoruz.

            if diff < 0.00001: # 0.1 birimden az değişimleri 'sabit' kabul et
                center = (y_max + y_min) / 2
                axes[i].set_ylim(center - 0.5, center + 0.5)
            else:
                axes[i].set_ylim(y_min - diff*0.2, y_max + diff*0.2)
                
            axes[i].set_xlim(0, WINDOW_SIZE)

    return lines

ani = FuncAnimation(fig, update, frames=range(STEP, len(df), STEP), 
                    interval=100, blit=False, repeat=False)

plt.tight_layout()
plt.show()