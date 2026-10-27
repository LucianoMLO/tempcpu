"""Lição 3 · Dados sintéticos com gabarito (o que o modelo descobre quando você sabe a resposta certa)."""
from __future__ import annotations

import random
import tkinter as tk
from dataclasses import replace
from tkinter import ttk

import numpy as np

from lab import textos as T
from lab.modelos import ajustar_linear, avaliar_descoberta, comparar_gabarito, treinar_anomalia
from lab.sintetico import AMPLITUDE_HORA_C, BASE_C, DERIVA_DESVIO_C, ParametrosSinteticos, gerar
from lab.ui.graficos import COR_BOM, COR_TESTE, COR_TREINO, Area, barras_horizontais, novo_canvas
from lab.ui.licao2 import _barras_semanais
from lab.ui.passos import LicaoPassos, Passo, botao
from lab.ui.quiz import Quiz
from tema import CARTAO, FONTE, SUAVE, TEXTO, ZONAS, br

LICAO = 3
# campo, mínimo, máximo, passo, casas decimais
CONTROLES = [("dias", 3, 30, 1, 0), ("ruido_c", 0.5, 6.0, 0.1, 1), ("efeito_uso", 0.10, 0.60, 0.01, 2),
             ("efeito_tomada", 0.0, 10.0, 0.5, 1), ("poeira_por_dia", 0.0, 0.30, 0.01, 2),
             ("correlacao_uso_freq", 0.0, 0.95, 0.05, 2), ("episodios", 0, 30, 1, 0)]
COR_PERTO, COR_MEIO, COR_LONGE = ZONAS["normal"][1], ZONAS["atencao"][1], ZONAS["quente"][1]


def criar(janela) -> LicaoPassos:
    from lab.ui.passos_novos import passo_regularizacao
    funcoes = [passo1, passo2, passo3, passo4, passo5, passo_regularizacao, passo6]
    passos = [Passo(t, f) for t, f in zip(T.L3_PASSOS, funcoes)]

    def concluir() -> None:
        janela.estado.progresso.marcar_concluida(LICAO)
        janela.mostrar_inicio()

    return LicaoPassos(janela, LICAO, passos, ao_concluir=concluir)


def _valor(campo: str, v: float):
    return int(round(v)) if campo == "dias" else round(float(v), 4)


# ---------------- passo 1: gerar os dados ----------------
def passo1(area: tk.Frame, lic: LicaoPassos) -> None:
    jan = lic.janela
    est = jan.estado
    lic.texto(area, T.L3_P1)
    grade = tk.Frame(area, bg=CARTAO)
    grade.pack(fill="both", expand=True)
    grade.columnconfigure(0, weight=0)
    grade.columnconfigure(1, weight=1)
    grade.rowconfigure(0, weight=1)

    esq = tk.Frame(grade, bg=CARTAO)
    esq.grid(row=0, column=0, sticky="n", padx=(0, 16))
    dir_ = tk.Frame(grade, bg=CARTAO)
    dir_.grid(row=0, column=1, sticky="nsew")

    rotulos: dict[str, tk.Label] = {}
    escalas: dict[str, ttk.Scale] = {}
    pendente = {"id": None}

    gabarito_txt = lic.texto(dir_, "")
    gabarito_txt.pack_forget()
    tk.Label(dir_, text=T.L3_P1_GABARITO_TITULO, bg=CARTAO, fg=SUAVE, font=(FONTE, 9, "bold"), anchor="w").pack(fill="x")
    gabarito_txt.pack(fill="x", pady=(2, 6))
    nota = tk.Label(dir_, text="", bg=CARTAO, fg=SUAVE, font=(FONTE, 9), anchor="w")
    nota.pack(fill="x")
    tk.Label(dir_, text=T.L3_P1_GRAFICO, bg=CARTAO, fg=SUAVE, font=(FONTE, 9, "bold"), anchor="w").pack(fill="x", pady=(4, 0))
    cv = novo_canvas(dir_, 230)
    cv.pack(fill="both", expand=True)

    def atualizar_rotulo(campo: str) -> None:
        v = getattr(est.params, campo)
        casas = next(c for c in CONTROLES if c[0] == campo)[4]
        rotulos[campo].config(text=T.L3_CONTROLES[campo].format(v=br(v, casas)))

    def redesenhar() -> None:
        pendente["id"] = None
        p = est.params
        conj = est.sintetico()
        gabarito_txt.definir(T.L3_P1_GABARITO.format(base=br(BASE_C, 0), amp=br(AMPLITUDE_HORA_C, 0), uso=br(p.efeito_uso, 2),
                                                     tomada=br(p.efeito_tomada, 1), poeira=br(p.poeira_por_dia, 2), deriva=br(DERIVA_DESVIO_C, 1), ruido=br(p.ruido_c, 1)))
        nota.config(text=T.L3_P1_NOTA.format(n=f"{conj.n:,}".replace(",", "."), dias=p.dias))
        _scatter(cv, conj)

    def agendar() -> None:
        if pendente["id"] is not None:
            area.after_cancel(pendente["id"])
        pendente["id"] = area.after(150, redesenhar)

    def cancelar_pendente(evento=None) -> None:
        """Ao trocar de passo a área é destruída: o redesenho agendado não pode mais tocar nos widgets."""
        if (evento is None or evento.widget is area) and pendente["id"] is not None:
            try:
                area.after_cancel(pendente["id"])
            except tk.TclError:
                pass
            pendente["id"] = None

    area.bind("<Destroy>", cancelar_pendente)

    def mudou(campo: str, minimo: float, passo: float, valor: str) -> None:
        i = int(round(float(valor)))
        if abs(float(valor) - i) > 1e-6:
            escalas[campo].set(i)
            return
        novo = _valor(campo, minimo + i * passo)
        if getattr(est.params, campo) != novo:
            est.params = replace(est.params, **{campo: novo})
            est.params_do_aprendiz = True              # a lição 2 passa a respeitar os valores dele, inclusive zero
            atualizar_rotulo(campo)
            agendar()

    for campo, minimo, maximo, passo, casas in CONTROLES:
        rotulos[campo] = tk.Label(esq, text="", bg=CARTAO, fg=TEXTO, font=(FONTE, 9, "bold"), anchor="w")
        rotulos[campo].pack(fill="x", pady=(6, 0))
        n = int(round((maximo - minimo) / passo))
        esc = ttk.Scale(esq, from_=0, to=n, orient="horizontal", length=300)
        esc.set(int(round((float(getattr(est.params, campo)) - minimo) / passo)))
        esc.config(command=lambda v, c=campo, m=minimo, p=passo: mudou(c, m, p, v))
        esc.pack(anchor="w")
        escalas[campo] = esc
        atualizar_rotulo(campo)

    linha = tk.Frame(esq, bg=CARTAO)
    linha.pack(fill="x", pady=(10, 0))
    tk.Label(linha, text=T.L3_SEMENTE, bg=CARTAO, fg=TEXTO, font=(FONTE, 9, "bold")).pack(side="left")
    caixa = ttk.Spinbox(linha, from_=1, to=9999, width=6, command=lambda: ler_semente())
    caixa.set(est.params.semente)
    caixa.pack(side="left", padx=6)

    def trocar_semente(v: int) -> None:
        v = max(1, min(9999, v))
        caixa.set(v)
        if v != est.params.semente:
            est.params = replace(est.params, semente=v)
            agendar()

    def ler_semente(_evento=None) -> None:
        try:
            trocar_semente(int(caixa.get()))
        except ValueError:                              # texto que não é número: volta ao valor anterior
            caixa.set(est.params.semente)

    caixa.bind("<Return>", ler_semente)
    caixa.bind("<FocusOut>", ler_semente)

    def novo_sorteio() -> None:
        trocar_semente(random.randint(1, 9999))

    def padrao() -> None:
        est.params = ParametrosSinteticos()
        est.params_do_aprendiz = False
        for campo, minimo, _, passo, _ in CONTROLES:
            escalas[campo].set(int(round((float(getattr(est.params, campo)) - minimo) / passo)))
            atualizar_rotulo(campo)
        caixa.set(est.params.semente)
        agendar()

    botao(esq, T.L3_NOVO_SORTEIO, novo_sorteio).pack(anchor="w", pady=(6, 0))
    botao(esq, T.L3_PADRAO, padrao).pack(anchor="w", pady=(6, 0))
    cv.bind("<Configure>", lambda _e: _scatter(cv, est.sintetico()))
    redesenhar()
    area.escalas = escalas                      # usados pelos testes de interface
    area.padrao = padrao
    area.novo_sorteio = novo_sorteio
    area.gabarito_txt = gabarito_txt


def _scatter(cv: tk.Canvas, conj) -> None:
    cv.delete("all")
    a = Area(cv)
    if not a.pronto():
        return
    idx = np.flatnonzero(conj.mascara(["uso"]))[::max(1, conj.n // 1500)]
    x, y = conj.dados["uso"][idx], conj.dados["temperatura"][idx]
    a.definir(0, 100, float(y.min() - 2) // 5 * 5, float(-(-(y.max() + 2) // 5) * 5))
    a.eixos([(v, str(v)) for v in range(0, 101, 20)], rotulo_y="°C")
    a.pontos(x, y, COR_TREINO, 1.6)


# ---------------- passo 2: o que o modelo descobre ----------------
def passo2(area: tk.Frame, lic: LicaoPassos) -> None:
    est = lic.janela.estado
    conj = est.sintetico()
    aj = ajustar_linear(conj)
    linhas = {l["nome"]: l for l in comparar_gabarito(aj.coeficientes, conj.gabarito)}
    lic.texto(area, T.L3_P2)
    tabela = tk.Frame(area, bg=CARTAO)
    tabela.pack(fill="x", pady=(2, 8))
    for j, titulo in enumerate(T.L3_TAB_COLUNAS):
        tk.Label(tabela, text=titulo, bg=CARTAO, fg=SUAVE, font=(FONTE, 9, "bold"), anchor="w" if j == 0 else "e", width=26 if j == 0 else 14
                 ).grid(row=0, column=j, sticky="ew", padx=4, pady=(0, 3))
    for i, (chave, nome) in enumerate(T.L3_TAB_LINHAS.items(), start=1):
        l = linhas[chave]
        casas = 4 if chave == "freq" else 3 if chave in ("uso", "dia") else 2
        pct = l["erro_pct"]
        if pct is not None:
            erro, cor = f"{pct:.1f}%".replace(".", ","), COR_PERTO if pct <= 10 else COR_MEIO if pct <= 25 else COR_LONGE
        else:
            erro, cor = T.L3_ERRO_ABS.format(v=br(l["erro_abs"], casas)), SUAVE
        valores = [nome, br(l["verdadeiro"], casas), br(l["descoberto"], casas), erro]
        for j, v in enumerate(valores):
            tk.Label(tabela, text=v, bg=CARTAO, fg=cor if j == 3 else TEXTO, font=(FONTE, 10, "bold" if j == 3 else "normal"),
                     anchor="w" if j == 0 else "e").grid(row=i, column=j, sticky="ew", padx=4, pady=1)
    lic.texto(area, T.L3_P2_METRICAS.format(mae=br(aj.mae_teste), r2=br(aj.r2_teste, 2)))
    perto = (linhas["uso"]["erro_pct"] or 0) <= 15 and (linhas["tomada"]["erro_pct"] or 0) <= 15
    lic.texto(area, T.L3_P2_PERTO if perto else T.L3_P2_LONGE)
    lic.texto(area, T.L3_P2_FREQ, fonte=(FONTE, 9), cor=SUAVE)
    area.tabela = linhas                         # usado pelos testes de interface
    area.perto = perto


# ---------------- passo 3: estragar de propósito ----------------
def _cenarios() -> list[tuple[ParametrosSinteticos, int | None]]:
    base = ParametrosSinteticos()
    return [(base, None), (replace(base, ruido_c=6.0), None), (base, 60),
            (replace(base, correlacao_uso_freq=0.95), 60)]


def passo3(area: tk.Frame, lic: LicaoPassos) -> None:
    jan = lic.janela
    lic.texto(area, T.L3_P3)
    corpo = tk.Frame(area, bg=CARTAO)
    corpo.pack(fill="both", expand=True)

    def calcular(progresso, cancelar):
        saida = []
        cen = _cenarios()
        for i, (p, minutos) in enumerate(cen):
            if cancelar():
                from lab.modelos import Cancelado
                raise Cancelado()
            progresso(i / len(cen), T.L3_P3_CALCULANDO)
            saida.append(avaliar_descoberta(p, range(1, 9), minutos))
        return saida

    jan.treinar(corpo, "cenarios3", (), calcular, ao_pronto=lambda r: _montar_passo3(corpo, lic, r),
                refazer=lambda: lic.mostrar(lic.indice))


def _montar_passo3(corpo: tk.Frame, lic: LicaoPassos, r: list[dict]) -> None:
    if not corpo.winfo_exists():
        return
    tk.Label(corpo, text=T.L3_P3_GRAF, bg=CARTAO, fg=SUAVE, font=(FONTE, 9, "bold"), anchor="w").pack(fill="x")
    cv = novo_canvas(corpo, 150)
    cv.pack(fill="x", pady=(2, 6))
    cores = ["#c9ced6", COR_TREINO, COR_TESTE, "#c8695d"]
    itens = [(nome, d["erro_uso_pct"], c) for nome, d, c in zip(T.L3_CENARIOS, r, cores)]
    cv.bind("<Configure>", lambda _e: barras_horizontais(cv, itens, formato=lambda v: f"{v:.1f}%".replace(".", ","), rotulo_largura=300))
    for nome, d in zip(T.L3_CENARIOS, r):
        lic.texto(corpo, T.L3_P3_TAB.format(cenario=nome, freq=br(d["freq_efeito"], 2), mae=br(d["mae"])), fonte=(FONTE, 9), cor=SUAVE)
    p, ruido, poucos, colinear = r
    lic.texto(corpo, T.L3_P3_RUIDO.format(a=br(p["mae"]), b=br(ruido["mae"]), ec=br(ruido["erro_uso_pct"])))
    lic.texto(corpo, T.L3_P3_POUCOS.format(a=br(p["erro_uso_pct"]), b=br(poucos["erro_uso_pct"])))
    lic.texto(corpo, T.L3_P3_COLINEAR.format(a=br(poucos["erro_uso_pct"]), b=br(colinear["erro_uso_pct"]),
                                             freq=br(colinear["freq_efeito"], 1)))
    igual = abs(colinear["mae"] - poucos["mae"]) / poucos["mae"] < 0.1
    lic.texto(corpo, (T.L3_P3_PREVISAO_IGUAL if igual else T.L3_P3_PREVISAO_MUDOU).format(a=br(poucos["mae"]), b=br(colinear["mae"])))
    corpo.cenarios = r                           # usado pelos testes de interface


# ---------------- passo 4: poeira escondida ----------------
def passo4(area: tk.Frame, lic: LicaoPassos) -> None:
    jan = lic.janela
    est = jan.estado
    lic.texto(area, T.L3_P4)
    estado = {"poeira": est.params.poeira_por_dia or 0.2}
    rotulo = tk.Label(area, text="", bg=CARTAO, fg=TEXTO, font=(FONTE, 10, "bold"), anchor="w")
    rotulo.pack(fill="x")
    esc = ttk.Scale(area, from_=0, to=30, orient="horizontal", length=420)
    esc.set(int(round(estado["poeira"] * 100)))
    esc.pack(anchor="w", pady=(0, 6))
    resultado = tk.Frame(area, bg=CARTAO)

    def atualizar_rotulo() -> None:
        rotulo.config(text=T.L3_P4_CONTROLE.format(v=br(estado["poeira"], 2)))

    def mudou(valor: str) -> None:
        i = int(round(float(valor)))
        if abs(float(valor) - i) > 1e-6:
            esc.set(i)
            return
        estado["poeira"] = i / 100
        atualizar_rotulo()

    def treinar() -> None:
        for w in resultado.winfo_children():
            w.destroy()
        poeira = estado["poeira"]
        params = replace(est.params, dias=21, episodios=0, poeira_por_dia=poeira)

        def calcular(progresso, cancelar):
            c = gerar(params)
            return treinar_anomalia(c, semente=params.semente, progresso=progresso, cancelar=cancelar), ajustar_linear(c)

        jan.treinar(resultado, "poeira3", (poeira, params.semente, params.ruido_c, params.efeito_uso, params.efeito_tomada,
                                            params.correlacao_uso_freq), calcular,
                    ao_pronto=lambda r: _mostrar_poeira(resultado, lic, r, poeira), refazer=treinar)

    esc.config(command=mudou)
    atualizar_rotulo()
    botao(area, T.L3_P4_BOTAO, treinar, destaque=True).pack(anchor="w", pady=4)
    resultado.pack(fill="both", expand=True)
    area.escala_poeira = esc
    area.treinar_poeira = treinar
    area.resultado_poeira = resultado


def _mostrar_poeira(pai: tk.Frame, lic: LicaoPassos, r, poeira: float) -> None:
    if not pai.winfo_exists():
        return
    res, aj = r
    tk.Label(pai, text=T.L3_P4_GRAF, bg=CARTAO, fg=SUAVE, font=(FONTE, 9, "bold"), anchor="w").pack(fill="x")
    cv = novo_canvas(pai, 170)
    cv.pack(fill="x", pady=(2, 6))
    cv.bind("<Configure>", lambda _e: _barras_semanais(cv, res))
    achada = res.inclinacao if res.inclinacao is not None else 0.0
    lic.texto(pai, T.L3_P4_RESULT.format(verdade=br(poeira * 7, 1), achada=br(achada, 1), dia=br(aj.coeficientes["dia"], 3),
                                          poeira=br(poeira, 2)))
    if poeira == 0:
        lic.texto(pai, T.L3_P4_SEM_POEIRA, fonte=(FONTE, 9), cor=SUAVE)
    pai.medidas = (poeira * 7, achada, aj.coeficientes["dia"])    # usado pelos testes de interface


# ---------------- passo 5: usar nas outras lições ----------------
def passo5(area: tk.Frame, lic: LicaoPassos) -> None:
    jan = lic.janela
    lic.texto(area, T.L3_P5)
    linha = tk.Frame(area, bg=CARTAO)
    linha.pack(anchor="w", pady=6)

    def abrir(n: int) -> None:
        jan.estado.usar_sintetico()
        jan.abrir_licao(n)

    b1 = botao(linha, T.L3_P5_ABRIR_1, lambda: abrir(1), destaque=True)
    b1.pack(side="left", padx=(0, 8))
    b2 = botao(linha, T.L3_P5_ABRIR_2, lambda: abrir(2), destaque=True)
    b2.pack(side="left")
    lic.texto(area, T.L3_P5_NOTA, fonte=(FONTE, 9), cor=SUAVE)
    area.abrir = abrir


# ---------------- passo 6: resumo e perguntas ----------------
def passo6(area: tk.Frame, lic: LicaoPassos) -> None:
    tk.Label(area, text=T.L3_P6, bg=CARTAO, fg=TEXTO, font=(FONTE, 10, "bold"), anchor="w").pack(fill="x")
    for item in T.L3_RESUMO:
        lic.texto(area, "•  " + item)
    quiz = Quiz(area, lic.janela, LICAO, T.L3_QUIZ)
    quiz.pack(fill="x", pady=(6, 0))
    area.quiz = quiz
