"""Lição 2 · Quente para o que você faz (anomalia: o que é normal e o que foge disso)."""
from __future__ import annotations

import time
import tkinter as tk
from tkinter import ttk

import numpy as np

from lab import textos as T
from lab.dados import ALVO, ENTRADAS_PADRAO
from lab.modelos import SENSIBILIDADE_PADRAO, detectar, episodios_de, suavizar, treinar_anomalia
from lab.ui.graficos import (COR_ALERTA_FAIXA, COR_BOM, COR_PREVISTO, COR_REAL, COR_TESTE, COR_TREINO, Area, novo_canvas,
                             reduzir_media)
from lab.ui.passos import LicaoPassos, Passo, botao
from lab.ui.quiz import Quiz
from tema import CARTAO, FONTE, GRADE, SUAVE, TEXTO, ZONAS, br

ENTRADAS = list(ENTRADAS_PADRAO)
LICAO = 2
LIMITE_TENDENCIA = 0.75       # °C por semana: sem poeira, o acaso fica abaixo de ~0,35 (8 sementes), com folga
COR_EPISODIO = "#e6a39a"
COR_VERDADE = "#3f4f66"


def criar(janela) -> LicaoPassos:
    funcoes = [passo1, passo2, passo3, passo4, passo5, passo6]
    passos = [Passo(t, f) for t, f in zip(T.L2_PASSOS, funcoes)]

    def concluir() -> None:
        janela.estado.progresso.marcar_concluida(LICAO)
        janela.mostrar_inicio()

    return LicaoPassos(janela, LICAO, passos, ao_concluir=concluir)


def _semente(conj) -> int:
    return conj.semente if conj.semente is not None else 7


def _data(ts: float) -> str:
    return time.strftime("%d/%m/%Y", time.localtime(int(ts)))


def _treinar(jan, pai, conj, ao_pronto, refazer) -> None:
    semente = _semente(conj)
    jan.treinar(pai, "anomalia", (tuple(ENTRADAS), semente),
                lambda progresso, cancelar: treinar_anomalia(conj, ENTRADAS, semente, progresso, cancelar),
                ao_pronto=ao_pronto, refazer=refazer, licao=LICAO)


# ---------------- passo 1: a ideia ----------------
def passo1(area: tk.Frame, lic: LicaoPassos) -> None:
    jan = lic.janela
    conj = jan.estado.conjunto(LICAO)
    lic.aviso_qualidade(area, conj)
    lic.texto(area, T.L2_P1)
    if conj.origem == "sintetico":
        p = jan.estado.params_licao(LICAO)
        lic.texto(area, T.L2_FONTE_SINT.format(dias=p.dias, poeira=br(p.poeira_por_dia, 1), n=p.episodios),
                  fonte=(FONTE, 9), cor=SUAVE)
    else:
        lic.texto(area, T.L2_FONTE_REAL, fonte=(FONTE, 9), cor=SUAVE)
    cv = novo_canvas(area, 230)
    cv.pack(fill="both", expand=True, pady=(4, 4))
    lic.texto(area, T.L2_P1_GRAFICO, fonte=(FONTE, 9), cor=SUAVE)
    cv.bind("<Configure>", lambda _e: _ideia(cv, conj))


def _ideia(cv: tk.Canvas, conj) -> None:
    cv.delete("all")
    a = Area(cv)
    idx = np.flatnonzero(conj.mascara(["uso"]))
    if not a.pronto() or len(idx) < 50:
        a.mensagem(T.ESTADO_SEM_DADOS_AINDA)
        return
    x, y = conj.dados["uso"][idx], conj.dados[ALVO][idx]
    angulo, intercepto = np.polyfit(x, y, 1)
    alto_uso, baixo_uso = 90, 8
    temp = round(float(angulo * alto_uso + intercepto))
    a.definir(0, 100, float((min(y.min(), temp) - 3) // 5 * 5), float(-(-(max(y.max(), temp) + 3) // 5) * 5))
    a.eixos([(v, str(v)) for v in range(0, 101, 20)], rotulo_y=T.L2_P1_EIXO_Y)
    cv.create_text(a.esq + a.largura / 2, cv.winfo_height() - 6, text=T.L2_P1_EIXO_X, fill=SUAVE, font=(FONTE, 8, "bold"))
    passo = max(1, len(idx) // 1200)
    a.pontos(x[::passo], y[::passo], "#c9d6ea", 1.6)
    a.linha([0, 100], [intercepto, angulo * 100 + intercepto], COR_PREVISTO, 2)
    cv.create_text(a.px(30), a.py(angulo * 30 + intercepto) + 18, text=T.L2_P1_ESPERADO, anchor="w", fill=COR_PREVISTO,
                   font=(FONTE, 9, "bold"))
    a.horizontal(temp, SUAVE, 1, (4, 3))
    a.pontos([alto_uso], [temp], COR_BOM, 7)
    a.pontos([baixo_uso], [temp], ZONAS["quente"][1], 7)
    cv.create_text(a.px(alto_uso) - 12, a.py(temp) - 14, text=T.L2_P1_NORMAL.format(temp=temp, uso=alto_uso), anchor="e",
                   fill=COR_BOM, font=(FONTE, 9, "bold"))
    cv.create_text(a.px(baixo_uso) + 12, a.py(temp) - 14, text=T.L2_P1_ESTRANHO.format(temp=temp, uso=baixo_uso), anchor="w",
                   fill=ZONAS["quente"][1], font=(FONTE, 9, "bold"))


# ---------------- passo 2: aprender o normal ----------------
def passo2(area: tk.Frame, lic: LicaoPassos) -> None:
    jan = lic.janela
    conj = jan.estado.conjunto(LICAO)
    corpo = tk.Frame(area, bg=CARTAO)
    corpo.pack(fill="both", expand=True)
    _treinar(jan, corpo, conj, lambda r: _montar_passo2(corpo, lic, r), refazer=lambda: lic.mostrar(lic.indice))


def _montar_passo2(corpo: tk.Frame, lic: LicaoPassos, res) -> None:
    if not corpo.winfo_exists():
        return
    treino = res.no_treino
    lic.texto(corpo, T.L2_P2.format(n=f"{int(treino.sum()):,}".replace(",", "."), ini=_data(res.ts[treino][0]),
                                    fim=_data(res.ts[treino][-1])))
    lic.texto(corpo, T.L2_P2_ERRO.format(erro=br(res.erro_tipico)))
    lic.texto(corpo, T.L2_P2_COMO, fonte=(FONTE, 9), cor=SUAVE)
    corpo.erro_tipico = res.erro_tipico


# ---------------- passo 3: medido × esperado ----------------
def _dias_da_prova(res) -> list[tuple[str, np.ndarray]]:
    """(rótulo, índices) de cada dia do período de prova."""
    prova = np.flatnonzero(~res.no_treino)
    dias: dict[str, list[int]] = {}
    for i in prova:
        dias.setdefault(time.strftime("%d/%m", time.localtime(int(res.ts[i]))), []).append(int(i))
    return [(k, np.array(v)) for k, v in dias.items()]


def passo3(area: tk.Frame, lic: LicaoPassos) -> None:
    jan = lic.janela
    conj = jan.estado.conjunto(LICAO)
    lic.texto(area, T.L2_P3)
    corpo = tk.Frame(area, bg=CARTAO)
    corpo.pack(fill="both", expand=True)
    _treinar(jan, corpo, conj, lambda r: _montar_passo3(corpo, lic, r), refazer=lambda: lic.mostrar(lic.indice))


def _montar_passo3(corpo: tk.Frame, lic: LicaoPassos, res) -> None:
    if not corpo.winfo_exists():
        return
    dias = _dias_da_prova(res)
    if not dias:
        lic.texto(corpo, T.ESTADO_SEM_DADOS_AINDA)
        return
    marcado, episodios = detectar(res.ts, res.residuo, res.erro_tipico)
    # abre no primeiro dia que tem episódio marcado (se houver), senão no primeiro dia da prova
    inicial = next((k for k, (_, idx) in enumerate(dias) if marcado[idx].any()), 0)

    barra = tk.Frame(corpo, bg=CARTAO)
    barra.pack(fill="x", pady=(0, 4))
    tk.Label(barra, text=T.L2_P3_DIA, bg=CARTAO, fg=TEXTO, font=(FONTE, 10, "bold")).pack(side="left")
    combo = ttk.Combobox(barra, values=[d for d, _ in dias], state="readonly", width=8, font=(FONTE, 10))
    combo.current(inicial)
    combo.pack(side="left", padx=(6, 12))
    resumo = lic.texto(barra, "", fonte=(FONTE, 10))
    resumo.pack_forget()
    resumo.pack(side="left", fill="x", expand=True)

    tk.Label(corpo, text=T.L2_P3_GRAF_A, bg=CARTAO, fg=SUAVE, font=(FONTE, 9, "bold"), anchor="w").pack(fill="x")
    cv_a = novo_canvas(corpo, 200)
    cv_a.pack(fill="both", expand=True)
    tk.Label(corpo, text=T.L2_P3_GRAF_B, bg=CARTAO, fg=SUAVE, font=(FONTE, 9, "bold"), anchor="w").pack(fill="x", pady=(6, 0))
    cv_b = novo_canvas(corpo, 150)
    cv_b.pack(fill="both", expand=True)
    estado = {"dia": inicial}
    limite = SENSIBILIDADE_PADRAO * res.erro_tipico

    def idx_dia() -> np.ndarray:
        return dias[estado["dia"]][1]

    def ticks(ts: np.ndarray) -> list[tuple[float, str]]:
        passos = np.linspace(ts[0], ts[-1], 6)
        return [(float(t), time.strftime("%H:%M", time.localtime(int(t)))) for t in passos]

    def desenhar_a() -> None:
        cv_a.delete("all")
        a = Area(cv_a)
        if not a.pronto():
            return
        idx = idx_dia()
        ts = res.ts[idx].astype(float)
        lo = float(min(res.medido[idx].min(), res.esperado[idx].min())) - 2
        hi = float(max(res.medido[idx].max(), res.esperado[idx].max())) + 2
        a.definir(ts[0], ts[-1], float(lo // 5 * 5), float(-(-hi // 5) * 5))
        for ini, fim in episodios_de(marcado[idx]):
            a.faixa_x(ts[ini], ts[min(fim, len(ts)) - 1], COR_ALERTA_FAIXA)
        a.eixos(ticks(ts), rotulo_y="°C")
        a.linha_com_quebras(ts, res.medido[idx], COR_REAL, 2)
        a.linha_com_quebras(ts, res.esperado[idx], COR_PREVISTO, 2)
        a.legenda([(COR_REAL, T.L2_P3_LEG_MEDIDO), (COR_PREVISTO, T.L2_P3_LEG_ESPERADO)])

    def desenhar_b() -> None:
        cv_b.delete("all")
        a = Area(cv_b)
        if not a.pronto():
            return
        idx = idx_dia()
        ts = res.ts[idx].astype(float)
        r = res.residuo[idx]
        topo = max(float(r.max()), limite * 1.2) + 1
        base = min(float(r.min()), -limite) - 1
        a.definir(ts[0], ts[-1], float(base // 5 * 5), float(-(-topo // 5) * 5))
        for ini, fim in episodios_de(marcado[idx]):
            a.faixa_x(ts[ini], ts[min(fim, len(ts)) - 1], COR_ALERTA_FAIXA)
        a.eixos(ticks(ts), rotulo_y="°C")
        a.horizontal(0, SUAVE, 1)
        a.linha_com_quebras(ts, r, "#c9d6ea", 1)
        a.linha_com_quebras(ts, suavizar(r, 5), COR_REAL, 2)
        a.horizontal(limite, ZONAS["quente"][1], 2, (5, 3))
        a.legenda([(ZONAS["quente"][1], T.L2_P3_LEG_LIMITE.format(k=br(SENSIBILIDADE_PADRAO))),
                   (COR_EPISODIO, T.L2_P3_LEG_EPISODIO)])

    def atualizar_texto() -> None:
        n = len(episodios_de(marcado[idx_dia()]))
        resumo.definir(T.L2_P3_ACHOU.format(n=n) if n else T.L2_P3_NENHUM)

    def mudou(_e=None) -> None:
        estado["dia"] = combo.current()
        atualizar_texto()
        desenhar_a()
        desenhar_b()

    combo.bind("<<ComboboxSelected>>", mudou)
    cv_a.bind("<Configure>", lambda _e: desenhar_a())
    cv_b.bind("<Configure>", lambda _e: desenhar_b())
    atualizar_texto()
    corpo.combo_dia = combo
    corpo.mudou_dia = mudou
    corpo.resumo_dia = resumo
    corpo.dias = [d for d, _ in dias]


# ---------------- passo 4: o limite do estranho ----------------
def passo4(area: tk.Frame, lic: LicaoPassos) -> None:
    jan = lic.janela
    conj = jan.estado.conjunto(LICAO)
    lic.texto(area, T.L2_P4)
    corpo = tk.Frame(area, bg=CARTAO)
    corpo.pack(fill="both", expand=True)
    _treinar(jan, corpo, conj, lambda r: _montar_passo4(corpo, lic, r), refazer=lambda: lic.mostrar(lic.indice))


def _montar_passo4(corpo: tk.Frame, lic: LicaoPassos, res) -> None:
    if not corpo.winfo_exists():
        return
    prova = ~res.no_treino
    pidx = np.flatnonzero(prova)
    sintetico = res.verdade is not None
    verdade_eps = episodios_de(res.verdade & prova) if sintetico else []
    estado = {"k": SENSIBILIDADE_PADRAO}

    rotulo = tk.Label(corpo, text="", bg=CARTAO, fg=TEXTO, font=(FONTE, 10, "bold"), anchor="w")
    rotulo.pack(fill="x")
    escala = ttk.Scale(corpo, from_=15, to=50, orient="horizontal", length=520)
    escala.set(int(round(SENSIBILIDADE_PADRAO * 10)))
    escala.pack(anchor="w", pady=(0, 4))
    tk.Label(corpo, text=T.L2_P4_GRAF, bg=CARTAO, fg=SUAVE, font=(FONTE, 9, "bold"), anchor="w").pack(fill="x")
    cv = novo_canvas(corpo, 190)
    cv.pack(fill="both", expand=True)
    mensagem = lic.texto(corpo, "")

    suave = suavizar(res.residuo, 5)

    def calcular() -> dict:
        marcado, eps = detectar(res.ts, res.residuo, res.erro_tipico, estado["k"])
        marcado = marcado & prova
        eps_prova = [(a, b) for a, b in eps if prova[a]]
        achou = sum(1 for a, b in verdade_eps if marcado[a:b].any()) if sintetico else 0
        normais = prova & ~res.verdade if sintetico else prova
        falsos = float((marcado & normais).sum() / max(1, normais.sum()) * 100)
        return {"marcado": marcado, "eps": eps_prova, "achou": achou, "falsos": falsos}

    def desenhar() -> None:
        cv.delete("all")
        a = Area(cv)
        if not a.pronto():
            return
        dados = calcular()
        limite = estado["k"] * res.erro_tipico
        x = np.arange(len(pidx), dtype=float)
        y = suave[pidx]
        topo = max(float(y.max()), limite * 1.15) + 1
        a.definir(0, len(pidx), float(min(y.min(), -2) // 5 * 5), float(-(-topo // 5) * 5))
        base = pidx[0]
        for ini, fim in dados["eps"]:
            a.faixa_x(ini - base, fim - base, COR_EPISODIO)
        ticks = [(int(k * (len(pidx) - 1) / 5), time.strftime("%d/%m", time.localtime(int(res.ts[pidx[int(k * (len(pidx) - 1) / 5)]]))))
                 for k in range(6)]
        a.eixos(ticks, rotulo_y="°C")
        a.horizontal(0, SUAVE, 1)
        a.linha(*reduzir_media(x, y, 900), COR_REAL, 1)
        a.horizontal(limite, ZONAS["quente"][1], 2, (5, 3))
        legenda = [(ZONAS["quente"][1], T.L2_P4_LEG_LIMITE), (COR_EPISODIO, T.L2_P4_LEG_MARCADO)]
        if sintetico:
            for ini, fim in verdade_eps:
                cv.create_polygon(a.px(ini - base) - 4, a.topo + 14, a.px(ini - base) + 4, a.topo + 14, a.px(ini - base), a.topo + 22,
                                  fill=COR_VERDADE, outline="")
            legenda.append((COR_VERDADE, T.L2_P4_LEG_VERDADE))
        a.legenda(legenda)

    def atualizar_texto() -> None:
        dados = calcular()
        k = estado["k"]
        rotulo.config(text=T.L2_P4_CONTROLE.format(k=br(k), lim=br(k * res.erro_tipico)))
        minutos = int(dados["marcado"].sum())
        if sintetico and not verdade_eps:
            texto = T.L2_P4_RESULT_SEM_GABARITO.format(ep=len(dados["eps"]), minutos=minutos, fa=br(dados["falsos"], 2))
            corpo.metricas = (0, 0, dados["falsos"], len(dados["eps"]))
        elif sintetico:
            rec = dados["achou"] / len(verdade_eps)
            texto = T.L2_P4_RESULT_SINT.format(ep=len(dados["eps"]), minutos=minutos, n=len(verdade_eps), achou=dados["achou"],
                                               rec=f"{rec * 100:.0f}", fa=br(dados["falsos"], 2))
            if dados["falsos"] > 3:
                texto += " " + T.L2_P4_BAIXA
            elif rec < 0.5:
                texto += " " + T.L2_P4_ALTA
            elif rec >= 0.8 and dados["falsos"] <= 1:
                texto += " " + T.L2_P4_OK
            corpo.metricas = (dados["achou"], len(verdade_eps), dados["falsos"], len(dados["eps"]))
        else:
            texto = T.L2_P4_RESULT_REAL.format(ep=len(dados["eps"]), minutos=minutos)
            corpo.metricas = (None, 0, dados["falsos"], len(dados["eps"]))
        mensagem.definir(texto)

    def mudou(valor: str) -> None:
        v = int(round(float(valor)))
        if abs(float(valor) - v) > 1e-6:
            escala.set(v)
            return
        k = v / 10
        if abs(k - estado["k"]) > 1e-9:
            estado["k"] = k
            atualizar_texto()
            desenhar()

    escala.config(command=mudou)
    cv.bind("<Configure>", lambda _e: desenhar())
    atualizar_texto()
    corpo.escala = escala
    corpo.estado_passo4 = estado


# ---------------- passo 5: tendência por semana ----------------
def passo5(area: tk.Frame, lic: LicaoPassos) -> None:
    jan = lic.janela
    conj = jan.estado.conjunto(LICAO)
    lic.texto(area, T.L2_P5)
    corpo = tk.Frame(area, bg=CARTAO)
    corpo.pack(fill="both", expand=True)
    _treinar(jan, corpo, conj, lambda r: _montar_passo5(corpo, lic, r), refazer=lambda: lic.mostrar(lic.indice))


def _montar_passo5(corpo: tk.Frame, lic: LicaoPassos, res) -> None:
    if not corpo.winfo_exists():
        return
    jan = lic.janela
    semanas = res.semanas
    if semanas:
        tk.Label(corpo, text=T.L2_P5_GRAF, bg=CARTAO, fg=SUAVE, font=(FONTE, 9, "bold"), anchor="w").pack(fill="x")
        cv = novo_canvas(corpo, 180)
        cv.pack(fill="both", expand=True, pady=(2, 6))
        cv.bind("<Configure>", lambda _e: _barras_semanais(cv, res))
    if res.inclinacao is None:
        lic.texto(corpo, T.L2_P5_POUCAS.format(n=len(semanas)))
        botao(corpo, T.L2_P5_BOTAO_POEIRA, lambda: _ver_com_poeira(jan), destaque=True).pack(anchor="w", pady=4)
        corpo.sem_tendencia = True
        return
    incl = res.inclinacao
    texto = T.L2_P5_SOBE if incl > LIMITE_TENDENCIA else T.L2_P5_DESCE if incl < -LIMITE_TENDENCIA else T.L2_P5_PLANA
    lic.texto(corpo, texto.format(incl=br(abs(incl) if texto is T.L2_P5_DESCE else incl)))
    corpo.inclinacao = incl


def _ver_com_poeira(jan) -> None:
    jan.estado.usar_sintetico()
    jan.abrir_licao(LICAO)


def _barras_semanais(cv: tk.Canvas, res) -> None:
    cv.delete("all")
    a = Area(cv)
    sem = res.semanas
    if not a.pronto() or not sem:
        return
    valores = [m for _, m, _ in sem]
    alto = max(max(valores), 1.0) * 1.25
    baixo = min(min(valores), -0.5) * 1.25 if min(valores) < 0 else -0.5
    a.definir(-0.6, len(sem) - 0.4, float(baixo), float(alto))
    a.eixos([(i, T.L2_P5_SEMANA.format(n=s + 1)) for i, (s, _, _) in enumerate(sem)], casas_y=1, rotulo_y="°C")
    a.horizontal(0, SUAVE, 1)
    for i, (_, m, _) in enumerate(sem):
        x0, x1, y0, y1 = a.px(i - 0.3), a.px(i + 0.3), a.py(0), a.py(m)
        cv.create_rectangle(x0, min(y0, y1), x1, max(y0, y1), fill=COR_TESTE if m > 0 else COR_TREINO, width=0)
        cv.create_text((x0 + x1) / 2, min(y0, y1) - 8, text=br(m, 1), fill=TEXTO, font=(FONTE, 9, "bold"))
    if res.inclinacao is not None:
        x = np.arange(len(sem), dtype=float)
        angulo, interc = np.polyfit(x, np.array(valores), 1)
        a.linha([0, len(sem) - 1], [interc, angulo * (len(sem) - 1) + interc], ZONAS["quente"][1], 2, (5, 3))


# ---------------- passo 6: resumo e perguntas ----------------
def passo6(area: tk.Frame, lic: LicaoPassos) -> None:
    tk.Label(area, text=T.L2_P6, bg=CARTAO, fg=TEXTO, font=(FONTE, 10, "bold"), anchor="w").pack(fill="x")
    for item in T.L2_RESUMO:
        lic.texto(area, "•  " + item)
    quiz = Quiz(area, lic.janela, LICAO, T.L2_QUIZ)
    quiz.pack(fill="x", pady=(6, 0))
    area.quiz = quiz
