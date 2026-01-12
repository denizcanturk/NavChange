import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# 1. VERİ YÜKLEME VE HESAPLAMA
df = pd.read_csv('DetailToAnalyse.csv')
df.columns = [col.strip().replace('"', '') for col in df.columns]

# Tüm sütunları sayısal yap
for col in df.columns:
    df[col] = pd.to_numeric(df[col], errors='coerce')

# --- BİRİM TESTİ HESAPLAMASI ---
# Toplam Yer Hızı (Ground Speed) = sqrt(Vx^2 + Vy^2)
df['GroundSpeed'] = np.sqrt(df['VelocityX']**2 + df['VelocityY']**2)

# Mesafe Değişimi (Dosyadaki veriden)
df['Dist_Delta'] = df['DistanceToSteerpoint'].diff().abs()

# Tahmini Mesafe Değişimi (Hız * Zaman) -> dt = 0.05sn
df['Expected_Dist_Delta'] = df['GroundSpeed'] * 0.05

# --- ANALİZ PANELLERİ İÇİN HAZIRLIK ---
angle_cols = ["PlatformAzimuth", "RollAngle", "PitchAngle", "PresentTrueHeading", 
              "PresentMagneticHeading", "GreatCircleSteeringError", "ComputedCourseDeviation"]

# Derece dönüşümü (Senin tespitlerine göre True kalsın)
for col in angle_cols:
    if col in df.columns:
        df[col] = df[col] * (180.0 / np.pi)
        df[col] = df[col].rolling(window=10, min_periods=1, center=True).mean()

# Farklar
df['Diff_Azimuth_True'] = df['PlatformAzimuth'] - df['PresentTrueHeading']
df['Diff_True_Mag'] = df['PresentTrueHeading'] - df['PresentMagneticHeading']

# 2. GRAFİK KURULUMU (6x2)
plot_cols = ["VelocityX", "VelocityY", "GroundSpeed", "DistanceToSteerpoint",
             "RollAngle", "PitchAngle", "PresentTrueHeading", "PlatformAzimuth",
             "GreatCircleSteeringError", "ComputedCourseDeviation", 
             "Diff_Azimuth_True", "Diff_True_Mag"]

fig, axes = plt.subplots(nrows=6, ncols=2, figsize=(16, 22))
axes = axes.flatten()
lines = []

for i, col in enumerate(plot_cols):
    color = 'tab:red' if 'Diff' in col else ('tab:green' if 'Speed' in col else '#1f77b4')
    line, = axes[i].plot([], [], label=col, color=color, lw=2)
    axes[i].set_title(f"{col}")
    axes[i].grid(True, alpha=0.3)
    lines.append(line)

def update(frame):
    start = max(0, frame - 150)
    end = frame
    subset = df.iloc[start:end]
    if not subset.empty:
        for i, col in enumerate(plot_cols):
            y_data = subset[col].values
            lines[i].set_data(np.arange(len(y_data)), y_data)
            y_min, y_max = np.min(y_data), np.max(y_data)
            margin = max((y_max - y_min) * 0.15, 0.5)
            axes[i].set_ylim(y_min - margin, y_max + margin)
            axes[i].set_xlim(0, 150)
    return lines

# 3. BİRİM TESTİ RAPORU (Terminalde görünecek)
actual_move = df['Dist_Delta'].mean()
expected_move = df['Expected_Dist_Delta'].mean()
ratio = actual_move / expected_move if expected_move != 0 else 0

print("\n--- BİRİM DOĞRULAMA ANALİZİ ---")
print(f"Saniyede ortalama katedilen mesafe (Dosya): {actual_move*20:.2f} birim/sn")
print(f"Saniyede ortalama katedilen mesafe (Hız Hesabı): {expected_move*20:.2f} birim/sn")
print(f"Oran (Mesafe / Hız): {ratio:.4f}")

if 0.9 < ratio < 1.1:
    print("SONUÇ: Hız ve Mesafe birimleri UYUMLU (Muhtemelen m/s ve metre).")
elif 0.4 < ratio < 0.6:
    print("SONUÇ: Birimlerde uyuşmazlık var (Knots/Feet veya benzeri dönüşüm gerekebilir).")
else:
    print("SONUÇ: Birimler arasında karmaşık bir ilişki var, katsayıları inceleyin.")

ani = FuncAnimation(fig, update, frames=range(10, len(df), 10), interval=200, blit=False)
plt.tight_layout()
plt.show()