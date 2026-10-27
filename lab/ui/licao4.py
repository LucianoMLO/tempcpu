"""Lição 4 · Em qual faixa está? (classificação, acurácia que engana, matriz de confusão, precisão e revocação)."""
from __future__ import annotations

import tkinter as tk

import numpy as np

from lab import textos as T
from lab.dados import ALVO, ENTRADAS_PADRAO, dividir_por_tempo
from lab.modelos import episodios_de
from lab.modelos2 import classificar, limite_padrao, varrer_limiar
from lab.ui.controles import Escala, tabela, titulo_pequeno
from lab.ui.graficos import COR_BOM, COR_TESTE, COR_TREINO, Area, barras_horizontais, novo_canvas, reduzir_media
from lab.ui.passos import LicaoPassos, Passo
from lab.ui.quiz import Quiz
from tema import CARTAO, FONTE, SUAVE, TEXTO, ZONAS, br

LICAO = 4
COR_QUENTE = ZONAS["quente"][1]
COR_FAIXA_QUENTE = "#f9e2de"
LIMIARES = [round(0.05 * i, 2) for i in range(1, 20)]
VIZINHOS = [1, 3, 5, 7, 9, 15, 21, 31, 51]


def criar(janela) -> LicaoPassos:
    funcoes = [passo1, passo2, passo3, passo4, passo5, passo6, passo7]
    passos = [Passo(t, f) for t, f in zip(T.L4_PASSOS, funcoes)]

    def concluir() -> None:
        janela.estado.progresso.marcar_concluida(LICAO)
        janela.mostrar_inicio()

    return LicaoPassos(janela, LICAO, passos, ao_concluir=concluir)


def _pct(v: float) -> str:
    return br(100 * v, 0)


def _local(lic: LicaoPassos) -> dict:
    """Estado da lição: escolhas do aprendiz que valem em todos os passos e resultados já calculados."""
    if not hasattr(lic, "local"):
        conj = lic.janela.estado.conjunto(LICAO)
        lic.local = {"limite": limite_padrao(conj), "k": 15, "limiar": 0.5, "cache": {}}
    return lic.local


def _resultado(lic: LicaoPassos):
    """Classifica com o limite e o k atuais (guarda o resultado para não repetir o cálculo)."""
    conj = lic.janela.estado.conjunto(LICAO)
    loc = _local(lic)
    semente = conj.semente if conj.semente is not None else 7
    chave = (loc["limite"], loc["k"], semente)
    if chave not in loc["cache"]:
        loc["cache"][chave] = classificar(conj, loc["limite"], k_vizinhos=loc["k"], semente=semente)
    return loc["cache"][chave]


def _erro(pai, lic: LicaoPassos, e: Exception) -> None:
    lic.texto(pai, str(e), cor=COR_QUENTE)


def _limites_possiveis(conj) -> list[int]:
    idx = np.flatnonzero(conj.mascara(list(ENTRADAS_PADRAO)))
    t = conj.dados[ALVO][idx]
    lo, hi = int(round(np.percentile(t, 70))), int(round(np.percentile(t, 97)))
    return list(range(lo, max(hi, lo + 1) + 1))


# ---------------- passo 1: a pergunta ----------------
def passo1(area: tk.Frame, lic: LicaoPassos) -> None:
    jan = lic.janela
    conj = jan.estado.conjunto(LICAO)
    lic.aviso_qualidade(area, conj)
    lic.texto(area, T.L4_P1)
    loc = _local(lic)
    opcoes = _limites_possiveis(conj)
    if loc["limite"] not in opcoes:
        opcoes = sorted(set(opcoes) | {int(loc["limite"])})
    idx = np.flatnonzero(conj.mascara(list(ENTRADAS_PADRAO)))
    temp = conj.dados[ALVO][idx]
    tr, te = dividir_por_tempo(np.arange(len(idx)))
    cv = novo_canvas(area, 230)
    resumo = lic.texto(area, "")

    def desenhar(_e=None) -> None:
        cv.delete("all")
        a = Area(cv)
        if not a.pronto():
            return
        lim = loc["limite"]
        lo, hi = int(np.floor(temp.min())), int(np.ceil(temp.max()))
        contagens, bordas = np.histogram(temp, bins=np.arange(lo, hi + 2))
        a.definir(lo, hi + 1, 0, float(contagens.max()) * 1.08)
        a.eixos([(v, str(v)) for v in range(lo, hi + 1, max(1, (hi - lo) // 8))], rotulo_y=T.L4_P1_EIXO_Y)
        cv.create_text(a.esq + a.largura / 2, cv.winfo_height() - 6, text=T.L4_P1_EIXO_X, fill=SUAVE, font=(FONTE, 8, "bold"))
        for c, b0 in zip(contagens, bordas[:-1]):
            x0, x1 = a.px(b0) + 1, a.px(b0 + 1) - 1
            cv.create_rectangle(x0, a.py(c), x1, a.py(0), fill=COR_QUENTE if b0 + 0.5 > lim else COR_TREINO, width=0)
        a.vertical(lim, TEXTO, 1, (4, 3))

    def atualizar(v) -> None:
        loc["limite"] = int(v)
        lim = loc["limite"]
        acima = temp > lim
        resumo.definir(T.L4_P1_RESUMO.format(c=lim, p=_pct(acima.mean()), n=f"{int(acima.sum()):,}".replace(",", "."), t=f"{len(temp):,}".replace(",", "."),
                                             pt=_pct(acima[tr].mean()), pe=_pct(acima[te].mean())))
        desenhar()

    escala = Escala(area, opcoes, int(loc["limite"]), lambda v: T.L4_P1_ROTULO.format(c=v), atualizar, atraso=0)
    escala.pack(anchor="w")
    titulo_pequeno(area, T.L4_P1_GRAF).pack(fill="x")
    cv.pack(fill="both", expand=True)
    resumo.pack_forget()
    resumo.pack(fill="x", pady=(0, 6))
    lic.texto(area, T.L4_P1_FONTE, fonte=(FONTE, 9), cor=SUAVE)
    cv.bind("<Configure>", desenhar)
    atualizar(int(loc["limite"]))
    area.escala = escala                      # usados pelos testes de interface
    area.texto_resumo = resumo


# ---------------- passo 2: um primeiro classificador ----------------
def passo2(area: tk.Frame, lic: LicaoPassos) -> None:
    lic.texto(area, T.L4_P2)
    try:
        r = _resultado(lic)
    except ValueError as e:
        _erro(area, lic, e)
        return
    titulo_pequeno(area, T.L4_P2_GRAF).pack(fill="x")
    cv = novo_canvas(area, 220)
    cv.pack(fill="both", expand=True)
    m = r.modelos["logistica"]
    lic.texto(area, T.L4_P2_ACERTO.format(a=_pct(m["acuracia"]), n=f"{r.n_teste:,}".replace(",", ".")))

    def desenhar(_e=None) -> None:
        cv.delete("all")
        a = Area(cv)
        if not a.pronto():
            return
        n = len(r.probabilidade)
        a.definir(0, n, 0, 1)
        for ini, fim in episodios_de(r.verdade):
            a.faixa_x(ini, fim, COR_FAIXA_QUENTE)
        a.eixos(None, casas_y=1)
        x, y = reduzir_media(np.arange(n, dtype=float), r.probabilidade, 900)
        a.linha(x, y, COR_TREINO, 1)
        a.horizontal(0.5, SUAVE, 1, (4, 3))
        a.legenda([(COR_TREINO, T.L4_P2_LEGENDA_PROB), (COR_FAIXA_QUENTE, T.L4_P2_LEGENDA_REAL)])

    cv.bind("<Configure>", desenhar)
    area.resultado = r


# ---------------- passo 3: a acurácia engana ----------------
def passo3(area: tk.Frame, lic: LicaoPassos) -> None:
    try:
        r = _resultado(lic)
    except ValueError as e:
        _erro(area, lic, e)
        return
    m = r.modelos["logistica"]
    lic.texto(area, T.L4_P3.format(a=_pct(m["acuracia"])))
    titulo_pequeno(area, T.L4_P3_BARRAS).pack(fill="x")
    cv = novo_canvas(area, 170)
    cv.pack(fill="x")
    itens = [(f"{T.L4_P3_PREGUICOSO}: acurácia", 100 * r.sempre_normal_acuracia, COR_TESTE),
             (f"{T.L4_P3_LOGISTICA}: acurácia", 100 * m["acuracia"], COR_BOM),
             (f"{T.L4_P3_PREGUICOSO}: calor achado", 0.0, COR_TESTE),
             (f"{T.L4_P3_LOGISTICA}: calor achado", 100 * (m["revocacao"] or 0.0), COR_BOM)]
    cv.bind("<Configure>", lambda _e: barras_horizontais(cv, itens, formato=lambda v: f"{v:.0f}%", rotulo_largura=250))
    lic.texto(area, T.L4_P3_CONCLUSAO.format(pa=_pct(r.sempre_normal_acuracia), la=_pct(m["acuracia"]), lr=_pct(m["revocacao"] or 0.0)))
    area.resultado = r


# ---------------- passo 4: matriz de confusão ----------------
def passo4(area: tk.Frame, lic: LicaoPassos) -> None:
    lic.texto(area, T.L4_P4)
    try:
        r = _resultado(lic)
    except ValueError as e:
        _erro(area, lic, e)
        return
    (vn, fp), (fn, vp) = r.modelos["logistica"]["matriz"]
    grade = tk.Frame(area, bg=CARTAO)
    grade.pack(pady=(4, 8))
    tk.Label(grade, text=T.L4_P4_TITULO_PREVISTO, bg=CARTAO, fg=SUAVE, font=(FONTE, 9, "bold")).grid(row=0, column=1, columnspan=2, pady=(0, 4))
    tk.Label(grade, text=T.L4_P4_TITULO_REAL, bg=CARTAO, fg=SUAVE, font=(FONTE, 9, "bold"), wraplength=90).grid(row=1, column=0, rowspan=2, padx=(0, 8))
    celulas = [(vn, T.L4_P4_CELULAS[0], COR_BOM), (fp, T.L4_P4_CELULAS[1], COR_TESTE), (fn, T.L4_P4_CELULAS[2], COR_QUENTE), (vp, T.L4_P4_CELULAS[3], COR_BOM)]
    for k, (n, rotulo, cor) in enumerate(celulas):
        c = tk.Frame(grade, bg=CARTAO, highlightbackground=cor, highlightthickness=2, width=190, height=86)
        c.grid(row=1 + k // 2, column=1 + k % 2, padx=3, pady=3)
        c.grid_propagate(False)
        tk.Label(c, text=f"{n:,}".replace(",", "."), bg=CARTAO, fg=cor, font=(FONTE, 18, "bold")).place(relx=0.5, rely=0.36, anchor="center")
        tk.Label(c, text=rotulo, bg=CARTAO, fg=TEXTO, font=(FONTE, 9)).place(relx=0.5, rely=0.74, anchor="center")
    lic.texto(area, T.L4_P4_FRASE.format(q=f"{vp + fn:,}".replace(",", "."), vp=f"{vp:,}".replace(",", "."), fn=f"{fn:,}".replace(",", "."),
                                         nm=f"{vn + fp:,}".replace(",", "."), fp=f"{fp:,}".replace(",", ".")))
    area.resultado = r


# ---------------- passo 5: precisão e revocação ----------------
def passo5(area: tk.Frame, lic: LicaoPassos) -> None:
    lic.texto(area, T.L4_P5)
    try:
        r = _resultado(lic)
    except ValueError as e:
        _erro(area, lic, e)
        return
    loc = _local(lic)
    curva = varrer_limiar(r.probabilidade, r.verdade, LIMIARES)
    quentes = int(r.verdade.sum())
    cv = novo_canvas(area, 220)
    valores = lic.texto(area, "")

    def desenhar(_e=None) -> None:
        cv.delete("all")
        a = Area(cv)
        if not a.pronto():
            return
        a.definir(0, 1, 0, 1.02)
        a.eixos([(v, f"{int(v * 100)}%") for v in (0.0, 0.25, 0.5, 0.75, 1.0)], casas_y=1)
        pr = [(c["limiar"], c["precisao"]) for c in curva if c["precisao"] is not None]
        a.linha([x for x, _ in pr], [y for _, y in pr], COR_TREINO, 2)
        a.linha([c["limiar"] for c in curva], [c["revocacao"] or 0.0 for c in curva], COR_TESTE, 2)
        a.vertical(loc["limiar"], TEXTO, 1, (2, 3))
        a.legenda([(COR_TREINO, T.L4_P5_LEG_PRECISAO), (COR_TESTE, T.L4_P5_LEG_REVOCACAO)])

    def atualizar(v) -> None:
        loc["limiar"] = float(v)
        c = next(x for x in curva if abs(x["limiar"] - float(v)) < 1e-9)
        if c["alarmes"] == 0:
            valores.definir(T.L4_P5_SEM_AVISOS)
        else:
            vp = round((c["precisao"] or 0.0) * c["alarmes"])
            valores.definir(T.L4_P5_VALORES.format(al=f"{c['alarmes']:,}".replace(",", "."), pr=_pct(c["precisao"] or 0.0), rv=_pct(c["revocacao"] or 0.0),
                                                   vp=f"{vp:,}".replace(",", "."), q=f"{quentes:,}".replace(",", ".")))
        desenhar()

    escala = Escala(area, LIMIARES, min(LIMIARES, key=lambda x: abs(x - loc["limiar"])), lambda v: T.L4_P5_ROTULO.format(p=int(round(v * 100))), atualizar, atraso=0)
    escala.pack(anchor="w")
    titulo_pequeno(area, T.L4_P5_GRAF).pack(fill="x")
    cv.pack(fill="both", expand=True)
    valores.pack_forget()
    valores.pack(fill="x", pady=(0, 4))
    lic.texto(area, T.L4_P5_DICA, fonte=(FONTE, 9), cor=SUAVE)
    cv.bind("<Configure>", desenhar)
    atualizar(loc["limiar"] if loc["limiar"] in LIMIARES else 0.5)
    area.escala = escala
    area.texto_valores = valores
    area.curva = curva


# ---------------- passo 6: outros classificadores ----------------
def passo6(area: tk.Frame, lic: LicaoPassos) -> None:
    lic.texto(area, T.L4_P6)
    loc = _local(lic)
    corpo = tk.Frame(area, bg=CARTAO)
    conclusao = lic.texto(area, "")

    def mostrar(k) -> None:
        loc["k"] = int(k)
        for w in corpo.winfo_children():
            w.destroy()
        try:
            r = _resultado(lic)
        except ValueError as e:
            tk.Label(corpo, text=str(e), bg=CARTAO, fg=COR_QUENTE, font=(FONTE, 10), wraplength=700, justify="left").pack(anchor="w")
            return
        linhas = []
        for chave in ("logistica", "arvore", "vizinhos"):
            m = r.modelos[chave]
            linhas.append([T.L4_P6_NOMES[chave], _pct(m["acuracia"]) + "%", "-" if m["precisao"] is None else _pct(m["precisao"]) + "%",
                           "-" if m["revocacao"] is None else _pct(m["revocacao"]) + "%"])
        tabela(corpo, T.L4_P6_COLUNAS, linhas, larguras=[22, 12, 12, 12]).pack(anchor="w", pady=(4, 6))
        acs = [100 * r.modelos[c]["acuracia"] for c in r.modelos]
        conclusao.definir(T.L4_P6_CONCLUSAO.format(a1=br(min(acs), 1), a2=br(max(acs), 1)))
        corpo.resultado = r

    escala = Escala(area, VIZINHOS, loc["k"] if loc["k"] in VIZINHOS else 15, lambda v: T.L4_P6_ROTULO.format(k=v), mostrar, atraso=250, comprimento=360)
    escala.pack(anchor="w")
    corpo.pack(fill="x")
    conclusao.pack_forget()
    conclusao.pack(fill="x")
    mostrar(escala.valor)
    area.escala = escala
    area.tabela = corpo


# ---------------- passo 7: resumo e perguntas ----------------
def passo7(area: tk.Frame, lic: LicaoPassos) -> None:
    tk.Label(area, text=T.L4_P7, bg=CARTAO, fg=TEXTO, font=(FONTE, 10, "bold"), anchor="w").pack(fill="x")
    for item in T.L4_RESUMO:
        lic.texto(area, "•  " + item)
    quiz = Quiz(area, lic.janela, LICAO, T.L4_QUIZ)
    quiz.pack(fill="x", pady=(6, 0))
    area.quiz = quiz
