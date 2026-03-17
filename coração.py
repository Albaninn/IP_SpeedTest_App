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
        self.title("Lucas - Network Monitor Pro")
        self.geometry("900x600")

        # Dados para o gráfico (últimos 30 pings)
        self.historico_ping = deque([0] * 30, maxlen=30)
        self.lista_ips = ["8.8.8.8", "google.com", "1.1.1.1"]
        
        # --- Layout Principal (Grid) ---
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar (Pings em texto e Speedtest)
        self.sidebar = ctk.CTkFrame(self, width=300, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        self.label_lista = ctk.CTkLabel(self.sidebar, text="Monitor de IPs", font=("Arial", 16, "bold"))
        self.label_lista.pack(pady=10)

        self.txt_monitor = ctk.CTkTextbox(self.sidebar, width=250, height=200)
        self.txt_monitor.pack(pady=5)

        self.btn_speed = ctk.CTkButton(self.sidebar, text="Iniciar Speedtest", command=self.iniciar_speedtest)
        self.btn_speed.pack(pady=20)
        
        self.lbl_speed = ctk.CTkLabel(self.sidebar, text="Aguardando...", wraplength=250)
        self.lbl_speed.pack()

        # Área do Gráfico
        self.frame_grafico = ctk.CTkFrame(self)
        self.frame_grafico.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        
        self.fig, self.ax = plt.subplots(figsize=(5, 4), dpi=100)
        self.fig.patch.set_facecolor('#2b2b2b') # Cor de fundo do gráfico (dark mode)
        self.ax.set_facecolor('#2b2b2b')
        self.ax.tick_params(colors='white')
        self.line, = self.ax.plot(self.historico_ping, color='#1f538d', linewidth=2)
        self.ax.set_ylim(0, 200) # Limite inicial de 200ms
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.frame_grafico)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

        # Threads
        threading.Thread(target=self.loop_monitoramento, daemon=True).start()

    def loop_monitoramento(self):
        while True:
            relatorio = ""
            for i, host in enumerate(self.lista_ips):
                ms = ping(host)
                latencia = ms * 1000 if ms else 0
                status = f"{latencia:.1f} ms" if ms else "🔴 TIMEOUT"
                relatorio += f"{host[:15]:<15} | {status}\n"
                
                # O primeiro IP da lista vai para o gráfico
                if i == 0:
                    self.historico_ping.append(latencia)
            
            self.atualizar_interface(relatorio)
            time.sleep(1)

    def atualizar_interface(self, relatorio):
        # Atualiza texto
        self.txt_monitor.delete("1.0", "end")
        self.txt_monitor.insert("1.0", relatorio)
        
        # Atualiza gráfico
        self.line.set_ydata(self.historico_ping)
        self.ax.relim()
        self.ax.autoscale_view(scalex=False, scaley=True)
        self.canvas.draw()

    def iniciar_speedtest(self):
        self.lbl_speed.configure(text="Iniciando Speedtest...\n(Isso causará pico no gráfico)")
        self.btn_speed.configure(state="disabled")
        threading.Thread(target=self.rodar_speedtest, daemon=True).start()

    def rodar_speedtest(self):
        try:
            # Solução para o erro 403: Forçar um secure=True ou usar o CLI diretamente
            st = speedtest.Speedtest(secure=True) 
            st.get_best_server()
            d = st.download() / 10**6
            u = st.upload() / 10**6
            self.lbl_speed.configure(text=f"Download: {d:.2f} Mbps\nUpload: {u:.2f} Mbps")
        except Exception as e:
            self.lbl_speed.configure(text=f"Erro: Speedtest indisponível no momento.\n{e}")
        finally:
            self.btn_speed.configure(state="normal")

if __name__ == "__main__":
    app = AppRede()
    app.mainloop()