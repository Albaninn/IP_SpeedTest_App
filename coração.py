import customtkinter as ctk
import speedtest
from ping3 import ping
import threading
import time
import json
import os
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from collections import deque

class AppRede(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Lucas - MultiPing Pro v2")
        self.geometry("1100x850")
        
        # Caminho do arquivo de salvamento
        self.config_file = "hosts_config.json"
        self.hosts = self.carregar_hosts()
        
        # O deque agora armazena tuplas: (latencia, is_timeout)
        self.dados_pings = {h["ip"]: deque([(0, False)] * 60, maxlen=60) for h in self.hosts}
        self.widgets_graficos = {}

        # --- Layout ---
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=250)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        ctk.CTkLabel(self.sidebar, text="Hosts", font=("Arial", 16, "bold")).pack(pady=10)
        ctk.CTkButton(self.sidebar, text="+ Adicionar Host", command=self.janela_adicionar).pack(pady=5, padx=10)
        
        ctk.CTkLabel(self.sidebar, text="Speedtest", font=("Arial", 16, "bold")).pack(pady=20)
        self.btn_speed = ctk.CTkButton(self.sidebar, text="Iniciar Teste", command=self.iniciar_speedtest)
        self.btn_speed.pack(pady=5)
        self.lbl_speed = ctk.CTkLabel(self.sidebar, text="---")
        self.lbl_speed.pack(pady=10)

        self.scroll_frame = ctk.CTkScrollableFrame(self, label_text="Monitoramento Detalhado")
        self.scroll_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)

        self.atualizar_lista_graficos()
        threading.Thread(target=self.loop_monitoramento, daemon=True).start()

    def carregar_hosts(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, "r") as f:
                return json.load(f)
        return [{"ip": "8.8.8.8", "nome": "Google DNS"}]

    def salvar_hosts(self):
        with open(self.config_file, "w") as f:
            json.dump(self.hosts, f)

    def atualizar_lista_graficos(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        self.widgets_graficos = {}

        for host in self.hosts:
            ip, nome = host["ip"], host["nome"]
            frame_item = ctk.CTkFrame(self.scroll_frame)
            frame_item.pack(fill="x", pady=8, padx=5)

            header = ctk.CTkFrame(frame_item, fg_color="transparent")
            header.pack(fill="x", padx=10)
            
            # Label do Nome - Agora com Bind de clique duplo
            lbl_info = ctk.CTkLabel(header, text=f"{nome.upper()} ({ip})", font=("Consolas", 13, "bold"), cursor="hand2")
            lbl_info.pack(side="left", pady=5)
            # Bind: Clique duplo (Button-1 é o esquerdo)
            lbl_info.bind("<Double-Button-1>", lambda event, i=ip: self.editar_nome_host(i))
            
            # Dica visual rápida
            ctk.CTkLabel(header, text="(clique duplo para editar nome)", font=("Arial", 10, "italic"), text_color="gray").pack(side="left", padx=10)

            btn_del = ctk.CTkButton(header, text="X", width=30, fg_color="#ac0000", command=lambda i=ip: self.remover_host(i))
            btn_del.pack(side="right")

            # --- Configuração do Gráfico (Mantendo a lógica das vspans) ---
            fig, ax = plt.subplots(figsize=(10, 1.8), dpi=85)
            fig.patch.set_facecolor('#1e1e1e')
            ax.set_facecolor('#1e1e1e')
            ax.tick_params(colors='gray', labelsize=7)
            
            line, = ax.plot([d[0] for d in self.dados_pings[ip]], color='#1f77b4', linewidth=1.5)
            
            canvas = FigureCanvasTkAgg(fig, master=frame_item)
            canvas.get_tk_widget().pack(fill="x", expand=True)

            self.widgets_graficos[ip] = {"line": line, "ax": ax, "canvas": canvas, "label": lbl_info, "vspans": []}

    def editar_nome_host(self, ip):
        # Janela para pedir o novo nome
        dialog = ctk.CTkInputDialog(text=f"Novo nome para o IP {ip}:", title="Editar Nome")
        novo_nome = dialog.get_input()
        
        if novo_nome:
            # Atualiza na lista self.hosts
            for host in self.hosts:
                if host["ip"] == ip:
                    host["nome"] = novo_nome
                    break
            
            self.salvar_hosts()
            self.atualizar_lista_graficos() # Recarrega a UI para mostrar o novo nome
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        self.widgets_graficos = {}

        for host in self.hosts:
            ip, nome = host["ip"], host["nome"]
            frame_item = ctk.CTkFrame(self.scroll_frame)
            frame_item.pack(fill="x", pady=8, padx=5)

            header = ctk.CTkFrame(frame_item, fg_color="transparent")
            header.pack(fill="x", padx=10)
            
            lbl_info = ctk.CTkLabel(header, text=f"{nome.upper()} ({ip})", font=("Consolas", 13, "bold"))
            lbl_info.pack(side="left", pady=5)
            
            btn_del = ctk.CTkButton(header, text="X", width=30, fg_color="#aa3333", command=lambda i=ip: self.remover_host(i))
            btn_del.pack(side="right")

            fig, ax = plt.subplots(figsize=(10, 1.8), dpi=85)
            fig.patch.set_facecolor('#1e1e1e')
            ax.set_facecolor('#1e1e1e')
            ax.tick_params(colors='gray', labelsize=7)
            
            line, = ax.plot([d[0] for d in self.dados_pings[ip]], color='#1f77b4', linewidth=1.5)
            
            canvas = FigureCanvasTkAgg(fig, master=frame_item)
            canvas.get_tk_widget().pack(fill="x", expand=True)

            self.widgets_graficos[ip] = {"line": line, "ax": ax, "canvas": canvas, "label": lbl_info, "vspans": []}

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
                    historico = list(self.dados_pings[ip])
                    
                    # Atualiza a linha azul
                    w["line"].set_ydata([d[0] for d in historico])
                    
                    # Gerencia os blocos vermelhos (vspans)
                    for p in w["vspans"]:
                        p.remove()
                    w["vspans"] = []

                    # Percorre o histórico e desenha blocos onde is_timeout é True
                    for i, (val, timeout) in enumerate(historico):
                        if timeout:
                            span = w["ax"].axvspan(i-0.5, i+0.5, color='red', alpha=0.6)
                            w["vspans"].append(span)

                    # Label de status
                    if is_timeout:
                        w["label"].configure(text=f"🔴 {host['nome'].upper()} | TIMEOUT", text_color="#ff5555")
                    else:
                        w["label"].configure(text=f"{host['nome'].upper()} | {latencia:.1f} ms", text_color="white")

                    w["ax"].relim()
                    w["ax"].autoscale_view()
            
            try:
                for ip in self.widgets_graficos:
                    self.widgets_graficos[ip]["canvas"].draw_idle()
            except: pass
            time.sleep(1)

    def janela_adicionar(self):
        dialog_nome = ctk.CTkInputDialog(text="Nome do Host:", title="Adicionar")
        nome = dialog_nome.get_input()
        if nome:
            dialog_ip = ctk.CTkInputDialog(text="IP ou URL:", title="Adicionar")
            ip = dialog_ip.get_input()
            if ip:
                self.hosts.append({"ip": ip, "nome": nome})
                self.dados_pings[ip] = deque([(0, False)] * 60, maxlen=60)
                self.salvar_hosts()
                self.atualizar_lista_graficos()

    def remover_host(self, ip):
        self.hosts = [h for h in self.hosts if h["ip"] != ip]
        self.salvar_hosts()
        self.atualizar_lista_graficos()

    def iniciar_speedtest(self):
        self.btn_speed.configure(state="disabled")
        threading.Thread(target=self.rodar_speedtest, daemon=True).start()

    def rodar_speedtest(self):
        try:
            st = speedtest.Speedtest(secure=True)
            st.get_best_server()
            self.lbl_speed.configure(text=f"Down: {st.download()/10**6:.1f} | Up: {st.upload()/10**6:.1f}")
        except: self.lbl_speed.configure(text="Erro")
        finally: self.btn_speed.configure(state="normal")

if __name__ == "__main__":
    app = AppRede()
    app.mainloop()