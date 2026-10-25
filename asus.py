"""Leitura da ventoinha pela interface WMI da ASUS (driver ATK que veio de fábrica).

Condições da sentinela (ADR 0002):
- só o método DSTS (leitura de status); nunca DEVS ou qualquer outro método;
- IDs fixos nesta lista, nunca vindos de configuração;
- falha ou classe ausente = None, sem erro para o usuário.
"""
from __future__ import annotations

IDS_LEITURA = {
    "ventoinha_cpu": 0x00110013,
    "ventoinha_gpu": 0x00110014,
}
BIT_PRESENCA = 0x00010000
NAO_SUPORTADO = 0xFFFFFFFE


def decodificar_rpm(bruto: int | None) -> int | None:
    """DSTS de ventoinha: bit 16 = presente; 16 bits baixos = RPM/100."""
    if bruto is None or bruto == NAO_SUPORTADO or not bruto & BIT_PRESENCA:
        return None
    return (bruto & 0xFFFF) * 100


class AsusAtk:
    def __init__(self, conexao_wmi) -> None:
        """`conexao_wmi`: wmi.WMI(namespace="root/wmi"). Levanta erro se a classe ASUS não existir."""
        self._obj = conexao_wmi.AsusAtkWmi_WMNB()[0]

    def _dsts(self, chave: str) -> int | None:
        try:
            return int(self._obj.DSTS(Device_ID=IDS_LEITURA[chave])[0])
        except Exception:
            return None

    def ventoinha_cpu_rpm(self) -> int | None:
        return decodificar_rpm(self._dsts("ventoinha_cpu"))
