"""Núcleo de machine learning das lições novas (v1.2), sem interface.

Validação cruzada e boosting (Lição 1), Isolation Forest (Lição 2), Ridge e Lasso (Lição 3), classificação (Lição 4),
agrupamento e PCA (Lição 5). Mesmos ganchos de `lab.modelos`: `progresso(fracao, texto)` e `cancelar()`.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.ensemble import HistGradientBoostingRegressor, IsolationForest, RandomForestRegressor
from sklearn.linear_model import Lasso, LinearRegression, LogisticRegression, Ridge
from sklearn.metrics import mean_absolute_error, silhouette_score
from sklearn.model_selection import KFold
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor

from lab.dados import ALVO, ENTRADAS_PADRAO, Conjunto, dividir_por_tempo
from lab.modelos import (Cancelar, MINIMO_EPISODIO_MIN, LACUNA_MAX_S, Progresso, ResultadoAnomalia, _indices, _passo,
                         avaliar_deteccao, detectar, episodios_de, ENTRADAS_LINEAR)

BLOCOS_VALIDACAO = 5
RODADAS_BOOSTING = 200


# ======================= Lição 1 · passo 7: validação cruzada =======================
@dataclass
class ResultadoValidacao:
    profundidades: list[int]
    erro_validacao: list[float]          # média dos 5 blocos
    desvio_validacao: list[float]        # variação entre blocos
    escolhida: int                       # a de menor erro na validação (sem olhar o teste)
    erro_teste_escolhida: float          # o teste continua inédito até aqui
    erro_teste: list[float]              # erro de teste de cada profundidade (só para comparar)
    preferida_pelo_teste: int            # a que o teste "escolheria"
    n_treino: int
    n_teste: int


def validacao_cruzada(conj: Conjunto, entradas: list[str] | None = None, semente: int = 7, profundidade_max: int = 20,
                      progresso: Progresso | None = None, cancelar: Cancelar | None = None) -> ResultadoValidacao:
    """Escolhe a profundidade da árvore só com o treino: 5 blocos de tempo, treina em 4 e confere no outro."""
    entradas = entradas or ENTRADAS_PADRAO
    idx = _indices(conj, entradas)
    tr, te = dividir_por_tempo(idx)
    X, _ = conj.matriz(entradas)
    y = conj.dados[ALVO]
    profs = list(range(1, profundidade_max + 1))
    blocos = list(KFold(BLOCOS_VALIDACAO, shuffle=False).split(tr))
    media, desvio, teste = [], [], []
    for d in profs:
        _passo(progresso, cancelar, d / (profundidade_max + 1), f"Testando a profundidade {d} em {BLOCOS_VALIDACAO} blocos")
        erros = []
        for a, b in blocos:
            m = DecisionTreeRegressor(max_depth=d, random_state=semente).fit(X[tr[a]], y[tr[a]])
            erros.append(mean_absolute_error(y[tr[b]], m.predict(X[tr[b]])))
        media.append(float(np.mean(erros)))
        desvio.append(float(np.std(erros)))
        full = DecisionTreeRegressor(max_depth=d, random_state=semente).fit(X[tr], y[tr])
        teste.append(float(mean_absolute_error(y[te], full.predict(X[te]))))
    escolhida = profs[int(np.argmin(media))]
    return ResultadoValidacao(profs, media, desvio, escolhida, teste[escolhida - 1], teste, profs[int(np.argmin(teste))],
                              len(tr), len(te))


# ======================= Lição 1 · passo 8: boosting =======================
@dataclass
class ResultadoBoosting:
    rodadas: list[int]
    erro_treino: list[float]
    erro_teste: list[float]
    melhor_rodada: int                    # a de menor erro no teste
    erro_arvore: float                    # melhor árvore simples, no teste
    erro_floresta: float
    erro_linear: float
    n_treino: int
    n_teste: int


def curva_boosting(conj: Conjunto, entradas: list[str] | None = None, semente: int = 7, rodadas_max: int = RODADAS_BOOSTING,
                   progresso: Progresso | None = None, cancelar: Cancelar | None = None) -> ResultadoBoosting:
    """Erro de treino e de teste de árvores pequenas em sequência (`HistGradientBoostingRegressor`), rodada a rodada."""
    entradas = entradas or ENTRADAS_PADRAO
    idx = _indices(conj, entradas)
    tr, te = dividir_por_tempo(idx)
    X, _ = conj.matriz(entradas)
    y = conj.dados[ALVO]
    _passo(progresso, cancelar, 0.1, "Treinando as árvores em sequência")
    gb = HistGradientBoostingRegressor(max_iter=rodadas_max, learning_rate=0.1, max_depth=3, min_samples_leaf=20,
                                       early_stopping=False, random_state=semente).fit(X[tr], y[tr])
    e_tr = [float(mean_absolute_error(y[tr], p)) for p in gb.staged_predict(X[tr])]
    e_te = [float(mean_absolute_error(y[te], p)) for p in gb.staged_predict(X[te])]
    _passo(progresso, cancelar, 0.6, "Comparando com a melhor árvore")
    arvores = [mean_absolute_error(y[te], DecisionTreeRegressor(max_depth=d, random_state=semente).fit(X[tr], y[tr]).predict(X[te]))
               for d in range(1, 21)]
    _passo(progresso, cancelar, 0.8, "Comparando com a floresta e o modelo linear")
    flor = RandomForestRegressor(n_estimators=60, min_samples_leaf=20, random_state=semente, n_jobs=1).fit(X[tr], y[tr])
    Xc, _ = conj.matriz(entradas, circular=True)
    lin = LinearRegression().fit(Xc[tr], y[tr])
    _passo(progresso, cancelar, 1.0, "Pronto")
    return ResultadoBoosting(list(range(1, len(e_te) + 1)), e_tr, e_te, int(np.argmin(e_te)) + 1, float(min(arvores)),
                             float(mean_absolute_error(y[te], flor.predict(X[te]))),
                             float(mean_absolute_error(y[te], lin.predict(Xc[te]))), len(tr), len(te))


# ======================= Lição 2 · passo 7: Isolation Forest =======================
@dataclass
class ResultadoIsolamento:
    pontuacao: np.ndarray                 # menor = mais estranho (um valor por minuto útil)
    no_treino: np.ndarray
    ts: np.ndarray


def treinar_isolamento(conj: Conjunto, res: ResultadoAnomalia, semente: int = 7,
                       progresso: Progresso | None = None, cancelar: Cancelar | None = None) -> ResultadoIsolamento:
    """Aprende como é um minuto "comum" (uso, frequência, temperatura e hora) no período de treino e pontua todos."""
    idx = _indices(conj, ENTRADAS_PADRAO)
    if len(idx) != len(res.ts):
        raise ValueError("O resultado da Lição 2 não corresponde a estes dados.")
    ang = 2 * np.pi * conj.dados["hora"][idx] / 24
    X = np.column_stack([conj.dados["uso"][idx], conj.dados["freq"][idx], conj.dados[ALVO][idx], np.sin(ang), np.cos(ang)])
    _passo(progresso, cancelar, 0.3, "Isolando os minutos raros")
    modelo = IsolationForest(n_estimators=100, random_state=semente, n_jobs=1).fit(X[res.no_treino])
    _passo(progresso, cancelar, 0.9, "Pontuando todos os minutos")
    pont = modelo.score_samples(X)
    return ResultadoIsolamento(pont, res.no_treino.copy(), res.ts)


def marcar_isolamento(iso: ResultadoIsolamento, estranhos_pct: float,
                      minimo_min: int = MINIMO_EPISODIO_MIN) -> tuple[np.ndarray, list[tuple[int, int]]]:
    """Marca como estranhos os `estranhos_pct`% minutos de menor pontuação do treino (o limite vem do treino) e exige
    que durem pelo menos `minimo_min` minutos seguidos, como no método da lição."""
    limite = float(np.percentile(iso.pontuacao[iso.no_treino], estranhos_pct))
    quente = iso.pontuacao < limite
    marcado = np.zeros(len(quente), dtype=bool)
    eps: list[tuple[int, int]] = []
    i, n = 0, len(quente)
    while i < n:
        if not quente[i]:
            i += 1
            continue
        j = i + 1
        while j < n and quente[j] and iso.ts[j] - iso.ts[j - 1] <= LACUNA_MAX_S:
            j += 1
        if j - i >= minimo_min:
            marcado[i:j] = True
            eps.append((i, j))
        i = j
    return marcado, eps


def comparar_deteccao(res: ResultadoAnomalia, iso: ResultadoIsolamento, estranhos_pct: float) -> dict:
    """Recall e falsos alarmes (só no sintético) dos dois métodos, no período de prova."""
    prova = ~res.no_treino
    m_iso, e_iso = marcar_isolamento(iso, estranhos_pct)
    m_res, e_res = detectar(res.ts, res.residuo, res.erro_tipico)
    m_iso &= prova
    m_res &= prova
    saida = {"iso_episodios": sum(1 for a, _ in e_iso if prova[a]), "res_episodios": sum(1 for a, _ in e_res if prova[a]),
             "iso_marcado": m_iso, "res_marcado": m_res}
    if res.verdade is not None:
        saida["iso_recall"], saida["iso_falsos"] = avaliar_deteccao(res.verdade, m_iso, prova)
        saida["res_recall"], saida["res_falsos"] = avaliar_deteccao(res.verdade, m_res, prova)
        saida["n_reais"] = len(episodios_de(res.verdade & prova))
    return saida


# ======================= Lição 3 · passo 7: Ridge e Lasso =======================
FORCAS = [0.0, 0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0]


@dataclass
class ResultadoRegularizacao:
    forcas: list[float]
    linear: dict[str, float]                       # mínimos quadrados, sem regularizar
    ridge: list[dict[str, float]]                  # coeficientes (na unidade original) para cada força
    lasso: list[dict[str, float]]
    mae_teste: dict[str, list[float]]              # "linear" (constante), "ridge", "lasso"
    zerados_lasso: list[list[str]]                 # entradas que o Lasso zerou, para cada força
    n_treino: int


def _coef_original(coef_padronizado: np.ndarray, escala: np.ndarray, nomes: list[str]) -> dict[str, float]:
    return {n: float(c / s) for n, c, s in zip(nomes, coef_padronizado, escala)}


def regularizacao(conj: Conjunto, semente: int = 7, progresso: Progresso | None = None,
                  cancelar: Cancelar | None = None) -> ResultadoRegularizacao:
    """Ajusta o modelo linear, o Ridge e o Lasso em várias forças de regularização. A força λ multiplica a penalidade
    por exemplo (Ridge: alpha = λ·n; Lasso: alpha = λ) sobre entradas padronizadas; os coeficientes voltam à unidade original."""
    idx = _indices(conj, ENTRADAS_LINEAR, 20)
    tr, te = dividir_por_tempo(idx)
    X, nomes = conj.matriz(ENTRADAS_LINEAR, circular=True)
    y = conj.dados[ALVO]
    esc = StandardScaler().fit(X[tr])
    Z_tr, Z_te = esc.transform(X[tr]), esc.transform(X[te])
    lin = LinearRegression().fit(X[tr], y[tr])
    mae_lin = float(mean_absolute_error(y[te], lin.predict(X[te])))
    ridge, lasso, m_r, m_l, zerados = [], [], [], [], []
    for k, lam in enumerate(FORCAS):
        _passo(progresso, cancelar, k / len(FORCAS), "Ajustando com mais e mais regularização")
        r = Ridge(alpha=max(lam * len(tr), 1e-9)).fit(Z_tr, y[tr])
        ridge.append(_coef_original(r.coef_, esc.scale_, nomes))
        m_r.append(float(mean_absolute_error(y[te], r.predict(Z_te))))
        if lam == 0.0:
            l = LinearRegression().fit(Z_tr, y[tr])
        else:
            l = Lasso(alpha=lam, max_iter=20000).fit(Z_tr, y[tr])
        lasso.append(_coef_original(l.coef_, esc.scale_, nomes))
        m_l.append(float(mean_absolute_error(y[te], l.predict(Z_te))))
        zerados.append([n for n, c in zip(nomes, l.coef_) if abs(c) < 1e-12])
    _passo(progresso, cancelar, 1.0, "Pronto")
    return ResultadoRegularizacao(list(FORCAS), {n: float(c) for n, c in zip(nomes, lin.coef_)}, ridge, lasso,
                                  {"linear": [mae_lin] * len(FORCAS), "ridge": m_r, "lasso": m_l}, zerados, len(tr))


# ======================= Lição 4: classificação =======================
@dataclass
class ResultadoClassificacao:
    limite_c: float
    taxa_quente_treino: float                 # fração dos minutos de treino acima do limite
    taxa_quente_teste: float
    sempre_normal_acuracia: float             # o "palpite" que nunca avisa
    modelos: dict[str, dict]                  # nome -> {acuracia, precisao, revocacao, matriz [[vn, fp], [fn, vp]]}
    probabilidade: np.ndarray                 # da regressão logística, no teste
    verdade: np.ndarray                       # True = acima do limite, no teste
    n_treino: int
    n_teste: int


def limite_padrao(conj: Conjunto, percentil: float = 90.0) -> float:
    """Limite (°C inteiro) acima do qual ficam os ~10% minutos mais quentes: dá uma classe rara, como na vida real."""
    idx = _indices(conj, ENTRADAS_PADRAO)
    return float(round(np.percentile(conj.dados[ALVO][idx], percentil)))


def _metricas(verdade: np.ndarray, previsto: np.ndarray) -> dict:
    vp = int(np.sum(verdade & previsto))
    fp = int(np.sum(~verdade & previsto))
    fn = int(np.sum(verdade & ~previsto))
    vn = int(np.sum(~verdade & ~previsto))
    n = max(1, len(verdade))
    return {"acuracia": (vp + vn) / n, "precisao": vp / (vp + fp) if vp + fp else None, "revocacao": vp / (vp + fn) if vp + fn else None,
            "matriz": [[vn, fp], [fn, vp]]}


def classificar(conj: Conjunto, limite_c: float, k_vizinhos: int = 15, semente: int = 7, limiar: float = 0.5,
                progresso: Progresso | None = None, cancelar: Cancelar | None = None) -> ResultadoClassificacao:
    """Prevê se a temperatura passa de `limite_c` com regressão logística, árvore e k-vizinhos, divisão por tempo."""
    idx = _indices(conj, ENTRADAS_PADRAO)
    tr, te = dividir_por_tempo(idx)
    X, _ = conj.matriz(ENTRADAS_PADRAO, circular=True)
    alta = conj.dados[ALVO] > limite_c
    y_tr, y_te = alta[tr], alta[te]
    if y_tr.sum() < 5 or y_te.sum() < 5:
        raise ValueError(f"Com o limite de {limite_c:.0f} °C há poucos minutos quentes para aprender ou conferir "
                         f"({int(y_tr.sum())} no treino e {int(y_te.sum())} no teste). Baixe o limite.")
    esc = StandardScaler().fit(X[tr])
    Z_tr, Z_te = esc.transform(X[tr]), esc.transform(X[te])
    modelos: dict[str, dict] = {}
    _passo(progresso, cancelar, 0.2, "Treinando a regressão logística")
    logi = LogisticRegression(max_iter=1000).fit(Z_tr, y_tr)
    proba = logi.predict_proba(Z_te)[:, 1]
    modelos["logistica"] = _metricas(y_te, proba >= limiar)
    _passo(progresso, cancelar, 0.5, "Treinando a árvore")
    arv = DecisionTreeClassifier(max_depth=5, random_state=semente).fit(Z_tr, y_tr)
    modelos["arvore"] = _metricas(y_te, arv.predict(Z_te))
    _passo(progresso, cancelar, 0.8, "Treinando os k-vizinhos")
    knn = KNeighborsClassifier(n_neighbors=int(k_vizinhos)).fit(Z_tr, y_tr)
    modelos["vizinhos"] = _metricas(y_te, knn.predict(Z_te))
    _passo(progresso, cancelar, 1.0, "Pronto")
    return ResultadoClassificacao(float(limite_c), float(y_tr.mean()), float(y_te.mean()), float(1 - y_te.mean()), modelos,
                                  proba, y_te, len(tr), len(te))


def varrer_limiar(proba: np.ndarray, verdade: np.ndarray, limiares: list[float]) -> list[dict]:
    """Precisão, revocação e número de alarmes para cada limiar de decisão da regressão logística."""
    saida = []
    for t in limiares:
        m = _metricas(verdade, proba >= t)
        saida.append({"limiar": t, "precisao": m["precisao"], "revocacao": m["revocacao"], "alarmes": int((proba >= t).sum())})
    return saida


# ======================= Lição 5: agrupamento e PCA =======================
VARIAVEIS_AGRUPAMENTO = ["uso", "freq", "temperatura"]
NOMES_REGIME = {0: "ocioso", 1: "trabalho leve", 2: "carga alta"}


@dataclass
class ResultadoAgrupamento:
    k: int
    rotulos: np.ndarray                    # grupo de cada minuto útil
    centros: np.ndarray                    # k × variáveis, na unidade original
    inercia: float
    silhueta: float
    tamanhos: list[int]
    indices: np.ndarray                    # posição de cada minuto útil no conjunto
    pureza: float | None = None            # só no sintético: fração dos minutos no regime mais comum de cada grupo
    ordem_uso: list[int] = field(default_factory=list)   # grupos do menos ao mais ocupado


def _matriz_agrupamento(conj: Conjunto) -> tuple[np.ndarray, np.ndarray]:
    idx = _indices(conj, ENTRADAS_PADRAO)
    X = np.column_stack([conj.dados[v][idx] for v in VARIAVEIS_AGRUPAMENTO])
    return idx, X


def agrupar(conj: Conjunto, k: int, semente: int = 7, amostra_silhueta: int = 3000) -> ResultadoAgrupamento:
    idx, X = _matriz_agrupamento(conj)
    esc = StandardScaler().fit(X)
    Z = esc.transform(X)
    km = KMeans(n_clusters=k, n_init=5, random_state=semente).fit(Z)
    rng = np.random.default_rng(semente)
    sel = np.arange(len(Z)) if len(Z) <= amostra_silhueta else np.sort(rng.choice(len(Z), amostra_silhueta, replace=False))
    sil = float(silhouette_score(Z[sel], km.labels_[sel])) if k > 1 and len(set(km.labels_[sel])) > 1 else 0.0
    centros = esc.inverse_transform(km.cluster_centers_)
    pureza = None
    if conj.regime is not None:
        reg = conj.regime[idx]
        acertos = sum(int(np.bincount(reg[km.labels_ == g]).max()) for g in range(k) if np.any(km.labels_ == g))
        pureza = acertos / len(idx)
    return ResultadoAgrupamento(k, km.labels_, centros, float(km.inertia_), sil, [int(np.sum(km.labels_ == g)) for g in range(k)], idx,
                                pureza, [int(g) for g in np.argsort(centros[:, 0])])


def varrer_k(conj: Conjunto, ks: range | list[int] = range(2, 9), semente: int = 7, progresso: Progresso | None = None,
             cancelar: Cancelar | None = None) -> dict[str, list[float]]:
    inercia, silhueta, pureza = [], [], []
    ks = list(ks)
    for i, k in enumerate(ks):
        _passo(progresso, cancelar, i / len(ks), f"Agrupando em {k} grupos")
        r = agrupar(conj, k, semente)
        inercia.append(r.inercia)
        silhueta.append(r.silhueta)
        pureza.append(r.pureza if r.pureza is not None else float("nan"))
    _passo(progresso, cancelar, 1.0, "Pronto")
    return {"k": [float(k) for k in ks], "inercia": inercia, "silhueta": silhueta, "pureza": pureza}


@dataclass
class ResultadoPCA:
    variaveis: list[str]
    variancia: list[float]                 # fração explicada por componente (decrescente)
    cargas: np.ndarray                     # componentes × variáveis
    projecao: np.ndarray                   # amostra de minutos em 2 componentes
    rotulos_amostra: np.ndarray | None     # regime verdadeiro dos minutos da amostra (sintético) ou None


VARIAVEIS_PCA = ["uso", "freq", "tomada", "temperatura"]


def componentes(conj: Conjunto, semente: int = 7, amostra: int = 1500) -> ResultadoPCA:
    idx = _indices(conj, ENTRADAS_PADRAO)
    X = np.column_stack([conj.dados[v][idx] for v in VARIAVEIS_PCA])
    Z = StandardScaler().fit_transform(X)
    pca = PCA(n_components=len(VARIAVEIS_PCA)).fit(Z)
    rng = np.random.default_rng(semente)
    sel = np.arange(len(Z)) if len(Z) <= amostra else np.sort(rng.choice(len(Z), amostra, replace=False))
    proj = pca.transform(Z[sel])[:, :2]
    return ResultadoPCA(list(VARIAVEIS_PCA), [float(v) for v in pca.explained_variance_ratio_], pca.components_, proj,
                        None if conj.regime is None else conj.regime[idx][sel])
