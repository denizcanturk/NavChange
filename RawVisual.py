import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# 1. Veriyi Yükle
df = pd.read_csv('DetailToAnalyse.csv')
df.columns = [col.strip().replace('"', '') for col in df.columns]

# Analiz edilecek ham sütunlar (Hız hesaplaması yapmıyoruz)
columns_to_show = [
    "VelocityX", "VelocityY", "VelocityZ", 
    "PlatformAzimuth", "RollAngle", "PitchAngle", 
    "PresentTrueHeading", "PresentMagneticHeading"
]

# Sayısal veriye çevir ve hataları temizle
for col in columns_to_show:
    df[col] = pd.to_numeric(df[col], errors='coerce')
df = df.fillna(method='ffill').fillna(0) # Eksik verileri bir öncekiyle doldur

# 2. Grafik Kurulumu
fig, axes = plt.subplots(nrows=4, ncols=2, figsize=(16, 12))
axes = axes.flatten()
lines = []

for i, col in enumerate(columns_to_show):
    # Değişim hızı değil, ham değerleri çiziyoruz
    line, = axes[i].plot([], [], label='Ham Değer', color='tab:blue', lw=1.5)
    axes[i].set_title(f"{col}")
    axes[i].grid(True, alpha=0.3)
    lines.append(line)

# Animasyon Ayarları
WINDOW_SIZE = 150  # Ekranda kaç veri noktası görünsün?
STEP = 10         # Her karede kaç satır ilerlesin? (Saniyede 2 kayıt hissi için)

def init():
    for ax in axes:
        ax.set_xlim(0, WINDOW_SIZE)
    return lines

def update(frame):
    start = max(0, frame - WINDOW_SIZE)
    end = frame
    
    subset = df.iloc[start:end]
    
    if not subset.empty:
        for i, col in enumerate(columns_to_show):
            y_data = subset[col].values
            x_data = np.arange(len(y_data))
            
            lines[i].set_data(x_data, y_data)
            
            # Dinamik eksen ölçeklendirme
            if len(y_data) > 0:
                y_min, y_max = np.min(y_data), np.max(y_data)
                # Değerler sabitse (min==max) grafik bozulmasın diye küçük bir pay ekle
                margin = (y_max - y_min) * 0.1 if y_max != y_min else 0.1
                axes[i].set_ylim(y_min - margin, y_max + margin)
                axes[i].set_xlim(0, WINDOW_SIZE)
                
    return lines

# interval=500 yaparak (0.5 saniye) saniyede 2 yeni kayıt gösterimini simüle edebiliriz
ani = FuncAnimation(fig, update, frames=range(STEP, len(df), STEP), 
                    init_func=init, blit=False, interval=100, repeat=False)

plt.tight_layout()
plt.show()