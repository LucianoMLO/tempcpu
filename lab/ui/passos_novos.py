"""Passos novos das lições 1 a 3 (v1.2): validação cruzada, boosting, Isolation Forest, Ridge e Lasso."""
from __future__ import annotations

import tkinter as tk
from dataclasses import replace

import numpy as np

from lab import textos as T
from lab.dados import ENTRADAS_PADRAO
from lab.modelos import amostra_de, episodios_de
from lab.modelos2 import (FORCAS, comparar_deteccao, curva_boosting, regularizacao, treinar_isolamento, validacao_cruzada)
from lab.sintetico import gerar
from lab.ui.controles import Escala, titulo_pequeno
from lab.ui.graficos import COR_BOM, COR_PREVISTO, COR_REAL, COR_TESTE, COR_TREINO, Area, novo_canvas
from lab.ui.passos import LicaoPassos, botao
from tema import CARTAO, FONTE, SUAVE, TEXTO, ZONAS, br

ENTRADAS = list(ENTRADAS_PADRAO)
COR_RIDGE = "#8a6bb8"
COR_LASSO = ZONAS["normal"][1]


def _semente(conj) -> int:
    return conj.semente if conj.semente is not None else 7


# =========================== Lição 1 · validação cruzada ===========================
def passo_validacao(area: tk.Frame, lic: LicaoPassos) -> None:
    jan = lic.janela
    conj = jan.estado.conjunto()
    semente = _semente(conj)
    lic.texto(area, T.L1_P7)
    corpo = tk.Frame(area, bg=CARTAO)
    corpo.pack(fill="both", expand=True)
    jan.treinar(corpo, "validacao1", (tuple(ENTRADAS), semente),
                lambda progresso, cancelar: validacao_cruzada(conj, ENTRADAS, semente, progresso=progresso, cancelar=cancelar),
                ao_pronto=lambda r: _montar_validacao(corpo, lic, r), refazer=lambda: lic.mostrar(lic.indice))


def _montar_validacao(corpo: tk.Frame, lic: LicaoPassos, r) -> None:
    if not corpo.winfo_exists():
        return
    estado = {"revelado": False}
    d = r.escolhida
    titulo_pequeno(corpo, T.L1_P7_GRAF).pack(fill="x")
    cv = novo_canvas(corpo, 240)
    cv.pack(fill="both", expand=True)
    lic.texto(corpo, T.L1_P7_ESCOLHA.format(d=d, e=br(r.erro_validacao[d - 1], 2), dp=br(r.desvio_validacao[d - 1], 2)))
    linha_botao = tk.Frame(corpo, bg=CARTAO)
    linha_botao.pack(fill="x", pady=(4, 4))
    revela = lic.texto(corpo, "")
    lic.texto(corpo, T.L1_P7_NOTA, fonte=(FONTE, 9), cor=SUAVE)

    def desenhar(_e=None) -> None:
        cv.delete("all")
        a = Area(cv)
        if not a.pronto():
            return
        sup = [m + s for m, s in zip(r.erro_validacao, r.desvio_validacao)]
        inf = [max(0.0, m - s) for m, s in zip(r.erro_validacao, r.desvio_validacao)]
        topo = max(sup + (r.erro_teste if estado["revelado"] else []))
        a.definir(1, 20, 0, topo * 1.08)
        a.eixos([(v, str(v)) for v in (1, 5, 10, 15, 20)], casas_y=1, rotulo_y="°C")
        a.linha(r.profundidades, sup, COR_TREINO, 1, (3, 3))
        a.linha(r.profundidades, inf, COR_TREINO, 1, (3, 3))
        a.linha(r.profundidades, r.erro_validacao, COR_TREINO, 2)
        a.vertical(d, TEXTO, 1, (2, 3))
        a.pontos([d], [r.erro_validacao[d - 1]], COR_TREINO, 4.5)
        itens = [(COR_TREINO, T.L1_P7_LEGENDA_VALIDACAO)]
        if estado["revelado"]:
            a.linha(r.profundidades, r.erro_teste, COR_TESTE, 2)
            a.pontos([d], [r.erro_teste[d - 1]], COR_TESTE, 4.5)
            itens.append((COR_TESTE, T.L1_P7_LEGENDA_TESTE))
        a.legenda(itens)

    def revelar() -> None:
        estado["revelado"] = True
        botao_revelar.config(state="disabled")
        et = r.erro_teste_escolhida
        p, ep = r.preferida_pelo_teste, r.erro_teste[r.preferida_pelo_teste - 1]
        if p == d:
            revela.definir(T.L1_P7_REVELA_IGUAL.format(d=d, et=br(et, 2)))
        else:
            dif = et - ep
            revela.definir(T.L1_P7_REVELA_DIFERENTE.format(d=d, et=br(et, 2), p=p, ep=br(ep, 2), dif=br(dif, 2),
                                                           adjetivo=T.L1_P7_PEQUENA if dif <= 0.05 else T.L1_P7_NOTAVEL))
        desenhar()

    botao_revelar = botao(linha_botao, T.L1_P7_BOTAO, revelar, destaque=True)
    botao_revelar.pack(side="left")
    cv.bind("<Configure>", desenhar)
    corpo.resultado = r                      # usados pelos testes de interface
    corpo.revelar = revelar
    corpo.texto_revela = revela


# =========================== Lição 1 · boosting ===========================
def passo_boosting(area: tk.Frame, lic: LicaoPassos) -> None:
    jan = lic.janela
    conj = jan.estado.conjunto()
    semente = _semente(conj)
    lic.texto(area, T.L1_P8)
    corpo = tk.Frame(area, bg=CARTAO)
    corpo.pack(fill="both", expand=True)
    jan.treinar(corpo, "boosting1", (tuple(ENTRADAS), semente),
                lambda progresso, cancelar: curva_boosting(conj, ENTRADAS, semente, progresso=progresso, cancelar=cancelar),
                ao_pronto=lambda r: _montar_boosting(corpo, lic, r), refazer=lambda: lic.mostrar(lic.indice))


def _montar_boosting(corpo: tk.Frame, lic: LicaoPassos, r) -> None:
    if not corpo.winfo_exists():
        return
    inicial = 10
    estado = {"n": inicial}
    escala = Escala(corpo, r.rodadas, inicial, lambda v: T.L1_P8_ROTULO.format(n=v), lambda v: atualizar(v), atraso=0)
    escala.pack(anchor="w")
    titulo_pequeno(corpo, T.L1_P8_GRAF).pack(fill="x")
    cv = novo_canvas(corpo, 240)
    cv.pack(fill="both", expand=True)
    texto = lic.texto(corpo, "")
    compara = lic.texto(corpo, "")

    def desenhar(_e=None) -> None:
        cv.delete("all")
        a = Area(cv)
        if not a.pronto():
            return
        topo = max(max(r.erro_teste[:60]), r.erro_arvore, r.erro_floresta, r.erro_linear) * 1.05
        a.definir(1, len(r.rodadas), 0, topo)
        a.eixos([(v, str(v)) for v in (1, 50, 100, 150, 200) if v <= len(r.rodadas)], casas_y=1, rotulo_y="°C")
        for valor, cor, rot in ((r.erro_arvore, "#9a6fb0", T.L1_P8_LINHA_ARVORE), (r.erro_floresta, COR_BOM, T.L1_P8_LINHA_FLORESTA),
                                (r.erro_linear, SUAVE, T.L1_P8_LINHA_LINEAR)):
            a.horizontal(valor, cor, 1, (4, 3))
        a.linha(r.rodadas, r.erro_treino, COR_TREINO, 2)
        a.linha(r.rodadas, r.erro_teste, COR_TESTE, 2)
        n = estado["n"]
        a.vertical(n, TEXTO, 1, (2, 3))
        a.pontos([n], [r.erro_treino[n - 1]], COR_TREINO, 4.5)
        a.pontos([n], [r.erro_teste[n - 1]], COR_TESTE, 4.5)
        a.legenda([(COR_TREINO, T.L1_P8_LEGENDA_TREINO), (COR_TESTE, T.L1_P8_LEGENDA_TESTE), ("#9a6fb0", T.L1_P8_LINHA_ARVORE),
                   (COR_BOM, T.L1_P8_LINHA_FLORESTA), (SUAVE, T.L1_P8_LINHA_LINEAR)])

    def atualizar(n: int) -> None:
        estado["n"] = int(n)
        n = int(n)
        te, tr = r.erro_teste[n - 1], r.erro_treino[n - 1]
        frases = [T.L1_P8_VALORES.format(n=n, tr=br(tr, 2), te=br(te, 2))]
        if n <= 10:
            frases.append(T.L1_P8_POUCAS)
        elif te <= min(r.erro_teste) * 1.01:
            frases.append(T.L1_P8_MUITAS)
        texto.definir("  ".join(frases))
        desenhar()

    m = min(r.erro_teste)
    final = [T.L1_P8_COMPARA.format(arv=br(r.erro_arvore, 2), flo=br(r.erro_floresta, 2), lin=br(r.erro_linear, 2),
                                    m=br(m, 2), r=r.melhor_rodada),
             T.L1_P8_MELHOR.format(arv=br(r.erro_arvore, 2)) if m < r.erro_arvore else T.L1_P8_PIOR.format(arv=br(r.erro_arvore, 2)),
             T.L1_P8_LINEAR_EMPATA if m <= r.erro_linear * 1.05 else T.L1_P8_LINEAR_VENCE]
    compara.definir("  ".join(final))
    cv.bind("<Configure>", desenhar)
    atualizar(inicial)
    corpo.escala = escala
    corpo.resultado = r
    corpo.texto_valores = texto
    corpo.texto_compara = compara


# =========================== Lição 2 · Isolation Forest ===========================
def passo_isolamento(area: tk.Frame, lic: LicaoPassos) -> None:
    from lab.ui.licao2 import _treinar
    jan = lic.janela
    conj = jan.estado.conjunto(2)
    semente = _semente(conj)
    lic.aviso_qualidade(area, conj)
    lic.texto(area, T.L2_P7)
    corpo = tk.Frame(area, bg=CARTAO)
    corpo.pack(fill="both", expand=True)
    refazer = lambda: lic.mostrar(lic.indice)

    def com_residuo(res) -> None:
        if not corpo.winfo_exists():
            return
        jan.treinar(corpo, "isolamento", (semente,), lambda progresso, cancelar: treinar_isolamento(conj, res, semente, progresso, cancelar),
                    ao_pronto=lambda iso: _montar_isolamento(corpo, lic, res, iso), refazer=refazer, licao=2)

    _treinar(jan, corpo, conj, com_residuo, refazer)


def _faixa(cv: tk.Canvas, y: float, altura: float, n: int, marcado: np.ndarray, cor: str, rotulo: str, esq: int, larg: float) -> None:
    cv.create_text(esq - 8, y + altura / 2, text=rotulo, anchor="e", fill=TEXTO, font=(FONTE, 8))
    cv.create_rectangle(esq, y, esq + larg, y + altura, fill="#f1f3f7", width=0)
    for a, b in episodios_de(marcado):
        cv.create_rectangle(esq + a / n * larg, y, max(esq + b / n * larg, esq + a / n * larg + 2), y + altura, fill=cor, width=0)


def _montar_isolamento(corpo: tk.Frame, lic: LicaoPassos, res, iso) -> None:
    if not corpo.winfo_exists():
        return
    prova = ~res.no_treino
    escala_pct = Escala(corpo, list(range(1, 16)), 5, lambda v: T.L2_P7_ROTULO.format(p=v), lambda v: atualizar(int(v)), atraso=150)
    escala_pct.pack(anchor="w")
    cv = novo_canvas(corpo, 140)
    cv.pack(fill="x", pady=(2, 4))
    titulo_pequeno(corpo, T.L2_P7_TABELA_TITULO).pack(fill="x")
    linhas = lic.texto(corpo, "")
    fim = lic.texto(corpo, "", fonte=(FONTE, 9), cor=SUAVE)
    estado = {"d": None}

    def desenhar(_e=None) -> None:
        cv.delete("all")
        d = estado["d"]
        if d is None or cv.winfo_width() < 200:
            return
        n = int(prova.sum())
        esq, larg = 200, cv.winfo_width() - 220
        linhas_faixa = []
        if res.verdade is not None:
            linhas_faixa.append((res.verdade[prova], ZONAS["quente"][1], T.L2_P7_FAIXA_VERDADE))
        linhas_faixa.append((d["res_marcado"][prova], COR_TESTE, T.L2_P7_FAIXA_RESIDUO))
        linhas_faixa.append((d["iso_marcado"][prova], COR_TREINO, T.L2_P7_FAIXA_ISOLAMENTO))
        for k, (m, cor, rot) in enumerate(linhas_faixa):
            _faixa(cv, 10 + k * 40, 28, n, m, cor, rot, esq, larg)

    def atualizar(pct: int) -> None:
        d = comparar_deteccao(res, iso, float(pct))
        estado["d"] = d
        if res.verdade is not None:
            nr = d["n_reais"]
            partes = [T.L2_P7_LINHA_SINT.format(nome=T.L2_METODO_RESIDUO, a=round(d["res_recall"] * nr) if d["res_recall"] is not None else 0, n=nr, f=br(d["res_falsos"], 1)),
                      T.L2_P7_LINHA_SINT.format(nome=T.L2_METODO_ISOLAMENTO, a=round(d["iso_recall"] * nr) if d["iso_recall"] is not None else 0, n=nr, f=br(d["iso_falsos"], 1))]
            ficou = (d["iso_recall"] or 0) > (d["res_recall"] or 0)
            fim.definir(T.L2_P7_FIM_SINT_ISO_MELHOR if ficou else T.L2_P7_FIM_SINT_RES)
        else:
            partes = [T.L2_P7_LINHA_REAL.format(nome=T.L2_METODO_RESIDUO, e=d["res_episodios"]),
                      T.L2_P7_LINHA_REAL.format(nome=T.L2_METODO_ISOLAMENTO, e=d["iso_episodios"])]
            fim.definir(T.L2_P7_FIM_REAL)
        linhas.definir("\n".join(partes))
        desenhar()

    cv.bind("<Configure>", desenhar)
    atualizar(5)
    corpo.escala = escala_pct
    corpo.estado = estado
    corpo.texto_linhas = linhas


# =========================== Lição 3 · Ridge e Lasso ===========================
MINUTOS = list(range(40, 601, 20))
CORRELACAO_PASSO = 0.95


def passo_regularizacao(area: tk.Frame, lic: LicaoPassos) -> None:
    jan = lic.janela
    est = jan.estado
    lic.texto(area, T.L3_P7)
    estado = {"minutos": 100, "semente": 1, "forca": 0.03, "r": None, "gab": None}

    controles = tk.Frame(area, bg=CARTAO)
    controles.pack(fill="x")
    graficos = tk.Frame(area, bg=CARTAO)
    graficos.pack(fill="both", expand=True)
    for c in range(3):
        graficos.columnconfigure(c, weight=1, uniform="r")
    cvs = []
    titulos = (T.L3_P7_GRAF_USO, T.L3_P7_GRAF_FREQ, T.L3_P7_GRAF_ERRO)
    for c, tit in enumerate(titulos):
        titulo_pequeno(graficos, tit).grid(row=0, column=c, sticky="w", padx=(0 if c == 0 else 8, 0))
        cv = novo_canvas(graficos, 190)
        cv.grid(row=1, column=c, sticky="nsew", padx=(0 if c == 0 else 8, 0))
        cvs.append(cv)
    valores = lic.texto(area, "")
    zerou = lic.texto(area, "")
    erro_txt = lic.texto(area, "", fonte=(FONTE, 9), cor=SUAVE)
    lic.texto(area, T.L3_P7_NOTA, fonte=(FONTE, 9), cor=SUAVE)

    def recalcular() -> None:
        p = replace(est.params, correlacao_uso_freq=CORRELACAO_PASSO, episodios=0, semente=estado["semente"])
        grande = gerar(p)
        amostra = amostra_de(grande, estado["minutos"], estado["semente"])
        estado["r"] = regularizacao(amostra, semente=estado["semente"])
        estado["gab"] = amostra.gabarito
        redesenhar()

    def desenhar(cv: tk.Canvas, idx: int) -> None:
        r, g = estado["r"], estado["gab"]
        cv.delete("all")
        a = Area(cv, margem=(46, 10, 14, 30))
        if r is None or not a.pronto():
            return
        k = list(range(len(FORCAS)))
        if idx == 0:
            series = {"linear": [r.linear["uso"]] * len(k), "ridge": [c["uso"] for c in r.ridge], "lasso": [c["uso"] for c in r.lasso]}
            verdade = g["uso"]
        elif idx == 1:
            series = {"linear": [r.linear["freq"] * 500] * len(k), "ridge": [c["freq"] * 500 for c in r.ridge], "lasso": [c["freq"] * 500 for c in r.lasso]}
            verdade = 0.0
        else:
            series = dict(r.mae_teste)
            verdade = None
        todos = [v for s in series.values() for v in s] + ([verdade] if verdade is not None else [])
        lo, hi = min(todos), max(todos)
        folga = (hi - lo) * 0.12 or 0.1
        a.definir(0, len(k) - 1, lo - folga if idx != 2 else max(0.0, lo - folga), hi + folga)
        a.eixos([(i, f"{FORCAS[i]:g}".replace(".", ",")) for i in (0, 3, 5, 7, 9)], casas_y=2 if idx != 2 else 1)
        if verdade is not None:
            a.horizontal(verdade, TEXTO, 1, (4, 3))
        a.linha(k, series["linear"], SUAVE, 1, (4, 3))
        a.linha(k, series["ridge"], COR_RIDGE, 2)
        a.linha(k, series["lasso"], COR_LASSO, 2)
        i = FORCAS.index(estado["forca"])
        a.vertical(i, TEXTO, 1, (2, 3))
        if idx == 0:
            a.legenda([(TEXTO, T.L3_P7_LEG_VERDADE), (SUAVE, T.L3_P7_LEG_LINEAR), (COR_RIDGE, T.L3_P7_LEG_RIDGE), (COR_LASSO, T.L3_P7_LEG_LASSO)], y=6)

    def redesenhar() -> None:
        r, g = estado["r"], estado["gab"]
        if r is None:
            return
        for i, cv in enumerate(cvs):
            desenhar(cv, i)
        i = FORCAS.index(estado["forca"])
        rd, ls = r.ridge[i], r.lasso[i]
        f = lambda v, c=2: br(v, c)
        valores.definir(T.L3_P7_VALORES.format(f=f"{estado['forca']:g}".replace(".", ","), ru=f(rd["uso"]), vu=f(g["uso"]), rf=f(rd["freq"] * 500),
                                               lu=f(ls["uso"]), lf=f(ls["freq"] * 500), nu=f(r.linear["uso"]), nf=f(r.linear["freq"] * 500)))
        z = r.zerados_lasso[i]
        if z:
            frase = T.L3_P7_ZEROU.format(lista=", ".join(z))
            if "freq" in z:
                frase += " " + T.L3_P7_FREQ_ZERADA
        else:
            frase = T.L3_P7_ZEROU_NADA
        zerou.definir(frase)
        partes = [T.L3_P7_ERRO_PREVISAO.format(el=br(r.mae_teste["linear"][i], 2), er=br(r.mae_teste["ridge"][i], 2), es=br(r.mae_teste["lasso"][i], 2))]
        if max(r.mae_teste["ridge"][i], r.mae_teste["lasso"][i]) > r.mae_teste["linear"][i] * 1.25:
            partes.append(T.L3_P7_REGULARIZAR_DEMAIS)
        erro_txt.definir("  ".join(partes))

    def mudou_forca(v) -> None:
        estado["forca"] = v
        redesenhar()

    def mudou_minutos(v) -> None:
        estado["minutos"] = int(v)
        recalcular()

    def nova() -> None:
        estado["semente"] += 1
        recalcular()

    f_escala = Escala(controles, FORCAS, 0.03, lambda v: T.L3_P7_FORCA.format(f=f"{v:g}".replace(".", ",")), mudou_forca, atraso=0)
    f_escala.pack(side="left", padx=(0, 20))
    m_escala = Escala(controles, MINUTOS, 100, lambda v: T.L3_P7_MINUTOS.format(n=v), mudou_minutos, atraso=250, comprimento=300)
    m_escala.pack(side="left")
    botao(controles, T.L3_P7_NOVA_AMOSTRA, nova).pack(side="left", padx=14)
    for i, cv in enumerate(cvs):
        cv.bind("<Configure>", lambda _e, i=i, cv=cv: desenhar(cv, i))
    recalcular()
    area.estado_reg = estado                  # usados pelos testes de interface
    area.escala_forca = f_escala
    area.escala_minutos = m_escala
    area.texto_valores = valores
    area.texto_zerou = zerou
    area.botao_nova = lambda: nova()
