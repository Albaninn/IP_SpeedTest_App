import customtkinter as ctk
import speedtest
from ping3 import ping
import threading
import time
import json
import os
import tkinter as tk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import deque

class AppRede(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Lucas - MultiPing Pro (Auto-Equalize)")
        self.geometry("1200x800")
        
        self.config_file = "hosts_config.json"
        self.hosts = self.carregar_hosts()
        self.dados_pings = {h["ip"]: deque([(0, False)] * 60, maxlen=60) for h in self.hosts}
        self.widgets_graficos = {}

        # Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=200)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        ctk.CTkLabel(self.sidebar, text="Config", font=("Arial", 16, "bold")).pack(pady=10)
        ctk.CTkButton(self.sidebar, text="+ Add Host", command=self.janela_adicionar).pack(pady=5, padx=10)
        self.btn_speed = ctk.CTkButton(self.sidebar, text="Speedtest", command=self.iniciar_speedtest)
        self.btn_speed.pack(pady=20, padx=10)
        self.lbl_speed = ctk.CTkLabel(self.sidebar, text="---")
        self.lbl_speed.pack()

        # Área de Trabalho
        self.main_pane = tk.PanedWindow(self, orient=tk.VERTICAL, bg="#1a1a1a", sashwidth=6, sashrelief=tk.RAISED)
        self.main_pane.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        self.topo_vazio = tk.Frame(self.main_pane, bg="#1a1a1a")
        self.main_pane.add(self.topo_vazio, height=100) # Espaço de folga inicial pequeno

        self.container_graficos = tk.Frame(self.main_pane, bg="#242424")
        self.main_pane.add(self.container_graficos)

        self.ips_pane = tk.PanedWindow(self.container_graficos, orient=tk.VERTICAL, bg="#242424", sashwidth=4)
        self.ips_pane.pack(fill="both", expand=True)

        self.atualizar_lista_graficos()
        threading.Thread(target=self.loop_monitoramento, daemon=True).start()

    def carregar_hosts(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, "r") as f: return json.load(f)
        return [{"ip": "8.8.8.8", "nome": "Google DNS"}]

    def salvar_hosts(self):
        with open(self.config_file, "w") as f: json.dump(self.hosts, f)

    def atualizar_lista_graficos(self):
        for child in self.ips_pane.winfo_children():
            child.destroy()
        self.widgets_graficos = {}

        for host in self.hosts:
            ip, nome = host["ip"], host["nome"]
            container_host = tk.Frame(self.ips_pane, bg="#1e1e1e")
            # Adicionamos sem definir height fixa aqui para permitir o cálculo proporcional depois
            self.ips_pane.add(container_host, minsize=50)

            header = tk.Frame(container_host, bg="#333", height=25)
            header.pack(fill="x", side="top")
            
            lbl = tk.Label(header, text=f"{nome.upper()} ({ip})", bg="#333", fg="white", font=("Consolas", 9, "bold"))
            lbl.pack(side="left", padx=10)
            lbl.bind("<Double-Button-1>", lambda e, i=ip: self.editar_nome_host(i))

            btn_del = tk.Button(header, text="X", bg="#922", fg="white", bd=0, command=lambda i=ip: self.remover_host(i))
            btn_del.pack(side="right", padx=5)

            fig, ax = plt.subplots()
            fig.patch.set_facecolor('#1e1e1e')
            ax.set_facecolor('#1e1e1e')
            ax.tick_params(colors='gray', labelsize=7)
            line, = ax.plot([0]*60, color='#1f77b4', linewidth=1.5)
            
            canvas = FigureCanvasTkAgg(fig, master=container_host)
            canvas_widget = canvas.get_tk_widget()
            canvas_widget.pack(fill="both", expand=True)

            self.widgets_graficos[ip] = {"line": line, "ax": ax, "canvas": canvas, "label": lbl, "vspans": []}

        # --- A MÁGICA DA DIVISÃO IGUAL ---
        # Forçamos a atualização da interface para saber o tamanho real do pane
        self.update_idletasks()
        altura_total = self.ips_pane.winfo_height()
        quantidade = len(self.hosts)
        
        if quantidade > 0:
            altura_cada = altura_total // quantidade
            for child in self.ips_pane.winfo_children():
                self.ips_pane.paneconfig(child, height=altura_cada)

    def loop_monitoramento(self):
        while True:
            for host in self.hosts:
                ip = host["ip"]
                ms = ping(ip, timeout=1)
                is_timeout = ms is None
                latencia = ms * 1000 if not is_timeout else 0
                
                if ip in self.dados_pings:
                    self.dados_pings[ip].append((latencia, is_timeout))
                    if ip in self.widgets_graficos:
                        w = self.widgets_graficos[ip]
                        hist = list(self.dados_pings[ip])
                        w["line"].set_ydata([d[0] for d in hist])
                        
                        for p in w["vspans"]: p.remove()
                        w["vspans"] = []
                        for i, (val, timeout) in enumerate(hist):
                            if timeout:
                                span = w["ax"].axvspan(i-0.5, i+0.5, color='red', alpha=0.6)
                                w["vspans"].append(span)

                        w["label"].config(text=f"{host['nome'].upper()} | {latencia:.1f} ms" if not is_timeout else f"🔴 {host['nome'].upper()} | TIMEOUT")
                        w["ax"].relim(); w["ax"].autoscale_view(); w["canvas"].draw_idle()
            time.sleep(1)

    def editar_nome_host(self, ip):
        dialog = ctk.CTkInputDialog(text=f"Novo nome:", title="Editar")
        novo = dialog.get_input()
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
        self.btn_speed.configure(state="disabled")
        threading.Thread(target=self.rodar_speedtest, daemon=True).start()

    def rodar_speedtest(self):
        try:
            st = speedtest.Speedtest(secure=True); st.get_best_server()
            self.lbl_speed.configure(text=f"D: {st.download()/10**6:.1f}\nU: {st.upload()/10**6:.1f}")
        except: self.lbl_speed.configure(text="Erro")
        finally: self.btn_speed.configure(state="normal")

if __name__ == "__main__":
    app = AppRede()
    app.mainloop()