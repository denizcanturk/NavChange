import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# 1. Veriyi Yükle
df = pd.read_csv('DetailToAnalyse.csv')

# Sütun isimlerini temizle (Eğer hala gerekiyorsa)
df.columns = [col.strip().replace('"', '') for col in df.columns]

# 2. Veri Hazırlığı
# Veri 20Hz olduğu için her satır arası sabit 0.05 sn kabul ediyoruz 
# (Zaman damgaları 0 göründüğü için en sağlıklı yöntem budur)
fixed_dt = 0.05 

columns_to_analyze = [
    "VelocityX", "VelocityY", "VelocityZ", 
    "PlatformAzimuth", "RollAngle", "PitchAngle", 
    "PresentTrueHeading", "PresentMagneticHeading"
]

# Değişim Hızlarını Hesapla
rate_cols = []
for col in columns_to_analyze:
    if col in df.columns:
        rate_col_name = f"{col}_Rate"
        # Sayısal veriye zorla
        df[col] = pd.to_numeric(df[col], errors='coerce')
        # Değişim hızı = (Fark / 0.05)
        # Gürültüyü azaltmak için 5 örnekli hareketli ortalama (rolling mean) ekledik
        df[rate_col_name] = (df[col].diff() / fixed_dt).rolling(window=5, center=True).mean()
        rate_cols.append(rate_col_name)

# NaN değerleri temizle (başlangıçtaki boşluklar için)
df = df.fillna(0)

# 3. Grafik Kurulumu
fig, axes = plt.subplots(nrows=4, ncols=2, figsize=(16, 12))
axes = axes.flatten()
lines = []

for i, col in enumerate(rate_cols):
    line, = axes[i].plot([], [], label='Değişim Hızı', color='tab:red', lw=1.2)
    axes[i].set_title(f"{col}")
    axes[i].grid(True, alpha=0.3)
    lines.append(line)

# Animasyon Ayarları
WINDOW_SIZE = 100  # Ekranda görünecek nokta sayısı
STEP = 1          # Her adımda ilerleme miktarı

def init():
    for ax in axes:
        ax.set_xlim(0, WINDOW_SIZE)
    return lines

def update(frame):
    start = max(0, frame - WINDOW_SIZE)
    end = frame
    
    subset = df.iloc[start:end]
    
    if not subset.empty:
        for i, col in enumerate(rate_cols):
            y_data = subset[col].values
            x_data = np.arange(len(y_data))
            
            lines[i].set_data(x_data, y_data)
            
            # Eksen sınırlarını güvenli bir şekilde güncelle
            if len(y_data) > 0:
                y_min, y_max = np.min(y_data), np.max(y_data)
                
                # Değerler geçerli (sayı) ise sınırları ayarla
                if np.isfinite(y_min) and np.isfinite(y_max):
                    margin = (y_max - y_min) * 0.1 + 0.01
                    axes[i].set_ylim(y_min - margin, y_max + margin)
                
                axes[i].set_xlim(0, WINDOW_SIZE)
                
    return lines

# interval=50 (saniyede 20 kare tazeleme hızı simülasyonu)
ani = FuncAnimation(fig, update, frames=range(STEP, len(df), STEP), 
                    init_func=init, blit=False, interval=50, repeat=False)

plt.tight_layout()
plt.show()