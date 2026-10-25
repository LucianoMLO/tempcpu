"""Janela "Histórico": linha do tempo de uma ou mais variáveis, com granularidade e resumo do período."""
from __future__ import annotations

import time
import tkinter as tk
from bisect import bisect_left
from tkinter import ttk

from historico import NIVEIS, ROTULO_NIVEL, VARIAVEIS, Historico
from motivos import COR_CATEGORIA, ROTULO_CATEGORIA, Categoria, categoria_de, rotulo_de
from tema import BORDA, CARTAO, FONTE, FUNDO, GRADE, SUAVE, TEXTO, ZONAS, br, cartao

PERIODOS = {"1 hora": 3600, "6 horas": 6 * 3600, "24 horas": 86400, "7 dias": 7 * 86400,
            "30 dias": 30 * 86400, "1 ano": 365 * 86400, "Tudo": 0}
PASSO = {"minuto": 60, "hora": 3600, "dia": 86400, "semana": 7 * 86400, "mes": 30 * 86400}
TEMPERATURAS = ("cpu_c", "gpu_c", "soc_c")
MAX_PONTOS_AUTO = 1500
MAX_PONTOS = 5000
MAX_UNIDADES = 2   # eixo esquerdo e direito
BANDA = "#dfe6ef"

# nome curto no botão e cor da linha (suaves e distintas entre si)
CURTO = {"cpu_c": "CPU °C", "gpu_c": "GPU °C", "soc_c": "SoC °C", "uso_cpu": "Uso da CPU %",
         "clk_mhz": "Frequência MHz", "ventoinha_rpm": "Ventoinha RPM", "bateria_pct": "Bateria %",
         "tomada": "Na tomada"}
COR_VAR = {"cpu_c": "#3f4f66", "gpu_c": "#6b8fc4", "soc_c": "#4fa3a3", "uso_cpu": "#d08a4e",
           "clk_mhz": "#9a7fc0", "ventoinha_rpm": "#a67c52", "bateria_pct": "#5aa469", "tomada": "#9aa5b4"}


def unidade_de(var: str) -> str:
    return VARIAVEIS[var][1] or "fração"


def agrupar_unidades(selecionadas: list[str]) -> tuple[list[tuple[str, list[str]]], list[str]]:
    """Agrupa as variáveis por unidade, na ordem escolhida. Cabem 2 unidades (eixo esquerdo e direito);
    as variáveis de uma terceira unidade vão para a lista de rejeitadas."""
    grupos: list[tuple[str, list[str]]] = []
    rejeitadas: list[str] = []
    for var in selecionadas:
        un = unidade_de(var)
        existente = next((g for g in grupos if g[0] == un), None)
        if existente:
            existente[1].append(var)
        elif len(grupos) < MAX_UNIDADES:
            grupos.append((un, [var]))
        else:
            rejeitadas.append(var)
    return grupos, rejeitadas


def ponto_mais_proximo(pontos: list[dict], ts: float, tolerancia: float) -> dict | None:
    """Ponto da série (ordenada por ts) mais perto de `ts`, se estiver dentro da tolerância."""
    if not pontos:
        return None
    i = bisect_left([p["ts"] for p in pontos], ts)
    candidatos = pontos[max(0, i - 1):i + 1]
    melhor = min(candidatos, key=lambda p: abs(p["ts"] - ts))
    return melhor if abs(melhor["ts"] - ts) <= tolerancia else None


def escolher_nivel(duracao_s: float, escolha: str) -> tuple[str, str]:
    """(nível usado, aviso). "Automática" mantém ≤ 1.500 pontos; escolha manual com > 5.000 pontos sobe de nível."""
    if escolha == "Automática":
        for nivel in ("minuto", "hora", "dia", "semana", "mes"):
            if duracao_s / PASSO[nivel] <= MAX_PONTOS_AUTO:
                return nivel, ""
        return "mes", ""
    nivel = {v: k for k, v in ROTULO_NIVEL.items()}[escolha]
    original = nivel
    while duracao_s / PASSO[nivel] > MAX_PONTOS and nivel != "mes":
        nivel = NIVEIS[NIVEIS.index(nivel) + 1]
    aviso = f"{ROTULO_NIVEL[original]} teria pontos demais neste período; usando {ROTULO_NIVEL[nivel].lower()}." if nivel != original else ""
    return nivel, aviso


def ticks_bonitos(baixo: float, alto: float, alvo: int = 6) -> list[float]:
    """Valores redondos (1, 2, 5 × 10^k) entre baixo e alto."""
    if alto <= baixo:
        return [baixo]
    bruto = (alto - baixo) / alvo
    base = 10 ** (len(str(int(bruto))) - 1) if bruto >= 1 else 10 ** (-1)
    passo = next((m * base for m in (1, 2, 5, 10) if m * base >= bruto), 10 * base)
    v = (int(baixo // passo) + (0 if baixo % passo == 0 else 1)) * passo
    out = []
    while v <= alto + 1e-9:
        out.append(round(v, 6))
        v += passo
    return out


def formatar_x(ts: float, duracao_s: float) -> str:
    t = time.localtime(ts)
    if duracao_s <= 36 * 3600:
        return time.strftime("%H:%M", t)
    if duracao_s <= 14 * 86400:
        return time.strftime("%d/%m %Hh", t)
    return time.strftime("%d/%m/%y", t)


def escala_y(var: str, dados: list[dict]) -> tuple[float, float]:
    """Limites do eixo. O topo nunca fica abaixo do maior valor (senão a linha some do gráfico)."""
    dmin = min(d["min"] for d in dados)
    dmax = max(d["max"] for d in dados)
    if var in TEMPERATURAS:
        baixo = (min(dmin - 4, 40) // 5) * 5
        alto = -(-max(dmax + 4, 80) // 5) * 5
    elif var in ("uso_cpu", "bateria_pct"):
        baixo, alto = 0, 100
    elif var == "tomada":
        baixo, alto = 0, 1
    else:
        alvo = max(dmax * 1.05, 1)
        ticks = ticks_bonitos(0, alvo * 1.6, 6)
        baixo, alto = 0, next((t for t in ticks if t >= alvo), alvo)
    return float(baixo), float(alto)


class JanelaHistorico:
    def __init__(self, raiz: tk.Tk, historico: Historico, cfg: dict, ao_fechar) -> None:
        self.h = historico
        self.cfg = cfg
        self.ao_fechar = ao_fechar
        self.selecionadas: list[str] = ["cpu_c"]
        self.series: dict[str, list[dict]] = {}
        self.grupos: list[tuple[str, list[str]]] = []
        self.escalas: dict[str, tuple[float, float]] = {}
        self.nivel = "minuto"
        self.janela_s = 0.0
        self.inicio = 0
        self.fim = 0
        self.geom = (0.0, 0.0, 0, 0)  # esquerda, direita, topo, base do gráfico (px)

        self.top = tk.Toplevel(raiz)
        self.top.title("TempCPU — Histórico")
        self.top.configure(bg=FUNDO)
        self.top.geometry("1040x740")
        self.top.minsize(780, 600)
        self.top.protocol("WM_DELETE_WINDOW", self.fechar)

        barra = tk.Frame(self.top, bg=FUNDO)
        barra.pack(fill="x", padx=16, pady=(14, 0))
        self.cb_per = self._combo(barra, "Período", list(PERIODOS), "24 horas", 10)
        self.cb_niv = self._combo(barra, "Granularidade", ["Automática", *ROTULO_NIVEL.values()], "Automática", 12)
        self.lbl_base = tk.Label(barra, text="", bg=FUNDO, fg=SUAVE, font=(FONTE, 9))
        self.lbl_base.pack(side="right")

        chips = tk.Frame(self.top, bg=FUNDO)
        chips.pack(fill="x", padx=16, pady=(10, 0))
        tk.Label(chips, text="Variáveis", bg=FUNDO, fg=SUAVE, font=(FONTE, 9)).pack(side="left", padx=(0, 8))
        self.botoes: dict[str, tk.Button] = {}
        for var in VARIAVEIS:
            b = tk.Button(chips, text=CURTO[var], relief="flat", bd=0, font=(FONTE, 9), padx=10, pady=3,
                          cursor="hand2", command=lambda v=var: self.alternar_variavel(v))
            b.pack(side="left", padx=(0, 6))
            self.botoes[var] = b
        self._pintar_botoes()

        graf = cartao(self.top, "Linha do tempo")
        graf.pack(fill="both", expand=True, padx=16, pady=(10, 0))
        self.cv = tk.Canvas(graf, bg=CARTAO, highlightthickness=0, height=330)
        self.cv.pack(fill="both", expand=True, pady=(6, 0))
        self.cv.bind("<Configure>", lambda _e: self.desenhar())
        self.cv.bind("<Motion>", self.ao_mover)
        self.cv.bind("<Leave>", lambda _e: self.cv.delete("cursor"))
        self.cv.bind("<Button-1>", self.ao_clicar)
        self.lbl_hover = tk.Label(graf, text="", bg=CARTAO, fg=TEXTO, font=(FONTE, 9, "bold"), anchor="w",
                                  justify="left", wraplength=980)
        self.lbl_hover.pack(fill="x", pady=(4, 0))
        self.lbl_aviso = tk.Label(graf, text="", bg=CARTAO, fg=ZONAS["atencao"][1], font=(FONTE, 9), anchor="w")
        self.lbl_aviso.pack(fill="x")

        legenda = tk.Frame(graf, bg=CARTAO)
        legenda.pack(fill="x", pady=(2, 0))
        tk.Label(legenda, text="Motivo do aquecimento:", bg=CARTAO, fg=SUAVE, font=(FONTE, 8)).pack(side="left")
        for cat in Categoria:
            if cat is Categoria.INDEFINIDA:
                continue
            tk.Label(legenda, text="  ■", bg=CARTAO, fg=COR_CATEGORIA[cat], font=(FONTE, 9)).pack(side="left")
            tk.Label(legenda, text=ROTULO_CATEGORIA[cat], bg=CARTAO, fg=SUAVE, font=(FONTE, 8)).pack(side="left")

        res = cartao(self.top, "O que ocorreu")
        res.pack(fill="x", padx=16, pady=(10, 14))
        self.lbl_periodo = tk.Label(res, text="", bg=CARTAO, fg=TEXTO, font=(FONTE, 9), justify="left", anchor="w", wraplength=960)
        self.lbl_periodo.pack(fill="x", pady=(4, 0))
        self.lbl_ponto = tk.Label(res, text="", bg=CARTAO, fg=SUAVE, font=(FONTE, 9), justify="left", anchor="w", wraplength=960)
        self.lbl_ponto.pack(fill="x", pady=(6, 0))
        res.bind("<Configure>", lambda e: [l.config(wraplength=max(300, e.width - 40)) for l in (self.lbl_periodo, self.lbl_ponto)])

        for cb in (self.cb_per, self.cb_niv):
            cb.bind("<<ComboboxSelected>>", lambda _e: self.atualizar())
        self.atualizar()
        self._ciclo = self.top.after(60_000, self._recarregar)

    def _combo(self, pai, rotulo, valores, padrao, largura) -> ttk.Combobox:
        tk.Label(pai, text=rotulo, bg=FUNDO, fg=SUAVE, font=(FONTE, 9)).pack(side="left", padx=(0, 6))
        cb = ttk.Combobox(pai, values=valores, state="readonly", width=largura, font=(FONTE, 9))
        cb.set(padrao)
        cb.pack(side="left", padx=(0, 16))
        return cb

    # ---------- variáveis ----------
    def _pintar_botoes(self) -> None:
        for var, b in self.botoes.items():
            if var in self.selecionadas:
                b.config(bg=COR_VAR[var], fg="white", activebackground=COR_VAR[var], activeforeground="white")
            else:
                b.config(bg=GRADE, fg=TEXTO, activebackground=BORDA, activeforeground=TEXTO)

    def alternar_variavel(self, var: str) -> None:
        if var in self.selecionadas:
            if len(self.selecionadas) == 1:   # sempre sobra pelo menos uma
                return
            self.selecionadas.remove(var)
        else:
            self.selecionadas.append(var)
        self._pintar_botoes()
        self.atualizar()

    # ---------- ciclo de vida ----------
    def existe(self) -> bool:
        try:
            return bool(self.top.winfo_exists())
        except tk.TclError:
            return False

    def trazer(self) -> None:
        self.top.deiconify()
        self.top.lift()
        self.top.focus_force()
        self.atualizar()

    def fechar(self) -> None:
        try:
            self.top.after_cancel(self._ciclo)
        except Exception:
            pass
        self.top.destroy()
        self.ao_fechar()

    def _recarregar(self) -> None:
        if self.existe():
            self.atualizar()
            self._ciclo = self.top.after(60_000, self._recarregar)

    # ---------- dados ----------
    def atualizar(self) -> None:
        agora = int(time.time())
        dur = PERIODOS[self.cb_per.get()]
        if dur == 0:
            primeiro = self.h.primeiro_ts()
            dur = max(3600, agora - primeiro) if primeiro else 3600
        self.inicio, self.fim, self.janela_s = agora - dur, agora + 60, float(dur)
        self.nivel, aviso = escolher_nivel(dur, self.cb_niv.get())
        self.grupos, rejeitadas = agrupar_unidades(self.selecionadas)
        if rejeitadas:
            nomes = ", ".join(CURTO[v] for v in rejeitadas)
            aviso = (aviso + " " if aviso else "") + f"O gráfico mostra até {MAX_UNIDADES} unidades diferentes; não foi desenhado: {nomes}."
        self.lbl_aviso.config(text=aviso)
        try:
            desenhadas = [v for _, vs in self.grupos for v in vs]
            self.series = {v: self.h.serie(v, self.inicio, self.fim, self.nivel) for v in desenhadas}
            self.lbl_periodo.config(text=self.h.resumir(self.inicio, self.fim, self.nivel))
            c = self.h.contagem()
            self.lbl_base.config(text=f"Guardado: {c.get('minuto', 0):,} minutos · {c.get('hora', 0):,} horas · "
                                      f"{c.get('dia', 0):,} dias".replace(",", "."))
        except Exception as e:
            self.series = {}
            self.lbl_periodo.config(text=f"Não foi possível ler o histórico: {type(e).__name__}: {e}")
        self.lbl_ponto.config(text="Clique no gráfico para ver o resumo daquele ponto.", fg=SUAVE)
        self.desenhar()

    # ---------- desenho ----------
    def _x(self, ts: float) -> float:
        esq, dir_, _, _ = self.geom
        return esq + (ts - self.inicio) / max(1, self.fim - self.inicio) * (dir_ - esq)

    def _y(self, v: float, unidade: str) -> float:
        _, _, topo, base = self.geom
        baixo, alto = self.escalas[unidade]
        return topo + (alto - v) / max(1e-9, alto - baixo) * (base - topo)

    def desenhar(self) -> None:
        cv = self.cv
        cv.delete("all")
        w, h = cv.winfo_width(), cv.winfo_height()
        if w < 140 or h < 110:
            return
        com_dado = [(un, [v for v in vs if self.series.get(v)]) for un, vs in self.grupos]
        com_dado = [(un, vs) for un, vs in com_dado if vs]
        if not com_dado:
            cv.create_text(w / 2, h / 2, text="Ainda não há dados destas variáveis neste período.",
                           fill=SUAVE, font=(FONTE, 10))
            self.escalas = {}
            return
        duas = len(com_dado) == 2
        self.geom = (50.0, w - (50.0 if duas else 14.0), 26, h - 40)
        esq, dir_, topo, base = self.geom
        self.escalas = {}
        for un, vs in com_dado:
            juntos = [d for v in vs for d in self.series[v]]
            self.escalas[un] = escala_y(vs[0], juntos)

        # faixas de zona: só quando o eixo esquerdo é de temperatura
        un_esq, vs_esq = com_dado[0]
        if un_esq == "°C":
            baixo, alto = self.escalas[un_esq]
            cortes = [baixo, self.cfg["ALERTA_C"], self.cfg["QUENTE_C"], self.cfg["DANO_C"], alto]
            for (a, b), z in zip(zip(cortes, cortes[1:]), ("normal", "atencao", "quente", "dano")):
                a, b = max(a, baixo), min(b, alto)
                if b > a:
                    cv.create_rectangle(esq, self._y(b, un_esq), dir_, self._y(a, un_esq), fill=ZONAS[z][2], width=0)
        for i, (un, vs) in enumerate(com_dado):
            baixo, alto = self.escalas[un]
            for v in ticks_bonitos(baixo, alto):
                if i == 0:
                    cv.create_line(esq, self._y(v, un), dir_, self._y(v, un), fill=CARTAO if un == "°C" else GRADE)
                x = esq - 5 if i == 0 else dir_ + 5
                cv.create_text(x, self._y(v, un), text=br(v, 0 if alto > 5 else 1), anchor="e" if i == 0 else "w",
                               fill=SUAVE, font=(FONTE, 8))
            cv.create_text(6 if i == 0 else w - 6, topo - 14, text=un, anchor="nw" if i == 0 else "ne",
                           fill=SUAVE, font=(FONTE, 8, "bold"))

        for t in range(7):  # eixo do tempo
            ts = self.inicio + (self.fim - self.inicio) * t / 6
            cv.create_text(min(max(self._x(ts), esq + 18), dir_ - 18), base + 14, text=formatar_x(ts, self.janela_s),
                           fill=SUAVE, font=(FONTE, 8))

        passo = PASSO[self.nivel]
        unico = sum(len(vs) for _, vs in com_dado) == 1
        for un, vs in com_dado:
            for var in vs:
                self._desenhar_serie(var, un, passo, unico)

        # legenda das linhas (acima do gráfico)
        x = esq
        for un, vs in com_dado:
            for var in vs:
                cv.create_line(x, 8, x + 16, 8, fill=COR_VAR[var], width=3)
                t = cv.create_text(x + 21, 8, text=CURTO[var], anchor="w", fill=TEXTO, font=(FONTE, 8, "bold"))
                x = cv.bbox(t)[2] + 16

        # faixa de motivos (da primeira variável desenhada)
        primeiro = self.series[com_dado[0][1][0]]
        larg = max(2.0, (dir_ - esq) / max(1, self.fim - self.inicio) * passo)
        for d in primeiro:
            cat = categoria_de(d["motivo"]) if d["motivo"] else None
            if cat:
                xx = self._x(d["ts"])
                cv.create_rectangle(xx, base + 24, xx + min(larg, 12), base + 32, fill=COR_CATEGORIA[cat], width=0)
        cv.create_text(esq - 5, base + 28, text="motivo", anchor="e", fill=SUAVE, font=(FONTE, 7))

    def _desenhar_serie(self, var: str, un: str, passo: int, com_banda: bool) -> None:
        cv = self.cv
        cor = COR_VAR[var]
        segmentos: list[list[dict]] = [[]]
        for d in self.series[var]:  # quebra quando falta mais de 2,5 passos: computador desligado/pausado
            if segmentos[-1] and d["ts"] - segmentos[-1][-1]["ts"] > 2.5 * passo:
                segmentos.append([])
            segmentos[-1].append(d)
        for seg in segmentos:
            if com_banda and len(seg) >= 2 and any(d["max"] != d["min"] for d in seg):
                pts = [c for d in seg for c in (self._x(d["ts"]), self._y(d["max"], un))]
                pts += [c for d in reversed(seg) for c in (self._x(d["ts"]), self._y(d["min"], un))]
                cv.create_polygon(*pts, fill=BANDA, outline="")
            if len(seg) >= 2:
                cv.create_line(*[c for d in seg for c in (self._x(d["ts"]), self._y(d["med"], un))], fill=cor, width=2)
            if len(seg) <= 80:
                for d in seg:
                    x, y = self._x(d["ts"]), self._y(d["med"], un)
                    cv.create_oval(x - 2.5, y - 2.5, x + 2.5, y + 2.5, fill=cor, outline=CARTAO)

    # ---------- interação ----------
    def _ts_em(self, x: float) -> float:
        return self.inicio + (x - self.geom[0]) / max(1.0, self.geom[1] - self.geom[0]) * (self.fim - self.inicio)

    def _vars_desenhadas(self) -> list[str]:
        return [v for _, vs in self.grupos for v in vs if self.series.get(v)]

    def _pontos_em(self, x: float) -> dict[str, dict]:
        """Ponto mais próximo de cada variável desenhada."""
        if not self.escalas or self.geom[1] <= self.geom[0]:
            return {}
        ts = self._ts_em(x)
        tol = 3 * PASSO[self.nivel] + (self.fim - self.inicio) / 80
        achados = {v: ponto_mais_proximo(self.series[v], ts, tol) for v in self._vars_desenhadas()}
        return {v: p for v, p in achados.items() if p}

    def ao_mover(self, e) -> None:
        self.cv.delete("cursor")
        pontos = self._pontos_em(e.x)
        if not pontos:
            self.lbl_hover.config(text="")
            return
        ref = next(iter(pontos.values()))
        xx = self._x(ref["ts"])
        self.cv.create_line(xx, self.geom[2], xx, self.geom[3], fill=SUAVE, dash=(2, 3), tags="cursor")
        quando = f"{time.strftime('%d/%m %H:%M', time.localtime(ref['ts']))} ({ROTULO_NIVEL[self.nivel].lower()})"
        if len(pontos) == 1:
            var, d = next(iter(pontos.items()))
            un = VARIAVEIS[var][1]
            casas = 2 if var == "tomada" else 1
            txt = f"{quando} · mín {br(d['min'], casas)} · média {br(d['med'], casas)} · máx {br(d['max'], casas)} {un}"
        else:
            partes = []
            for var, d in pontos.items():
                casas = 2 if var == "tomada" else 0 if VARIAVEIS[var][1] in ("RPM", "MHz", "%") else 1
                partes.append(f"{CURTO[var].rsplit(' ', 1)[0] if VARIAVEIS[var][1] else CURTO[var]} "
                              f"{br(d['med'], casas)} {VARIAVEIS[var][1]}".strip())
            txt = f"{quando} · médias: " + " · ".join(partes)
        if ref["motivo"]:
            txt += f" · {rotulo_de(ref['motivo'])}"
        self.lbl_hover.config(text=txt)

    def ao_clicar(self, e) -> None:
        pontos = self._pontos_em(e.x)
        if pontos:
            d = next(iter(pontos.values()))
            quando = time.strftime("%d/%m/%Y %H:%M", time.localtime(d["ts"]))
            self.lbl_ponto.config(text=f"{ROTULO_NIVEL[self.nivel]} de {quando}: {d['resumo']}", fg=TEXTO)
