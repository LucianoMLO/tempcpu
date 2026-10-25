"""TempCPU — temperatura do processador em tempo real, gráfico por zonas e diagnóstico.

Uso:
    pythonw app.py            fica na área de notificação (ícone com a temperatura); clique abre a janela
    pythonw app.py --janela   idem, já com a janela aberta
    python app.py --cli       imprime uma leitura por intervalo no terminal (Ctrl+C sai)
"""
from __future__ import annotations

import gc
import queue
import sys
import threading
import time
import tkinter as tk
from collections import deque
from pathlib import Path

from diagnostico import Coletor, Item, Retrato, analisar
from historico import Gravador, Historico
from sensores import DetectorParada, LeitorTemperatura, Leitura, SemLeitura, eh_admin
import sistema
from dicas import Dica, texto_dos_termos
from tema import (BORDA, CARTAO, CINZA_ICONE, FONTE, FUNDO, GRADE, LINHA, PRIORIDADE, SUAVE, TEXTO, ZONAS,
                  br, cartao, zona_de)

PASTA = Path(__file__).resolve().parent

TJMAX_PADRAO = 105.0  # Ryzen 7 4800HS; usado só se o firmware não informar seus limites

CONFIG_PADRAO = {
    "INTERVALO_S": 2.0,    # leitura a cada 2 segundos
    "ALERTA_C": 75.0,      # verde -> amarelo
    "QUENTE_C": 90.0,      # amarelo -> vermelho
    "DANO_C": None,        # vermelho -> crítico. None ("auto") = limite de redução de desempenho do firmware
    "JANELA_MIN": 5.0,     # minutos de histórico no gráfico
    "DIAGNOSTICO_S": 4.0,  # intervalo da coleta de processos/energia
    "PARADA_MIN": 3.0,     # leitura ACPI sem mudar por este tempo = parada
    "FAN_ALTA_RPM": 4500.0,  # acima disso a ventoinha conta como rotação alta
    "DIAGNOSTICO_OCULTO_S": 30.0,  # coleta com a janela minimizada (alimenta o histórico)
    "RETENCAO_DIAS": 365.0,  # minutos guardados; resumos por hora/dia/semana/mês ficam para sempre
    "ICONE_ATUALIZA_S": 60.0,  # número do ícone (barra de tarefas e bandeja) a cada tantos segundos, ou já se a faixa mudar
    "SALVAR_PROGRAMAS": 1.0,  # 1 = guarda o nome do programa que mais consome CPU a cada minuto
}


def carregar_config() -> dict:
    """Lê .env (chave=valor) sobre os defaults; sem dependência extra. "auto" = None."""
    config = dict(CONFIG_PADRAO)
    env = PASTA / ".env"
    if env.exists():
        for linha in env.read_text(encoding="utf-8").splitlines():
            linha = linha.strip()
            if not linha or linha.startswith("#") or "=" not in linha:
                continue
            chave, valor = (p.strip() for p in linha.split("=", 1))
            if chave in config:
                if valor.lower() == "auto":
                    config[chave] = None
                    continue
                if valor.lower() in ("sim", "true"):
                    config[chave] = 1.0
                    continue
                if valor.lower() in ("nao", "não", "false"):
                    config[chave] = 0.0
                    continue
                try:
                    config[chave] = float(valor)
                except ValueError:
                    pass
    if config["DANO_C"] is None:
        config["DANO_C"] = TJMAX_PADRAO  # provisório até ler o firmware (App.aplicar_limites_firmware)
        config["DANO_AUTO"] = True
    return config


class App:
    def __init__(self, raiz: tk.Tk, config: dict[str, float]) -> None:
        self.raiz = raiz
        self.cfg = config
        self.intervalo_ms = max(500, int(config["INTERVALO_S"] * 1000))
        pontos = int(config["JANELA_MIN"] * 60 / config["INTERVALO_S"])
        self.historico: deque[float] = deque(maxlen=max(10, pontos))
        self.minimo: float | None = None
        self.maximo: float | None = None
        self.leitor: LeitorTemperatura | None = None
        self.ultima: float | None = None
        self.retrato: Retrato | None = None
        self.erro_diag = ""
        self.detector = DetectorParada(config["PARADA_MIN"])
        self.parada = False
        self.rpm: int | None = None
        self.rpm_novo = False   # True só no tick em que a ventoinha foi lida de fato
        self.asus = None
        self._asus_tentou = -1e9
        self.motivo_sem_fan = ""
        self.desliga_c: float | None = None  # desligamento crítico do firmware
        self.ativo = True                        # monitoramento ligado
        self.visivel = False                     # janela aberta
        self.pedidos: queue.Queue = queue.Queue()  # ações vindas de outras threads (bandeja, 2ª instância)
        self.diag_acordar = threading.Event()    # acorda a coleta de diagnóstico (ex.: ao abrir a janela)
        self.janela_historico = None
        self.janela_lab = None
        self._chave_icone: tuple | None = None
        self._icone_em = -1e9    # quando o ícone foi redesenhado pela última vez (monotonic)
        self._icone_estado: tuple | None = None
        self._fan_em = -1e9      # ventoinha: leitura WMI custa ~7 ms, então a cada 10 s
        self._icone_tk = None
        self._diag_gravado = 0.0
        self.erro_hist = ""
        self.gravador: Gravador | None = None
        try:
            self.hist = Historico(retencao_dias=int(config["RETENCAO_DIAS"]))
            self.hist.limpar()
            self.gravador = Gravador(self.hist, lambda c: zona_de(c, self.cfg),
                                     salvar_programas=bool(config["SALVAR_PROGRAMAS"]))
        except Exception as e:  # sem banco o app continua só mostrando
            self.hist = None
            self.erro_hist = f"Histórico indisponível: {type(e).__name__}: {e}"
        self.inicio_ativo = False
        self.bandeja = None

        raiz.title("TempCPU")
        raiz.configure(bg=FUNDO)
        raiz.geometry("980x620")
        raiz.minsize(820, 540)
        raiz.columnconfigure(0, weight=5, uniform="c")
        raiz.columnconfigure(1, weight=4, uniform="c")
        raiz.rowconfigure(0, weight=1)

        esq = tk.Frame(raiz, bg=FUNDO)
        esq.grid(row=0, column=0, sticky="nsew", padx=(16, 8), pady=16)
        dir_ = tk.Frame(raiz, bg=FUNDO)
        dir_.grid(row=0, column=1, sticky="nsew", padx=(8, 16), pady=16)

        # --- Card da temperatura ---
        card = cartao(esq, "Temperatura do processador")
        card.pack(fill="x")
        linha = tk.Frame(card, bg=CARTAO)
        linha.pack(fill="x")
        self.lbl_valor = tk.Label(linha, text="--,- °C", font=(FONTE, 38, "bold"), bg=CARTAO, fg=TEXTO)
        self.lbl_valor.pack(side="left")
        self.lbl_estado = tk.Label(linha, text="Lendo…", font=(FONTE, 11, "bold"),
                                   bg=GRADE, fg=SUAVE, padx=12, pady=4)
        self.lbl_estado.pack(side="left", padx=14)
        botoes = tk.Frame(linha, bg=CARTAO)  # em duas linhas: três botões não cabem lado a lado no card
        botoes.pack(side="right")
        topo = tk.Frame(botoes, bg=CARTAO)
        topo.pack(anchor="e", pady=(0, 6))
        self.btn_monitor = tk.Button(botoes, text="Pausar monitoramento", command=self.alternar_monitor,
                                     relief="flat", bg=GRADE, fg=TEXTO, activebackground=BORDA,
                                     font=(FONTE, 9), padx=10, pady=3, cursor="hand2", bd=0)
        self.btn_monitor.pack(anchor="e")
        self.btn_hist = tk.Button(topo, text="Histórico", command=self.abrir_historico, relief="flat",
                                  bg=GRADE, fg=TEXTO, activebackground=BORDA, font=(FONTE, 9), padx=10, pady=3,
                                  cursor="hand2", bd=0)
        self.btn_hist.pack(side="right")
        Dica(self.btn_hist, "Gráfico do histórico gravado: temperatura, uso, frequência, ventoinha e tomada, por minuto, hora ou dia.")
        self.btn_lab = tk.Button(topo, text="Laboratório", command=self.abrir_laboratorio, relief="flat",
                                 bg=GRADE, fg=TEXTO, activebackground=BORDA, font=(FONTE, 9), padx=10, pady=3,
                                 cursor="hand2", bd=0)
        self.btn_lab.pack(side="right", padx=(0, 8))
        self.btn_lab.bind("<Button-3>", self.menu_laboratorio)
        Dica(self.btn_lab, "Lições opcionais de machine learning com o seu histórico. Clique com o botão direito para remover.")
        self.barra = tk.Canvas(card, bg=CARTAO, highlightthickness=0, height=40)
        self.barra.pack(fill="x", pady=(6, 2))
        self.barra.bind("<Configure>", lambda _e: self.desenhar_barra())
        self.lbl_detalhe = tk.Label(card, text="", font=(FONTE, 9), bg=CARTAO, fg=SUAVE, justify="left",
                                    anchor="w", wraplength=480)
        self.lbl_detalhe.pack(fill="x")
        self.lbl_gpu = tk.Label(card, text="", font=(FONTE, 9, "bold"), bg=CARTAO, fg=TEXTO, justify="left",
                                anchor="w", wraplength=480)
        self.lbl_gpu.pack(fill="x", pady=(6, 0))
        Dica(self.lbl_gpu, lambda: texto_dos_termos(self.lbl_gpu.cget("text")))

        # --- Gráfico ---
        graf = cartao(esq, f"Últimos {config['JANELA_MIN']:g} minutos")
        graf.pack(fill="both", expand=True, pady=(12, 0))
        self.grafico = tk.Canvas(graf, bg=CARTAO, highlightthickness=0)
        self.grafico.pack(fill="both", expand=True, pady=(6, 0))
        self.grafico.bind("<Configure>", lambda _e: self.desenhar_grafico())

        # --- Diagnóstico ---
        uso = cartao(dir_, "Uso da CPU e processos")
        uso.pack(fill="x")
        self.lbl_sistema = tk.Label(uso, text="Coletando…", font=(FONTE, 9), bg=CARTAO, fg=TEXTO, justify="left",
                                    anchor="w", wraplength=380)
        self.lbl_sistema.pack(fill="x", pady=(2, 6))
        self.cv_proc = tk.Canvas(uso, bg=CARTAO, highlightthickness=0, height=112)
        self.cv_proc.pack(fill="x")
        self.cv_proc.bind("<Configure>", lambda _e: self.desenhar_processos())

        sug = cartao(dir_, "Diagnóstico e sugestões")
        sug.pack(fill="both", expand=True, pady=(12, 0))
        self.txt = tk.Text(sug, wrap="word", bg=CARTAO, fg=TEXTO, relief="flat", font=(FONTE, 9),
                           padx=0, pady=4, cursor="arrow", spacing1=2, spacing3=4)
        self.txt.pack(fill="both", expand=True)
        self.txt.tag_configure("titulo", font=(FONTE, 10, "bold"), foreground=TEXTO, spacing1=10, spacing3=2)
        for p, (_, cor) in PRIORIDADE.items():
            self.txt.tag_configure(p, foreground=cor)
        self.txt.tag_configure("item", lmargin1=0, lmargin2=16)
        self.txt.configure(state="disabled")

        raiz.protocol("WM_DELETE_WINDOW", self.esconder)
        raiz.bind("<Map>", self._ao_mapear)
        raiz.bind("<Unmap>", self._ao_desmapear)
        self.iniciar_bandeja()
        threading.Thread(target=self.laco_diagnostico, daemon=True).start()
        threading.Thread(target=self.consultar_inicio, daemon=True).start()
        raiz.after(50, self.atualizar)
        raiz.after(250, self.processar_pedidos)
        raiz.after(8000, self.ciclo_memoria)

    # ---------- bandeja e janela ----------
    def iniciar_bandeja(self) -> None:
        try:
            from bandeja import Bandeja
            self.bandeja = Bandeja(
                ao_abrir=lambda: self.pedidos.put("abrir"),
                ao_alternar_monitor=lambda: self.pedidos.put("monitor"),
                monitor_ativo=lambda: self.ativo,
                ao_alternar_inicio=self.alternar_inicio,
                inicio_ativo=lambda: self.inicio_ativo,
                ao_sair=lambda: self.pedidos.put("sair"),
                ao_historico=lambda: self.pedidos.put("historico"),
                ao_laboratorio=lambda: self.pedidos.put("laboratorio"),
            )
            self.bandeja.iniciar()
        except Exception as e:  # sem pystray/Pillow: a janela vira o app inteiro
            self.bandeja = None
            self.erro_diag = f"Ícone da bandeja indisponível: {e}"
            self.pedidos.put("abrir")

    def processar_pedidos(self) -> None:
        """Executa na thread da janela o que a bandeja e a 2ª instância pediram (tkinter não é thread-safe)."""
        while not self.pedidos.empty():
            pedido = self.pedidos.get_nowait()
            try:  # um pedido com erro não pode matar o laço (e com ele o menu da bandeja, inclusive "Sair")
                if pedido == "abrir":
                    self.abrir_janela()
                elif pedido == "monitor":
                    self.alternar_monitor()
                elif pedido == "historico":
                    self.abrir_historico()
                elif pedido == "laboratorio":
                    self.abrir_laboratorio()
                elif pedido == "sair":
                    self.sair()
                    return
                elif isinstance(pedido, tuple) and pedido[0] == "erro":
                    self.abrir_janela()
                    self.lbl_gpu.config(text=pedido[1], fg=ZONAS["quente"][1])
            except Exception as e:
                self.lbl_gpu.config(text=f"Erro ao executar '{pedido}': {type(e).__name__}: {e}",
                                    fg=ZONAS["quente"][1])
        self.raiz.after(250, self.processar_pedidos)

    def abrir_janela(self) -> None:
        self.raiz.deiconify()
        self.raiz.lift()
        self.raiz.attributes("-topmost", True)
        self.raiz.after(200, lambda: self.raiz.attributes("-topmost", False))
        self.raiz.focus_force()
        self._mostrou()

    def _mostrou(self) -> None:
        if not self.visivel:
            self.visivel = True
            self.diag_acordar.set()
            self.atualizar_tela()

    def _ao_mapear(self, e) -> None:
        """Janela restaurada (clique no botão da barra de tarefas ou na bandeja)."""
        if e.widget is self.raiz:
            self._mostrou()

    def _ao_desmapear(self, e) -> None:
        if e.widget is self.raiz and self.raiz.state() in ("iconic", "withdrawn"):
            self.visivel = False
            self.raiz.after(3000, self.liberar_memoria)

    def esconder(self) -> None:
        """Fechar (X) minimiza: o botão fica na barra de tarefas mostrando temperatura e cor da faixa."""
        if self.bandeja is None:  # sem ícone na bandeja, fechar é sair
            self.sair()
            return
        self.raiz.iconify()

    def abrir_historico(self) -> None:
        if self.hist is None:
            self.abrir_janela()
            self.lbl_gpu.config(text=self.erro_hist, fg=ZONAS["quente"][1])
            return
        from linha_do_tempo import JanelaHistorico
        if self.janela_historico is not None and self.janela_historico.existe():
            self.janela_historico.trazer()
        else:
            self.janela_historico = JanelaHistorico(self.raiz, self.hist, self.cfg,
                                                    ao_fechar=lambda: setattr(self, "janela_historico", None))

    def abrir_laboratorio(self) -> None:
        """Módulo opcional em processo separado (ADR 0004). `laboratorio` só usa a biblioteca padrão."""
        import laboratorio
        if self.janela_lab is not None and self.janela_lab.existe():
            self.janela_lab.trazer()
        else:
            self.janela_lab = laboratorio.acionar(self.raiz, lambda: setattr(self, "janela_lab", None))

    def menu_laboratorio(self, evento) -> None:
        import laboratorio
        menu = tk.Menu(self.raiz, tearoff=0)
        laboratorio.montar_menu(menu, self.raiz)
        menu.tk_popup(evento.x_root, evento.y_root)

    def liberar_memoria(self) -> None:
        if not self.visivel:
            gc.collect()
            sistema.liberar_memoria()

    def ciclo_memoria(self) -> None:
        """Com a janela minimizada, devolve ao Windows as páginas sem uso a cada minuto."""
        self.liberar_memoria()
        self.raiz.after(60_000, self.ciclo_memoria)

    def sair(self) -> None:
        if self.gravador:
            self.gravador.fechar()
        if self.hist:
            self.hist.fechar()
        if self.bandeja:
            self.bandeja.parar()
        self.raiz.destroy()

    def alternar_monitor(self) -> None:
        self.ativo = not self.ativo
        self.btn_monitor.config(text="Pausar monitoramento" if self.ativo else "Retomar monitoramento")
        if self.bandeja:
            self.bandeja.atualizar_menu()
        if not self.ativo:
            self.ultima = None
            self.atualizar_bandeja()
            self.sem_leitura("Monitoramento pausado: nenhuma leitura é feita até você retomar.", "Pausado")
            self.lbl_gpu.config(text="")
        else:
            self.lbl_estado.config(text="Lendo…", bg=GRADE, fg=SUAVE)

    def consultar_inicio(self) -> None:
        try:
            self.inicio_ativo = sistema.inicio_automatico_ativo()
        except Exception:
            self.inicio_ativo = False
        if self.bandeja:
            self.bandeja.atualizar_menu()

    def alternar_inicio(self) -> None:
        """Roda na thread do pystray (schtasks/PowerShell levam 1–3 s)."""
        if self.inicio_ativo:
            ok, msg = sistema.desativar_inicio_automatico()
        else:
            ok, msg = sistema.ativar_inicio_automatico()
        self.consultar_inicio()
        if not ok:
            self.pedidos.put(("erro", f"Não foi possível alterar o início com o Windows: {msg or 'erro desconhecido'}"))

    def atualizar_bandeja(self, leitura: Leitura | None = None) -> None:
        """Mesmo número e cor no ícone da bandeja, no botão da barra de tarefas e no título da janela."""
        if not self.ativo:
            texto, cor, dica, titulo = "||", CINZA_ICONE, "TempCPU — monitoramento pausado", "TempCPU — pausado"
        else:
            ventoinha = f" · ventoinha {self.rpm:,} RPM".replace(",", ".") if self.rpm is not None else ""
            if leitura is None:
                texto, cor, titulo = "--", CINZA_ICONE, "TempCPU — sem leitura"
                dica = f"TempCPU — sem leitura{ventoinha}"
            elif self.parada:
                texto, cor, titulo = "--", CINZA_ICONE, "TempCPU — leitura parada"
                dica = f"TempCPU — leitura parada desde {self._hora_parada()}{ventoinha}\nClique para abrir"
            else:
                nome, cor, _ = ZONAS[zona_de(leitura.celsius, self.cfg)]
                texto, titulo = f"{leitura.celsius:.0f}", f"TempCPU — {leitura.celsius:.0f} °C"
                dica = f"TempCPU — CPU {br(leitura.celsius)} °C ({nome}){ventoinha}\nClique para abrir"
        agora = time.monotonic()
        # Discreto: o número só é redesenhado a cada ICONE_ATUALIZA_S (60 s), com o valor daquele instante,
        # ou na hora quando a faixa de cor ou o estado (pausado, sem leitura, parada) mudam.
        estado = (cor, texto if texto in ("||", "--") else "n")
        if estado == self._icone_estado and agora - self._icone_em < self.cfg["ICONE_ATUALIZA_S"]:
            return
        self._icone_estado, self._icone_em = estado, agora
        if self.bandeja:
            self.bandeja.mostrar(texto, cor, dica)
        self.icone_barra(texto, cor, titulo)

    def icone_barra(self, texto: str, cor: str, titulo: str) -> None:
        """Botão da barra de tarefas: o ícone da janela passa a ser o número sobre a cor da faixa."""
        if (texto, cor) != self._chave_icone:
            self._chave_icone = (texto, cor)
            try:
                from PIL import ImageTk
                from bandeja import desenhar_icone
                self._icone_tk = ImageTk.PhotoImage(desenhar_icone(texto, cor, "suave"))
                self.raiz.iconphoto(True, self._icone_tk)
            except Exception:
                pass
        if self.raiz.title() != titulo:
            self.raiz.title(titulo)

    def _hora_parada(self) -> str:
        return time.strftime("%H:%M", time.localtime(self.detector.desde)) if self.detector.desde else "?"

    def aplicar_limites_firmware(self) -> None:
        """Zona crítica = redução de desempenho do firmware; linha extra = desligamento (se DANO_C=auto)."""
        limites = self.leitor.limites_firmware() if self.leitor else None
        if not limites:
            return
        passivo, critico = limites
        self.desliga_c = critico
        if self.cfg.get("DANO_AUTO") and passivo > self.cfg["QUENTE_C"]:
            self.cfg["DANO_C"] = passivo

    def ler_ventoinha(self) -> None:
        """ASUS ATK (só DSTS, IDs fixos). Ausente/falha = sem ventoinha, sem erro."""
        if self.asus is None and time.monotonic() - self._asus_tentou >= 300:  # retenta a cada 5 min
            self._asus_tentou = time.monotonic()
            try:
                from asus import AsusAtk
                self.asus = AsusAtk(self.leitor.conexao_root_wmi())
                self.motivo_sem_fan = ""
            except Exception as e:
                self.asus = None
                self.motivo_sem_fan = ("precisa de administrador" if not eh_admin()
                                       else "interface ASUS não encontrada") + f" ({type(e).__name__})"
        if self.asus is None or time.monotonic() - self._fan_em < 10:
            self.rpm_novo = False
            return
        self._fan_em = time.monotonic()
        self.rpm = self.asus.ventoinha_cpu_rpm()
        self.rpm_novo = True

    # ---------- temperatura ----------
    def atualizar(self) -> None:
        if self.ativo:
            try:
                if self.leitor is None:
                    self.leitor = LeitorTemperatura()
                    self.aplicar_limites_firmware()
                leitura = self.leitor.ler()
                self.ler_ventoinha()
                self.parada = self.detector.atualizar(leitura)
                if not self.parada:
                    self.registrar(leitura)
                self.gravar_amostra(leitura)
                self.atualizar_bandeja(leitura)
                if self.visivel:
                    self.mostrar(leitura)
                    self.mostrar_extras()
            except SemLeitura as e:
                self.atualizar_bandeja(None)
                if self.visivel:
                    self.sem_leitura(str(e))
            except Exception as e:  # WMI indisponível, pywin32 ausente etc.
                self.atualizar_bandeja(None)
                if self.visivel:
                    self.sem_leitura(f"{type(e).__name__}: {e}")
        if self.visivel:
            self.atualizar_diagnostico()
        self.gravar_diagnostico()
        self.raiz.after(self.intervalo_ms, self.atualizar)

    def gravar_amostra(self, leitura: Leitura) -> None:
        if not self.gravador:
            return
        amd = self.leitor.amd_ultimo
        gpu = self.leitor.ler_gpu()
        self.gravador.amostra(time.time(), leitura.celsius, leitura.fonte, self.parada,
                              gpu_c=gpu.celsius if gpu else None, soc_c=amd.get("soc"),
                              clk_mhz=amd.get("clk_cpu"), rpm=self.rpm if self.rpm_novo else None)

    def gravar_diagnostico(self) -> None:
        """Uma vez por coleta nova: classifica os motivos do aquecimento e entrega ao histórico."""
        r = self.retrato
        if not (self.gravador and self.ativo and r and r.coletado_em != self._diag_gravado):
            return
        self._diag_gravado = r.coletado_em
        causas, _ = analisar(r, self.ultima, self.cfg, rpm=self.rpm, parada=self.parada)
        self.gravador.diagnostico(time.time(), r, causas)

    def atualizar_tela(self) -> None:
        """Redesenha tudo ao abrir a janela (enquanto oculta, só o histórico é atualizado)."""
        self.desenhar_barra()
        self.desenhar_grafico()
        self.atualizar_diagnostico()

    def sem_leitura(self, msg: str, estado: str = "Sem leitura") -> None:
        self.lbl_valor.config(text="--,- °C", fg=SUAVE)
        self.lbl_estado.config(text=estado, bg=GRADE, fg=TEXTO)
        self.lbl_detalhe.config(text=msg, wraplength=480)
        self.desenhar_barra()

    def mostrar_extras(self) -> None:
        """Linha com GPU, SoC, frequência e ventoinha — o que estiver disponível."""
        partes = []
        gpu = self.leitor.ler_gpu() if self.leitor else None
        if gpu:
            partes.append(f"GPU {br(gpu.celsius)} °C")
        amd = self.leitor.amd_ultimo if self.leitor else {}
        if amd.get("soc"):
            partes.append(f"SoC {amd['soc']} °C")
        if amd.get("clk_cpu"):
            partes.append(f"CPU a {amd['clk_cpu']:,} MHz".replace(",", "."))
        if self.rpm is not None:
            partes.append(f"Ventoinha {self.rpm:,} RPM".replace(",", "."))
        if self.rpm is None and self.motivo_sem_fan:
            partes.append(f"Ventoinha indisponível: {self.motivo_sem_fan}")
        if not gpu:
            partes.append("GPU: temperatura não exposta sem driver de núcleo")
        cor = ZONAS[zona_de(gpu.celsius, self.cfg)][1] if gpu else SUAVE
        self.lbl_gpu.config(text="  ·  ".join(partes), fg=cor)

    def registrar(self, leitura: Leitura) -> None:
        c = leitura.celsius
        self.ultima = c
        self.historico.append(c)
        self.minimo = c if self.minimo is None else min(self.minimo, c)
        self.maximo = c if self.maximo is None else max(self.maximo, c)

    def mostrar(self, leitura: Leitura) -> None:
        c = leitura.celsius
        fonte = f"Fonte: {leitura.fonte} ({leitura.sensor}) · leitura a cada {self.cfg['INTERVALO_S']:g} s"
        if self.parada:
            self.lbl_valor.config(text=f"{br(c)} °C", fg=SUAVE)
            self.lbl_estado.config(text="Leitura parada", bg=GRADE, fg=TEXTO)
            self.lbl_detalhe.config(text=f"Valor sem mudar desde {self._hora_parada()}: o firmware não está "
                                         f"atualizando a zona ACPI. Não use este número como temperatura atual.\n{fonte}")
            self.raiz.title("TempCPU — leitura parada")
        else:
            nome, forte, faixa = ZONAS[zona_de(c, self.cfg)]
            self.lbl_valor.config(text=f"{br(c)} °C", fg=forte)
            self.lbl_estado.config(text=nome, bg=faixa, fg=forte)
            minmax = (f"Mín {br(self.minimo)} °C · Máx {br(self.maximo)} °C · "
                      if self.minimo is not None else "")
            self.lbl_detalhe.config(
                text=f"{minmax}{time.strftime('%H:%M:%S')}\n{fonte}"
                     + ("\nACPI: o firmware só atualiza este valor em degraus; pode ficar parado." if leitura.fonte == "ACPI" else ""))
            self.raiz.title(f"TempCPU — {c:.0f} °C")
        self.desenhar_barra()
        self.desenhar_grafico()

    # ---------- diagnóstico ----------
    def laco_diagnostico(self) -> None:
        """Fora da thread da janela (psutil/powercfg levam centenas de ms). Com a janela minimizada coleta
        a cada DIAGNOSTICO_OCULTO_S (alimenta o histórico); com ela aberta, a cada DIAGNOSTICO_S."""
        try:
            coletor = Coletor()
        except Exception as e:
            self.erro_diag = f"Diagnóstico indisponível: {e}"
            return
        while True:
            self.diag_acordar.wait(self.cfg["DIAGNOSTICO_S"] if self.visivel else self.cfg["DIAGNOSTICO_OCULTO_S"])
            self.diag_acordar.clear()
            if not self.ativo:
                continue
            try:
                self.retrato = coletor.coletar()
            except Exception as e:
                self.erro_diag = f"Falha na coleta: {e}"

    def atualizar_diagnostico(self) -> None:
        r = self.retrato
        if r is None:
            if self.erro_diag:
                self.lbl_sistema.config(text=self.erro_diag)
            return
        energia = "na tomada" if r.na_tomada else ("na bateria" if r.na_tomada is False else "")
        if r.bateria is not None:
            energia += f" ({r.bateria}%)"
        turbo = "" if r.estado_max_ac is None else f" · estado máx. CPU {r.estado_max_ac}%"
        self.lbl_sistema.config(text=f"Uso total: {r.uso_cpu:.0f}%  ·  Plano: {r.plano_energia or '?'}\n"
                                     f"Energia: {energia}{turbo}")
        self.desenhar_processos()

        causas, sugestoes = analisar(r, self.ultima, self.cfg, rpm=self.rpm, parada=self.parada)
        t = self.txt
        topo = t.yview()[0]
        t.configure(state="normal")
        t.delete("1.0", "end")
        self._secao("O que pode estar elevando a temperatura", causas)
        self._secao("Como baixar a temperatura", sugestoes)
        t.configure(state="disabled")
        t.yview_moveto(topo)

    def _secao(self, titulo: str, itens: list[Item]) -> None:
        t = self.txt
        t.insert("end", titulo + "\n", "titulo")
        for i in itens:
            marca, _ = PRIORIDADE[i.prioridade]
            t.insert("end", f"{marca}  ", (i.prioridade, "item"))
            t.insert("end", i.texto + "\n", "item")

    # ---------- desenho ----------
    def faixas(self, baixo: float, alto: float) -> list[tuple[float, float, str]]:
        """Limites (de, até, zona) recortados à escala visível."""
        cortes = [baixo, self.cfg["ALERTA_C"], self.cfg["QUENTE_C"], self.cfg["DANO_C"], alto]
        nomes = ["normal", "atencao", "quente", "dano"]
        return [(max(a, baixo), min(b, alto), z) for a, b, z in zip(cortes, cortes[1:], nomes)
                if min(b, alto) > max(a, baixo)]

    def escala(self) -> tuple[int, int]:
        baixo = min([30.0, *self.historico]) - 5 if self.historico else 30.0
        alto = max([self.cfg["DANO_C"] + 10, *self.historico]) + 2
        return int(baixo // 5 * 5), int(-(-alto // 5) * 5)

    def desenhar_barra(self) -> None:
        """Régua das zonas com marcador na temperatura atual e os limites embaixo."""
        cv = self.barra
        cv.delete("all")
        w = cv.winfo_width()
        if w < 40:
            return
        baixo, alto = self.escala()

        def x(v: float) -> float:
            return 4 + (v - baixo) / (alto - baixo) * (w - 8)

        for de, ate, z in self.faixas(baixo, alto):
            cv.create_rectangle(x(de), 10, x(ate), 20, fill=ZONAS[z][2], outline=ZONAS[z][2])
        for lim in (self.cfg["ALERTA_C"], self.cfg["QUENTE_C"], self.cfg["DANO_C"]):
            cv.create_text(x(lim), 30, text=f"{lim:.0f}°", fill=SUAVE, font=(FONTE, 8))
        if self.ultima is not None:
            px = min(max(x(self.ultima), 6), w - 6)
            cor = SUAVE if self.parada else ZONAS[zona_de(self.ultima, self.cfg)][1]
            cv.create_oval(px - 6, 9, px + 6, 21, fill=cor, outline=CARTAO, width=2)

    def desenhar_grafico(self) -> None:
        cv = self.grafico
        cv.delete("all")
        w, h = cv.winfo_width(), cv.winfo_height()
        if w < 60 or h < 60:
            return
        esq, dir_, topo, base = 32, 4, 6, 6
        baixo, alto = self.escala()

        def y(v: float) -> float:
            return topo + (alto - v) / (alto - baixo) * (h - topo - base)

        for de, ate, z in self.faixas(baixo, alto):
            nome, forte, faixa = ZONAS[z]
            cv.create_rectangle(esq, y(ate), w - dir_, y(de), fill=faixa, width=0)

        for v in range(baixo, alto + 1, 10 if alto - baixo > 50 else 5):
            cv.create_line(esq, y(v), w - dir_, y(v), fill=CARTAO)
            cv.create_text(esq - 4, y(v), text=str(v), anchor="e", fill=SUAVE, font=(FONTE, 8))
        cv.create_line(esq, y(self.cfg["DANO_C"]), w - dir_, y(self.cfg["DANO_C"]),
                       fill=ZONAS["dano"][1], width=1, dash=(6, 3))
        if self.desliga_c and baixo < self.desliga_c < alto:
            cv.create_line(esq, y(self.desliga_c), w - dir_, y(self.desliga_c), fill=ZONAS["dano"][1], width=2)
            cv.create_text(w - dir_ - 6, y(self.desliga_c) - 2, text=f"desliga {self.desliga_c:.0f}°",
                           anchor="se", fill=ZONAS["dano"][1], font=(FONTE, 8, "bold"))

        for de, ate, z in self.faixas(baixo, alto):  # rótulos por cima da grade
            nome, forte, faixa = ZONAS[z]
            if y(de) - y(ate) >= 16:
                rot = cv.create_text(esq + 8, y(ate) + 4, text=nome, anchor="nw", fill=forte, font=(FONTE, 8, "bold"))
                x0, y0, x1, y1 = cv.bbox(rot)
                fundo = cv.create_rectangle(x0 - 3, y0 - 1, x1 + 3, y1 + 1, fill=faixa, width=0)
                cv.tag_lower(fundo, rot)

        dados = list(self.historico)
        n = self.historico.maxlen
        passo = (w - dir_ - esq - 6) / (n - 1)
        inicio = esq + (n - len(dados)) * passo
        if len(dados) >= 2:
            pts = []
            for i, v in enumerate(dados):
                pts += [inicio + i * passo, y(v)]
            cv.create_line(*pts, fill=LINHA, width=2)
        if dados:
            ux, uy = inicio + (len(dados) - 1) * passo, y(dados[-1])
            cor = ZONAS[zona_de(dados[-1], self.cfg)][1]
            cv.create_oval(ux - 4, uy - 4, ux + 4, uy + 4, fill=cor, outline=CARTAO, width=2)

    def desenhar_processos(self) -> None:
        cv = self.cv_proc
        cv.delete("all")
        w = cv.winfo_width()
        r = self.retrato
        if r is None or w < 60:
            return
        if not r.processos:
            cv.create_text(0, 10, text="Nenhum processo acima de 0,5% da CPU.", anchor="w", fill=SUAVE, font=(FONTE, 9))
            return
        nome_w, val_w = 150, 44
        for i, (nome, uso) in enumerate(r.processos):
            yy = 4 + i * 22
            cor = PRIORIDADE["alta" if uso >= 25 else "media" if uso >= 10 else "dica"][1]
            cv.create_text(0, yy + 7, text=nome[:22], anchor="w", fill=TEXTO, font=(FONTE, 9))
            larg = w - nome_w - val_w
            cv.create_rectangle(nome_w, yy + 2, nome_w + larg, yy + 12, fill=GRADE, width=0)
            cv.create_rectangle(nome_w, yy + 2, nome_w + max(2, larg * min(uso, 100) / 100), yy + 12, fill=cor, width=0)
            cv.create_text(w, yy + 7, text=f"{uso:.0f}%", anchor="e", fill=TEXTO, font=(FONTE, 9))


def modo_cli(config: dict[str, float]) -> None:
    leitor = LeitorTemperatura()
    try:
        while True:
            try:
                l = leitor.ler()
                zona = ZONAS[zona_de(l.celsius, config)][0]
                print(f"{time.strftime('%H:%M:%S')}  {br(l.celsius):>5} °C  {zona:<8} [{l.fonte}: {l.sensor}]", flush=True)
            except SemLeitura as e:
                print(f"{time.strftime('%H:%M:%S')}  sem leitura: {e}", flush=True)
            time.sleep(config["INTERVALO_S"])
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    cfg = carregar_config()
    if "--cli" in sys.argv:
        modo_cli(cfg)
    else:
        instancia = sistema.InstanciaUnica()
        if not instancia.primeira:  # já está rodando (ex.: iniciou com o Windows): só abre a janela dela
            instancia.avisar_primeira()
            sys.exit(0)
        sistema.definir_app_id()
        raiz = tk.Tk()
        raiz.withdraw()
        app = App(raiz, cfg)
        instancia.ao_ser_chamada(lambda: app.pedidos.put("abrir"))
        if "--janela" in sys.argv or app.bandeja is None:
            app.pedidos.put("abrir")
        else:
            raiz.iconify()  # começa minimizado: o botão da barra de tarefas já mostra a temperatura
        raiz.mainloop()
