"""Dados sintéticos com relação conhecida (o "gabarito").

A verdade, minuto a minuto (jornada fictícia das 07h às 22h):

    temperatura = 38 + 4·sen(2π·(hora − 8)/24) + efeito_uso·uso + efeito_tomada·tomada
                  + poeira_por_dia·dia + deriva_lenta + ruído          (+ episódios injetados)

- A frequência NÃO esquenta nada por si (efeito 0): ela só anda junto com o uso (correlacao_uso_freq).
- A deriva lenta é um fator escondido (AR(1)) que nenhuma entrada enxerga: é o que torna enganosa uma
  avaliação com minutos embaralhados.
- A rotação da ventoinha é consequência: 2400 + 45·(temperatura − 40) + ruído.
"""
from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import datetime

import numpy as np
from scipy.signal import lfilter

from lab.dados import FRACAO_TREINO, Conjunto

BASE_C = 38.0
AMPLITUDE_HORA_C = 4.0
DERIVA_DESVIO_C = 1.5
DERIVA_PHI = 0.995
FREQ_EFEITO_C = 0.0
MIN_POR_DIA = 15 * 60          # 07:00 às 22:00
HORA_INICIO = 7
INICIO_FIXO = int(datetime(2026, 1, 5, 0, 0).timestamp())  # segunda-feira, hora local


@dataclass
class ParametrosSinteticos:
    dias: int = 14
    ruido_c: float = 2.0
    efeito_uso: float = 0.35          # °C por 1% de uso
    efeito_tomada: float = 5.0        # °C
    poeira_por_dia: float = 0.0       # °C por dia
    correlacao_uso_freq: float = 0.6
    semente: int = 7
    episodios: int = 0                # episódios "quente para o que faz" injetados (lição 2)
    episodio_c: float = 10.0
    episodio_min: int = 15

    FAIXAS = {"dias": (3, 30), "ruido_c": (0.5, 6.0), "efeito_uso": (0.10, 0.60), "efeito_tomada": (0.0, 10.0),
              "poeira_por_dia": (0.0, 0.30), "correlacao_uso_freq": (0.0, 0.95), "episodios": (0, 30),
              "episodio_c": (3.0, 20.0), "episodio_min": (10, 60)}

    def validar(self) -> None:
        for nome, (lo, hi) in self.FAIXAS.items():
            v = getattr(self, nome)
            if not lo <= v <= hi:
                raise ValueError(f"{nome} = {v} fora da faixa {lo}–{hi}")

    def como_dicionario(self) -> dict:
        return {f.name: getattr(self, f.name) for f in fields(self) if f.name != "FAIXAS"}


def gabarito_de(p: ParametrosSinteticos) -> dict[str, float]:
    """Coeficientes verdadeiros, na mesma base de colunas do modelo linear (hora vira seno e cosseno)."""
    fase = 2 * np.pi * 8 / 24
    return {"intercepto": BASE_C, "uso": p.efeito_uso, "freq": FREQ_EFEITO_C, "tomada": p.efeito_tomada,
            "dia": p.poeira_por_dia, "hora_sen": AMPLITUDE_HORA_C * float(np.cos(fase)),
            "hora_cos": -AMPLITUDE_HORA_C * float(np.sin(fase))}


def _uso(rng: np.random.Generator, hora: np.ndarray) -> np.ndarray:
    """Segmentos de ociosidade, trabalho leve e rajadas pesadas; mais rajadas em horário comercial."""
    n = len(hora)
    uso = np.empty(n)
    i = 0
    while i < n:
        trabalho = 9 <= hora[i] < 12 or 14 <= hora[i] < 18
        p_pesado, p_leve = (0.35, 0.35) if trabalho else (0.08, 0.25)
        r = rng.random()
        if r < p_pesado:
            dur, nivel, desvio = int(rng.integers(3, 21)), 75.0, 12.0
        elif r < p_pesado + p_leve:
            dur, nivel, desvio = int(rng.integers(5, 31)), 30.0, 8.0
        else:
            dur, nivel, desvio = int(rng.integers(5, 41)), 10.0, 4.0
        uso[i:i + dur] = rng.normal(nivel, desvio)
        i += dur
    return np.clip(uso + rng.normal(0, 3, n), 1, 100)


def _tomada(rng: np.random.Generator, n: int) -> np.ndarray:
    """Sessões de 30 a 240 minutos, 70% delas na tomada."""
    tom = np.empty(n)
    i, estado = 0, float(rng.random() < 0.7)
    while i < n:
        dur = int(rng.integers(30, 241))
        tom[i:i + dur] = estado
        i += dur
        estado = float(rng.random() < 0.7)
    return tom


def _episodios(rng: np.random.Generator, n: int, p: ParametrosSinteticos) -> list[tuple[int, int]]:
    """Posições (início, fim) dentro de um mesmo dia, só no período de prova (últimos 30%), separadas por ≥ 1 h."""
    ini_min = int(n * FRACAO_TREINO) + 30
    aceitos: list[tuple[int, int]] = []
    for _ in range(5_000):
        if len(aceitos) == p.episodios:
            break
        s = int(rng.integers(ini_min, n - p.episodio_min))
        e = s + p.episodio_min
        if s // MIN_POR_DIA != (e - 1) // MIN_POR_DIA:
            continue                                      # não atravessa a noite
        if any(s < b + 60 and a < e + 60 for a, b in aceitos):
            continue
        aceitos.append((s, e))
    return sorted(aceitos)


def gerar(p: ParametrosSinteticos) -> Conjunto:
    """Gera o conjunto completo, sempre igual para a mesma semente."""
    p.validar()
    rng = np.random.default_rng(p.semente)
    n = p.dias * MIN_POR_DIA
    dia_idx = np.repeat(np.arange(p.dias), MIN_POR_DIA)
    minuto_do_dia = np.tile(np.arange(MIN_POR_DIA), p.dias)
    hora = (HORA_INICIO + minuto_do_dia // 60).astype(float)
    ts = INICIO_FIXO + dia_idx.astype(np.int64) * 86400 + (HORA_INICIO * 60 + minuto_do_dia).astype(np.int64) * 60

    uso = _uso(rng, hora)
    z = (uso - uso.mean()) / uso.std()
    w = p.correlacao_uso_freq * z + np.sqrt(1 - p.correlacao_uso_freq ** 2) * rng.normal(size=n)
    freq = np.clip(3000 + 500 * w, 1400, 4300)
    tomada = _tomada(rng, n)
    deriva = lfilter([1.0], [1.0, -DERIVA_PHI], rng.normal(0, DERIVA_DESVIO_C * np.sqrt(1 - DERIVA_PHI ** 2), n))

    temp = (BASE_C + AMPLITUDE_HORA_C * np.sin(2 * np.pi * (hora - 8) / 24) + p.efeito_uso * uso
            + p.efeito_tomada * tomada + p.poeira_por_dia * dia_idx + deriva + rng.normal(0, p.ruido_c, n))

    anomalia = np.zeros(n, dtype=bool)
    avisos: list[str] = []
    if p.episodios:
        pos = _episodios(rng, n, p)
        for s, e in pos:
            temp[s:e] += p.episodio_c
            anomalia[s:e] = True
        if len(pos) < p.episodios:
            avisos.append(f"Só coube {len(pos)} dos {p.episodios} episódios pedidos.")

    ventoinha = np.maximum(0.0, 2400 + 45 * (temp - 40) + rng.normal(0, 60, n))
    dados = {"temperatura": temp, "uso": uso, "freq": freq, "tomada": tomada, "hora": hora,
             "ventoinha": ventoinha, "dia": (ts - ts[0]) / 86400.0}
    return Conjunto("sintetico", ts, dados, semente=p.semente, parametros=p, gabarito=gabarito_de(p),
                    anomalia=anomalia, avisos=avisos)
