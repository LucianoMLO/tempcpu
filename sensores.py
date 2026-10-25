"""Fontes de temperatura no Windows, sem instalar driver no núcleo do sistema.

Ordem de preferência para a CPU:
1. AMD ADL — sensor de CPU exposto pelo driver de vídeo AMD já instalado (APUs Ryzen).
   Atualiza a cada segundo. Modo usuário, sem driver novo.
2. LibreHardwareMonitor — só se o usuário já o tiver aberto (este app não o instala nem recomenda).
3. Zona térmica ACPI (WMI root/wmi) — sensor da placa, guardado pelo Windows e relido só
   quando o firmware avisa. Pode ficar parado por horas: ver DetectorParada.
"""
from __future__ import annotations

import ctypes
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

KELVIN_ZERO = 273.15
SEM_JANELA = 0x08000000
# Caminho fixo (não resolve pelo PATH): é onde o driver NVIDIA instala a ferramenta.
NVIDIA_SMI = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "nvidia-smi.exe"

# Nomes de sensor do LHM em ordem de preferência (o primeiro que existir vence).
PREFERENCIA_LHM = ("CPU Package", "Core (Tctl/Tdie)", "Core (Tdie)", "Core (Tctl)", "Core Max", "Core Average")
PREFERENCIA_GPU = ("GPU Core", "GPU Hot Spot", "GPU Package")


@dataclass
class Leitura:
    celsius: float
    fonte: str                 # "AMD", "LibreHardwareMonitor", "ACPI", "nvidia-smi"
    sensor: str                # nome do sensor/zona usado
    carimbo: int | None = None  # ACPI ThermalStamp: muda a cada releitura feita pelo Windows


class SemLeitura(Exception):
    """Nenhuma fonte devolveu temperatura; a mensagem diz o que fazer."""


def eh_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def acpi_para_celsius(decimos_kelvin: int) -> float:
    """MSAcpi_ThermalZoneTemperature devolve décimos de Kelvin (3592 -> 86,1 °C)."""
    return round(decimos_kelvin / 10 - KELVIN_ZERO, 1)


def escolher_sensor_lhm(sensores: list[tuple[str, str, float]]) -> tuple[str, float] | None:
    """Recebe (identificador, nome, valor) e devolve o melhor sensor de CPU."""
    da_cpu = [(nome, valor) for ident, nome, valor in sensores
              if "cpu" in ident.lower() and valor and valor > 0]
    if not da_cpu:
        return None
    por_nome = dict(da_cpu)
    for nome in PREFERENCIA_LHM:
        if nome in por_nome:
            return nome, por_nome[nome]
    return max(da_cpu, key=lambda s: s[1])


def escolher_sensor_gpu(sensores: list[tuple[str, str, float]]) -> tuple[str, float] | None:
    """Igual ao da CPU, para identificadores de GPU do LHM (/gpu-nvidia, /gpu-amd, /gpu-intel)."""
    da_gpu = [(nome, valor) for ident, nome, valor in sensores
              if "gpu" in ident.lower() and valor and valor > 0]
    if not da_gpu:
        return None
    por_nome = dict(da_gpu)
    for nome in PREFERENCIA_GPU:
        if nome in por_nome:
            return nome, por_nome[nome]
    return max(da_gpu, key=lambda s: s[1])


def zona_mais_quente(zonas: list[tuple[str, int]]) -> tuple[str, float] | None:
    """Recebe (instância, décimos de Kelvin) e devolve a zona mais quente em °C."""
    validas = [(nome, acpi_para_celsius(v)) for nome, v in zonas if v and v > 0]
    validas = [(n, c) for n, c in validas if -20 < c < 150]  # descarta lixo de firmware
    return max(validas, key=lambda z: z[1]) if validas else None


class DetectorParada:
    """Marca a leitura como parada quando valor e carimbo não mudam por `minutos`.
    Só se aplica a fontes com carimbo (ACPI); as demais nunca são consideradas paradas."""

    def __init__(self, minutos: float) -> None:
        self.limite_s = minutos * 60
        self._chave: tuple | None = None
        self._desde_mono = 0.0
        self.desde: float | None = None  # time.time() da última mudança

    def atualizar(self, leitura: Leitura, agora: float | None = None) -> bool:
        if leitura.carimbo is None:
            self._chave = None
            return False
        agora = time.monotonic() if agora is None else agora
        chave = (leitura.celsius, leitura.carimbo)
        if chave != self._chave:
            self._chave = chave
            self._desde_mono = agora
            self.desde = time.time()
            return False
        return agora - self._desde_mono >= self.limite_s


class LeitorTemperatura:
    """Mantém as conexões abertas e tenta as fontes em ordem."""

    def __init__(self) -> None:
        import wmi  # importado aqui para os testes rodarem sem pywin32
        self._wmi = wmi
        self._lhm = None
        self._acpi = None
        self._amd = None
        self._amd_tentado = False
        self.amd_ultimo: dict[str, int | None] = {}  # cpu, gpu, soc, clk_cpu da última leitura
        self._gpu_cache: Leitura | None = None
        self._gpu_em = -1e9
        self.ultimo_erro = ""

    def _conectar(self, namespace: str):
        try:
            return self._wmi.WMI(namespace=namespace)
        except Exception:
            return None

    def conexao_root_wmi(self):
        if self._acpi is None:
            self._acpi = self._conectar("root/wmi")
        return self._acpi

    # ---------- AMD ----------
    def _ler_amd(self) -> Leitura | None:
        if self._amd is None and not self._amd_tentado:
            self._amd_tentado = True
            try:
                from amd import AmdAdl
                self._amd = AmdAdl()
            except Exception as e:
                self.ultimo_erro = f"AMD: {e}"
        if self._amd is None:
            return None
        try:
            self.amd_ultimo = self._amd.ler()
        except Exception:
            self.amd_ultimo = {}
            return None
        cpu = self.amd_ultimo.get("cpu")
        return Leitura(float(cpu), "AMD", "CPU (driver de vídeo)") if cpu else None

    # ---------- LibreHardwareMonitor (só se já estiver aberto) ----------
    def _sensores_lhm(self) -> list[tuple[str, str, float]]:
        if self._lhm is None:
            self._lhm = self._conectar("root/LibreHardwareMonitor")
        if self._lhm is None:
            return []
        try:
            return [(s.Identifier, s.Name, float(s.Value or 0)) for s in self._lhm.Sensor(SensorType="Temperature")]
        except Exception:
            self._lhm = None  # LHM foi fechado; tenta reconectar na próxima
            return []

    def _ler_lhm(self) -> Leitura | None:
        escolhido = escolher_sensor_lhm(self._sensores_lhm())
        if escolhido:
            return Leitura(round(escolhido[1], 1), "LibreHardwareMonitor", escolhido[0])
        return None

    # ---------- ACPI ----------
    def _zonas_acpi(self) -> list:
        con = self.conexao_root_wmi()
        if con is None:
            return []
        try:
            return list(con.MSAcpi_ThermalZoneTemperature())
        except Exception as e:
            self.ultimo_erro = str(e)
            return []

    def _ler_acpi(self) -> Leitura | None:
        zonas = self._zonas_acpi()
        escolhida = zona_mais_quente([(z.InstanceName, int(z.CurrentTemperature)) for z in zonas])
        if not escolhida:
            return None
        z = next(z for z in zonas if z.InstanceName == escolhida[0])
        return Leitura(escolhida[1], "ACPI", escolhida[0].split("\\")[-1], int(z.ThermalStamp or 0))

    def limites_firmware(self) -> tuple[float, float] | None:
        """(redução de desempenho, desligamento) em °C, definidos pelo firmware na zona ACPI."""
        for z in self._zonas_acpi():
            passivo, critico = int(z.PassiveTripPoint or 0), int(z.CriticalTripPoint or 0)
            if passivo > 2732 and critico > 2732:
                return acpi_para_celsius(passivo), acpi_para_celsius(critico)
        return None

    # ---------- API pública ----------
    def ler(self) -> Leitura:
        leitura = self._ler_amd() or self._ler_lhm() or self._ler_acpi()
        if leitura:
            return leitura
        if not eh_admin():
            raise SemLeitura("Sem permissão para ler a zona térmica ACPI. Abra pelo iniciar.bat (pede administrador).")
        raise SemLeitura("Este computador não expõe temperatura da CPU por nenhuma fonte sem driver de núcleo.")

    def ler_gpu(self) -> Leitura | None:
        """GPU: AMD (mesma leitura da CPU), LHM se aberto, ou nvidia-smi (NVIDIA). None se nada expõe."""
        gpu = self.amd_ultimo.get("gpu")
        if gpu:
            return Leitura(float(gpu), "AMD", "GPU integrada")
        if time.monotonic() - self._gpu_em < 10:  # LHM/nvidia-smi custam mais: reaproveita por 10 s
            return self._gpu_cache
        self._gpu_cache, self._gpu_em = self._ler_gpu_externa(), time.monotonic()
        return self._gpu_cache

    def _ler_gpu_externa(self) -> Leitura | None:
        escolhido = escolher_sensor_gpu(self._sensores_lhm())
        if escolhido:
            return Leitura(round(escolhido[1], 1), "LibreHardwareMonitor", escolhido[0])
        if NVIDIA_SMI.exists():
            try:
                r = subprocess.run([str(NVIDIA_SMI), "--query-gpu=name,temperature.gpu", "--format=csv,noheader"],
                                   capture_output=True, text=True, timeout=5, creationflags=SEM_JANELA)
                nome, temp = r.stdout.strip().splitlines()[0].rsplit(",", 1)
                return Leitura(float(temp), "nvidia-smi", nome.strip())
            except Exception:
                return None
        return None
