import customtkinter as ctk
import speedtest
from ping3 import ping
import threading
import time
import json
import os
import tkinter as tk
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import deque
import matplotlib.dates as mdates
import matplotlib.ticker as mticker

class AppRede(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Network Monitor Pro")
        self.geometry("1300x850")
        
        # Arquivos e Estados
        self.config_file = "hosts_config.json"
        self.log_file = "log_quedas.txt"
        self.pausado = False
        self.intervalo_ping = 1.0  # Tempo entre disparos
        self.janela_minutos = 1    # Tempo visível no gráfico
        
        self.hosts = self.carregar_hosts()
        # Cada deque guarda: (latencia, is_timeout, timestamp)
        self.dados_pings = {h["ip"]: deque([(0, False, time.time())] * (self.janela_minutos * 60), 
                            maxlen=(self.janela_minutos * 60)) for h in self.hosts}
        self.widgets_graficos = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- Toolbar Superior ---
        self.toolbar = ctk.CTkFrame(self, height=60, corner_radius=0)
        self.toolbar.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        # Esquerda
        ctk.CTkButton(self.toolbar, text="+ Host", width=70, command=self.janela_adicionar).pack(side="left", padx=5)
        self.btn_speed = ctk.CTkButton(self.toolbar, text="Speedtest", width=90, command=self.iniciar_speedtest)
        self.btn_speed.pack(side="left", padx=5)
        
        # Controles de Tempo
        ctk.CTkLabel(self.toolbar, text="Ping (s):", font=("Arial", 11)).pack(side="left", padx=(15, 2))
        self.entry_ping = ctk.CTkEntry(self.toolbar, width=45); self.entry_ping.insert(0, "1"); self.entry_ping.pack(side="left", padx=2)
        
        ctk.CTkLabel(self.toolbar, text="Gráfico (min):", font=("Arial", 11)).pack(side="left", padx=(10, 2))
        self.entry_graph = ctk.CTkEntry(self.toolbar, width=45); self.entry_graph.insert(0, "1"); self.entry_graph.pack(side="left", padx=2)
        
        ctk.CTkButton(self.toolbar, text="Aplicar", width=60, fg_color="#555", command=self.aplicar_ajustes).pack(side="left", padx=5)

        # Direita
        self.btn_pause = ctk.CTkButton(self.toolbar, text="⏸ Pausar", width=100, fg_color="#a33", hover_color="#c44", command=self.alternar_pausa)
        self.btn_pause.pack(side="right", padx=5)
        
        ctk.CTkButton(self.toolbar, text="Reset Layout", width=110, fg_color="#444", hover_color="#555", command=self.rebalancear_graficos).pack(side="right", padx=5)

        self.lbl_speed = ctk.CTkLabel(self.toolbar, text="S: -- | D: -- | U: --", font=("Arial", 11))
        self.lbl_speed.pack(side="right", padx=20)

        # --- Área de Gráficos ---
        self.main_pane = tk.PanedWindow(self, orient=tk.VERTICAL, bg="#1a1a1a", sashwidth=8, sashrelief=tk.RAISED)
        self.main_pane.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        self.container_graficos = tk.Frame(self.main_pane, bg="#242424")
        self.main_pane.add(self.container_graficos)
        
        self.ips_pane = tk.PanedWindow(self.container_graficos, orient=tk.VERTICAL, bg="#242424", sashwidth=4)
        self.ips_pane.pack(fill="both", expand=True)

        self.atualizar_lista_graficos()
        
        # Início das Threads
        threading.Thread(target=self.thread_pings, daemon=True).start()
        threading.Thread(target=self.thread_atualiza_grafico, daemon=True).start()

    def aplicar_ajustes(self):
        try:
            self.intervalo_ping = float(self.entry_ping.get())
            novo_min = int(self.entry_graph.get())
            if novo_min != self.janela_minutos:
                self.janela_minutos = novo_min
                novo_tam = self.janela_minutos * 60
                for ip in self.dados_pings:
                    self.dados_pings[ip] = deque(list(self.dados_pings[ip]), maxlen=novo_tam)
                self.atualizar_lista_graficos()
        except: pass

    def alternar_pausa(self):
        self.pausado = not self.pausado
        self.btn_pause.configure(text="▶ Retomar" if self.pausado else "⏸ Pausar", 
                                 fg_color="#2a7a2a" if self.pausado else "#a33")

    def thread_pings(self):
        while True:
            if not self.pausado:
                for host in list(self.hosts):
                    ip = host["ip"]
                    try:
                        ms = ping(ip, timeout=0.8)
                        is_timeout = ms is None
                        latencia = ms * 1000 if not is_timeout else 0
                        host['ultima_latencia'] = (latencia, is_timeout)
                    except: pass
            time.sleep(max(0.1, self.intervalo_ping))

    def thread_atualiza_grafico(self):
        while True:
            agora = time.time()
            for host in list(self.hosts):
                ip = host["ip"]
                dado_ping = host.get('ultima_latencia', (0, False))
                # Se pausado, envia latência 0 mas mantém o tempo rodando
                final_dado = (dado_ping[0] if not self.pausado else 0, 
                              dado_ping[1] if not self.pausado else False, 
                              agora)
                
                if ip in self.dados_pings:
                    self.dados_pings[ip].append(final_dado)
                    self.atualizar_widget_grafico(ip, final_dado)
            time.sleep(1)

    def atualizar_widget_grafico(self, ip, ultimo_dado):
        if ip in self.widgets_graficos:
            w = self.widgets_graficos[ip]
            hist = list(self.dados_pings[ip])
            
            y_data = [d[0] for d in hist]
            x_data = [datetime.fromtimestamp(d[2]) for d in hist]
            
            w["line"].set_data(x_data, y_data)
            
            # Ajuste dinâmico Y
            max_v = max(y_data) if any(y_data) else 50
            w["ax"].set_ylim(0, max_v * 1.2)
            
            # Ajuste dinâmico X (Tempo)
            w["ax"].set_xlim(x_data[0], x_data[-1])
            w["ax"].xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
            w["ax"].xaxis.set_major_locator(mticker.MaxNLocator(6))

            # Stats no Header
            validos = [d[0] for d in hist if not d[1] and d[0] > 0]
            if validos:
                w["stats"].config(text=f"min: {min(validos):.1f} | max: {max(validos):.1f} | avg: {sum(validos)/len(validos):.1f}")

            # Desenho das barras de Timeout (Vermelhas)
            for p in w["vspans"]: p.remove()
            w["vspans"] = []
            for i, (v, t, ts) in enumerate(hist):
                if t:
                    dt = datetime.fromtimestamp(ts)
                    # Barra vertical na posição exata do tempo
                    w["vspans"].append(w["ax"].axvspan(dt, dt, color='red', alpha=0.5))
            
            lat, timeout, _ = ultimo_dado
            nome_h = next((h['nome'] for h in self.hosts if h['ip'] == ip), "HOST")
            
            # Logs de Queda
            if timeout and w["ultimo_status"]:
                self.registrar_log(f"QUEDA: {nome_h} ({ip})")
                w["ultimo_status"] = False
            elif not timeout and not w["ultimo_status"]:
                self.registrar_log(f"VOLTOU: {nome_h} ({ip})")
                w["ultimo_status"] = True

            txt = f"{nome_h.upper()} ({ip}) | {lat:.1f} ms" if not timeout else f"🔴 {nome_h.upper()} ({ip}) | TIMEOUT"
            if self.pausado: txt = f"⏸ {nome_h.upper()} ({ip}) - PAUSADO"
            
            w["label"].config(text=txt, fg="#ff5555" if timeout else "white")
            w["canvas"].draw_idle()

    def atualizar_lista_graficos(self):
        for child in self.ips_pane.winfo_children(): child.destroy()
        self.widgets_graficos = {}

        for index, host in enumerate(self.hosts):
            ip, nome = host["ip"], host["nome"]
            container = tk.Frame(self.ips_pane, bg="#1e1e1e")
            self.ips_pane.add(container, minsize=115, stretch="always") 

            header = tk.Frame(container, bg="#2b2b2b", height=30); header.pack(fill="x")
            btn_f = tk.Frame(header, bg="#2b2b2b"); btn_f.pack(side="left", padx=5)
            
            if index > 0:
                tk.Button(btn_f, text="▲", bg="#333", fg="white", font=("Arial", 7), command=lambda i=index: self.mover_host(i, -1), bd=0).pack(side="left", padx=1)
            if index < len(self.hosts)-1:
                tk.Button(btn_f, text="▼", bg="#333", fg="white", font=("Arial", 7), command=lambda i=index: self.mover_host(i, 1), bd=0).pack(side="left", padx=1)

            lbl_info = tk.Label(header, text=f"{nome.upper()} ({ip})", bg="#2b2b2b", fg="white", font=("Consolas", 10, "bold"))
            lbl_info.pack(side="left", padx=10)
            lbl_stats = tk.Label(header, text="min: - | max: - | avg: -", bg="#2b2b2b", fg="#aaa", font=("Consolas", 9)); lbl_stats.pack(side="left", padx=20)
            tk.Button(header, text="X", bg="#922", fg="white", bd=0, command=lambda i=ip: self.remover_host(i)).pack(side="right", padx=5)

            # Matplotlib Figure
            fig, ax = plt.subplots()
            fig.patch.set_facecolor('#1e1e1e')
            ax.set_facecolor('#1e1e1e')
            ax.grid(True, axis='y', color='#333', linestyle='--', linewidth=0.5)
            ax.tick_params(colors='gray', labelsize=8)
            
            # Margens: Left=0.08 para ver os MS, Bottom=0.25 para ver as Horas
            fig.subplots_adjust(left=0.08, right=0.98, top=0.92, bottom=0.25) 
            
            # Linha em estilo STEP (Degrau)
            line, = ax.step([], [], color='#00d4ff', linewidth=1.5, zorder=2, where='post')
            
            canvas = FigureCanvasTkAgg(fig, master=container)
            canvas.get_tk_widget().pack(fill="both", expand=True)

            self.widgets_graficos[ip] = {
                "line": line, "ax": ax, "canvas": canvas, "label": lbl_info, 
                "stats": lbl_stats, "vspans": [], "ultimo_status": True
            }
        self.rebalancear_graficos()

    def mover_host(self, index, direcao):
        self.hosts[index], self.hosts[index+direcao] = self.hosts[index+direcao], self.hosts[index]
        self.salvar_hosts(); self.atualizar_lista_graficos()

    def registrar_log(self, mensagem):
        try:
            timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            with open(self.log_file, "a") as f: f.write(f"[{timestamp}] {mensagem}\n")
        except: pass

    def carregar_hosts(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f: return json.load(f)
            except: pass
        return [{"ip": "8.8.8.8", "nome": "Google DNS"}]

    def salvar_hosts(self):
        try:
            with open(self.config_file, "w") as f: json.dump(self.hosts, f)
        except: pass

    def rebalancear_graficos(self):
        self.update_idletasks()
        h = self.ips_pane.winfo_height()
        if self.hosts:
            f = h // len(self.hosts)
            for c in self.ips_pane.winfo_children(): 
                try: self.ips_pane.paneconfig(c, height=f)
                except: pass

    def remover_host(self, ip):
        self.hosts = [h for h in self.hosts if h["ip"] != ip]
        self.salvar_hosts(); self.atualizar_lista_graficos()

    def janela_adicionar(self):
        n = ctk.CTkInputDialog(text="Nome:", title="Add").get_input()
        i = ctk.CTkInputDialog(text="IP:", title="Add").get_input()
        if n and i:
            self.hosts.append({"ip": i, "nome": n})
            self.dados_pings[i] = deque([(0, False, time.time())] * (self.janela_minutos * 60), maxlen=(self.janela_minutos * 60))
            self.salvar_hosts(); self.atualizar_lista_graficos()

    def iniciar_speedtest(self):
        self.btn_speed.configure(state="disabled", text="Calculando...")
        threading.Thread(target=self.rodar_speedtest, daemon=True).start()

    def rodar_speedtest(self):
        try:
            st = speedtest.Speedtest(secure=True); st.get_best_server()
            p, d, u = st.results.ping, st.download()/10**6, st.upload()/10**6
            self.lbl_speed.configure(text=f"S: {p:.0f}ms | D: {d:.1f}Mbps | U: {u:.1f}Mbps")
        except: self.lbl_speed.configure(text="Erro Speedtest")
        finally: self.btn_speed.configure(state="normal", text="Speedtest")

if __name__ == "__main__":
    AppRede().mainloop()

