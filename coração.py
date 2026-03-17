import customtkinter as ctk
import speedtest
from ping3 import ping
import threading
import time

class AppRede(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Meu MultiPing & Speedtest")
        self.geometry("500x400")

        # UI - Título
        self.label = ctk.CTkLabel(self, text="Monitor de Rede", font=("Roboto", 20, "bold"))
        self.label.pack(pady=10)

        # UI - Exibição de IPs
        self.status_pings = ctk.CTkTextbox(self, width=400, height=150)
        self.status_pings.pack(pady=10)

        # UI - Speedtest
        self.btn_speed = ctk.CTkButton(self, text="Rodar Speedtest", command=self.iniciar_speedtest_thread)
        self.btn_speed.pack(pady=10)
        
        self.label_speed = ctk.CTkLabel(self, text="Aguardando teste...")
        self.label_speed.pack()

        # Iniciar monitoramento de IPs em segundo plano
        self.ips = ["8.8.8.8", "1.1.1.1", "google.com"]
        threading.Thread(target=self.atualizar_pings, daemon=True).start()

    def atualizar_pings(self):
        while True:
            texto_final = ""
            for ip in self.ips:
                ms = ping(ip)
                status = f"{ms*1000:.1f}ms" if ms else "TIMEOUT"
                texto_final += f"📍 {ip}: {status}\n"
            
            self.status_pings.delete("1.0", "end")
            self.status_pings.insert("1.0", texto_final)
            time.sleep(2) # Atualiza a cada 2 segundos

    def iniciar_speedtest_thread(self):
        self.label_speed.configure(text="Testando... (Isso pode afetar o Ping)")
        self.btn_speed.configure(state="disabled")
        threading.Thread(target=self.rodar_speedtest, daemon=True).start()

    def rodar_speedtest(self):
        try:
            st = speedtest.Speedtest()
            st.get_best_server()
            down = st.download() / 10**6
            up = st.upload() / 10**6
            self.label_speed.configure(text=f"Download: {down:.2f} Mbps | Upload: {up:.2f} Mbps")
        except:
            self.label_speed.configure(text="Erro ao testar velocidade.")
        finally:
            self.btn_speed.configure(state="normal")

if __name__ == "__main__":
    app = AppRede()
    app.mainloop()