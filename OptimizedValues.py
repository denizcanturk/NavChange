import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# ---------------------------------------------------------
# 1. VERİ YÜKLEME VE ÖN İŞLEME
# ---------------------------------------------------------
#df = pd.read_csv('DetailToAnalyse.csv')
df = pd.read_csv('DnzRec.csv')
# Sütun isimlerindeki tırnak ve boşlukları temizle
df.columns = [col.strip().replace('"', '') for col in df.columns]

# Analiz edilecek tüm sütunlar
all_cols = [
    "VelocityX", "VelocityY", "VelocityZ", 
    "PlatformAzimuth", "RollAngle", "PitchAngle", 
    "PresentTrueHeading", "PresentMagneticHeading",
    "GreatCircleSteeringError", "ComputedCourseDeviation",
    "DistanceToSteerpoint"
]

# Sayısal formata çevir
for col in all_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

# ---------------------------------------------------------
# 2. BİRİM DÖNÜŞÜMLERİ
# ---------------------------------------------------------

# A) AÇILAR: Radyan -> Derece
angle_cols = [
    "PlatformAzimuth", "RollAngle", "PitchAngle", 
    "PresentTrueHeading", "PresentMagneticHeading",
    "GreatCircleSteeringError", "ComputedCourseDeviation"
]

for col in angle_cols:
    if col in df.columns:
        # Radyan'dan Dereceye çevir
        df[col] = df[col] * (180.0 / np.pi)
        # Gürültü filtreleme (Smooth) - Hafif titremeleri alır
        df[col] = df[col].rolling(window=10, min_periods=1, center=True).mean()

# B) HIZLAR: Feet/Saniye -> Knot (1 ft/s = 0.592484 knots)
velocity_cols = ["VelocityX", "VelocityY", "VelocityZ"]
KNOTS_CONVERSION = 0.592484

for col in velocity_cols:
    if col in df.columns:
        df[col] = df[col] * KNOTS_CONVERSION

# Yer Hızı (Ground Speed) Hesapla (Knot cinsinden)
df['GroundSpeed_Knots'] = np.sqrt(df['VelocityX']**2 + df['VelocityY']**2)

# Eksik verileri doldur
df = df.fillna(method='ffill').fillna(0)

# ---------------------------------------------------------
# 3. GRAFİK KURULUMU (5 Satır x 2 Sütun)
# ---------------------------------------------------------
# Sabit Delta grafikleri çıkarıldı, sadece kritik veriler kaldı.
plot_config = [
    {"col": "GroundSpeed_Knots", "color": "tab:green", "title": "Ground Speed (Knots)"},
    {"col": "DistanceToSteerpoint", "color": "tab:purple", "title": "Distance To Steerpoint (NM)"},
    
    {"col": "RollAngle", "color": "#1f77b4", "title": "Roll Angle (Deg)"},
    {"col": "PitchAngle", "color": "#1f77b4", "title": "Pitch Angle (Deg)"},
    
    {"col": "PresentTrueHeading", "color": "#1f77b4", "title": "True Heading (Deg)"},
    {"col": "PlatformAzimuth", "color": "tab:gray", "title": "Platform Azimuth (Deg)"},
    
    {"col": "GreatCircleSteeringError", "color": "tab:orange", "title": "Steering Error (Deg)"},
    {"col": "ComputedCourseDeviation", "color": "tab:orange", "title": "Course Deviation (Deg)"},
    
    {"col": "VelocityZ", "color": "tab:cyan", "title": "Vertical Velocity (Knots)"},
    {"col": "VelocityX", "color": "tab:blue", "title": "Velocity X (Knots)"} 
]

fig, axes = plt.subplots(nrows=5, ncols=2, figsize=(16, 18))
fig.suptitle(f"Uçuş Verileri Analiz Paneli (Hız: Knot, Açı: Derece)", fontsize=16, fontweight='bold')
axes = axes.flatten()
lines = []

for i, config in enumerate(plot_config):
    col_name = config["col"]
    line, = axes[i].plot([], [], label=col_name, color=config["color"], lw=2)
    axes[i].set_title(config["title"])
    axes[i].grid(True, alpha=0.3, linestyle='--')
    lines.append(line)

# ---------------------------------------------------------
# 4. ANİMASYON DÖNGÜSÜ
# ---------------------------------------------------------
WINDOW_SIZE = 200  # Ekranda görünen veri noktası sayısı
STEP = 1200           # Daha akıcı bir görüntü için adım sayısı düşürüldü

def init():
    for ax in axes:
        ax.set_xlim(0, WINDOW_SIZE)
    return lines

def update(frame):
    start = max(0, frame - WINDOW_SIZE)
    end = frame
    subset = df.iloc[start:end]
    
    if not subset.empty:
        for i, config in enumerate(plot_config):
            col_name = config["col"]
            y_data = subset[col_name].values
            x_data = np.arange(len(y_data))
            
            lines[i].set_data(x_data, y_data)
            
            # Dinamik Eksen Ölçekleme
            if len(y_data) > 0:
                y_min, y_max = np.min(y_data), np.max(y_data)
                diff = y_max - y_min
                
                # Eksen çok titremesin diye minimum marj (0.5 birim)
                margin = max(diff * 0.2, 0.5) 
                
                axes[i].set_ylim(y_min - margin, y_max + margin)
                axes[i].set_xlim(0, WINDOW_SIZE)

    if "TimeMarker" in df.columns and not subset.empty:
        # subset'in son satırı o anki "şimdiki zaman"dır
        current_time_val = subset["TimeMarker"].iloc[-1]
        print(f"Zaman: {current_time_val}")            
    return lines

# interval=100ms -> Saniyede 10 kare (Veri akışı daha pürüzsüz)
ani = FuncAnimation(fig, update, frames=range(STEP, len(df), STEP), 
                    init_func=init, blit=False, interval=10, repeat=False)

plt.tight_layout(rect=[0, 0.03, 1, 0.97])
plt.show()