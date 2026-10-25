"""Utilitários comuns dos testes do Laboratório (rodam no ambiente do Laboratório, com numpy e scikit-learn)."""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from historico import AcumuladorMinuto, Historico  # noqa: E402  (módulo do app: só cria bancos de teste)


def zona(_c):
    return "normal"


def gravar_minuto(h: Historico, ts: int, temp=60.0, uso=20.0, freq=3500.0, tomada=1.0, rpm=2600.0,
                  fonte="AMD", n_temp=30, n_uso=1) -> None:
    """Grava um minuto no banco de teste exatamente como o app grava."""
    acc = AcumuladorMinuto(ts)
    for i in range(n_temp):
        acc.amostras += 1
        acc.valor("cpu_c", temp, ts + i)
    if fonte:
        acc.fontes[fonte] += n_temp
    for _ in range(n_uso):
        acc.valor("uso_cpu", uso)
    if freq is not None:
        acc.valor("clk_mhz", freq)
    if tomada is not None:
        acc.valor("tomada", tomada)
    if rpm is not None:
        acc.valor("ventoinha_rpm", rpm)
    acc.programas["programa_secreto.exe"] += 1      # nome que o Laboratório nunca pode ler
    acc.pct_programa["programa_secreto.exe"] = 12.0
    h.gravar_minuto(acc.fechar(zona))
