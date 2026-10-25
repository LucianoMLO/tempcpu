"""Tipologia dos motivos de "O que pode estar elevando a temperatura".

Lista fechada: cada motivo tem um código estável (vai para o banco como variável de classe) e pertence
a uma categoria, que serve de classe mais ampla para análise. Códigos nunca são renomeados nem
reaproveitados; para mudar o sentido, crie um novo.
"""
from __future__ import annotations

from enum import Enum


class Categoria(str, Enum):
    CARGA = "carga"                    # o computador está trabalhando muito
    REFRIGERACAO = "refrigeracao"      # o calor não está saindo
    CONFIGURACAO = "configuracao"      # ajuste do sistema que libera mais calor
    ENERGIA = "energia"                # carregamento da bateria
    SENSOR = "sensor"                  # a medição não é confiável
    LIMITE = "limite"                  # chegou ao limite de proteção do firmware
    INDEFINIDA = "indefinida"          # quente sem causa evidente


class Motivo(str, Enum):
    PROCESSO_PESADO = "processo_pesado"
    CPU_CARGA_ALTA = "cpu_carga_alta"
    REFRIGERACAO_SUSPEITA = "refrigeracao_suspeita"
    VENTOINHA_PARADA = "ventoinha_parada"
    VENTOINHA_ALTA = "ventoinha_alta"
    TURBO_LIBERADO = "turbo_liberado"
    PLANO_ALTO_DESEMPENHO = "plano_alto_desempenho"
    CARREGANDO_BATERIA = "carregando_bateria"
    LEITURA_PARADA = "leitura_parada"
    LIMITE_FIRMWARE = "limite_firmware"
    SEM_CAUSA_EVIDENTE = "sem_causa_evidente"

    @property
    def categoria(self) -> Categoria:
        return _CATEGORIA[self]

    @property
    def rotulo(self) -> str:
        return _ROTULO[self]


_CATEGORIA = {
    Motivo.PROCESSO_PESADO: Categoria.CARGA,
    Motivo.CPU_CARGA_ALTA: Categoria.CARGA,
    Motivo.REFRIGERACAO_SUSPEITA: Categoria.REFRIGERACAO,
    Motivo.VENTOINHA_PARADA: Categoria.REFRIGERACAO,
    Motivo.VENTOINHA_ALTA: Categoria.REFRIGERACAO,
    Motivo.TURBO_LIBERADO: Categoria.CONFIGURACAO,
    Motivo.PLANO_ALTO_DESEMPENHO: Categoria.CONFIGURACAO,
    Motivo.CARREGANDO_BATERIA: Categoria.ENERGIA,
    Motivo.LEITURA_PARADA: Categoria.SENSOR,
    Motivo.LIMITE_FIRMWARE: Categoria.LIMITE,
    Motivo.SEM_CAUSA_EVIDENTE: Categoria.INDEFINIDA,
}

_ROTULO = {
    Motivo.PROCESSO_PESADO: "Programa pesado",
    Motivo.CPU_CARGA_ALTA: "CPU sob carga alta",
    Motivo.REFRIGERACAO_SUSPEITA: "Refrigeração suspeita",
    Motivo.VENTOINHA_PARADA: "Ventoinha parada",
    Motivo.VENTOINHA_ALTA: "Ventoinha em rotação alta",
    Motivo.TURBO_LIBERADO: "Turbo liberado",
    Motivo.PLANO_ALTO_DESEMPENHO: "Plano de alto desempenho",
    Motivo.CARREGANDO_BATERIA: "Carregando a bateria",
    Motivo.LEITURA_PARADA: "Leitura parada",
    Motivo.LIMITE_FIRMWARE: "Limite do firmware",
    Motivo.SEM_CAUSA_EVIDENTE: "Sem causa evidente",
}

ROTULO_CATEGORIA = {
    Categoria.CARGA: "Carga",
    Categoria.REFRIGERACAO: "Refrigeração",
    Categoria.CONFIGURACAO: "Configuração",
    Categoria.ENERGIA: "Energia",
    Categoria.SENSOR: "Sensor",
    Categoria.LIMITE: "Limite",
    Categoria.INDEFINIDA: "Indefinida",
}

# Cores suaves por categoria (marcadores do histórico)
COR_CATEGORIA = {
    Categoria.CARGA: "#6b8fc4",
    Categoria.REFRIGERACAO: "#c8695d",
    Categoria.CONFIGURACAO: "#b8902f",
    Categoria.ENERGIA: "#4f9d6e",
    Categoria.SENSOR: "#9aa5b4",
    Categoria.LIMITE: "#8f68b0",
    Categoria.INDEFINIDA: "#c9ced6",
}


def rotulo_de(codigo: str) -> str:
    """Rótulo legível a partir do código gravado no banco (tolera código desconhecido)."""
    try:
        return Motivo(codigo).rotulo
    except ValueError:
        return codigo


def categoria_de(codigo: str) -> Categoria | None:
    try:
        return Motivo(codigo).categoria
    except ValueError:
        return None
