"""Dados do Laboratório: leitura (somente leitura) do histórico, "minuto útil", variáveis e divisão treino/teste.

Só números entram aqui: nomes de programas nunca são lidos. O banco é aberto com `mode=ro` e `query_only`.
"""
from __future__ import annotations

import datetime
import os
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

MAX_MINUTOS_REAIS = 20_000     # os mais recentes (≈14 dias de uso contínuo)
MIN_AMOSTRAS_TEMP = 5          # amostras de temperatura por minuto para o minuto ser útil
FRACAO_TREINO = 0.7
ALVO = "temperatura"

# chave -> (nome na tela, coluna no banco ou None se derivada)
VARIAVEIS: dict[str, tuple[str, str | None]] = {
    "temperatura": ("Temperatura da CPU", "cpu_c_med"),
    "uso": ("Uso da CPU", "uso_cpu_med"),
    "freq": ("Frequência da CPU", "clk_mhz_med"),
    "tomada": ("Na tomada", "tomada_med"),
    "hora": ("Hora do dia", None),
    "ventoinha": ("Rotação da ventoinha", "ventoinha_rpm_med"),
    "dia": ("Dia (desde o início)", None),
}
# entradas das lições (a ventoinha só entra quando o usuário pede: ela é consequência, não causa)
ENTRADAS_PADRAO = ["uso", "freq", "tomada", "hora"]

# o que cada lição exige de dados reais: (dias, minutos úteis)
MINIMOS = {1: (3, 2_000), 2: (7, 5_000), 4: (5, 4_000), 5: (3, 2_000)}


class SemBanco(Exception):
    """Nenhum histórico encontrado."""


class BancoIlegivel(Exception):
    """O histórico existe, mas não pôde ser lido (em uso, corrompido ou de outra versão)."""


@dataclass
class Conjunto:
    origem: str                              # "real" | "sintetico"
    ts: np.ndarray                           # segundos (epoch), crescente, uma linha por minuto
    dados: dict[str, np.ndarray]             # variável -> valores (float; NaN = ausente)
    semente: int | None = None
    parametros: object | None = None         # ParametrosSinteticos (só no sintético)
    gabarito: dict[str, float] | None = None  # coeficientes verdadeiros (só no sintético)
    anomalia: np.ndarray | None = None       # True nos minutos de episódio injetado (só no sintético)
    regime: np.ndarray | None = None         # 0 = ocioso, 1 = trabalho leve, 2 = carga alta, minuto a minuto (só no sintético)
    avisos: list[str] = field(default_factory=list)
    filtragem: dict[str, int] | None = None  # só no real: quantos minutos gravados foram aproveitados ou descartados, e por quê

    @property
    def n(self) -> int:
        return len(self.ts)

    @property
    def dias(self) -> float:
        """Dias corridos entre o primeiro e o último minuto."""
        return float((self.ts[-1] - self.ts[0]) / 86400) if self.n > 1 else 0.0

    @property
    def dias_calendario(self) -> int:
        """Dias do calendário que o período toca (de uma manhã de segunda a uma noite de quarta = 3), na hora local."""
        if self.n == 0:
            return 0
        a, b = time.localtime(int(self.ts[0])), time.localtime(int(self.ts[-1]))
        dia = lambda t: datetime.date(t.tm_year, t.tm_mon, t.tm_mday).toordinal()
        return dia(b) - dia(a) + 1

    def mascara(self, entradas: list[str]) -> np.ndarray:
        """Minutos sem valor ausente no alvo e nas entradas pedidas."""
        ok = ~np.isnan(self.dados[ALVO])
        for e in entradas:
            ok &= ~np.isnan(self.dados[e])
        return ok

    def matriz(self, entradas: list[str], circular: bool = False) -> tuple[np.ndarray, list[str]]:
        """Matriz de entradas (n × k) e os nomes das colunas. Com `circular`, a hora vira seno e cosseno
        (23h e 0h ficam vizinhas), o que modelos lineares precisam; árvores usam a hora crua."""
        cols, nomes = [], []
        for e in entradas:
            if e == "hora" and circular:
                ang = 2 * np.pi * self.dados["hora"] / 24
                cols += [np.sin(ang), np.cos(ang)]
                nomes += ["hora_sen", "hora_cos"]
            else:
                cols.append(self.dados[e])
                nomes.append(e)
        return np.column_stack(cols), nomes


# ---------------- leitura do histórico ----------------
def caminho_do_banco() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(base) / "TempCPU" / "historico.db"


def _abrir_somente_leitura(caminho: Path) -> sqlite3.Connection:
    if not caminho.exists():
        raise SemBanco(f"Nenhum histórico encontrado em {caminho.parent}.")
    try:
        con = sqlite3.connect(f"{caminho.as_uri()}?mode=ro", uri=True, timeout=5)
        con.execute("PRAGMA query_only = ON")
        return con
    except sqlite3.Error as e:
        raise BancoIlegivel(f"Não foi possível abrir o histórico: {e}") from e


def carregar_real(caminho: Path | str | None = None) -> Conjunto:
    """Os minutos úteis mais recentes do histórico (até 20.000), do mais antigo ao mais novo.

    Minuto útil: temperatura com ≥ 5 amostras, uso medido, fonte diferente de ACPI (a ACPI pode ficar parada)
    e nenhuma entrada básica ausente. A rotação da ventoinha pode faltar (NaN): só importa se for escolhida."""
    caminho = Path(caminho) if caminho else caminho_do_banco()
    con = _abrir_somente_leitura(caminho)
    try:
        linhas = con.execute(
            "SELECT ts, cpu_c_med, uso_cpu_med, clk_mhz_med, tomada_med, ventoinha_rpm_med FROM minuto "
            "WHERE cpu_c_n >= ? AND uso_cpu_n >= 1 AND (fonte IS NULL OR fonte <> 'ACPI') "
            "AND cpu_c_med IS NOT NULL AND uso_cpu_med IS NOT NULL AND clk_mhz_med IS NOT NULL "
            "AND tomada_med IS NOT NULL ORDER BY ts DESC LIMIT ?", (MIN_AMOSTRAS_TEMP, MAX_MINUTOS_REAIS)).fetchall()
    except sqlite3.Error as e:
        con.close()
        raise BancoIlegivel(f"Não foi possível ler o histórico: {e}") from e
    linhas.reverse()
    desde = int(linhas[0][0]) if linhas else 0
    filtragem = _contar_filtragem(con, desde)
    con.close()
    if not linhas:
        c = _conjunto_real_vazio()
        c.filtragem = filtragem
        return c
    a = np.array([[np.nan if v is None else v for v in l] for l in linhas], dtype=float)
    ts = a[:, 0].astype(np.int64)
    dados = {"temperatura": a[:, 1], "uso": a[:, 2], "freq": a[:, 3], "tomada": a[:, 4], "ventoinha": a[:, 5],
             "hora": np.array([time.localtime(int(t)).tm_hour for t in ts], dtype=float),
             "dia": (ts - ts[0]) / 86400.0}
    return Conjunto("real", ts, dados, filtragem=filtragem)


def _contar_filtragem(con: sqlite3.Connection, desde: int) -> dict[str, int]:
    """Dos minutos gravados desde `desde`, quantos serviram e por que os outros não (cada minuto cai em um só motivo)."""
    try:
        linhas = con.execute(
            "SELECT CASE WHEN fonte = 'ACPI' THEN 'acpi' "
            "WHEN cpu_c_med IS NULL OR cpu_c_n < ? THEN 'poucas_amostras' "
            "WHEN uso_cpu_med IS NULL OR uso_cpu_n < 1 THEN 'sem_uso' "
            "WHEN clk_mhz_med IS NULL OR tomada_med IS NULL THEN 'sem_freq_tomada' ELSE 'util' END AS classe, COUNT(*) "
            "FROM minuto WHERE ts >= ? GROUP BY classe", (MIN_AMOSTRAS_TEMP, desde)).fetchall()
    except sqlite3.Error:
        return {}
    cont = {k: 0 for k in ("util", "acpi", "poucas_amostras", "sem_uso", "sem_freq_tomada")}
    cont.update({classe: n for classe, n in linhas})
    cont["total"] = sum(cont.values())
    return cont


def _conjunto_real_vazio() -> Conjunto:
    vazio = np.array([], dtype=float)
    return Conjunto("real", np.array([], dtype=np.int64), {k: vazio for k in VARIAVEIS})


def verificar_minimos(conj: Conjunto, licao: int) -> tuple[bool, str]:
    """Os dados reais bastam para a lição? Devolve (ok, mensagem em português)."""
    dias, minutos = MINIMOS[licao]
    if conj.origem == "sintetico":
        return True, ""
    if conj.dias_calendario >= dias and conj.n >= minutos:
        return True, ""
    return False, (f"Esta lição precisa de pelo menos {dias} dias e {minutos:,} minutos úteis de histórico; "
                   f"seu histórico tem {conj.dias_calendario} dia(s) e {conj.n:,} minutos úteis.").replace(",", ".")


# ---------------- divisão treino/teste ----------------
def dividir_por_tempo(indices: np.ndarray, fracao: float = FRACAO_TREINO) -> tuple[np.ndarray, np.ndarray]:
    """Os primeiros `fracao` minutos (no tempo) treinam; os últimos fazem a prova."""
    corte = int(len(indices) * fracao)
    return indices[:corte], indices[corte:]


def dividir_embaralhado(indices: np.ndarray, semente: int, fracao: float = FRACAO_TREINO) -> tuple[np.ndarray, np.ndarray]:
    """Sorteia minutos para treino e teste, misturando vizinhos no tempo (mostra o erro de avaliar assim)."""
    ordem = np.random.default_rng(semente).permutation(len(indices))
    corte = int(len(indices) * fracao)
    return np.sort(indices[ordem[:corte]]), np.sort(indices[ordem[corte:]])
