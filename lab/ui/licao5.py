"""Lição 5 · Descobrir grupos sem gabarito (k-means, inércia e silhueta, nomes, pureza, componentes principais)."""
from __future__ import annotations

import tkinter as tk

import numpy as np

from lab import textos as T
from lab.modelos2 import VARIAVEIS_AGRUPAMENTO, agrupar, componentes, varrer_k
from lab.ui.controles import Escala, tabela, titulo_pequeno
from lab.ui.graficos import COR_BOM, COR_TESTE, COR_TREINO, Area, novo_canvas
from lab.ui.passos import LicaoPassos, Passo
from lab.ui.quiz import Quiz
from tema import CARTAO, FONTE, SUAVE, TEXTO, br

LICAO = 5
CORES = ["#3f6fb0", "#d08a4e", "#4f9d6e", "#8a6bb8", "#c8695d", "#5aa6b0", "#a8a04a", "#7a7a7a"]
COR_SEM_GRUPO = "#aab3c2"
KS = list(range(2, 9))


def criar(janela) -> LicaoPassos:
    funcoes = [passo1, passo2, passo3, passo4, passo5, passo6, passo7]
    passos = [Passo(t, f) for t, f in zip(T.L5_PASSOS, funcoes)]

    def concluir() -> None:
        janela.estado.progresso.marcar_concluida(LICAO)
        janela.mostrar_inicio()

    return LicaoPassos(janela, LICAO, passos, ao_concluir=concluir)


def _semente(conj) -> int:
    return conj.semente if conj.semente is not None else 7


def _local(lic: LicaoPassos) -> dict:
    if not hasattr(lic, "local"):
        lic.local = {"k": 3, "cache": {}, "nomes": {}}
    return lic.local


def _agrup(lic: LicaoPassos, k: int):
    conj = lic.janela.estado.conjunto(LICAO)
    cache = _local(lic)["cache"]
    if k not in cache:
        cache[k] = agrupar(conj, k, _semente(conj))
    return cache[k]


def nomes_dos_grupos(res) -> list[str]:
    """Nomes sugeridos pelo uso médio de cada grupo (o aprendiz pode trocá-los)."""
    nomes = [""] * res.k
    contagem: dict[str, int] = {}
    for g in res.ordem_uso:
        uso = float(res.centros[g, 0])
        base = T.L5_P4_NOME_OCIOSO if uso < 20 else T.L5_P4_NOME_LEVE if uso < 50 else T.L5_P4_NOME_PESADO
        contagem[base] = contagem.get(base, 0) + 1
        nomes[g] = base if contagem[base] == 1 else f"{base} {contagem[base]}"
    if sum(contagem.values()) != res.k:
        nomes = [T.L5_P4_NOME_GENERICO.format(n=g + 1) for g in range(res.k)]
    return nomes


def _amostra(n: int, quantos: int = 1500) -> np.ndarray:
    return np.arange(n) if n <= quantos else np.sort(np.random.default_rng(7).choice(n, quantos, replace=False))


def _dispersao(cv: tk.Canvas, uso: np.ndarray, temp: np.ndarray, cores: list[str], centros=None, cores_centro=None) -> None:
    cv.delete("all")
    a = Area(cv)
    if not a.pronto():
        return
    a.definir(0, 100, float(np.floor(temp.min())) - 1, float(np.ceil(temp.max())) + 1)
    a.eixos([(v, str(v)) for v in range(0, 101, 20)], rotulo_y=T.L5_P1_EIXO_Y)
    cv.create_text(a.esq + a.largura / 2, cv.winfo_height() - 6, text=T.L5_P1_EIXO_X, fill=SUAVE, font=(FONTE, 8, "bold"))
    for x, y, c in zip(uso, temp, cores):
        a.pontos([x], [y], c, 1.8)
    if centros is not None:
        for (u, t), c in zip(centros, cores_centro):
            px, py = a.px(u), a.py(t)
            cv.create_oval(px - 7, py - 7, px + 7, py + 7, fill="white", outline=c, width=3)
            cv.create_text(px, py, text="×", fill=c, font=(FONTE, 10, "bold"))


# ---------------- passo 1: a ideia ----------------
def passo1(area: tk.Frame, lic: LicaoPassos) -> None:
    jan = lic.janela
    conj = jan.estado.conjunto(LICAO)
    lic.aviso_qualidade(area, conj)
    lic.texto(area, T.L5_P1)
    res = _agrup(lic, 2)                              # só para ter os minutos úteis
    idx = res.indices
    uso, temp = conj.dados["uso"][idx], conj.dados["temperatura"][idx]
    amostra = _amostra(len(idx))
    titulo_pequeno(area, T.L5_P1_GRAF).pack(fill="x")
    cv = novo_canvas(area, 260)
    cv.pack(fill="both", expand=True)
    cv.bind("<Configure>", lambda _e: _dispersao(cv, uso[amostra], temp[amostra], [COR_SEM_GRUPO] * len(amostra)))
    lic.texto(area, T.L5_P1_NOTA.format(n=f"{len(idx):,}".replace(",", ".")), fonte=(FONTE, 9), cor=SUAVE)


# ---------------- passo 2: k-means ----------------
def passo2(area: tk.Frame, lic: LicaoPassos) -> None:
    jan = lic.janela
    conj = jan.estado.conjunto(LICAO)
    loc = _local(lic)
    lic.texto(area, T.L5_P2)
    cv = novo_canvas(area, 260)
    tamanhos = lic.texto(area, "", fonte=(FONTE, 9), cor=SUAVE)

    def atualizar(k) -> None:
        loc["k"] = int(k)
        res = _agrup(lic, loc["k"])
        idx = res.indices
        uso, temp = conj.dados["uso"][idx], conj.dados["temperatura"][idx]
        amostra = _amostra(len(idx))
        cores = [CORES[g] for g in res.rotulos[amostra]]
        centros = [(c[VARIAVEIS_AGRUPAMENTO.index("uso")], c[VARIAVEIS_AGRUPAMENTO.index("temperatura")]) for c in res.centros]
        cv.unbind("<Configure>")
        cv.bind("<Configure>", lambda _e: _dispersao(cv, uso[amostra], temp[amostra], cores, centros, CORES[:res.k]))
        _dispersao(cv, uso[amostra], temp[amostra], cores, centros, CORES[:res.k])
        total = max(1, sum(res.tamanhos))
        tamanhos.definir(T.L5_P2_TAMANHOS.format(t=", ".join(f"{100 * n / total:.0f}%".replace(".", ",") for n in res.tamanhos)))

    escala = Escala(area, KS, loc["k"], lambda v: T.L5_P2_ROTULO.format(k=v), atualizar, atraso=150, comprimento=360)
    escala.pack(anchor="w")
    titulo_pequeno(area, T.L5_P2_GRAF).pack(fill="x")
    cv.pack(fill="both", expand=True)
    tamanhos.pack_forget()
    tamanhos.pack(fill="x")
    atualizar(loc["k"])
    area.escala = escala


# ---------------- passo 3: quantos grupos? ----------------
def _varredura(lic: LicaoPassos, corpo: tk.Frame, ao_pronto) -> None:
    jan = lic.janela
    conj = jan.estado.conjunto(LICAO)
    semente = _semente(conj)
    jan.treinar(corpo, "agrupamento5", (semente,), lambda progresso, cancelar: varrer_k(conj, KS, semente, progresso, cancelar),
                ao_pronto=ao_pronto, refazer=lambda: lic.mostrar(lic.indice), licao=LICAO)


def passo3(area: tk.Frame, lic: LicaoPassos) -> None:
    lic.texto(area, T.L5_P3)
    corpo = tk.Frame(area, bg=CARTAO)
    corpo.pack(fill="both", expand=True)

    def montar(v) -> None:
        if not corpo.winfo_exists():
            return
        grade = tk.Frame(corpo, bg=CARTAO)
        grade.pack(fill="both", expand=True)
        grade.columnconfigure(0, weight=1, uniform="g")
        grade.columnconfigure(1, weight=1, uniform="g")
        for c, (titulo, serie, cor) in enumerate(((T.L5_P3_GRAF_INERCIA, v["inercia"], COR_TREINO), (T.L5_P3_GRAF_SILHUETA, v["silhueta"], COR_TESTE))):
            titulo_pequeno(grade, titulo).grid(row=0, column=c, sticky="w", padx=(0 if c == 0 else 8, 0))
            cv = novo_canvas(grade, 200)
            cv.grid(row=1, column=c, sticky="nsew", padx=(0 if c == 0 else 8, 0))

            def desenhar(_e=None, cv=cv, serie=serie, cor=cor, c=c) -> None:
                cv.delete("all")
                a = Area(cv)
                if not a.pronto():
                    return
                lo, hi = min(serie), max(serie)
                folga = (hi - lo) * 0.1 or 0.1
                a.definir(KS[0], KS[-1], lo - folga if c else 0, hi + folga)
                a.eixos([(k, str(k)) for k in KS], casas_y=2 if c else 0)
                a.linha(KS, serie, cor, 2)
                a.pontos(KS, serie, cor, 3.5)

            cv.bind("<Configure>", desenhar)
        melhor = KS[int(np.argmax(v["silhueta"]))]
        lic.texto(corpo, T.L5_P3_MELHOR.format(k=melhor))
        corpo.varredura = v

    _varredura(lic, corpo, montar)


# ---------------- passo 4: dar nome aos grupos ----------------
def passo4(area: tk.Frame, lic: LicaoPassos) -> None:
    jan = lic.janela
    conj = jan.estado.conjunto(LICAO)
    loc = _local(lic)
    lic.texto(area, T.L5_P4)
    corpo = tk.Frame(area, bg=CARTAO)

    def mostrar(k) -> None:
        loc["k"] = int(k)
        for w in corpo.winfo_children():
            w.destroy()
        res = _agrup(lic, loc["k"])
        sug = nomes_dos_grupos(res)
        nomes = loc["nomes"].setdefault(res.k, list(sug))
        idx = res.indices
        total = max(1, len(idx))
        cabec = tk.Frame(corpo, bg=CARTAO)
        cabec.pack(fill="x")
        entradas: list[tk.Entry] = []
        for j, c in enumerate(T.L5_P4_COLUNAS):
            tk.Label(cabec, text=c, bg="#e8ebf1", fg=TEXTO, font=(FONTE, 9, "bold"), anchor="w", padx=8, pady=3).grid(row=0, column=j, sticky="ew")
            cabec.columnconfigure(j, weight=1)
        for r, g in enumerate(res.ordem_uso, start=1):
            e = tk.Entry(cabec, font=(FONTE, 9, "bold"), relief="flat", bg="#f4f6fa")
            e.insert(0, nomes[g])
            e.grid(row=r, column=0, sticky="ew", padx=2, pady=2)
            e.bind("<KeyRelease>", lambda _ev, g=g, e=e: nomes.__setitem__(g, e.get()))
            entradas.append(e)
            uso, freq, temp = res.centros[g]
            for j, v in enumerate([f"{100 * res.tamanhos[g] / total:.0f}%".replace(".", ","), f"{br(uso, 0)}%", f"{br(freq, 0)} MHz", f"{br(temp, 1)} °C"], start=1):
                tk.Label(cabec, text=v, bg=CARTAO, fg=TEXTO, font=(FONTE, 9), anchor="w", padx=8).grid(row=r, column=j, sticky="ew")
        corpo.entradas = entradas
        corpo.resultado = res

    escala = Escala(area, KS, loc["k"], lambda v: T.L5_P2_ROTULO.format(k=v), mostrar, atraso=150, comprimento=360)
    escala.pack(anchor="w")
    corpo.pack(fill="x", pady=(4, 6))
    lic.texto(area, T.L5_P4_DICA, fonte=(FONTE, 9), cor=SUAVE)
    mostrar(loc["k"])
    area.escala = escala
    area.corpo = corpo
    _ = conj


# ---------------- passo 5: conferir com o gabarito ----------------
def passo5(area: tk.Frame, lic: LicaoPassos) -> None:
    jan = lic.janela
    conj = jan.estado.conjunto(LICAO)
    if conj.regime is None:
        lic.texto(area, T.L5_P5_REAL)
        return
    lic.texto(area, T.L5_P5_SINTETICO)
    corpo = tk.Frame(area, bg=CARTAO)
    corpo.pack(fill="both", expand=True)
    loc = _local(lic)

    def montar(v) -> None:
        if not corpo.winfo_exists():
            return
        escala = Escala(corpo, KS, loc["k"], lambda x: T.L5_P2_ROTULO.format(k=x), lambda x: atualizar(x), atraso=150, comprimento=360)
        escala.pack(anchor="w")
        titulo_pequeno(corpo, T.L5_P5_GRAF).pack(fill="x")
        cv = novo_canvas(corpo, 190)
        cv.pack(fill="x")
        valor = lic.texto(corpo, "")
        matriz = tk.Frame(corpo, bg=CARTAO)
        resto = lic.texto(corpo, T.L5_P5_RUIDO, fonte=(FONTE, 9), cor=SUAVE)
        pureza = v["pureza"]

        def desenhar(_e=None) -> None:
            cv.delete("all")
            a = Area(cv)
            if not a.pronto():
                return
            a.definir(KS[0], KS[-1], 0, 1.02)
            a.eixos([(k, str(k)) for k in KS], casas_y=1)
            a.linha(KS, pureza, COR_BOM, 2)
            a.pontos(KS, pureza, COR_BOM, 3.5)
            a.vertical(loc["k"], TEXTO, 1, (2, 3))

        def atualizar(k) -> None:
            loc["k"] = int(k)
            res = _agrup(lic, loc["k"])
            valor.definir(T.L5_P5_VALOR.format(k=loc["k"], p=br(100 * pureza[KS.index(loc["k"])], 0)))
            for w in matriz.winfo_children():
                w.destroy()
            reg = conj.regime[res.indices]
            tab = np.zeros((3, res.k), dtype=int)
            for r_, g_ in zip(reg, res.rotulos):
                tab[int(r_), g_] += 1
            nomes = loc["nomes"].get(res.k) or nomes_dos_grupos(res)
            colunas = [T.L5_P5_TABELA] + [nomes[g] for g in res.ordem_uso]
            linhas = [[T.L5_P5_REGIMES[i]] + [f"{tab[i, g]:,}".replace(",", ".") for g in res.ordem_uso] for i in range(3)]
            tabela(matriz, colunas, linhas).pack(anchor="w")
            desenhar()

        matriz.pack(fill="x", pady=(4, 4), before=resto)
        cv.bind("<Configure>", desenhar)
        atualizar(loc["k"])
        corpo.escala = escala
        corpo.pureza = pureza

    _varredura(lic, corpo, montar)


# ---------------- passo 6: componentes principais ----------------
def passo6(area: tk.Frame, lic: LicaoPassos) -> None:
    jan = lic.janela
    conj = jan.estado.conjunto(LICAO)
    lic.texto(area, T.L5_P6)
    p = componentes(conj, _semente(conj))
    grade = tk.Frame(area, bg=CARTAO)
    grade.pack(fill="both", expand=True)
    grade.columnconfigure(0, weight=1, uniform="g")
    grade.columnconfigure(1, weight=2, uniform="g")
    titulo_pequeno(grade, T.L5_P6_GRAF_VAR).grid(row=0, column=0, sticky="w")
    titulo_pequeno(grade, T.L5_P6_GRAF_PROJ).grid(row=0, column=1, sticky="w", padx=(8, 0))
    cv_v = novo_canvas(grade, 220)
    cv_v.grid(row=1, column=0, sticky="nsew")
    cv_p = novo_canvas(grade, 220)
    cv_p.grid(row=1, column=1, sticky="nsew", padx=(8, 0))

    def desenhar_var(_e=None) -> None:
        cv_v.delete("all")
        a = Area(cv_v, margem=(40, 10, 14, 30))
        if not a.pronto():
            return
        n = len(p.variancia)
        a.definir(0.4, n + 0.6, 0, 1.0)
        a.eixos([(i + 1, f"C{i + 1}") for i in range(n)], casas_y=1)
        for i, v in enumerate(p.variancia):
            cv_v.create_rectangle(a.px(i + 1 - 0.3), a.py(v), a.px(i + 1 + 0.3), a.py(0), fill=COR_TREINO, width=0)
            cv_v.create_text(a.px(i + 1), a.py(v) - 8, text=f"{100 * v:.0f}%", fill=TEXTO, font=(FONTE, 8, "bold"))

    def desenhar_proj(_e=None) -> None:
        cv_p.delete("all")
        a = Area(cv_p, margem=(14, 10, 10, 30))
        if not a.pronto():
            return
        x, y = p.projecao[:, 0], p.projecao[:, 1]
        a.definir(float(x.min()) - 0.5, float(x.max()) + 0.5, float(y.min()) - 0.5, float(y.max()) + 0.5)
        cv_p.create_text(a.esq + a.largura / 2, cv_p.winfo_height() - 6, text=T.L5_P6_EIXO_X, fill=SUAVE, font=(FONTE, 8, "bold"))
        cv_p.create_text(4, a.topo, text=T.L5_P6_EIXO_Y, anchor="nw", fill=SUAVE, font=(FONTE, 8, "bold"))
        cores = [CORES[int(r)] for r in p.rotulos_amostra] if p.rotulos_amostra is not None else [COR_SEM_GRUPO] * len(x)
        for xi, yi, c in zip(x, y, cores):
            a.pontos([xi], [yi], c, 1.8)

    cv_v.bind("<Configure>", desenhar_var)
    cv_p.bind("<Configure>", desenhar_proj)
    lic.texto(area, T.L5_P6_VAR.format(a=br(100 * p.variancia[0], 0), b=br(100 * p.variancia[1], 0), c=br(100 * (p.variancia[0] + p.variancia[1]), 0)))
    cargas = p.cargas[0] * (1 if p.cargas[0].sum() >= 0 else -1)
    nomes = {"uso": "uso", "freq": "frequência", "tomada": "tomada", "temperatura": "temperatura"}
    lista = ", ".join(f"{nomes[v]} {br(c, 2)}" for v, c in zip(p.variaveis, cargas))
    lic.texto(area, T.L5_P6_CARGAS.format(lista=lista))
    sinais = [c for v, c in zip(p.variaveis, cargas) if v in ("uso", "freq", "temperatura")]
    if all(c > 0.2 for c in sinais):
        lic.texto(area, T.L5_P6_JUNTAS)
    area.resultado = p


# ---------------- passo 7: resumo e perguntas ----------------
def passo7(area: tk.Frame, lic: LicaoPassos) -> None:
    tk.Label(area, text=T.L5_P7, bg=CARTAO, fg=TEXTO, font=(FONTE, 10, "bold"), anchor="w").pack(fill="x")
    for item in T.L5_RESUMO:
        lic.texto(area, "•  " + item)
    quiz = Quiz(area, lic.janela, LICAO, T.L5_QUIZ)
    quiz.pack(fill="x", pady=(6, 0))
    area.quiz = quiz
