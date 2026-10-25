"""Análise da qualidade dos dados (quantitativa e qualitativa): os dados servem para aprender? o que falta?

Funções puras sobre um `Conjunto`. Cada item tem um valor (número em palavras), uma nota (boa, regular ou fraca; `None` =
só informativo), a explicação do que significa e, quando a nota não é boa, o que fazer. Os limiares ficam em `LIMIARES`.
"""
from __future__ import annotations

import datetime
import time
from dataclasses import dataclass, field

import numpy as np

from lab import textos as T
from lab.dados import MINIMOS, Conjunto

# nota "boa" a partir de A; "regular" a partir de B; abaixo disso, "fraca". (Itens de faixa usam funções próprias.)
LIMIARES = {
    "minutos": (5_000, 2_000),
    "periodo": (21.0, 7.0),          # dias
    "cobertura": (0.6, 0.3),         # fração dos dias do período com dados suficientes
    "uso": (40.0, 20.0),             # p90 − p10 do uso, em pontos percentuais
    "temperatura": (15.0, 8.0),      # p95 − p5, em °C
    "horas": (12, 6),                # horas do dia com dados suficientes
    "aproveitamento": (0.8, 0.5),    # fração dos minutos gravados que serviram
}
MIN_MINUTOS_POR_DIA = 120
MIN_MINUTOS_POR_HORA = 60
NUCLEO = ("minutos", "periodo", "uso", "temperatura")        # podem derrubar a nota geral até "fraca"
ORDEM = {"fraca": 0, "regular": 1, "boa": 2}


@dataclass
class Item:
    chave: str
    titulo: str
    valor: str
    nota: str | None            # "boa" | "regular" | "fraca" | None (informativo)
    explicacao: str
    sugestao: str = ""


@dataclass
class Prontidao:
    licao: int
    pode: bool
    recomendada: bool
    motivos: list[str] = field(default_factory=list)


@dataclass
class Relatorio:
    n: int
    dias: float
    itens: list[Item]
    geral: str
    prontidao: dict[int, Prontidao]
    horas: list[int]                          # minutos úteis em cada hora do dia (0 a 23)
    faixas_uso: list[tuple[str, int]]         # (rótulo da faixa, minutos)

    def item(self, chave: str) -> Item:
        return next(i for i in self.itens if i.chave == chave)


def _nota_por_limiar(v: float, chave: str) -> str:
    boa, regular = LIMIARES[chave]
    return "boa" if v >= boa else "regular" if v >= regular else "fraca"


def _br(x: float, casas: int = 0) -> str:
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _item(chave: str, valor: str, nota: str | None) -> Item:
    titulo, explicacao, sugestoes = T.QUAL_ITENS[chave]
    return Item(chave, titulo, valor, nota, explicacao, sugestoes.get(nota or "", ""))


def _dias_com_dados(ts: np.ndarray) -> tuple[int, int]:
    """(dias do calendário com ≥ 120 minutos úteis, dias do calendário no período)."""
    chaves = np.array([(lt.tm_year * 1000 + lt.tm_yday) for lt in (time.localtime(int(t)) for t in ts)])
    dias_unicos, contagens = np.unique(chaves, return_counts=True)
    com_dados = int((contagens >= MIN_MINUTOS_POR_DIA).sum())
    primeiro, ultimo = time.localtime(int(ts[0])), time.localtime(int(ts[-1]))
    dia = lambda t: datetime.date(t.tm_year, t.tm_mon, t.tm_mday).toordinal()
    total = dia(ultimo) - dia(primeiro)
    return com_dados, max(1, total + 1)


def analisar(conj: Conjunto) -> Relatorio | None:
    """Relatório de qualidade do conjunto, ou `None` se não há nenhum minuto útil."""
    idx = np.flatnonzero(conj.mascara(["uso", "freq", "tomada"]))
    if len(idx) == 0:
        return None
    d = conj.dados
    ts = conj.ts[idx]
    n = len(idx)
    itens: list[Item] = []

    com_dados, total_dias = _dias_com_dados(ts)
    dias = float(total_dias)
    itens.append(_item("minutos", T.QUAL_VALORES["minutos"].format(v=_br(n)), _nota_por_limiar(n, "minutos")))
    # o período conta dias do calendário (um conjunto de 21 dias vai de uma manhã a uma noite, 20,6 dias corridos)
    itens.append(_item("periodo", T.QUAL_VALORES["periodo"].format(v=_br(total_dias)), _nota_por_limiar(total_dias, "periodo")))
    itens.append(_item("cobertura", T.QUAL_VALORES["cobertura"].format(k=com_dados, n=total_dias),
                       _nota_por_limiar(com_dados / total_dias, "cobertura")))

    uso = d["uso"][idx]
    p10, p90 = np.percentile(uso, [10, 90])
    itens.append(_item("uso", T.QUAL_VALORES["uso"].format(a=_br(p10), b=_br(p90)), _nota_por_limiar(p90 - p10, "uso")))

    temp = d["temperatura"][idx]
    p5, p95 = np.percentile(temp, [5, 95])
    itens.append(_item("temperatura", T.QUAL_VALORES["temperatura"].format(a=_br(p5), b=_br(p95)),
                       _nota_por_limiar(p95 - p5, "temperatura")))

    f = float(np.mean(d["tomada"][idx]))
    nota_tomada = ("boa" if 0.10 <= f <= 0.90 else "regular" if 0.03 <= f <= 0.97 else "fraca")
    itens.append(_item("tomada", T.QUAL_VALORES["tomada"].format(pct=_br(f * 100)), nota_tomada))

    horas = np.zeros(24, dtype=int)
    for h in d["hora"][idx].astype(int):
        horas[h] += 1
    n_horas = int((horas >= MIN_MINUTOS_POR_HORA).sum())
    itens.append(_item("horas", T.QUAL_VALORES["horas"].format(k=n_horas), _nota_por_limiar(n_horas, "horas")))

    if conj.filtragem and conj.filtragem.get("total"):
        fl = conj.filtragem
        frac = fl["util"] / fl["total"]
        itens.append(_item("aproveitamento", T.QUAL_VALORES["aproveitamento"].format(
            uteis=_br(fl["util"]), total=_br(fl["total"]), pct=_br(frac * 100), acpi=_br(fl["acpi"]),
            poucas=_br(fl["poucas_amostras"]), sem_uso=_br(fl["sem_uso"] + fl["sem_freq_tomada"])),
            _nota_por_limiar(frac, "aproveitamento")))

    vent = float(np.mean(~np.isnan(d["ventoinha"][idx])))
    item_vent = _item("ventoinha", T.QUAL_VALORES["ventoinha"].format(pct=_br(vent * 100)), None)
    item_vent.sugestao = T.QUAL_VENTOINHA_DISPONIVEL if vent >= 0.5 else T.QUAL_VENTOINHA_INDISPONIVEL
    itens.append(item_vent)

    # nota geral: o núcleo pode derrubar até "fraca"; os demais itens derrubam no máximo até "regular"
    nucleo = [i.nota for i in itens if i.chave in NUCLEO]
    outros = [i.nota for i in itens if i.chave not in NUCLEO and i.nota]
    geral = min(nucleo, key=ORDEM.get)
    if any(o != "boa" for o in outros) and geral == "boa":
        geral = "regular"

    faixas = []
    for a in range(0, 100, 10):
        faixas.append((f"{a}–{a + 10}%", int(((uso >= a) & (uso < a + 10 if a < 90 else uso <= 100)).sum())))
    rel = Relatorio(n, dias, itens, geral, {}, [int(x) for x in horas], faixas)
    rel.prontidao = _prontidao(rel)
    return rel


def _prontidao(rel: Relatorio) -> dict[int, Prontidao]:
    pronto = {}
    for licao in (1, 2):
        min_dias, min_minutos = MINIMOS[licao]
        pode = rel.dias >= min_dias and rel.n >= min_minutos
        motivos = []
        if not pode:
            motivos.append(T.QUAL_PRONTIDAO_MOTIVO_MIN.format(dias=min_dias, minutos=_br(min_minutos),
                                                              tem_dias=_br(rel.dias), tem_minutos=_br(rel.n)))
        fracas = [i for i in rel.itens if i.nota == "fraca" and i.chave in NUCLEO + ("tomada", "horas")]
        motivos += [f"{i.titulo}: {i.sugestao}" for i in fracas if i.sugestao]
        recomendada = pode and not fracas and rel.geral != "fraca"
        if licao == 2 and rel.dias < 21:
            motivos.append(T.QUAL_PRONTIDAO_TENDENCIA)
        if licao == 2 and pode and rel.dias < 14:
            recomendada = False
        pronto[licao] = Prontidao(licao, pode, recomendada, motivos)
    pronto[3] = Prontidao(3, True, True, [])
    return pronto


def frase_da_prontidao(p: Prontidao) -> str:
    if p.licao == 3:
        return T.QUAL_PRONTIDAO["sintetica"].format(n=3)
    chave = "recomendada" if p.recomendada else "pode" if p.pode else "nao"
    return T.QUAL_PRONTIDAO[chave].format(n=p.licao)


def resumo_curto(rel: Relatorio) -> str:
    return T.QUAL_RESUMO_INICIO.format(nota=T.QUAL_NOTA[rel.geral].lower(), minutos=_br(rel.n), dias=_br(rel.dias))
