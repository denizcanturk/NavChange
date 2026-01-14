import tkinter as tk
from tkinter import ttk
import pandas as pd
import numpy as np
import math

# ---------------------------------------------------------
# AYARLAR
# ---------------------------------------------------------
FILE_NAME = 'DnzRec.csv'
UPDATE_INTERVAL = 50  # 50ms = Saniyede 20 kare (Daha akıcı olması için düşürdüm)

class CockpitApp:
    def __init__(self, root, datafile):
        self.root = root
        self.root.title("Flight Data Recorder - Pro Dashboard")
        self.root.geometry("1000x750") # Kontroller için boyutu biraz uzattım
        self.root.configure(bg="#202020")

        # --- VERİ YÜKLEME ---
        self.load_data(datafile)
        
        self.current_frame = 0
        self.is_playing = False # Başlangıçta duraklatılmış olsun
        self.speed_multiplier = 1 # Varsayılan hız 1x

        # --- ARAYÜZ ---
        self.create_widgets()
        
        # --- DÖNGÜYÜ BAŞLAT ---
        # İlk kareyi çiz ve bekle
        self.update_ui()
        self.root.after(UPDATE_INTERVAL, self.update_loop)

    def load_data(self, filename):
        try:
            df = pd.read_csv(filename)
            df.columns = [col.strip().replace('"', '') for col in df.columns]
            
            # 1. Hız Dönüşümü (Ft/s -> Knots)
            cols_vel = ["VelocityX", "VelocityY", "VelocityZ"]
            for c in cols_vel:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0) * 0.592484
            
            # Ground Speed
            df['GroundSpeed'] = np.sqrt(df['VelocityX']**2 + df['VelocityY']**2)

            # 2. Açı Dönüşümü (Radyan -> Derece)
            cols_ang = ["RollAngle", "PitchAngle", "PresentTrueHeading"]
            for c in cols_ang:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0) * (180.0 / np.pi)
            
            # Zaman Listesi
            if "TimeMarker" in df.columns:
                self.times = df["TimeMarker"].astype(str).values
            else:
                self.times = [f"F:{i}" for i in range(len(df))]

            self.df = df
            self.total_frames = len(df)
            print(f"Veri yüklendi: {self.total_frames} kayıt.")

        except Exception as e:
            print(f"Veri yükleme hatası: {e}")
            self.df = pd.DataFrame()
            self.total_frames = 0
            self.times = []

    def create_widgets(self):
        # 1. ÜST BİLGİ (Zaman)
        self.info_frame = tk.Frame(self.root, bg="#202020")
        self.info_frame.pack(side=tk.TOP, fill=tk.X, pady=5)
        
        self.lbl_time = tk.Label(self.info_frame, text="ZAMAN: --:--:--", font=("Consolas", 24, "bold"), fg="#00ff00", bg="black", padx=10)
        self.lbl_time.pack()

        # 2. GÖSTERGE PANELİ
        self.gauge_frame = tk.Frame(self.root, bg="#202020")
        self.gauge_frame.pack(expand=True, fill=tk.BOTH, padx=20, pady=10)

        self.canvas_airspeed = self.create_gauge_canvas(self.gauge_frame, "AIRSPEED (Knots)")
        self.canvas_attitude = self.create_gauge_canvas(self.gauge_frame, "ATTITUDE (Horizon)")
        self.canvas_heading = self.create_gauge_canvas(self.gauge_frame, "HEADING (Deg)")
        self.canvas_vsi = self.create_gauge_canvas(self.gauge_frame, "VERT. SPEED (Knots)")

        # 3. KONTROL PANELİ (ALT)
        self.control_frame = tk.LabelFrame(self.root, text="Oynatma Kontrolleri", bg="#303030", fg="white", padx=10, pady=10)
        self.control_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=20)

        # -- Play/Pause Butonu --
        self.btn_play = tk.Button(self.control_frame, text="▶ OYNAT", command=self.toggle_play, 
                                  bg="#444", fg="white", font=("Arial", 12, "bold"), width=10)
        self.btn_play.pack(side=tk.LEFT, padx=10)

        # -- Zaman Çubuğu (Timeline Slider) --
        # Frame sayısına göre 0'dan toplama kadar
        self.var_timeline = tk.IntVar(value=0)
        self.scale_timeline = tk.Scale(self.control_frame, from_=0, to=self.total_frames-1, 
                                       orient=tk.HORIZONTAL, variable=self.var_timeline, 
                                       command=self.on_seek, bg="#303030", fg="white", 
                                       highlightthickness=0, label="Zaman Çubuğu")
        self.scale_timeline.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)

        # -- Hız Sürgüsü --
        self.var_speed = tk.IntVar(value=1)
        self.scale_speed = tk.Scale(self.control_frame, from_=1, to=500, # 500x hıza kadar
                                    orient=tk.HORIZONTAL, variable=self.var_speed, 
                                    bg="#303030", fg="white", highlightthickness=0, 
                                    label="Hız Çarpanı (x)", length=200)
        self.scale_speed.pack(side=tk.RIGHT, padx=10)

    def create_gauge_canvas(self, parent, title):
        frame = tk.Frame(parent, bg="#202020")
        frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        lbl = tk.Label(frame, text=title, fg="#aaa", bg="#202020", font=("Arial", 10, "bold"))
        lbl.pack(side=tk.TOP)
        canvas = tk.Canvas(frame, width=220, height=220, bg="#202020", highlightthickness=0)
        canvas.pack()
        return canvas

    # --- KONTROL FONKSİYONLARI ---
    def toggle_play(self):
        self.is_playing = not self.is_playing
        if self.is_playing:
            self.btn_play.config(text="⏸ DURAKLAT", bg="darkred")
        else:
            self.btn_play.config(text="▶ OYNAT", bg="#444")

    def on_seek(self, val):
        # Kullanıcı timeline'ı kaydırdığında
        self.current_frame = int(val)
        self.update_ui() # Hemen güncelle ki görüntüyü görsün

    def update_loop(self):
        if self.is_playing and self.total_frames > 0:
            # Hız çarpanını al
            speed = self.var_speed.get()
            
            # Frame'i ilerlet
            self.current_frame += speed
            
            # Başa sarma veya durma kontrolü
            if self.current_frame >= self.total_frames:
                self.current_frame = 0 # Döngüye girsin mi? Evet.
                # self.is_playing = False # Veya dursun
            
            # Timeline slider'ını güncelle (ama on_seek tetiklemesin diye dikkatli olmalı, gerçi scale set komut tetiklemez genelde)
            self.var_timeline.set(self.current_frame)
            
            # Arayüzü çiz
            self.update_ui()

        # Döngüyü tekrarla
        self.root.after(UPDATE_INTERVAL, self.update_loop)

    def update_ui(self):
        if self.total_frames == 0: return
        
        # Güvenlik sınırı
        idx = min(self.current_frame, self.total_frames - 1)
        row = self.df.iloc[idx]
        
        # Zaman Yazısı
        t_str = str(self.times[idx])
        # Format temizleme (Varsa)
        display_time = t_str.split(' ')[1] if ' ' in t_str else t_str
        self.lbl_time.config(text=f"ZAMAN: {display_time}")

        # Çizimler
        self.draw_airspeed(row['GroundSpeed'])
        self.draw_attitude(row['RollAngle'], row['PitchAngle'])
        self.draw_heading(row['PresentTrueHeading'])
        self.draw_vsi(row['VelocityZ'])

    # --- ÇİZİM FONKSİYONLARI ---
    def draw_airspeed(self, speed):
        c = self.canvas_airspeed
        c.delete("all")
        c.create_oval(10, 10, 210, 210, fill="#101010", outline="#555", width=3)
        c.create_text(110, 160, text=f"{int(speed)}", fill="#00ff00", font=("Arial", 24, "bold"))
        c.create_text(110, 185, text="KTS", fill="#00ff00", font=("Arial", 10))
        
        max_speed = 600
        angle = 135 + (speed / max_speed) * 270
        rad = math.radians(angle)
        x = 110 + 80 * math.cos(rad)
        y = 110 + 80 * math.sin(rad)
        c.create_line(110, 110, x, y, fill="red", width=4, arrow=tk.LAST)
        c.create_oval(105, 105, 115, 115, fill="red")

    def draw_attitude(self, roll, pitch):
        # DÜZELTİLMİŞ YAPAY UFUK KODU
        c = self.canvas_attitude
        c.delete("all")
        cx, cy, radius = 110, 110, 100
        
        # 1. Gökyüzü (Arka plan)
        c.create_oval(cx-radius, cy-radius, cx+radius, cy+radius, fill="#00BFFF", outline="")

        # 2. Yeryüzü (Dönen Poligon)
        pitch_scale = 2.0
        offset = pitch * pitch_scale
        big_w, big_h = 400, 400
        
        # Dikdörtgen köşe noktaları
        rect_points = [(-big_w, offset), (big_w, offset), (big_w, big_h), (-big_w, big_h)]
        
        # Döndürme
        roll_rad = math.radians(-roll)
        cos_a, sin_a = math.cos(roll_rad), math.sin(roll_rad)
        
        rotated_poly = []
        for x, y in rect_points:
            rx = x * cos_a - y * sin_a + cx
            ry = x * sin_a + y * cos_a + cy
            rotated_poly.extend([rx, ry])
            
        # Yeri çiz (Kahverengi)
        c.create_polygon(rotated_poly, fill="#8B4513", outline="")
        
        # Ufuk Çizgisi
        c.create_line(rotated_poly[0], rotated_poly[1], rotated_poly[2], rotated_poly[3], fill="white", width=2)

        # 3. Maskeleme (Dışarı taşanları gizle)
        c.create_oval(cx-radius, cy-radius, cx+radius, cy+radius, outline="#202020", width=100, tags="mask") # Kalın dış sınır
        c.create_oval(cx-radius, cy-radius, cx+radius, cy+radius, outline="#555", width=3, fill="") # İnce iç sınır

        # 4. Uçak Sembolü
        wing_color = "#FFD700"
        c.create_line(cx-40, cy, cx-10, cy, width=4, fill=wing_color)
        c.create_line(cx-10, cy, cx, cy+10, width=4, fill=wing_color)
        c.create_line(cx, cy+10, cx+10, cy, width=4, fill=wing_color)
        c.create_line(cx+10, cy, cx+40, cy, width=4, fill=wing_color)
        c.create_oval(cx-2, cy-2, cx+2, cy+2, fill="red", outline="red")

        # 5. Pitch Çizgileri
        for p in [10, 20, -10, -20]:
            p_offset = (p + pitch) * pitch_scale
            if -radius < p_offset < radius:
                lw = 20
                pts = []
                for x, y in [(-lw, p_offset), (lw, p_offset)]:
                    rx = x * cos_a - y * sin_a + cx
                    ry = x * sin_a + y * cos_a + cy
                    pts.extend([rx, ry])
                c.create_line(pts, fill="white", width=1)

        c.create_text(cx, cy-80, text=f"R: {roll:.1f}°", fill="white", font=("Consolas", 10, "bold"))
        c.create_text(cx, cy+80, text=f"P: {pitch:.1f}°", fill="white", font=("Consolas", 10, "bold"))

    def draw_heading(self, heading):
        c = self.canvas_heading
        c.delete("all")
        c.create_oval(10, 10, 210, 210, fill="#101010", outline="#555", width=3)
        c.create_text(110, 90, text="▲", fill="yellow", font=("Arial", 20))
        c.create_text(110, 160, text=f"{int(heading)}°", fill="#00ff00", font=("Arial", 24, "bold"))
        
        angle_rad = math.radians(-heading - 90)
        x = 110 + 80 * math.cos(angle_rad)
        y = 110 + 80 * math.sin(angle_rad)
        c.create_line(110, 110, x, y, fill="red", width=3, arrow=tk.LAST)
        c.create_text(x, y, text="N", fill="red", font=("Arial", 12, "bold"))
        
        for label, deg in [("E", 90), ("S", 180), ("W", 270)]:
            rad = math.radians(deg - heading - 90)
            lx = 110 + 70 * math.cos(rad)
            ly = 110 + 70 * math.sin(rad)
            c.create_text(lx, ly, text=label, fill="white", font=("Arial", 10))

    def draw_vsi(self, vz):
        c = self.canvas_vsi
        c.delete("all")
        c.create_oval(10, 10, 210, 210, fill="#101010", outline="#555", width=3)
        c.create_text(110, 160, text=f"{vz:.1f}", fill="#00ff00", font=("Arial", 24, "bold"))
        c.create_text(110, 185, text="KTS UP", fill="#00ff00", font=("Arial", 10))
        
        max_vz = 20
        val = max(min(vz, max_vz), -max_vz)
        angle = 180 - (val / max_vz) * 90
        rad = math.radians(angle)
        x = 110 + 80 * math.cos(rad)
        y = 110 + 80 * math.sin(rad)
        c.create_line(110, 110, x, y, fill="white", width=4, arrow=tk.LAST)
        c.create_line(30, 110, 50, 110, fill="gray", width=2)

if __name__ == "__main__":
    root = tk.Tk()
    app = CockpitApp(root, FILE_NAME)
    root.mainloop()