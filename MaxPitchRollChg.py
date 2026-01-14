import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ---------------------------------------------------------
# AYARLAR
# ---------------------------------------------------------
FILE_NAME = 'DnzRec.csv'   # Dosya adını buradan değiştirin
SAMPLE_RATE = 20           # Veri frekansı (20 Hz)
IS_RADIAN = True           # Veriler Radyan ise True, Derece ise False

# ---------------------------------------------------------
# 1. VERİ YÜKLEME
# ---------------------------------------------------------
try:
    df = pd.read_csv(FILE_NAME)
    df.columns = [col.strip().replace('"', '') for col in df.columns]
except FileNotFoundError:
    print(f"HATA: '{FILE_NAME}' dosyası bulunamadı!")
    exit()

# Zaman formatı
if "TimeMarker" in df.columns:
    df["TimeMarker"] = pd.to_datetime(df["TimeMarker"])

# ---------------------------------------------------------
# 2. HESAPLAMA VE ANALİZ
# ---------------------------------------------------------
analyze_cols = ["RollAngle", "PitchAngle"]
results = {}

print(f"Analiz Başlıyor... (Birim Dönüşümü: {'Radyan->Derece' if IS_RADIAN else 'Yok, Zaten Derece'})")

for col in analyze_cols:
    if col in df.columns:
        # Önce veriyi sayısal formata çevirip ham halini alalım
        raw_values = pd.to_numeric(df[col], errors='coerce')
        
        # BİRİM DÖNÜŞÜMÜ KONTROLÜ
        if IS_RADIAN:
            degree_values = raw_values * (180.0 / np.pi)
        else:
            degree_values = raw_values # Dönüşüm yapma, olduğu gibi kullan
        
        # 1 Saniyelik Değişimi Hesapla
        # diff(SAMPLE_RATE): Şu anki satır ile 20 satır önceki (1 sn önceki) fark
        delta_1s = degree_values.diff(periods=SAMPLE_RATE).abs()
        
        # Maksimumu Bul
        max_val = delta_1s.max()
        max_idx = delta_1s.idxmax()
        time_of_max = df.loc[max_idx, "TimeMarker"] if max_idx in df.index else "Bilinmiyor"
        
        results[col] = {
            "max_change": max_val,
            "time": time_of_max,
            "series": delta_1s 
        }
        
        print(f"\n--- {col} ANALİZİ ---")
        print(f"1 Saniyedeki Maksimum Değişim: {max_val:.4f} Derece")
        print(f"Gerçekleştiği Zaman: {time_of_max}")
        print("-" * 30)

# ---------------------------------------------------------
# 3. GRAFİKLEME
# ---------------------------------------------------------
if results:
    fig, ax = plt.subplots(figsize=(12, 6))
    fig.suptitle("Saniyelik Açısal Değişim Miktarları (Delta / 1 sec)", fontsize=14)

    for col in results:
        # Zaman ekseni varsa onu kullan, yoksa index (satır no) kullan
        x_axis = df["TimeMarker"] if "TimeMarker" in df.columns else df.index
        ax.plot(x_axis, results[col]["series"], label=f"{col} Değişimi", linewidth=1.5)

    ax.set_ylabel("Değişim (Derece / 1 Saniye)")
    ax.set_xlabel("Zaman")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Maksimum noktaları işaretle
    for col in results:
        max_val = results[col]["max_change"]
        time_val = results[col]["time"]
        
        # Eğer zaman bilgisi varsa grafiğe ekle
        if "TimeMarker" in df.columns:
            ax.annotate(f'Max {col}: {max_val:.2f}°', 
                        xy=(time_val, max_val), 
                        xytext=(10, 15), textcoords='offset points',
                        arrowprops=dict(arrowstyle="->", color='red', lw=1.5),
                        bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.8))

    plt.tight_layout()
    plt.show()
else:
    print("Analiz edilecek sütunlar dosyada bulunamadı.")