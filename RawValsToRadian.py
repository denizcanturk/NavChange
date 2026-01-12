import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# 1. VERİ YÜKLEME VE ÖZEL FİLTRELEME
#df = pd.read_csv('DetailToAnalyse.csv')
#df.columns = [col.strip().replace('"', '') for col in df.columns]
df = pd.read_csv('DnzRec.csv')
columns_to_show = [
    "VelocityX", "VelocityY", "VelocityZ", 
    "PlatformAzimuth", "RollAngle", "PitchAngle", 
    "PresentTrueHeading", "PresentMagneticHeading"
]

angle_cols = ["PlatformAzimuth", "RollAngle", "PitchAngle", "PresentTrueHeading", "PresentMagneticHeading"]

for col in columns_to_show:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Radyan -> Derece
        """
        if col in angle_cols:
            df[col] = df[col] * (180.0 / np.pi)
        """
        # DİKKAT: PresentMagneticHeading için daha güçlü bir filtre uyguluyoruz
        if col == "PresentMagneticHeading":
            # 15 örnekli hareketli ortalama (Daha ağır bir yumuşatma)
            df[col] = df[col].rolling(window=15, min_periods=1, center=True).mean()
        else:
            # Diğerleri için hafif yumuşatma yeterli
            df[col] = df[col].rolling(window=5, min_periods=1, center=True).mean()

df = df.fillna(method='ffill').fillna(0)

# 2. GRAFİK KURULUMU
fig, axes = plt.subplots(nrows=4, ncols=2, figsize=(16, 12))
fig.suptitle("Navigasyon Verileri - Manyetik Rota Filtreli", fontsize=16)
axes = axes.flatten()
lines = []

for i, col in enumerate(columns_to_show):
    color = 'tab:red' if col == "PresentMagneticHeading" else '#1f77b4'
    line, = axes[i].plot([], [], label=col, color=color, lw=2)
    axes[i].set_title(f"{col}")
    axes[i].grid(True, alpha=0.3)
    lines.append(line)

# 3. ANİMASYON AYARLARI
WINDOW_SIZE = 200
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
            
            y_min, y_max = np.min(y_data), np.max(y_data)
            diff = y_max - y_min
            
            # Manyetik Heading için Y eksenini biraz daha geniş tut (salınımı görsel olarak bastırır)
            if col == "PresentMagneticHeading":
                # Eğer değişim çok küçükse ekseni daraltma, en az 5 derecelik bir pencere bırak
                margin = max(diff * 0.2, 2.5) 
                axes[i].set_ylim(y_min - margin, y_max + margin)
            else:
                margin = diff * 0.1 if diff > 0.1 else 1.0
                axes[i].set_ylim(y_min - margin, y_max + margin)
                
            axes[i].set_xlim(0, WINDOW_SIZE)
                
    return lines

ani = FuncAnimation(fig, update, frames=range(STEP, len(df), STEP), 
                    interval=300, blit=False, repeat=False)

plt.tight_layout(rect=[0, 0.03, 1, 0.95])
plt.show()