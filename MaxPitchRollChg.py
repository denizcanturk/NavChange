import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ---------------------------------------------------------
# AYARLAR
# ---------------------------------------------------------
FILE_NAME = 'i09.csv'
SAMPLE_RATE = 20           
IS_NORMALIZED = True       

# ---------------------------------------------------------
# 1. VERİ YÜKLEME
# ---------------------------------------------------------
try:
    with open(FILE_NAME, 'r') as f:
        header = f.readline().strip().replace('"', '')
    cols = [c.strip() for c in header.split(',')]
    df = pd.read_csv(FILE_NAME, skiprows=1, names=cols)
except FileNotFoundError:
    print(f"HATA: '{FILE_NAME}' bulunamadı!")
    exit()
except Exception:
    df = pd.read_csv(FILE_NAME)

if "TimeMarker" in df.columns:
    df["TimeMarker"] = pd.to_datetime(df["TimeMarker"])
else:
    df["TimeMarker"] = df.index

# ---------------------------------------------------------
# 2. HESAPLAMA (Calculated Delta)
# ---------------------------------------------------------
analyze_cols = ["RollAngle", "PitchAngle"]
results_calc = {}

for col in analyze_cols:
    if col in df.columns:
        raw = pd.to_numeric(df[col], errors='coerce')
        val = raw * 180.0 if IS_NORMALIZED else raw
        # 1 saniyelik mutlak değişim
        results_calc[col] = val.diff(periods=SAMPLE_RATE).abs()

# ---------------------------------------------------------
# 3. RATE VERİLERİ (System Data)
# ---------------------------------------------------------
rate_cols = ["RollRate", "PitchRate", "YawRate"]
results_rate = {}

for col in rate_cols:
    if col in df.columns:
        raw = pd.to_numeric(df[col], errors='coerce')
        val = raw * 180.0 if IS_NORMALIZED else raw
        results_rate[col] = val

# ---------------------------------------------------------
# 4. GRAFİKLEME
# ---------------------------------------------------------
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)

# --- ÜST GRAFİK: Sizin Hesapladığınız (Mutlak Değişim) ---
ax1.set_title("1. Calculated Angle Delta (Absolute Change / 1 sec)", fontsize=12, fontweight='bold')
for col_name, data in results_calc.items():
    line, = ax1.plot(df["TimeMarker"], data, label=f"Calc {col_name}", linewidth=1.5)
    
    # ANNOTATION (MAX VALUE)
    max_val = data.max()
    max_idx = data.idxmax()
    if pd.notna(max_val):
        x_pos = df["TimeMarker"][max_idx]
        ax1.annotate(f'Max: {max_val:.2f}°', 
                     xy=(x_pos, max_val), xytext=(10, 10), textcoords='offset points',
                     arrowprops=dict(arrowstyle="->", color=line.get_color(), lw=1.5),
                     bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.8))

ax1.set_ylabel("Change Magnitude (°/s)")
ax1.grid(True, alpha=0.3)
ax1.legend(loc="upper right")

# --- ALT GRAFİK: Dosyadaki Hazır Veri (Salınım Yapan) ---
ax2.set_title("2. System Angular Rates (Oscillating around 0)", fontsize=12, fontweight='bold')
# 0 Referans Çizgisi
ax2.axhline(0, color='black', linewidth=1, linestyle='--')

colors = {'RollRate': 'tab:blue', 'PitchRate': 'tab:orange', 'YawRate': 'tab:green'}
for col_name, data in results_rate.items():
    c = colors.get(col_name, 'black')
    line, = ax2.plot(df["TimeMarker"], data, label=f"System {col_name}", color=c, linewidth=1.5, alpha=0.7)
    
    # ANNOTATION (MAX ABSOLUTE VALUE)
    # Rate verisi - ve + olduğu için, en büyük etkiyi (şiddeti) bulmak için mutlak değere bakıyoruz
    # ama grafikte gerçek değerini (eksi veya artı) işaretliyoruz.
    max_idx = data.abs().idxmax()
    max_val = data[max_idx] # Gerçek değer (örn: -25.4)
    
    if pd.notna(max_val):
        x_pos = df["TimeMarker"][max_idx]
        ax2.annotate(f'Peak {col_name}: {max_val:.2f}°/s', 
                     xy=(x_pos, max_val), xytext=(10, 20 if max_val>0 else -20), textcoords='offset points',
                     arrowprops=dict(arrowstyle="->", color=c, lw=1.5),
                     bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.8))

ax2.set_ylabel("Rate (°/s)")
ax2.set_xlabel("Time")
ax2.grid(True, alpha=0.3)
ax2.legend(loc="upper right")

plt.tight_layout()
plt.show()