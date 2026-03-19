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
        self.title("Lucas - Network Monitor Pro")
        self.geometry("1200x800")
        
        self.config_file = "hosts_config.json"
        self.log_file = "log_quedas.txt"
        self.hosts = self.carregar_hosts()
        self.dados_pings = {h["ip"]: deque([(0, False)] * 60, maxlen=60) for h in self.hosts}
        self.widgets_graficos = {}

        # Layout
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

        # Botão Reset à DIREITA
        ctk.CTkButton(self.toolbar, text="Reset Layout", width=110, fg_color="#444", hover_color="#555", command=self.rebalancear_graficos).pack(side="right", padx=10)

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

    def atualizar_lista_graficos(self):
        # Limpa apenas na inicialização ou quando um host é REALMENTE deletado/adicionado
        for child in self.ips_pane.winfo_children(): child.destroy()
        self.widgets_graficos = {}

        for index, host in enumerate(self.hosts):
            ip, nome = host["ip"], host["nome"]
            container_host = tk.Frame(self.ips_pane, bg="#1e1e1e")
            # Identificamos o frame com o IP para facilitar a busca
            container_host.ip_referencia = ip 
            self.ips_pane.add(container_host, minsize=60, stretch="always")

            header = tk.Frame(container_host, bg="#2b2b2b", height=30, cursor="fleur")
            header.pack(fill="x", side="top")
            
            # Binds de Arraste (Agora com o evento de Soltar)
            header.bind("<Button-1>", self.iniciar_arraste)
            header.bind("<B1-Motion>", self.movimentar_arraste)
            header.bind("<ButtonRelease-1>", self.finalizar_arraste)
            
            lbl_info = tk.Label(header, text=f"{nome.upper()} ({ip})", bg="#2b2b2b", fg="white", font=("Consolas", 10, "bold"))
            lbl_info.pack(side="left", padx=10)
            # Repassar binds para o label também
            lbl_info.bind("<Button-1>", self.iniciar_arraste)
            lbl_info.bind("<B1-Motion>", self.movimentar_arraste)
            lbl_info.bind("<ButtonRelease-1>", self.finalizar_arraste)
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

    def iniciar_arraste(self, event):
        # Encontra qual container de gráfico foi clicado
        widget = event.widget
        while widget and widget.master != self.ips_pane:
            widget = widget.master
        self.container_selecionado = widget
        if self.container_selecionado:
            self.container_selecionado.config(bg="#3d3d3d") # Feedback visual

    def movimentar_arraste(self, event):
        if not hasattr(self, 'container_selecionado') or not self.container_selecionado:
            return

        # Posição do mouse dentro do painel de IPs
        y_mouse = self.ips_pane.winfo_pointery() - self.ips_pane.winfo_rooty()
        
        # Lista todos os gráficos (panes) atuais
        todos_panes = self.ips_pane.panes()
        
        for p in todos_panes:
            widget_vizinho = self.nametowidget(p)
            if widget_vizinho == self.container_selecionado:
                continue
            
            y_centro_vizinho = widget_vizinho.winfo_y() + (widget_vizinho.winfo_height() / 2)
            
            # Lógica de troca de posição no PanedWindow
            idx_selecionado = todos_panes.index(str(self.container_selecionado))
            idx_vizinho = todos_panes.index(p)

            # Se o mouse passou do centro do vizinho, move o painel
            if y_mouse < y_centro_vizinho and idx_selecionado > idx_vizinho:
                # Move para cima do vizinho
                self.ips_pane.add(self.container_selecionado, before=widget_vizinho)
                break
            elif y_mouse > y_centro_vizinho and idx_selecionado < idx_vizinho:
                # Move para baixo do vizinho
                self.ips_pane.add(self.container_selecionado, after=widget_vizinho)
                break

    def finalizar_arraste(self, event):
        if hasattr(self, 'container_selecionado') and self.container_selecionado:
            self.container_selecionado.config(bg="#1e1e1e")
            
            # Reconstrói a lista self.hosts na nova ordem para salvar
            nova_ordem = []
            for p in self.ips_pane.panes():
                w = self.nametowidget(p)
                ip_w = getattr(w, 'ip_referencia', None)
                for h in self.hosts:
                    if h['ip'] == ip_w:
                        nova_ordem.append(h)
                        break
            
            self.hosts = nova_ordem
            self.salvar_hosts()
            # self.rebalancear_graficos() # Opcional: para garantir que os tamanhos fiquem iguais após soltar

    # --- O restante do código (loop_monitoramento, save, etc) permanece igual ---
    def loop_monitoramento(self):
        while True:
            for host in list(self.hosts):
                ip = host["ip"]
                try:
                    ms = ping(ip, timeout=0.8)
                    is_timeout = ms is None
                    latencia = ms * 1000 if not is_timeout else 0
                except: is_timeout, latencia = True, 0

                if ip in self.widgets_graficos:
                    # Log de Queda
                    if is_timeout and self.widgets_graficos[ip]["ultimo_status"]:
                        self.registrar_log(f"QUEDA: {host['nome']} ({ip})"); self.widgets_graficos[ip]["ultimo_status"] = False
                    elif not is_timeout and not self.widgets_graficos[ip]["ultimo_status"]:
                        self.registrar_log(f"VOLTOU: {host['nome']} ({ip})"); self.widgets_graficos[ip]["ultimo_status"] = True

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
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        with open(self.log_file, "a") as f: f.write(f"[{timestamp}] {mensagem}\n")

    def carregar_hosts(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, "r") as f: return json.load(f)
        return [{"ip": "8.8.8.8", "nome": "Google DNS"}]

    def salvar_hosts(self):
        with open(self.config_file, "w") as f: json.dump(self.hosts, f)

    def rebalancear_graficos(self):
        self.update_idletasks()
        h = self.ips_pane.winfo_height()
        if self.hosts:
            f = h // len(self.hosts)
            for c in self.ips_pane.winfo_children(): self.ips_pane.paneconfig(c, height=f)

    def editar_nome_host(self, ip):
        novo = ctk.CTkInputDialog(text="Novo nome:", title="Editar").get_input()
        if novo:
            for h in self.hosts:
                if h["ip"] == ip: h["nome"] = novo
            self.salvar_hosts(); self.atualizar_lista_graficos()

    def remover_host(self, ip):
        self.hosts = [h for h in self.hosts if h["ip"] != ip]; self.salvar_hosts(); self.atualizar_lista_graficos()

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