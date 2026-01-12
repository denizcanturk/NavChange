import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from mpl_toolkits.mplot3d import Axes3D

# 1. VERİ HAZIRLIĞI
#df = pd.read_csv('DetailToAnalyse.csv')
df = pd.read_csv('DnzRec.csv')
df.columns = [col.strip().replace('"', '') for col in df.columns]

# Hız verilerini al (Feet/Saniye kabul ediyoruz)
# Eğer Knot olarak görmek istemiştik ama integrali (yol hesabını) 
# orijinal birim (Feet/sn) üzerinden yapmak daha hassastır.
cols = ["VelocityX", "VelocityY", "VelocityZ"]
for col in cols:
    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

# --- İNTEGRAL ALARAK KONUM HESAPLAMA ---
# dt = 0.05 saniye (20 Hz)
dt = 0.005

# Kümülatif toplam alarak anlık pozisyonu (Feet) buluyoruz
# Başlangıç noktası (0,0,0) kabul edilir.
df['PosX'] = (df['VelocityX'] * dt).cumsum()
df['PosY'] = (df['VelocityY'] * dt).cumsum()
# Z ekseni genellikle 'Down' olabilir, grafikte yukarı doğru görmek için - ile çarpabiliriz
# Eğer Z verisi pozitifken irtifa artıyorsa dokunma. Genelde NED (North-East-Down) sistemlerinde Z aşağıdır.
# Deneme amaçlı Z'yi olduğu gibi alalım, grafikte aşağı giderse - ile çarparız.
df['PosZ'] = (df['VelocityZ'] * dt).cumsum()

# Hız büyüklüğü (Renk haritası için)
df['Speed'] = np.sqrt(df['VelocityX']**2 + df['VelocityY']**2 + df['VelocityZ']**2)

# Veriyi biraz seyret (Animasyon performansı için)
# Her 5. veriyi alıyoruz
step = 5
df_plot = df.iloc[::step].reset_index(drop=True)

# 2. 3D GRAFİK KURULUMU
fig = plt.figure(figsize=(12, 10))
ax = fig.add_subplot(111, projection='3d')
fig.suptitle("3D Uçuş Yörüngesi ve Yer İzi", fontsize=16)

# Eksen Etiketleri (Birim: Feet)
ax.set_xlabel('X Mesafesi (ft)')
ax.set_ylabel('Y Mesafesi (ft)')
ax.set_zlabel('İrtifa Değişimi (ft)')

# Başlangıç Ayarları
# Arka plan rengini koyulaştırarak "Radar/Simülasyon" havası verelim
ax.set_facecolor('#1e1e1e') 
fig.patch.set_facecolor('#1e1e1e')
ax.tick_params(axis='x', colors='white')
ax.tick_params(axis='y', colors='white')
ax.tick_params(axis='z', colors='white')
ax.xaxis.label.set_color('white')
ax.yaxis.label.set_color('white')
ax.zaxis.label.set_color('white')

# Izgaraları daha silik yap
ax.grid(color='gray', linestyle=':', linewidth=0.5, alpha=0.5)

# Çizilecek nesneler
# Uçak (Nokta)
plane, = ax.plot([], [], [], marker='^', markersize=10, color='yellow', label='Hava Aracı')
# İz (Çizgi)
trail, = ax.plot([], [], [], color='cyan', linewidth=1.5, alpha=0.8, label='Uçuş İzi')
# Yer İzdüşümü (Gölge) - Derinlik algısı için çok önemlidir
shadow, = ax.plot([], [], [], color='gray', linewidth=1, alpha=0.4, linestyle='--')

# Eksen sınırlarını sabitlemek için tüm verinin min/max değerlerini al
x_min, x_max = df_plot['PosX'].min(), df_plot['PosX'].max()
y_min, y_max = df_plot['PosY'].min(), df_plot['PosY'].max()
z_min, z_max = df_plot['PosZ'].min(), df_plot['PosZ'].max()

# Z ekseni çok düz olabilir (düz uçuş), o yüzden manuel aralık verelim
# En az 100 ft'lik bir dikey pencere olsun
if abs(z_max - z_min) < 100:
    z_center = (z_max + z_min) / 2
    z_min = z_center - 50
    z_max = z_center + 50

ax.set_xlim(x_min, x_max)
ax.set_ylim(y_min, y_max)
ax.set_zlim(z_min, z_max)

# Görüş açısı (Elevation, Azimuth)
ax.view_init(elev=20, azim=-45)

def update(frame):
    # O anki kareye kadar olan veriler
    current_x = df_plot['PosX'][:frame]
    current_y = df_plot['PosY'][:frame]
    current_z = df_plot['PosZ'][:frame]
    
    # Son nokta (Uçak pozisyonu)
    head_x = df_plot['PosX'][frame]
    head_y = df_plot['PosY'][frame]
    head_z = df_plot['PosZ'][frame]
    
    # 1. İzi güncelle
    trail.set_data(current_x, current_y)
    trail.set_3d_properties(current_z)
    
    # 2. Uçağı güncelle
    plane.set_data([head_x], [head_y])
    plane.set_3d_properties([head_z])
    
    # 3. Yerdeki gölgeyi güncelle (Z ekseninin tabanına proje edilir)
    # Z=z_min seviyesinde çizelim
    shadow.set_data(current_x, current_y)
    shadow.set_3d_properties(np.full_like(current_z, z_min))
    
    # Kamera açısını hafifçe döndür (Sinematik etki)
    ax.view_init(elev=20, azim=-45 + frame * 0.1)
    
    # Başlıkta anlık hız bilgisi
    speed_now = df_plot['Speed'][frame] * 0.592484 # Knot çevrimi
    ax.set_title(f"3D Yörünge - Hız: {speed_now:.1f} kts", color='white', fontsize=14)
    
    return trail, plane, shadow

# Animasyonu oluştur
ani = FuncAnimation(fig, update, frames=range(1, len(df_plot)), 
                    interval=10, blit=False)

plt.legend(loc='upper left')
plt.show()