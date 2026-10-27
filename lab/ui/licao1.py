"""Lição 1 · Dá para prever a temperatura? (regressão e sobreajuste)."""
from __future__ import annotations

import time
import tkinter as tk
from tkinter import ttk

import numpy as np

from lab import textos as T
from lab.dados import ALVO, ENTRADAS_PADRAO, VARIAVEIS, dividir_embaralhado, dividir_por_tempo
from lab.modelos import curva_profundidade, importancia, previsto_x_real
from lab.ui.graficos import (COR_ALERTA_FAIXA, COR_BOM, COR_FAIXA_TESTE, COR_FAIXA_TREINO, COR_PREVISTO, COR_REAL,
                             COR_TESTE, COR_TREINO, Area, barras_horizontais, novo_canvas, reduzir)
from lab.ui.passos import LicaoPassos, Passo
from lab.ui.quiz import Quiz
from tema import CARTAO, FONTE, GRADE, SUAVE, TEXTO, ZONAS, br

ENTRADAS = list(ENTRADAS_PADRAO)
ENTRADAS_COM_VENTOINHA = ENTRADAS + ["ventoinha"]
PROFUNDIDADE_INICIAL = 3
MIN_LINHAS_VENTOINHA = 200


def criar(janela) -> LicaoPassos:
    from lab.ui.passos_novos import passo_validacao, passo_boosting
    funcoes = [passo1, passo2, passo3, passo4, passo5, passo_validacao, passo_boosting, passo6]
    passos = [Passo(t, f) for t, f in zip(T.L1_PASSOS, funcoes)]

    def concluir() -> None:
        janela.estado.progresso.marcar_concluida(1)
        janela.mostrar_inicio()

    return LicaoPassos(janela, 1, passos, ao_concluir=concluir)


def _arredondar(v: float, base: int, cima: bool) -> float:
    return float((-(-v // base) if cima else v // base) * base)


def _minutos_validos(conj, entradas=ENTRADAS) -> np.ndarray:
    return np.flatnonzero(conj.mascara(entradas))


def _semente(conj) -> int:
    return conj.semente if conj.semente is not None else 7


def _pt(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def _treinar_curva(jan, pai, conj, entradas, divisao, ao_pronto, refazer, linhas=None) -> None:
    """`linhas` fixa os minutos usados (para comparar modelos exatamente nas mesmas linhas)."""
    semente = _semente(conj)
    marca = None if linhas is None else (len(linhas), int(linhas[0]), int(linhas[-1]))
    jan.treinar(pai, "curva1", (tuple(entradas), divisao, semente) + (() if marca is None else (marca,)),
                lambda progresso, cancelar: curva_profundidade(conj, entradas, divisao, semente, progresso=progresso,
                                                               cancelar=cancelar, linhas=linhas),
                ao_pronto=ao_pronto, refazer=refazer)


# ---------------- passo 1: o problema ----------------
def passo1(area: tk.Frame, lic: LicaoPassos) -> None:
    conj = lic.janela.estado.conjunto()
    lic.aviso_qualidade(area, conj)
    lic.texto(area, T.L1_P1)
    tk.Label(area, text=lic.janela.estado.descricao_fonte(), bg=CARTAO, fg=SUAVE, font=(FONTE, 9), anchor="w").pack(fill="x")
    cv = novo_canvas(area, 250)
    cv.pack(fill="both", expand=True, pady=(4, 4))
    lic.texto(area, T.L1_P1_GRAFICO, fonte=(FONTE, 9), cor=SUAVE)
    cv.bind("<Configure>", lambda _e: _dispersao(cv, conj))


def _dispersao(cv: tk.Canvas, conj) -> None:
    cv.delete("all")
    a = Area(cv)
    idx = _minutos_validos(conj)
    if not a.pronto() or len(idx) == 0:
        a.mensagem(T.ESTADO_SEM_DADOS_AINDA)
        return
    idx = idx[::max(1, len(idx) // 1500)]
    x, y = conj.dados["uso"][idx], conj.dados[ALVO][idx]
    a.definir(0, 100, _arredondar(float(y.min()) - 2, 5, False), _arredondar(float(y.max()) + 2, 5, True))
    a.eixos([(v, f"{v}") for v in range(0, 101, 20)], rotulo_y=T.L1_P1_EIXO_Y)
    cv.create_text(a.esq + a.largura / 2, cv.winfo_height() - 6, text=T.L1_P1_EIXO_X, fill=SUAVE, font=(FONTE, 8, "bold"))
    a.pontos(x, y, COR_TREINO, 1.8)


# ---------------- passo 2: treino e teste (e o erro de embaralhar) ----------------
def passo2(area: tk.Frame, lic: LicaoPassos) -> None:
    jan = lic.janela
    conj = jan.estado.conjunto()
    semente = _semente(conj)
    lic.texto(area, T.L1_P2)
    var = tk.BooleanVar(value=False)
    cv = novo_canvas(area, 230)
    bloco = tk.Frame(area, bg=CARTAO)

    def redesenhar(*_):
        _linha_do_tempo_treino_teste(cv, conj, var.get(), semente)

    def alternar() -> None:
        for w in bloco.winfo_children():
            w.destroy()
        redesenhar()
        if var.get():
            _comparar_embaralhado(bloco, lic, conj)

    ttk.Checkbutton(area, text=T.L1_P2_EMBARALHAR, variable=var, command=alternar).pack(anchor="w", pady=(0, 4))
    cv.pack(fill="both", expand=True, pady=(0, 4))
    bloco.pack(fill="x")
    cv.bind("<Configure>", redesenhar)
    area.embaralhar = var                       # usado pelos testes de interface
    area.alternar_embaralhar = alternar


def _linha_do_tempo_treino_teste(cv: tk.Canvas, conj, embaralhado: bool, semente: int) -> None:
    cv.delete("all")
    a = Area(cv)
    idx = _minutos_validos(conj)
    if not a.pronto() or len(idx) < 10:
        a.mensagem(T.ESTADO_SEM_DADOS_AINDA)
        return
    n = len(idx)
    y = conj.dados[ALVO][idx]
    a.definir(0, n, _arredondar(float(y.min()) - 2, 5, False), _arredondar(float(y.max()) + 2, 5, True))
    ticks = [(int(k * (n - 1) / 5), time.strftime("%d/%m", time.localtime(int(conj.ts[idx[int(k * (n - 1) / 5)]])))) for k in range(6)]
    if not embaralhado:
        tr, te = dividir_por_tempo(np.arange(n))
        a.faixa_x(0, len(tr), COR_FAIXA_TREINO, T.L1_P2_TREINO.format(n=_pt(len(tr))), COR_TREINO)
        a.faixa_x(len(tr), n, COR_FAIXA_TESTE, T.L1_P2_TESTE.format(n=_pt(len(te))), COR_TESTE)
        a.eixos(ticks, rotulo_y="temperatura (°C)")
        xs, ys = reduzir(np.arange(n, dtype=float), y, 900)
        a.linha(xs, ys, COR_REAL, 1)
        a.vertical(len(tr), COR_TESTE, 2, (5, 3))
        return
    tr, te = dividir_embaralhado(np.arange(n), semente)
    a.eixos(ticks, rotulo_y="temperatura (°C)")
    xs, ys = reduzir(np.arange(n, dtype=float), y, 900)
    a.linha(xs, ys, COR_REAL, 1)
    # cada minuto de teste vira uma marca laranja no meio dos minutos de treino: os vizinhos se misturam
    for i in te[::max(1, len(te) // 220)]:
        x = a.px(i)
        cv.create_line(x, a.topo + a.altura - 14, x, a.topo + a.altura, fill=COR_TESTE, width=1)
    cv.create_text(a.esq + 8, a.topo + 8, anchor="w", fill=COR_TESTE, font=(FONTE, 9, "bold"),
                   text="marcas laranja = minutos de teste misturados aos de treino")


def _comparar_embaralhado(bloco: tk.Frame, lic: LicaoPassos, conj) -> None:
    jan = lic.janela
    lic.texto(bloco, T.L1_P2_EMB_TEXTO)
    resultado = tk.Frame(bloco, bg=CARTAO)
    resultado.pack(fill="x")
    tk.Label(resultado, text=T.L1_P2_EMB_CALCULANDO, bg=CARTAO, fg=SUAVE, font=(FONTE, 9)).pack(anchor="w")

    def mostrar(emb) -> None:
        if not resultado.winfo_exists():
            return
        tempo_res = jan.estado.buscar("curva1", (tuple(ENTRADAS), "tempo", _semente(conj)))
        if tempo_res is None:
            return
        for w in resultado.winfo_children():
            w.destroy()
        te, em = min(tempo_res.mae_teste), min(emb.mae_teste)
        pct = (te - em) / te * 100
        modelo = T.L1_P2_EMB_COMPARA if pct >= 3 else T.L1_P2_EMB_PEQUENA
        lic.texto(resultado, modelo.format(tempo=br(te), emb=br(em), pct=f"{pct:.0f}"))

    def com_tempo(_r) -> None:
        if resultado.winfo_exists():
            _treinar_curva(jan, resultado, conj, ENTRADAS, "embaralhado", mostrar,
                           refazer=lambda: lic.mostrar(lic.indice))

    _treinar_curva(jan, resultado, conj, ENTRADAS, "tempo", com_tempo, refazer=lambda: lic.mostrar(lic.indice))


# ---------------- passo 3: simples ou complexo ----------------
def passo3(area: tk.Frame, lic: LicaoPassos) -> None:
    jan = lic.janela
    conj = jan.estado.conjunto()
    semente = _semente(conj)
    lic.texto(area, T.L1_P3)
    corpo = tk.Frame(area, bg=CARTAO)
    corpo.pack(fill="both", expand=True)
    _treinar_curva(jan, corpo, conj, ENTRADAS, "tempo", lambda r: _montar_passo3(corpo, lic, conj, r, semente),
                   refazer=lambda: lic.mostrar(lic.indice))


def _montar_passo3(corpo: tk.Frame, lic: LicaoPassos, conj, r, semente: int) -> None:
    if not corpo.winfo_exists():
        return
    estado = {"d": PROFUNDIDADE_INICIAL}
    cache_b: dict[int, tuple] = {}

    rotulo = tk.Label(corpo, text="", bg=CARTAO, fg=TEXTO, font=(FONTE, 10, "bold"), anchor="w")
    rotulo.pack(fill="x")
    escala = ttk.Scale(corpo, from_=1, to=20, orient="horizontal", length=520)
    escala.set(PROFUNDIDADE_INICIAL)
    escala.pack(anchor="w", pady=(0, 6))

    graficos = tk.Frame(corpo, bg=CARTAO)
    graficos.pack(fill="both", expand=True)
    graficos.columnconfigure(0, weight=1, uniform="g")
    graficos.columnconfigure(1, weight=1, uniform="g")
    graficos.rowconfigure(1, weight=1)
    tk.Label(graficos, text=T.L1_P3_GRAF_A, bg=CARTAO, fg=SUAVE, font=(FONTE, 9, "bold"), anchor="w").grid(row=0, column=0, sticky="w")
    titulo_b = tk.Label(graficos, text="", bg=CARTAO, fg=SUAVE, font=(FONTE, 9, "bold"), anchor="w")
    titulo_b.grid(row=0, column=1, sticky="w", padx=(10, 0))
    cv_a = novo_canvas(graficos, 220)
    cv_a.grid(row=1, column=0, sticky="nsew")
    cv_b = novo_canvas(graficos, 220)
    cv_b.grid(row=1, column=1, sticky="nsew", padx=(10, 0))
    mensagem = lic.texto(corpo, "")
    lic.texto(corpo, T.L1_P3_NOTA_VALIDACAO, fonte=(FONTE, 9), cor=SUAVE)

    def previsto(d: int):
        if d not in cache_b:
            cache_b[d] = previsto_x_real(conj, ENTRADAS, d, "tempo", semente)
        return cache_b[d]

    def desenhar_a() -> None:
        cv_a.delete("all")
        a = Area(cv_a)
        if not a.pronto():
            return
        a.definir(1, 20, 0, max(max(r.mae_treino), max(r.mae_teste), r.mae_linear) * 1.1)
        a.faixa_x(r.melhor_profundidade + 0.5, 20, COR_ALERTA_FAIXA, T.L1_P3_ZONA, "#c8695d")
        a.eixos([(v, str(v)) for v in (1, 5, 10, 15, 20)], casas_y=1, rotulo_y="°C")
        a.horizontal(r.mae_linear, SUAVE, 1, (4, 3))
        cv_a.create_text(a.esq + a.largura - 4, a.py(r.mae_linear) - 8, text=T.L1_P3_LINEAR, anchor="e", fill=SUAVE, font=(FONTE, 8))
        a.linha(r.profundidades, r.mae_treino, COR_TREINO, 2)
        a.linha(r.profundidades, r.mae_teste, COR_TESTE, 2)
        d = estado["d"]
        a.vertical(d, TEXTO, 1, (2, 3))
        a.pontos([d], [r.mae_treino[d - 1]], COR_TREINO, 4.5)
        a.pontos([d], [r.mae_teste[d - 1]], COR_TESTE, 4.5)
        a.legenda([(COR_TREINO, T.L1_P3_LEGENDA_TREINO), (COR_TESTE, T.L1_P3_LEGENDA_TESTE)])

    def desenhar_b() -> None:
        cv_b.delete("all")
        a = Area(cv_b)
        if not a.pronto():
            return
        ts, real, prev = previsto(estado["d"])
        n = len(ts)
        a.definir(0, n, _arredondar(float(min(real.min(), prev.min())) - 2, 5, False),
                  _arredondar(float(max(real.max(), prev.max())) + 2, 5, True))
        ticks = [(int(k * (n - 1) / 3), time.strftime("%d/%m", time.localtime(int(ts[int(k * (n - 1) / 3)])))) for k in range(4)]
        a.eixos(ticks, rotulo_y="°C")
        x = np.arange(n, dtype=float)
        a.linha(*reduzir(x, real, 500), COR_REAL, 1)
        a.linha(*reduzir(x, prev, 500), COR_PREVISTO, 1)
        a.legenda([(COR_REAL, T.L1_P3_LEGENDA_REAL), (COR_PREVISTO, T.L1_P3_LEGENDA_PREVISTO)])

    def atualizar_texto() -> None:
        d = estado["d"]
        tr, te = r.mae_treino[d - 1], r.mae_teste[d - 1]
        melhor = min(r.mae_teste)
        valores = T.L1_P3_VALORES.format(d=d, tr=br(tr), te=br(te))
        if te <= melhor * 1.03:
            frase = T.L1_P3_BOM
        elif d < r.melhor_profundidade:
            frase = T.L1_P3_SUBAJUSTE if te > 1.3 * melhor else T.L1_P3_MEIO
        else:
            frase = T.L1_P3_SOBRE.format(tr=br(tr), te=br(te)) if (te > 1.08 * melhor and tr < 0.7 * te) else T.L1_P3_MEIO
        mensagem.definir(f"**{valores}** {frase}")
        rotulo.config(text=T.L1_P3_CONTROLE.format(d=d))
        titulo_b.config(text=T.L1_P3_GRAF_B.format(d=d))

    def mudou(valor: str) -> None:
        d = int(round(float(valor)))
        if abs(float(valor) - d) > 1e-6:
            escala.set(d)                      # encaixa nos números inteiros (a profundidade não tem meio-termo)
            return
        if d != estado["d"]:
            estado["d"] = d
            atualizar_texto()
            desenhar_a()
            desenhar_b()

    escala.config(command=mudou)
    cv_a.bind("<Configure>", lambda _e: desenhar_a())
    cv_b.bind("<Configure>", lambda _e: desenhar_b())
    atualizar_texto()
    corpo.escala = escala                      # usado pelos testes de interface
    corpo.estado_passo3 = estado


# ---------------- passo 4: contra quem ele precisa ganhar ----------------
def passo4(area: tk.Frame, lic: LicaoPassos) -> None:
    jan = lic.janela
    conj = jan.estado.conjunto()
    lic.texto(area, T.L1_P4)
    corpo = tk.Frame(area, bg=CARTAO)
    corpo.pack(fill="both", expand=True)
    _treinar_curva(jan, corpo, conj, ENTRADAS, "tempo", lambda r: _montar_passo4(corpo, lic, r),
                   refazer=lambda: lic.mostrar(lic.indice))


def _montar_passo4(corpo: tk.Frame, lic: LicaoPassos, r) -> None:
    if not corpo.winfo_exists():
        return
    d = r.melhor_profundidade
    arvore = min(r.mae_teste)
    tk.Label(corpo, text=T.L1_P4_GRAF, bg=CARTAO, fg=SUAVE, font=(FONTE, 9, "bold"), anchor="w").pack(fill="x")
    cv = novo_canvas(corpo, 150)
    cv.pack(fill="x", pady=(2, 6))
    itens = [(T.L1_P4_BARRAS[0], r.mae_media, "#c9ced6"), (T.L1_P4_BARRAS[1], r.mae_linear, COR_TREINO),
             (T.L1_P4_BARRAS[2].format(d=d), arvore, COR_TESTE)]
    cv.bind("<Configure>", lambda _e: barras_horizontais(cv, itens))
    lic.texto(corpo, T.L1_P4_R2.format(a=br(r.r2_teste[d - 1], 2), b=br(r.r2_linear, 2)))
    if arvore >= r.mae_media and r.mae_linear >= r.mae_media:
        frase = T.L1_P4_NAO_VENCEU
    elif r.mae_linear <= arvore * 1.02:
        frase = T.L1_P4_LINEAR_VENCE
    else:
        frase = T.L1_P4_ARVORE_VENCE
    lic.texto(corpo, frase)
    corpo.barras = itens                       # usado pelos testes de interface


# ---------------- passo 5: o que ele aprendeu (e a armadilha da ventoinha) ----------------
def passo5(area: tk.Frame, lic: LicaoPassos) -> None:
    jan = lic.janela
    conj = jan.estado.conjunto()
    lic.texto(area, T.L1_P5)
    corpo = tk.Frame(area, bg=CARTAO)
    corpo.pack(fill="both", expand=True)
    _treinar_curva(jan, corpo, conj, ENTRADAS, "tempo", lambda r: _montar_passo5(corpo, lic, conj, r),
                   refazer=lambda: lic.mostrar(lic.indice))


def _montar_passo5(corpo: tk.Frame, lic: LicaoPassos, conj, r) -> None:
    if not corpo.winfo_exists():
        return
    jan = lic.janela
    d = r.melhor_profundidade
    imp = importancia(conj, ENTRADAS, d, "tempo", _semente(conj))
    ordenado = sorted(imp.items(), key=lambda kv: -kv[1])
    tk.Label(corpo, text=T.L1_P5_GRAF, bg=CARTAO, fg=SUAVE, font=(FONTE, 9, "bold"), anchor="w").pack(fill="x")
    cv = novo_canvas(corpo, 120)
    cv.pack(fill="x", pady=(2, 6))
    itens = [(VARIAVEIS[k][0], max(v, 0.0), COR_TESTE if k == ordenado[0][0] else COR_TREINO) for k, v in ordenado]
    cv.bind("<Configure>", lambda _e: barras_horizontais(cv, itens))
    lic.texto(corpo, T.L1_P5_TOPO.format(nome=VARIAVEIS[ordenado[0][0]][0]))
    lic.texto(corpo, T.L1_P5_FREQ)

    var = tk.BooleanVar(value=False)
    bloco = tk.Frame(corpo, bg=CARTAO)

    def alternar() -> None:
        for w in bloco.winfo_children():
            w.destroy()
        if not var.get():
            return
        n = int(conj.mascara(ENTRADAS_COM_VENTOINHA).sum())
        if n < MIN_LINHAS_VENTOINHA:
            lic.texto(bloco, T.L1_P5_VENT_POUCOS.format(n=n))
            return

        linhas = np.flatnonzero(conj.mascara(ENTRADAS_COM_VENTOINHA))
        mesmas = len(linhas) == len(np.flatnonzero(conj.mascara(ENTRADAS)))

        def mostrar(sem, com) -> None:
            if not bloco.winfo_exists():
                return
            for w in bloco.winfo_children():
                w.destroy()
            ra, rb = sem.r2_teste[sem.melhor_profundidade - 1], com.r2_teste[com.melhor_profundidade - 1]
            lic.texto(bloco, T.L1_P5_VENT_ANTES.format(a=br(min(sem.mae_teste)), ra=br(ra, 2)))
            lic.texto(bloco, T.L1_P5_VENT_DEPOIS.format(b=br(min(com.mae_teste)), rb=br(rb, 2)))
            if not mesmas:
                lic.texto(bloco, T.L1_P5_VENT_MESMAS_LINHAS, fonte=(FONTE, 9), cor=SUAVE)
            lic.texto(bloco, T.L1_P5_VENT_ALERTA if rb > ra + 0.02 else T.L1_P5_VENT_SEM_GANHO.format(ra=br(ra, 2), rb=br(rb, 2)))
            bloco.resultado = (min(sem.mae_teste), min(com.mae_teste), ra, rb)    # usado pelos testes

        def com_ventoinha(sem) -> None:
            if bloco.winfo_exists():
                _treinar_curva(jan, bloco, conj, ENTRADAS_COM_VENTOINHA, "tempo", lambda com: mostrar(sem, com),
                               refazer=alternar, linhas=linhas)

        if mesmas:
            com_ventoinha(r)                                # mesmos minutos: reaproveita o resultado do passo 3
        else:
            _treinar_curva(jan, bloco, conj, ENTRADAS, "tempo", com_ventoinha, refazer=alternar, linhas=linhas)

    ttk.Checkbutton(corpo, text=T.L1_P5_VENTOINHA, variable=var, command=alternar).pack(anchor="w", pady=(6, 2))
    bloco.pack(fill="x")
    corpo.ventoinha = var
    corpo.alternar_ventoinha = alternar
    corpo.bloco_ventoinha = bloco
    corpo.importancias = ordenado


# ---------------- passo 6: resumo e perguntas ----------------
def passo6(area: tk.Frame, lic: LicaoPassos) -> None:
    tk.Label(area, text=T.L1_P6, bg=CARTAO, fg=TEXTO, font=(FONTE, 10, "bold"), anchor="w").pack(fill="x")
    for item in T.L1_RESUMO:
        lic.texto(area, "•  " + item)
    quiz = Quiz(area, lic.janela, 1, T.L1_QUIZ)
    quiz.pack(fill="x", pady=(6, 0))
    area.quiz = quiz
