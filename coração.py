import customtkinter as ctk
import speedtest
from ping3 import ping
import threading
import time
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import deque

class AppRede(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Lucas - MultiPing & Speedtest")
        self.geometry("1000x800")

        # Configurações de dados
        self.lista_ips = ["8.8.8.8", "google.com", "192.168.85.1", "201.148.84.138"]
        self.dados_pings = {ip: deque([0] * 40, maxlen=40) for ip in self.lista_ips}
        self.widgets_graficos = {}

        # --- Layout ---
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=250)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        ctk.CTkLabel(self.sidebar, text="Speedtest", font=("Arial", 16, "bold")).pack(pady=10)
        self.btn_speed = ctk.CTkButton(self.sidebar, text="Iniciar Teste", command=self.iniciar_speedtest)
        self.btn_speed.pack(pady=5)
        self.lbl_speed = ctk.CTkLabel(self.sidebar, text="---", font=("Consolas", 12))
        self.lbl_speed.pack(pady=10)

        # Área de Gráficos (Scrollable)
        self.scroll_frame = ctk.CTkScrollableFrame(self, label_text="Gráficos de Latência")
        self.scroll_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        # Criar os mini-gráficos iniciais
        self.inicializar_graficos()

        # Iniciar threads
        threading.Thread(target=self.loop_monitoramento, daemon=True).start()

    def inicializar_graficos(self):
        for ip in self.lista_ips:
            frame_item = ctk.CTkFrame(self.scroll_frame)
            frame_item.pack(fill="x", pady=5, padx=5)

            # Label do IP e Latência Atual
            lbl_info = ctk.CTkLabel(frame_item, text=f"HOST: {ip} | Atual: --", font=("Consolas", 12, "bold"))
            lbl_info.pack(side="top", anchor="w", padx=10)

            # Matplotlib Figure
            fig, ax = plt.subplots(figsize=(8, 1.5), dpi=80)
            fig.patch.set_facecolor('#1e1e1e')
            ax.set_facecolor('#1e1e1e')
            ax.tick_params(colors='gray', labelsize=8)
            ax.grid(True, color='#333333', linestyle='--')
            
            line, = ax.plot(list(self.dados_pings[ip]), color='#1f77b4', linewidth=1.5)
            
            canvas = FigureCanvasTkAgg(fig, master=frame_item)
            canvas_widget = canvas.get_tk_widget()
            canvas_widget.pack(fill="x", expand=True)

            self.widgets_graficos[ip] = {
                "line": line,
                "ax": ax,
                "canvas": canvas,
                "label": lbl_info
            }

    def loop_monitoramento(self):
        while True:
            for ip in self.lista_ips:
                ms = ping(ip)
                latencia = ms * 1000 if ms else 0
                
                self.dados_pings[ip].append(latencia)
                
                # Atualiza os componentes visuais de cada IP
                if ip in self.widgets_graficos:
                    w = self.widgets_graficos[ip]
                    w["line"].set_ydata(list(self.dados_pings[ip]))
                    
                    # Escala automática (Auto-scale Y)
                    w["ax"].relim()
                    w["ax"].autoscale_view()
                    
                    # Atualiza Label com cor (Vermelho se TIMEOUT)
                    txt_status = f"HOST: {ip:<20} | {latencia:.1f} ms" if ms else f"HOST: {ip:<20} | 🔴 TIMEOUT"
                    w["label"].configure(text=txt_status)
                    
            self.refresh_canvases()
            time.sleep(1)

    def refresh_canvases(self):
        # Redesenha todos os canvases
        for ip in self.lista_ips:
            if ip in self.widgets_graficos:
                self.widgets_graficos[ip]["canvas"].draw_idle()

    def iniciar_speedtest(self):
        self.btn_speed.configure(state="disabled", text="Testando...")
        threading.Thread(target=self.rodar_speedtest, daemon=True).start()

    def rodar_speedtest(self):
        try:
            st = speedtest.Speedtest(secure=True)
            st.get_best_server()
            d = st.download() / 10**6
            u = st.upload() / 10**6
            self.lbl_speed.configure(text=f"Download: {d:.1f} Mbps\nUpload: {u:.1f} Mbps")
        except Exception as e:
            self.lbl_speed.configure(text="Erro Speedtest")
        finally:
            self.btn_speed.configure(state="normal", text="Iniciar Teste")

if __name__ == "__main__":
    app = AppRede()
    app.mainloop()