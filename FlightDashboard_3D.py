import tkinter as tk
from tkinter import ttk
import pandas as pd
import numpy as np
import math
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from mpl_toolkits.mplot3d import Axes3D

# ---------------------------------------------------------
# AYARLAR
# ---------------------------------------------------------
FILE_NAME = 'i09.csv'
UPDATE_INTERVAL = 50      # 50ms = 20 FPS
PLOT_DOWNSAMPLE = 100     # Performans için örnekleme

class CockpitApp:
    def __init__(self, root, datafile):
        self.root = root
        self.root.title("Flight Data Recording Player")
        self.root.geometry("1600x950") 
        self.root.configure(bg="#202020")
        
        self.is_running = True
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # --- VERİ YÜKLEME ---
        self.load_data(datafile)
        
        self.current_frame = 0
        self.is_playing = False
        self.speed_multiplier = 1 

        # --- ARAYÜZ ---
        self.create_layout()
        
        print("Görünüşe göre hazırız... :)")
        # --- DÖNGÜ BAŞLAT ---
        self.update_ui()
        self.root.after(UPDATE_INTERVAL, self.update_loop)

    def on_closing(self):
        print("Tekrar Görüşmek üzere...")
        self.is_running = False
        self.is_playing = False
        try:
            self.root.after_cancel(self.update_loop)
        except:
            print("Shit happened... ")
        finally:
            self.root.destroy()
            plt.close('all')

    def load_data(self, filename):
        try:
            print("Veri yükleniyor...")
            with open(filename, 'r') as f:
                header_line = f.readline().strip()
            if header_line.startswith('"') and header_line.endswith('"'):
                header_line = header_line[1:-1]
            raw_cols = header_line.split(',')
            cols = [c.replace('""', '').strip() for c in raw_cols]
            seen = {}
            deduped_cols = []
            for c in cols:
                if c in seen:
                    seen[c] += 1
                    deduped_cols.append(f"{c}_{seen[c]}")
                else:
                    seen[c] = 0
                    deduped_cols.append(c)

            df = pd.read_csv(filename, skiprows=1, names=deduped_cols)
            
            # Zaman
            if "TimeMarker" in df.columns:
                df["TimeMarker_DT"] = pd.to_datetime(df["TimeMarker"], errors='coerce')
                self.times = df["TimeMarker"].astype(str).values
            else:
                df["TimeMarker_DT"] = pd.to_datetime(df.index, unit='s', origin='unix')
                self.times = [f"F:{i}" for i in range(len(df))]

            # Açılar (Normalize -> Derece)
            angle_cols = ["RollAngle", "PitchAngle", "PlatformAzimuth", 
                          "BlendedLatitude", "BlendedLongitude"]
            for c in angle_cols:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0) * 180.0
            
            # Rate (Normalize -> Derece/Saniye)
            rate_cols = ["RollRate", "PitchRate", "YawRate"]
            for c in rate_cols:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0) * 180.0

            # Hızlar
            vel_cols = ["VelocityX", "VelocityY", "VelocityZ"]
            for c in vel_cols:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0) * 0.592484
            
            df['GroundSpeed'] = np.sqrt(df['VelocityX']**2 + df['VelocityY']**2)
            
            # İrtifa
            if "BlendedEllipsoidHeight" in df.columns:
                df["Altitude"] = df["BlendedEllipsoidHeight"]
            else:
                df["Altitude"] = 0
            
            df["Altitude_Smooth"] = df["Altitude"].rolling(window=20, min_periods=1, center=True).mean()

            # Max Rate Stats
            df['RollRate_Max'] = df['RollRate'].abs().cummax()
            df['PitchRate_Max'] = df['PitchRate'].abs().cummax()
            df['YawRate_Max'] = df['YawRate'].abs().cummax()

            self.df = df
            self.total_frames = len(df)
            print(f"Veri Başarılı şekilde okundu...! Toplam {self.total_frames} kayıt.")

        except Exception as e:
            print(f"Hata: {e}")
            self.df = pd.DataFrame()
            self.total_frames = 0

    def create_layout(self):
        print("Form Yapısı Düzenleniyor...")
        # 1. ÜST PANEL
        self.top_frame = tk.Frame(self.root, bg="#202020")
        self.top_frame.pack(side=tk.TOP, fill=tk.X)
        self.lbl_time = tk.Label(self.top_frame, text="READY", font=("Consolas", 16, "bold"), fg="#00ff00", bg="black")
        self.lbl_time.pack(pady=5)

        # 2. ANA BÖLÜCÜ
        self.main_pane = tk.PanedWindow(self.root, orient=tk.HORIZONTAL, bg="#202020", sashwidth=5)
        self.main_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- SOL TARAF (HARİTA) ---
        self.map_frame = tk.Frame(self.main_pane, bg="black")
        self.main_pane.add(self.map_frame, minsize=600, stretch="always")
        self.create_3d_plot()

        # --- SAĞ TARAF (YAN PANEL) ---
        self.sidebar_pane = tk.PanedWindow(self.main_pane, orient=tk.VERTICAL, bg="#202020", sashwidth=5)
        self.main_pane.add(self.sidebar_pane, minsize=420)

        print("Göstergeler Hazırlanıyor...")
        # A) Göstergeler
        self.gauge_frame = tk.Frame(self.sidebar_pane, bg="#202020")
        self.sidebar_pane.add(self.gauge_frame, minsize=200) 
        
        self.gauge_frame.columnconfigure(0, weight=1)
        self.gauge_frame.columnconfigure(1, weight=1)
        self.gauge_frame.rowconfigure(0, weight=1)
        self.gauge_frame.rowconfigure(1, weight=1)
        
        self.canvas_airspeed = self.create_gauge_canvas(self.gauge_frame, "AIRSPEED", 0, 0)
        self.canvas_attitude = self.create_gauge_canvas(self.gauge_frame, "ATTITUDE", 0, 1)
        self.canvas_heading = self.create_gauge_canvas(self.gauge_frame, "HEADING", 1, 0)
        self.canvas_vsi = self.create_gauge_canvas(self.gauge_frame, "V. SPEED", 1, 1)

        # B) Rate Grafiği
        self.rate_container = tk.Frame(self.sidebar_pane, bg="#151515")
        self.sidebar_pane.add(self.rate_container, minsize=200)
        
        self.rate_plot_frame = tk.Frame(self.rate_container, bg="black")
        self.rate_plot_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.create_rate_plot()
        
        self.rate_stats_frame = tk.Frame(self.rate_container, bg="#202020", pady=5)
        self.rate_stats_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.lbl_roll_rate = self.create_stat_label(self.rate_stats_frame, "Roll Rate", "cyan", 0)
        self.lbl_pitch_rate = self.create_stat_label(self.rate_stats_frame, "Pitch Rate", "magenta", 1)
        self.lbl_yaw_rate = self.create_stat_label(self.rate_stats_frame, "Yaw Rate", "yellow", 2)

        # 3. KONTROLLER
        self.control_frame = tk.Frame(self.root, bg="#303030", pady=10)
        self.control_frame.pack(side=tk.BOTTOM, fill=tk.X)

        self.btn_play = tk.Button(self.control_frame, text="▶ OYNAT", command=self.toggle_play, 
                                  bg="#444", fg="white", font=("Arial", 12, "bold"), width=10)
        self.btn_play.pack(side=tk.LEFT, padx=20)

        self.var_smooth = tk.BooleanVar(value=False)
        self.chk_smooth = tk.Checkbutton(self.control_frame, text="Noise Filter", variable=self.var_smooth,
                                         bg="#303030", fg="white", selectcolor="#444", 
                                         activebackground="#303030", activeforeground="white",
                                         font=("Arial", 10, "bold"), command=self.update_ui)
        self.chk_smooth.pack(side=tk.LEFT, padx=10)

        self.var_timeline = tk.IntVar(value=0)
        self.scale_timeline = tk.Scale(self.control_frame, from_=0, to=max(0, self.total_frames-1), 
                                       orient=tk.HORIZONTAL, variable=self.var_timeline, 
                                       command=self.on_seek, bg="#303030", fg="white", 
                                       highlightthickness=0, label="Zaman", length=400)
        self.scale_timeline.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=20)

        self.var_speed = tk.IntVar(value=1)
        self.scale_speed = tk.Scale(self.control_frame, from_=1, to=500, orient=tk.HORIZONTAL, 
                                    variable=self.var_speed, bg="#303030", fg="white", 
                                    highlightthickness=0, label="Hız (x)", length=150)
        self.scale_speed.pack(side=tk.RIGHT, padx=20)

    def create_gauge_canvas(self, parent, title, r, c):
        frame = tk.Frame(parent, bg="#202020")
        frame.grid(row=r, column=c, padx=3, pady=3, sticky="nsew")
        
        lbl = tk.Label(frame, text=title, fg="#aaa", bg="#202020", font=("Arial", 8, "bold"))
        lbl.pack(side=tk.TOP)
        canvas = tk.Canvas(frame, width=160, height=160, bg="#202020", highlightthickness=0)
        canvas.pack(expand=True)
        return canvas

    def create_stat_label(self, parent, title, color, col_idx):
        print("Grafik Etiketleri Oluşturuluyor...")
        frame = tk.Frame(parent, bg="#252525", highlightbackground=color, highlightthickness=1)
        frame.grid(row=0, column=col_idx, padx=5, sticky="ew")
        parent.grid_columnconfigure(col_idx, weight=1)
        tk.Label(frame, text=title, fg=color, bg="#252525", font=("Arial", 9, "bold")).pack(side=tk.TOP, anchor="w", padx=2)
        lbl_val = tk.Label(frame, text="Cur: 0.00", fg="white", bg="#252525", font=("Consolas", 10))
        lbl_val.pack(side=tk.BOTTOM, anchor="e", padx=2, pady=1)
        return lbl_val

    def create_3d_plot(self):
        print("3D Grafik Hazırlanıyor...")
        self.fig3d = plt.figure(figsize=(8, 6), dpi=100, facecolor='#101010')
        self.ax3d = self.fig3d.add_subplot(111, projection='3d')
        self.ax3d.set_facecolor('#101010')
        self.ax3d.tick_params(colors='gray', labelsize=8)
        self.ax3d.set_xlabel('Lon', color='gray')
        self.ax3d.set_ylabel('Lat', color='gray')
        self.ax3d.set_zlabel('Alt', color='gray')
        self.ax3d.grid(color='gray', linestyle=':', linewidth=0.3, alpha=0.5)

        if self.total_frames > 0:
            step = PLOT_DOWNSAMPLE
            xs = self.df['BlendedLongitude'].values[::step]
            ys = self.df['BlendedLatitude'].values[::step]
            zs = self.df['Altitude'].values[::step]
            
            self.ax3d.plot(xs, ys, zs, color='#004400', linewidth=0.8, alpha=0.5)
            self.ax3d.scatter([xs[0]], [ys[0]], [zs[0]], color='green', marker='o', s=10)
            self.ax3d.scatter([xs[-1]], [ys[-1]], [zs[-1]], color='red', marker='x', s=10)
            self.plane_marker, = self.ax3d.plot([], [], [], marker='^', color='cyan', markersize=10, linestyle='None')
            
            self.ax3d.set_xlim(xs.min(), xs.max())
            self.ax3d.set_ylim(ys.min(), ys.max())
            self.ax3d.set_zlim(zs.min(), zs.max())

        self.canvas_3d = FigureCanvasTkAgg(self.fig3d, master=self.map_frame)
        self.canvas_3d.draw()
        self.canvas_3d.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    def create_rate_plot(self):
        print("2D Grafikler Hazırlanıyor...")
        self.figRate = plt.figure(figsize=(4, 3), dpi=100, facecolor='#151515')
        self.axRate = self.figRate.add_subplot(111)
        self.axRate.set_facecolor('#151515')
        self.axRate.tick_params(colors='gray', labelsize=8)
        self.axRate.set_title("Angular Rates (Sensors)", color='gray', fontsize=9)
        self.axRate.grid(color='gray', linestyle=':', linewidth=0.3, alpha=0.3)

        if self.total_frames > 0:
            step = PLOT_DOWNSAMPLE
            x = np.arange(0, self.total_frames, step)
            self.axRate.plot(x, self.df['RollRate'][::step], color='cyan', linewidth=0.8, label='Roll', alpha=0.8)
            self.axRate.plot(x, self.df['PitchRate'][::step], color='magenta', linewidth=0.8, label='Pitch', alpha=0.8)
            self.axRate.plot(x, self.df['YawRate'][::step], color='yellow', linewidth=0.8, label='Yaw', alpha=0.6)
            self.time_line_rate = self.axRate.axvline(x=0, color='white', linewidth=1.5, linestyle='--')

        self.canvas_rate = FigureCanvasTkAgg(self.figRate, master=self.rate_plot_frame)
        self.canvas_rate.draw()
        self.canvas_rate.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

    def toggle_play(self):
        self.is_playing = not self.is_playing 
        self.btn_play.config(text="⏸ DURAKLAT" if self.is_playing else "▶ OYNAT", bg="darkred" if self.is_playing else "#444")

    def on_seek(self, val):
        self.current_frame = int(val)
        self.update_ui()

    def update_loop(self):
        if not self.is_running: return
        if self.is_playing and self.total_frames > 0:
            speed = self.var_speed.get()
            self.current_frame += speed
            if self.current_frame >= self.total_frames:
                self.current_frame = 0
            self.var_timeline.set(self.current_frame)
            self.update_ui()
        if self.is_running:
            self.root.after(UPDATE_INTERVAL, self.update_loop)

    def update_ui(self):
        if not self.is_running or self.total_frames == 0: return
        idx = min(self.current_frame, self.total_frames - 1)
        row = self.df.iloc[idx]
        use_smooth = self.var_smooth.get()
        alt_val = row['Altitude_Smooth'] if use_smooth else row['Altitude']

        t_str = str(self.times[idx]).split(' ')[1] if ' ' in str(self.times[idx]) else str(self.times[idx])
        self.lbl_time.config(text=f"TIME: {t_str} | ALT: {int(alt_val)} ft")

        self.draw_airspeed(row['GroundSpeed'])
        self.draw_attitude(row['RollAngle'], row['PitchAngle'])
        self.draw_heading(row['PlatformAzimuth'])
        self.draw_vsi(row['VelocityZ'])

        self.plane_marker.set_data([row['BlendedLongitude']], [row['BlendedLatitude']])
        self.plane_marker.set_3d_properties([alt_val])
        self.canvas_3d.draw_idle()

        self.time_line_rate.set_xdata([idx])
        self.canvas_rate.draw_idle()
        
        #### ==================================================
        # BURADA BIR IYILEŞTIRME YAPMAM LAZIM... :( 
        
        self.lbl_roll_rate.config(text=f"Cur: {row['RollRate']:.1f}°/s | Max: {row['RollRate_Max']:.1f}")
        self.lbl_pitch_rate.config(text=f"Cur: {row['PitchRate']:.1f}°/s | Max: {row['PitchRate_Max']:.1f}")
        self.lbl_yaw_rate.config(text=f"Cur: {row['YawRate']:.1f}°/s | Max: {row['YawRate_Max']:.1f}")

    # --- YENİ "HAVALI" YAPAY UFUK FONKSİYONU ---
    def draw_attitude(self, roll, pitch):
        #print("Havalı Attitude Göstergesi çiziliyor...")
        c = self.canvas_attitude
        c.delete("all")
        # Canvas genişliği 160x160. Merkezi 80, 80.
        cx, cy, r = 80, 80, 70
        
        # 1. Gökyüzü (Arka plan)
        c.create_oval(cx-r, cy-r, cx+r, cy+r, fill="#00BFFF", outline="")
        
        # 2. Yeryüzü (Kahverengi Poligon)
        pitch_scale = 1.2
        offset = pitch * pitch_scale
        w, h = 300, 300
        
        # Dikdörtgen noktaları (Merkeze göre)
        pts = [(-w, offset), (w, offset), (w, h), (-w, h)]
        
        # Dönme (Rotation)
        rad = math.radians(-roll)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        r_pts = []
        for x, y in pts:
            # Döndürülmüş koordinatları merkeze ekle
            rx = x * cos_a - y * sin_a + cx
            ry = x * sin_a + y * cos_a + cy
            r_pts.extend([rx, ry])
            
        # Poligonu çiz
        c.create_polygon(r_pts, fill="#8B4513", outline="")
        # Ufuk Çizgisi (Beyaz)
        c.create_line(r_pts[0], r_pts[1], r_pts[2], r_pts[3], fill="white", width=2)
        
        # 3. MASKELEME (Masking)
        # Göstergenin dışına taşan kısımları arkaplan rengiyle (#202020) kapatıyoruz.
        # Bu kalın bir "simit" gibidir.
        c.create_oval(cx-r, cy-r, cx+r, cy+r, outline="#202020", width=60, tags="mask")
        
        # 4. ÇERÇEVE (Bezel)
        # Maskenin üzerine ince gri bir çerçeve
        c.create_oval(cx-r, cy-r, cx+r, cy+r, outline="#555", width=2, fill="")
        c.create_oval(cx-r, cy-r, cx+r, cy+r, outline="#555", width=3, fill="") # İnce iç sınır
        
        # 5. UÇAK SEMBOLÜ (Sabit)
        wing_color = "#FFD700"
        #c.create_line(cx-20, cy, cx-5, cy, width=2, fill=wing_color)
        #c.create_line(cx+5, cy, cx+20, cy, width=2, fill=wing_color)
        
        c.create_line(cx-40, cy, cx-10, cy, width=4, fill=wing_color)
        c.create_line(cx-10, cy, cx, cy+10, width=4, fill=wing_color)
        c.create_line(cx, cy+10, cx+10, cy, width=4, fill=wing_color)
        c.create_line(cx+10, cy, cx+40, cy, width=4, fill=wing_color)
        c.create_oval(cx-2, cy-2, cx+2, cy+2, fill="red", outline="red")
        
        
        # 5. Pitch Çizgileri
        for p in [10, 20, -10, -20]:
            p_offset = (p + pitch) * pitch_scale
            if -r < p_offset < r:
                lw = 20
                pts = []
                for x, y in [(-lw, p_offset), (lw, p_offset)]:
                    rx = x * cos_a - y * sin_a + cx
                    ry = x * sin_a + y * cos_a + cy
                    pts.extend([rx, ry])
                c.create_line(pts, fill="white", width=1)
                
        # 6. METİN (Roll Bilgisi)
        c.create_text(cx, cy-50, text=f"R:{roll:.0f}", fill="white", font=("Consolas", 8))
        c.create_text(cx, cy+50, text=f"P: {pitch:.1f}°", fill="white", font=("Consolas", 8))


    def draw_airspeed(self, speed):
        #print("Air Speed Göstergesi çiziliyor...")
        c = self.canvas_airspeed; c.delete("all")
        c.create_oval(10, 10, 150, 150, fill="#101010", outline="#555", width=2)
        c.create_text(80, 110, text=f"{int(speed)}", fill="#00ff00", font=("Arial", 18, "bold"))
        c.create_text(80, 130, text="KTS", fill="#00ff00", font=("Arial", 8))
        angle = 135 + (speed / 600) * 270
        rad = math.radians(angle)
        x = 80 + 50 * math.cos(rad); y = 80 + 50 * math.sin(rad)
        c.create_line(80, 80, x, y, fill="red", width=3, arrow=tk.LAST)

    def draw_heading(self, hdg):
        #print("Heading Göstergesi çiziliyor...")
        c = self.canvas_heading; c.delete("all")
        c.create_oval(10, 10, 150, 150, fill="#101010", outline="#555", width=2)
        c.create_text(80, 110, text=f"{int(hdg)}°", fill="#00ff00", font=("Arial", 18, "bold"))
        c.create_text(80, 60, text="▲", fill="yellow", font=("Arial", 12))
        rad = math.radians(-hdg - 90)
        x = 80 + 50 * math.cos(rad); y = 80 + 50 * math.sin(rad)
        c.create_line(80, 80, x, y, fill="red", width=3, arrow=tk.LAST)
        c.create_text(x, y, text="N", fill="red", font=("Arial", 8, "bold"))

    def draw_vsi(self, vz):
        #print("Vertical Speed Göstergesi çiziliyor...")
        c = self.canvas_vsi; c.delete("all")
        c.create_oval(10, 10, 150, 150, fill="#101010", outline="#555", width=2)
        c.create_text(80, 110, text=f"{vz:.1f}", fill="#00ff00", font=("Arial", 18, "bold"))
        val = max(min(vz, 20), -20); angle = 180 - (val/20)*90
        rad = math.radians(angle)
        x = 80 + 50 * math.cos(rad); y = 80 + 50 * math.sin(rad)
        c.create_line(80, 80, x, y, fill="white", width=3, arrow=tk.LAST)

if __name__ == "__main__":
    root = tk.Tk()
    app = CockpitApp(root, FILE_NAME)
    root.mainloop()