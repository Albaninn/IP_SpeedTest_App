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

class AppRede(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Network Monitor Pro")
        self.geometry("1200x800")
        
        self.config_file = "hosts_config.json"
        self.log_file = "log_quedas.txt"
        self.pausado = False  # Estado do monitoramento
        
        self.hosts = self.carregar_hosts()
        self.dados_pings = {h["ip"]: deque([(0, False)] * 60, maxlen=60) for h in self.hosts}
        self.widgets_graficos = {}

        # Layout Principal
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # --- Toolbar Superior ---
        self.toolbar = ctk.CTkFrame(self, height=50, corner_radius=0)
        self.toolbar.grid(row=0, column=0, sticky="ew", padx=5, pady=5)

        # Botões à Esquerda
        ctk.CTkButton(self.toolbar, text="+ Add Host", width=100, command=self.janela_adicionar).pack(side="left", padx=5)
        self.btn_speed = ctk.CTkButton(self.toolbar, text="Speedtest", width=100, command=self.iniciar_speedtest)
        self.btn_speed.pack(side="left", padx=5)
        
        self.lbl_speed = ctk.CTkLabel(self.toolbar, text="S: -- | D: -- | U: --", font=("Arial", 11))
        self.lbl_speed.pack(side="left", padx=15)

        # Botões à DIREITA
        # 1. Botão Pausar/Play
        self.btn_pause = ctk.CTkButton(self.toolbar, text="⏸ Pausar Ping", width=120, fg_color="#a33", hover_color="#c44", command=self.alternar_pausa)
        self.btn_pause.pack(side="right", padx=5)

        # 2. Reset Layout
        ctk.CTkButton(self.toolbar, text="Reset Layout", width=110, fg_color="#444", hover_color="#555", command=self.rebalancear_graficos).pack(side="right", padx=5)

        # --- Área de Gráficos ---
        self.main_pane = tk.PanedWindow(self, orient=tk.VERTICAL, bg="#1a1a1a", sashwidth=8, sashrelief=tk.RAISED)
        self.main_pane.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        self.topo_vazio = tk.Frame(self.main_pane, bg="#1a1a1a")
        self.main_pane.add(self.topo_vazio, height=30) 

        self.container_graficos = tk.Frame(self.main_pane, bg="#242424")
        self.main_pane.add(self.container_graficos)

        self.ips_pane = tk.PanedWindow(self.container_graficos, orient=tk.VERTICAL, bg="#242424", sashwidth=4)
        self.ips_pane.pack(fill="both", expand=True)

        self.atualizar_lista_graficos()
        threading.Thread(target=self.loop_monitoramento, daemon=True).start()

    def alternar_pausa(self):
        self.pausado = not self.pausado
        if self.pausado:
            self.btn_pause.configure(text="▶ Retomar", fg_color="#2a7a2a", hover_color="#3a8a3a")
        else:
            self.btn_pause.configure(text="⏸ Pausar Ping", fg_color="#a33", hover_color="#c44")

    def atualizar_lista_graficos(self):
        for child in self.ips_pane.winfo_children(): 
            child.destroy()
        self.widgets_graficos = {}

        for index, host in enumerate(self.hosts):
            ip, nome = host["ip"], host["nome"]
            container_host = tk.Frame(self.ips_pane, bg="#1e1e1e")
            self.ips_pane.add(container_host, minsize=60, stretch="always")

            header = tk.Frame(container_host, bg="#2b2b2b", height=30)
            header.pack(fill="x", side="top")
            
            btn_frame = tk.Frame(header, bg="#2b2b2b")
            btn_frame.pack(side="left", padx=5)
            
            if index > 0:
                tk.Button(btn_frame, text="▲", bg="#333", fg="white", font=("Arial", 7), 
                          command=lambda i=index: self.mover_host(i, -1), bd=0, width=2).pack(side="left", padx=1)
            
            if index < len(self.hosts) - 1:
                tk.Button(btn_frame, text="▼", bg="#333", fg="white", font=("Arial", 7), 
                          command=lambda i=index: self.mover_host(i, 1), bd=0, width=2).pack(side="left", padx=1)

            texto_titulo = f"{nome.upper()} ({ip})"
            lbl_info = tk.Label(header, text=texto_titulo, bg="#2b2b2b", fg="white", font=("Consolas", 10, "bold"), cursor="hand2")
            lbl_info.pack(side="left", padx=10)
            lbl_info.bind("<Double-Button-1>", lambda e, i=ip: self.editar_nome_host(i))

            lbl_stats = tk.Label(header, text="min: - | max: - | avg: -", bg="#2b2b2b", fg="#aaa", font=("Consolas", 9))
            lbl_stats.pack(side="left", padx=20)

            tk.Button(header, text="X", bg="#922", fg="white", bd=0, command=lambda i=ip: self.remover_host(i)).pack(side="right", padx=5)

            fig, ax = plt.subplots()
            fig.patch.set_facecolor('#1e1e1e')
            ax.set_facecolor('#1e1e1e')
            ax.tick_params(colors='gray', labelsize=8)
            ax.set_xlim(0, 59)
            fig.subplots_adjust(left=0.04, right=1, top=1, bottom=0) 
            
            line, = ax.step(range(60), [0]*60, color='#00d4ff', linewidth=1.5, zorder=2, where='post')
            canvas = FigureCanvasTkAgg(fig, master=container_host)
            canvas.get_tk_widget().pack(fill="both", expand=True)

            self.widgets_graficos[ip] = {"line": line, "ax": ax, "canvas": canvas, "label": lbl_info, "stats": lbl_stats, "vspans": [], "ultimo_status": True}
        
        self.rebalancear_graficos()

    def mover_host(self, index, direcao):
        if hasattr(self, '_movendo') and self._movendo: return
        self._movendo = True

        novo_index = index + direcao
        self.hosts[index], self.hosts[novo_index] = self.hosts[novo_index], self.hosts[index]
        self.salvar_hosts()
        self.atualizar_lista_graficos()

        self.after(300, lambda: setattr(self, '_movendo', False))

    def loop_monitoramento(self):
        while True:
            if not self.pausado:
                for host in list(self.hosts):
                    ip = host["ip"]
                    try:
                        ms = ping(ip, timeout=0.8)
                        is_timeout = ms is None
                        latencia = ms * 1000 if not is_timeout else 0
                    except: is_timeout, latencia = True, 0

                    if ip in self.widgets_graficos:
                        if is_timeout and self.widgets_graficos[ip]["ultimo_status"]:
                            self.registrar_log(f"QUEDA: {host['nome']} ({ip})")
                            self.widgets_graficos[ip]["ultimo_status"] = False
                        elif not is_timeout and not self.widgets_graficos[ip]["ultimo_status"]:
                            self.registrar_log(f"VOLTOU: {host['nome']} ({ip})")
                            self.widgets_graficos[ip]["ultimo_status"] = True

                    if ip in self.dados_pings:
                        self.dados_pings[ip].append((latencia, is_timeout))
                        if ip in self.widgets_graficos:
                            w = self.widgets_graficos[ip]
                            hist = list(self.dados_pings[ip])
                            valores_validos = [d[0] for d in hist if not d[1]]
                            
                            y_data = [d[0] for d in hist]
                            w["line"].set_data(range(len(y_data)), y_data)
                            
                            max_v = max(y_data) if y_data else 1
                            w["ax"].set_ylim(0, max_v * 1.2)
                            w["ax"].set_xlim(0, 59)

                            if valores_validos:
                                v_min, v_max, v_avg = min(valores_validos), max(valores_validos), sum(valores_validos)/len(valores_validos)
                                w["stats"].config(text=f"min: {v_min:.1f} | max: {v_max:.1f} | avg: {v_avg:.1f}")

                            for p in w["vspans"]: p.remove()
                            w["vspans"] = []
                            for i, (v, t) in enumerate(hist):
                                if t: w["vspans"].append(w["ax"].axvspan(i-0.5, i+0.5, color='red', alpha=0.6, zorder=1))
                            
                            txt = f"{host['nome'].upper()} ({ip}) | {latencia:.1f} ms" if not is_timeout else f"🔴 {host['nome'].upper()} ({ip}) | TIMEOUT"
                            w["label"].config(text=txt, fg="#ff5555" if is_timeout else "white")
                            w["canvas"].draw_idle()
            time.sleep(1)

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

    def editar_nome_host(self, ip):
        novo = ctk.CTkInputDialog(text="Novo nome:", title="Editar").get_input()
        if novo:
            for h in self.hosts:
                if h["ip"] == ip: h["nome"] = novo
            self.salvar_hosts(); self.atualizar_lista_graficos()

    def remover_host(self, ip):
        self.hosts = [h for h in self.hosts if h["ip"] != ip]
        self.salvar_hosts(); self.atualizar_lista_graficos()

    def janela_adicionar(self):
        n = ctk.CTkInputDialog(text="Nome:", title="Add").get_input()
        if n:
            i = ctk.CTkInputDialog(text="IP:", title="Add").get_input()
            if i:
                self.hosts.append({"ip": i, "nome": n})
                self.dados_pings[i] = deque([(0, False)] * 60, maxlen=60)
                self.salvar_hosts(); self.atualizar_lista_graficos()

    def iniciar_speedtest(self):
        self.btn_speed.configure(state="disabled", text="Running...")
        threading.Thread(target=self.rodar_speedtest, daemon=True).start()

    def rodar_speedtest(self):
        try:
            st = speedtest.Speedtest(secure=True); st.get_best_server()
            p, d, u = st.results.ping, st.download()/10**6, st.upload()/10**6
            self.lbl_speed.configure(text=f"S: {p:.0f}ms | D: {d:.1f}Mbps | U: {u:.1f}Mbps")
        except: self.lbl_speed.configure(text="Erro no Speedtest")
        finally: self.btn_speed.configure(state="normal", text="Speedtest")

if __name__ == "__main__":
    AppRede().mainloop()