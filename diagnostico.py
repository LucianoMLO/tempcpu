"""Diagnóstico do que está aquecendo o processador e sugestões para baixar a temperatura.

`coletar()` lê o sistema (psutil + powercfg); `analisar()` é puro e testável.
Nada aqui altera configuração do Windows: só sugere.
"""
from __future__ import annotations

import re
import subprocess
import time
from dataclasses import dataclass, field

from motivos import Motivo

IGNORAR = {"system idle process", "idle", ""}
SEM_JANELA = 0x08000000  # CREATE_NO_WINDOW: powercfg não pisca console no pythonw


@dataclass
class Retrato:
    uso_cpu: float = 0.0                                    # % do total
    processos: list[tuple[str, float]] = field(default_factory=list)  # (nome, % do total), agregado por nome
    plano_energia: str = ""
    estado_max_ac: int | None = None                        # % estado máximo do processador na tomada
    estado_max_dc: int | None = None                        # idem na bateria
    na_tomada: bool | None = None
    bateria: int | None = None
    horas_ligado: float = 0.0
    software_asus: bool = False
    coletado_em: float = 0.0                                # time.time() da coleta


@dataclass
class Item:
    texto: str
    prioridade: str  # "alta", "media", "dica"
    motivo: Motivo | None = None  # só nas causas; vai para o banco


# ---------------- coleta ----------------
def _powercfg(*args: str) -> str:
    try:
        r = subprocess.run(["powercfg", *args], capture_output=True, timeout=5, creationflags=SEM_JANELA)
        return r.stdout.decode("cp850", errors="ignore")
    except Exception:
        return ""


def ler_energia() -> tuple[str, int | None, int | None]:
    """(nome do plano, estado máximo AC %, estado máximo DC %)."""
    plano = re.search(r"\((.+)\)", _powercfg("/getactivescheme"))
    hexas = re.findall(r"0x([0-9a-fA-F]{8})\s*$",
                       _powercfg("/query", "SCHEME_CURRENT", "SUB_PROCESSOR", "PROCTHROTTLEMAX"), re.M)
    ac = int(hexas[-2], 16) if len(hexas) >= 2 else None
    dc = int(hexas[-1], 16) if len(hexas) >= 2 else None
    return (plano.group(1) if plano else ""), ac, dc


class Coletor:
    """Mantém os objetos de processo entre chamadas (psutil precisa de duas amostras para o %)."""

    def __init__(self) -> None:
        import psutil
        self.ps = psutil
        self.ncpu = psutil.cpu_count() or 1
        self._energia: tuple[str, int | None, int | None] = ("", None, None)
        self._energia_em = 0.0
        psutil.cpu_percent(None)
        for p in psutil.process_iter(["name"]):
            try:
                p.cpu_percent(None)
            except Exception:
                pass

    def coletar(self) -> Retrato:
        ps = self.ps
        soma: dict[str, float] = {}
        nomes_vistos: set[str] = set()
        for p in ps.process_iter(["name"]):
            try:
                nome = (p.info["name"] or "").strip()
                nomes_vistos.add(nome.lower())
                if nome.lower() in IGNORAR:
                    continue
                soma[nome] = soma.get(nome, 0.0) + p.cpu_percent(None) / self.ncpu
            except Exception:
                continue
        top = sorted(((n, round(v, 1)) for n, v in soma.items() if v >= 0.5), key=lambda x: -x[1])[:5]

        if time.time() - self._energia_em > 60:  # plano de energia muda pouco
            self._energia = ler_energia()
            self._energia_em = time.time()
        bat = ps.sensors_battery()
        return Retrato(
            uso_cpu=ps.cpu_percent(None),
            processos=top,
            plano_energia=self._energia[0],
            estado_max_ac=self._energia[1],
            estado_max_dc=self._energia[2],
            na_tomada=bat.power_plugged if bat else None,
            bateria=int(bat.percent) if bat else None,
            horas_ligado=(time.time() - ps.boot_time()) / 3600,
            software_asus=any(n.startswith(("armourycrate", "asusoptimization", "myasus")) for n in nomes_vistos),
            coletado_em=time.time(),
        )


# ---------------- análise ----------------
def analisar(r: Retrato, temp: float | None, cfg: dict[str, float],
             rpm: int | None = None, parada: bool = False) -> tuple[list[Item], list[Item]]:
    """Devolve (causas prováveis, sugestões), mais importantes primeiro.
    `parada=True`: a temperatura não é confiável agora; nenhuma conclusão é tirada dela."""
    causas: list[Item] = []
    sugestoes: list[Item] = []
    if parada:
        temp = None
        causas.append(Item("A leitura de temperatura está parada (o firmware não atualiza a zona ACPI): "
                           "conclusões por temperatura suspensas. Use a ventoinha como referência.", "media", Motivo.LEITURA_PARADA))
    quente = temp is not None and temp >= cfg["ALERTA_C"]
    critico = temp is not None and temp >= cfg["QUENTE_C"]
    ordem = {"alta": 0, "media": 1, "dica": 2}

    if rpm is not None:
        if rpm == 0 and (quente or r.uso_cpu >= 60):
            causas.append(Item("Ventoinha da CPU parada com o processador quente ou sob carga: "
                               "pode estar travada, suja ou desconectada.", "alta", Motivo.VENTOINHA_PARADA))
            sugestoes.append(Item("Verifique se a ventoinha gira (som/saída de ar). Parada com calor exige "
                                  "assistência técnica.", "alta"))
        elif rpm >= cfg["FAN_ALTA_RPM"]:
            causas.append(Item(f"Ventoinha em rotação alta ({rpm:,} RPM): o notebook está no limite para "
                               "dissipar o calor.".replace(",", "."), "media", Motivo.VENTOINHA_ALTA))

    if temp is not None and temp >= cfg["DANO_C"]:
        causas.append(Item("Temperatura no limite de proteção do firmware: a CPU já está reduzindo desempenho para esfriar.", "alta", Motivo.LIMITE_FIRMWARE))
        sugestoes.append(Item("Salve o trabalho e feche os programas pesados agora; se não baixar, desligue o computador.", "alta"))

    pesados = [(n, v) for n, v in r.processos if v >= 10]
    for nome, uso in pesados:
        causas.append(Item(f"{nome} está usando {uso:.0f}% da CPU.", "alta" if uso >= 25 else "media", Motivo.PROCESSO_PESADO))
    if pesados:
        nomes = ", ".join(n for n, _ in pesados[:3])
        sugestoes.append(Item(f"Feche ou pause {nomes} se não estiver usando (Gerenciador de Tarefas: Ctrl+Shift+Esc).",
                              "alta" if quente else "media"))
    if any(n.lower().startswith(("chrome", "msedge", "firefox", "brave", "opera")) for n, _ in pesados):
        sugestoes.append(Item("Navegador pesado: feche abas com vídeo/anúncios e ative a economia de memória/eficiência.", "media"))

    if r.uso_cpu >= 60:
        causas.append(Item(f"CPU sob carga alta: {r.uso_cpu:.0f}% de uso total.", "alta", Motivo.CPU_CARGA_ALTA))
    elif quente and r.uso_cpu < 20:
        causas.append(Item(f"Temperatura alta com a CPU quase ociosa ({r.uso_cpu:.0f}% de uso): "
                           "pode indicar refrigeração deficiente (poeira, saídas de ar bloqueadas, pasta térmica velha).",
                           "alta", Motivo.REFRIGERACAO_SUSPEITA))
        sugestoes.append(Item("Verifique as saídas de ar: limpe a poeira com ar comprimido (ventoinha travada) "
                              "e não use o notebook sobre cama, sofá ou colo.", "alta"))
        sugestoes.append(Item("Persistindo após a limpeza, a pasta térmica pode estar ressecada: troca em assistência técnica.",
                              "media"))

    plano = r.plano_energia.lower()
    if any(k in plano for k in ("alto desempenho", "desempenho máximo", "high performance", "ultimate")):
        causas.append(Item(f"Plano de energia '{r.plano_energia}' mantém a CPU em frequência alta.", "media", Motivo.PLANO_ALTO_DESEMPENHO))
        sugestoes.append(Item("Troque para o plano 'Equilibrado' (Configurações > Sistema > Energia).", "media"))

    if quente and r.estado_max_ac == 100:
        causas.append(Item("Turbo (boost) liberado: estado máximo do processador em 100% na tomada.", "media", Motivo.TURBO_LIBERADO))
        sugestoes.append(Item("Limitar o estado máximo do processador a 99% desliga o turbo e costuma baixar 10–20 °C "
                              "com pouca perda no uso comum. Opções de Energia > Alterar configurações avançadas > "
                              "Gerenciamento de energia do processador > Estado máximo = 99%.",
                              "alta" if critico else "media"))

    if r.software_asus:
        sugestoes.append(Item("No MyASUS / Armoury Crate, use o modo de ventoinha 'Silencioso' ou 'Equilibrado' "
                              "(o modo 'Turbo/Desempenho' aumenta o limite de potência).", "media" if quente else "dica"))

    if r.na_tomada and r.bateria is not None and r.bateria < 95:
        causas.append(Item(f"Bateria carregando ({r.bateria}%): o carregamento também gera calor.", "dica", Motivo.CARREGANDO_BATERIA))

    if r.horas_ligado >= 72:
        sugestoes.append(Item(f"Ligado há {r.horas_ligado / 24:.0f} dias: reinicie para encerrar processos acumulados.", "dica"))

    sugestoes += [
        Item("Use um suporte que eleve a traseira ou uma base com cooler para melhorar a entrada de ar.", "dica"),
        Item("Mantenha o ambiente ventilado; cada grau a menos no ambiente é um a menos na CPU.", "dica"),
        Item("Limpeza preventiva das ventoinhas a cada 6–12 meses.", "dica"),
    ]
    if not causas:
        if quente:
            causas.append(Item("Sem causa evidente nos processos; acompanhe o gráfico por alguns minutos.", "dica",
                               Motivo.SEM_CAUSA_EVIDENTE))
        else:
            causas.append(Item("Nada fora do normal agora.", "dica"))

    causas.sort(key=lambda i: ordem[i.prioridade])
    sugestoes.sort(key=lambda i: ordem[i.prioridade])
    return causas, sugestoes
