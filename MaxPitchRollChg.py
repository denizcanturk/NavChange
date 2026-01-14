import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ---------------------------------------------------------
# AYARLAR
# ---------------------------------------------------------
FILE_NAME = 'DnzRec.csv'  # Dosya adını buradan değiştirin
SAMPLE_RATE = 20          # Veri frekansı (20 Hz ise buraya 20 yazın)

# ---------------------------------------------------------
# 1. VERİ YÜKLEME
# ---------------------------------------------------------
try:
    df = pd.read_csv(FILE_NAME)
    df.columns = [col.strip().replace('"', '') for col in df.columns]
except FileNotFoundError:
    print("Dosya bulunamadı!")
    exit()

# Zaman formatı
if "TimeMarker" in df.columns:
    df["TimeMarker"] = pd.to_datetime(df["TimeMarker"])

# ---------------------------------------------------------
# 2. HESAPLAMA (RADYAN -> DERECE -> DELTA)
# ---------------------------------------------------------
analyze_cols = ["RollAngle", "PitchAngle"]
results = {}

for col in analyze_cols:
    if col in df.columns:
        # 1. Radyan'dan Dereceye Çevir
        # Not: Eğer veriniz zaten derece ise bu satırı silin!
        degree_values = pd.to_numeric(df[col], errors='coerce') * (180.0 / np.pi)
        
        # 2. Gürültüden kaçınmak için hafif yumuşatma (Opsiyonel)
        # degree_values = degree_values.rolling(window=5).mean()
        
        # 3. 1 Saniyelik Değişimi Hesapla
        # diff(SAMPLE_RATE): Şu anki satır ile 20 satır önceki (1 sn önceki) farkı alır
        delta_1s = degree_values.diff(periods=SAMPLE_RATE).abs()
        
        # 4. Maksimumu Bul
        max_val = delta_1s.max()
        max_idx = delta_1s.idxmax()
        time_of_max = df.loc[max_idx, "TimeMarker"] if max_idx in df.index else "Bilinmiyor"
        
        results[col] = {
            "max_change": max_val,
            "time": time_of_max,
            "series": delta_1s # Grafik için saklayalım
        }
        
        print(f"--- {col} ANALİZİ ---")
        print(f"1 Saniyedeki Maksimum Değişim: {max_val:.4f} Derece")
        print(f"Gerçekleştiği Zaman: {time_of_max}")
        print("-" * 30)

# ---------------------------------------------------------
# 3. GRAFİKLEME (ZAMAN İÇİNDEKİ DEĞİŞİM HIZI)
# ---------------------------------------------------------
fig, ax = plt.subplots(figsize=(12, 6))
fig.suptitle("Saniyelik Açısal Değişim Miktarları (Delta / 1 sec)", fontsize=14)

for col in analyze_cols:
    if col in results:
        ax.plot(df["TimeMarker"], results[col]["series"], label=f"{col} Değişimi")

ax.set_ylabel("Değişim (Derece / 1 Saniye)")
ax.set_xlabel("Zaman")
ax.legend()
ax.grid(True, alpha=0.3)

# Maksimum noktaları işaretle
for col in analyze_cols:
    if col in results:
        max_val = results[col]["max_change"]
        time_val = results[col]["time"]
        ax.annotate(f'Max {col}: {max_val:.2f}°', 
                    xy=(time_val, max_val), 
                    xytext=(10, 10), textcoords='offset points',
                    arrowprops=dict(arrowstyle="->", color='red'))

plt.tight_layout()
plt.show()