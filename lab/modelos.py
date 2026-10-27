"""Núcleo de machine learning do Laboratório (sem interface).

Cada função recebe um `Conjunto`, devolve dataclasses simples e aceita dois ganchos opcionais:
`progresso(fracao, texto)` e `cancelar()` (devolve True para parar; levanta `Cancelado`).
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Callable

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import KFold
from sklearn.tree import DecisionTreeRegressor

from lab.dados import ALVO, ENTRADAS_PADRAO, Conjunto, dividir_embaralhado, dividir_por_tempo
from lab.sintetico import ParametrosSinteticos, gerar

Progresso = Callable[[float, str], None]
Cancelar = Callable[[], bool]

MIN_LINHAS = 200
MIN_MIN_POR_SEMANA = 500       # semana com menos minutos úteis não entra na tendência
MINIMO_EPISODIO_MIN = 10
SENSIBILIDADE_PADRAO = 2.5       # × erro típico (calibrado: recall ≥ 80% com falsos alarmes ≤ 3%)
JANELA_SUAVIZACAO_MIN = 5        # média móvel do resíduo antes do limite (reduz o efeito do ruído)
LACUNA_MAX_S = 120             # buraco maior que isso separa episódios


class Cancelado(Exception):
    """O usuário cancelou o treino."""


def _passo(progresso: Progresso | None, cancelar: Cancelar | None, fracao: float, texto: str) -> None:
    if cancelar and cancelar():
        raise Cancelado()
    if progresso:
        progresso(fracao, texto)


def _indices(conj: Conjunto, entradas: list[str], minimo: int = MIN_LINHAS) -> np.ndarray:
    idx = np.flatnonzero(conj.mascara(entradas))
    if len(idx) < minimo:
        raise ValueError(f"Poucos dados: {len(idx)} minutos úteis (o mínimo é {minimo}).")
    return idx


def _dividir(idx: np.ndarray, divisao: str, semente: int) -> tuple[np.ndarray, np.ndarray]:
    if divisao == "tempo":
        return dividir_por_tempo(idx)
    if divisao == "embaralhado":
        return dividir_embaralhado(idx, semente)
    raise ValueError("divisao deve ser 'tempo' ou 'embaralhado'")


# ======================= Lição 1: regressão e sobreajuste =======================
@dataclass
class ResultadoCurva:
    entradas: list[str]
    divisao: str
    profundidades: list[int]
    mae_treino: list[float]
    mae_teste: list[float]
    r2_teste: list[float]
    mae_media: float            # "chutar a média do treino", medido no teste
    mae_linear: float
    r2_linear: float
    melhor_profundidade: int    # a de menor erro no teste
    n_treino: int
    n_teste: int


def curva_profundidade(conj: Conjunto, entradas: list[str] | None = None, divisao: str = "tempo", semente: int = 7,
                       profundidade_max: int = 20, progresso: Progresso | None = None,
                       cancelar: Cancelar | None = None, linhas: np.ndarray | None = None) -> ResultadoCurva:
    """Erro de treino × erro de teste de uma árvore de decisão, da profundidade 1 até `profundidade_max`.
    `linhas` restringe a análise a esses minutos (para comparar dois modelos exatamente nas mesmas linhas)."""
    entradas = entradas or ENTRADAS_PADRAO
    idx = _indices(conj, entradas)
    if linhas is not None:
        idx = np.intersect1d(idx, linhas)
        if len(idx) < MIN_LINHAS:
            raise ValueError(f"Poucos dados: {len(idx)} minutos úteis (o mínimo é {MIN_LINHAS}).")
    tr, te = _dividir(idx, divisao, semente)
    X, _ = conj.matriz(entradas)
    y = conj.dados[ALVO]
    mae_tr, mae_te, r2_te = [], [], []
    profs = list(range(1, profundidade_max + 1))
    for d in profs:
        _passo(progresso, cancelar, d / (profundidade_max + 1), f"Treinando a árvore com profundidade {d}")
        arv = DecisionTreeRegressor(max_depth=d, random_state=semente).fit(X[tr], y[tr])
        mae_tr.append(float(mean_absolute_error(y[tr], arv.predict(X[tr]))))
        p = arv.predict(X[te])
        mae_te.append(float(mean_absolute_error(y[te], p)))
        r2_te.append(float(r2_score(y[te], p)))
    _passo(progresso, cancelar, profundidade_max / (profundidade_max + 1), "Treinando o modelo linear")
    Xc, _ = conj.matriz(entradas, circular=True)
    lin = LinearRegression().fit(Xc[tr], y[tr])
    pl = lin.predict(Xc[te])
    media = float(np.mean(y[tr]))
    return ResultadoCurva(
        entradas=list(entradas), divisao=divisao, profundidades=profs, mae_treino=mae_tr, mae_teste=mae_te,
        r2_teste=r2_te, mae_media=float(mean_absolute_error(y[te], np.full(len(te), media))),
        mae_linear=float(mean_absolute_error(y[te], pl)), r2_linear=float(r2_score(y[te], pl)),
        melhor_profundidade=profs[int(np.argmin(mae_te))], n_treino=len(tr), n_teste=len(te))


def previsto_x_real(conj: Conjunto, entradas: list[str], profundidade: int, divisao: str = "tempo",
                    semente: int = 7) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(ts, real, previsto) no período de teste, para a profundidade escolhida."""
    idx = _indices(conj, entradas)
    tr, te = _dividir(idx, divisao, semente)
    X, _ = conj.matriz(entradas)
    y = conj.dados[ALVO]
    arv = DecisionTreeRegressor(max_depth=profundidade, random_state=semente).fit(X[tr], y[tr])
    return conj.ts[te], y[te], arv.predict(X[te])


def importancia(conj: Conjunto, entradas: list[str], profundidade: int, divisao: str = "tempo", semente: int = 7,
                repeticoes: int = 5) -> dict[str, float]:
    """Quanto o erro de teste (°C) piora quando os valores de cada entrada são embaralhados: quanto maior, mais o
    modelo depende dela (`permutation importance`)."""
    idx = _indices(conj, entradas)
    tr, te = _dividir(idx, divisao, semente)
    X, nomes = conj.matriz(entradas)
    y = conj.dados[ALVO]
    arv = DecisionTreeRegressor(max_depth=profundidade, random_state=semente).fit(X[tr], y[tr])
    r = permutation_importance(arv, X[te], y[te], scoring="neg_mean_absolute_error", n_repeats=repeticoes,
                               random_state=semente)
    return {n: float(v) for n, v in zip(nomes, r.importances_mean)}


# ======================= Lição 2: "quente para o que você faz" =======================
@dataclass
class ResultadoAnomalia:
    entradas: list[str]
    ts: np.ndarray
    medido: np.ndarray
    esperado: np.ndarray
    residuo: np.ndarray                     # medido − esperado
    no_treino: np.ndarray                   # True nos minutos do período em que o "normal" foi aprendido
    erro_tipico: float                      # °C; medido só em minutos que o modelo não viu
    semanas: list[tuple[int, float, int]] = field(default_factory=list)   # (semana, mediana do resíduo, minutos)
    inclinacao: float | None = None         # °C por semana (None se < 3 semanas)
    verdade: np.ndarray | None = None       # episódios injetados (só sintético)


def _sigma_robusto(x: np.ndarray) -> float:
    return float(1.4826 * np.median(np.abs(x - np.median(x))))


def _floresta(semente: int) -> RandomForestRegressor:
    return RandomForestRegressor(n_estimators=60, min_samples_leaf=20, random_state=semente, n_jobs=1)


def treinar_anomalia(conj: Conjunto, entradas: list[str] | None = None, semente: int = 7,
                     progresso: Progresso | None = None, cancelar: Cancelar | None = None) -> ResultadoAnomalia:
    """Aprende o "normal" no período inicial (70%) e calcula o esperado em todos os minutos.

    O erro típico vem de previsões em blocos de tempo que o modelo não viu (validação cruzada em 5 blocos
    contíguos). Resíduo calculado nos próprios minutos de treino seria otimista demais."""
    entradas = entradas or ENTRADAS_PADRAO
    if "ventoinha" in entradas:
        raise ValueError("A rotação da ventoinha é consequência da temperatura e não pode entrar aqui.")
    idx = _indices(conj, entradas)
    tr, te = dividir_por_tempo(idx)
    X, _ = conj.matriz(entradas)
    y = conj.dados[ALVO]

    esperado = np.empty(len(idx))
    pos = {int(i): k for k, i in enumerate(idx)}
    blocos = list(KFold(5, shuffle=False).split(tr))
    for k, (a, b) in enumerate(blocos):
        _passo(progresso, cancelar, k / (len(blocos) + 1), f"Aprendendo o normal (bloco {k + 1} de {len(blocos)})")
        modelo = _floresta(semente).fit(X[tr[a]], y[tr[a]])
        for i, p in zip(tr[b], modelo.predict(X[tr[b]])):
            esperado[pos[int(i)]] = p
    _passo(progresso, cancelar, len(blocos) / (len(blocos) + 1), "Treinando o modelo final")
    final = _floresta(semente).fit(X[tr], y[tr])
    for i, p in zip(te, final.predict(X[te])):
        esperado[pos[int(i)]] = p

    medido = y[idx]
    residuo = medido - esperado
    no_treino = np.zeros(len(idx), dtype=bool)
    no_treino[:len(tr)] = True
    erro = max(_sigma_robusto(residuo[no_treino]), 0.1)

    ts = conj.ts[idx]
    semanas, inclinacao = tendencia_semanal(ts, residuo)
    verdade = conj.anomalia[idx] if conj.anomalia is not None else None
    _passo(progresso, cancelar, 1.0, "Pronto")
    return ResultadoAnomalia(list(entradas), ts, medido, esperado, residuo, no_treino, erro, semanas, inclinacao, verdade)


def tendencia_semanal(ts: np.ndarray, residuo: np.ndarray) -> tuple[list[tuple[int, float, int]], float | None]:
    """Mediana semanal do resíduo (semanas de 7 dias desde o primeiro minuto) e a inclinação em °C/semana.
    Precisa de ≥ 3 semanas com ≥ 500 minutos úteis; senão a inclinação é None."""
    semana = ((ts - ts[0]) // (7 * 86400)).astype(int)
    semanas = []
    for s in np.unique(semana):
        m = semana == s
        if int(m.sum()) >= MIN_MIN_POR_SEMANA:
            semanas.append((int(s), float(np.median(residuo[m])), int(m.sum())))
    if len(semanas) < 3:
        return semanas, None
    x = np.array([s for s, _, _ in semanas], dtype=float)
    return semanas, float(np.polyfit(x, np.array([m for _, m, _ in semanas]), 1)[0])


def suavizar(x: np.ndarray, janela: int) -> np.ndarray:
    """Média móvel centrada de `janela` minutos (ímpar), repetindo os valores das pontas."""
    if janela <= 1:
        return x.copy()
    janela |= 1
    pad = janela // 2
    return np.convolve(np.pad(x, (pad, pad), mode="edge"), np.ones(janela) / janela, mode="valid")[:len(x)]


def detectar(ts: np.ndarray, residuo: np.ndarray, erro_tipico: float, k: float = SENSIBILIDADE_PADRAO,
             minimo_min: int = MINIMO_EPISODIO_MIN, janela: int = JANELA_SUAVIZACAO_MIN) -> tuple[np.ndarray, list[tuple[int, int]]]:
    """Marca como estranho o que ficou acima de `k` × erro típico por pelo menos `minimo_min` minutos seguidos,
    depois de suavizar o resíduo em `janela` minutos. Devolve a máscara dos minutos marcados e os episódios
    (início, fim exclusivo). Só o lado quente conta."""
    quente = suavizar(residuo, janela) > k * erro_tipico
    marcado = np.zeros(len(ts), dtype=bool)
    episodios: list[tuple[int, int]] = []
    i, n = 0, len(ts)
    while i < n:
        if not quente[i]:
            i += 1
            continue
        j = i + 1
        while j < n and quente[j] and ts[j] - ts[j - 1] <= LACUNA_MAX_S:
            j += 1
        if j - i >= minimo_min:
            marcado[i:j] = True
            episodios.append((i, j))
        i = j
    return marcado, episodios


def episodios_de(verdade: np.ndarray) -> list[tuple[int, int]]:
    """Trechos contínuos (início, fim exclusivo) em que a máscara é verdadeira."""
    out, i, n = [], 0, len(verdade)
    while i < n:
        if verdade[i]:
            j = i
            while j < n and verdade[j]:
                j += 1
            out.append((i, j))
            i = j
        else:
            i += 1
    return out


def avaliar_deteccao(verdade: np.ndarray, marcado: np.ndarray, regiao: np.ndarray) -> tuple[float | None, float]:
    """(recall dos episódios injetados, falsos alarmes em % dos minutos normais), só dentro de `regiao`.
    Um episódio injetado conta como achado se algum minuto dele foi marcado."""
    reais = [(a, b) for a, b in episodios_de(verdade & regiao)]
    achados = sum(1 for a, b in reais if marcado[a:b].any())
    recall = achados / len(reais) if reais else None
    normais = regiao & ~verdade
    falsos = float((marcado & normais).sum() / max(1, normais.sum()) * 100)
    return recall, falsos


def varredura_sensibilidade(res: ResultadoAnomalia, ks: list[float]) -> list[dict]:
    """Para cada sensibilidade: episódios e minutos marcados no período de prova e, no sintético, recall e
    falsos alarmes. Não retreina nada: o controle da lição responde na hora."""
    prova = ~res.no_treino
    linhas = []
    for k in ks:
        marcado, eps = detectar(res.ts, res.residuo, res.erro_tipico, k)
        marcado &= prova
        linha = {"k": k, "episodios": sum(1 for a, _ in eps if prova[a]), "minutos": int(marcado.sum())}
        if res.verdade is not None:
            linha["recall"], linha["falsos_alarmes"] = avaliar_deteccao(res.verdade, marcado, prova)
        linhas.append(linha)
    return linhas


# ======================= Lição 3: o que o modelo descobre =======================
ENTRADAS_LINEAR = ["uso", "freq", "tomada", "hora", "dia"]


@dataclass
class AjusteLinear:
    coeficientes: dict[str, float]     # inclui "intercepto"; hora vira hora_sen e hora_cos
    mae_teste: float
    r2_teste: float
    correlacao_uso_freq: float


def ajustar_linear(conj: Conjunto, entradas: list[str] | None = None, minimo: int = MIN_LINHAS) -> AjusteLinear:
    """Regressão linear para ler os coeficientes. Ajusta nos primeiros 70% e confere nos últimos 30%."""
    entradas = entradas or ENTRADAS_LINEAR
    idx = _indices(conj, entradas, minimo)
    tr, te = dividir_por_tempo(idx)
    X, nomes = conj.matriz(entradas, circular=True)
    y = conj.dados[ALVO]
    lin = LinearRegression().fit(X[tr], y[tr])
    p = lin.predict(X[te])
    coef = {"intercepto": float(lin.intercept_), **{n: float(c) for n, c in zip(nomes, lin.coef_)}}
    corr = float(np.corrcoef(conj.dados["uso"][idx], conj.dados["freq"][idx])[0, 1])
    return AjusteLinear(coef, float(mean_absolute_error(y[te], p)), float(r2_score(y[te], p)), corr)


def comparar_gabarito(descoberto: dict[str, float], gabarito: dict[str, float]) -> list[dict]:
    """Linhas (nome, verdadeiro, descoberto, erro absoluto, erro % quando o verdadeiro não é zero)."""
    linhas = []
    for nome, verdadeiro in gabarito.items():
        d = descoberto.get(nome)
        if d is None:
            continue
        linhas.append({"nome": nome, "verdadeiro": verdadeiro, "descoberto": d, "erro_abs": abs(d - verdadeiro),
                       "erro_pct": abs(d - verdadeiro) / abs(verdadeiro) * 100 if abs(verdadeiro) > 1e-9 else None})
    return linhas


def amostra_de(conj: Conjunto, quantos: int, semente: int) -> Conjunto:
    """Subconjunto de `quantos` minutos sorteados (mantendo a ordem do tempo): simula ter poucos exemplos."""
    idx = np.sort(np.random.default_rng(semente).choice(conj.n, size=min(quantos, conj.n), replace=False))
    return Conjunto(conj.origem, conj.ts[idx], {k: v[idx] for k, v in conj.dados.items()}, conj.semente, conj.parametros,
                    conj.gabarito, None if conj.anomalia is None else conj.anomalia[idx],
                    None if conj.regime is None else conj.regime[idx])


def avaliar_descoberta(params: ParametrosSinteticos, sementes: range | list[int] = range(1, 9),
                       minutos: int | None = None) -> dict[str, float]:
    """Média, em vários sorteios, de como o modelo linear descobre o gabarito com estes parâmetros:
    erro % do coeficiente do uso, efeito descoberto da frequência em °C por 500 MHz (verdade 0) e erro médio de
    teste. `minutos` limita os exemplos (simula poucos dados). Vários sorteios evitam concluir algo por sorte de um só."""
    erros_uso, freqs, maes = [], [], []
    for s in sementes:
        c = gerar(replace(params, semente=s))
        if minutos:
            c = amostra_de(c, minutos, s)
        aj = ajustar_linear(c, minimo=20)
        linhas = {l["nome"]: l for l in comparar_gabarito(aj.coeficientes, c.gabarito)}
        erros_uso.append(linhas["uso"]["erro_pct"])
        freqs.append(abs(linhas["freq"]["descoberto"]) * 500)
        maes.append(aj.mae_teste)
    return {"erro_uso_pct": float(np.mean(erros_uso)), "freq_efeito": float(np.mean(freqs)), "mae": float(np.mean(maes))}
