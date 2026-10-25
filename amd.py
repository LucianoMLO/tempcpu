"""Sensores da AMD pela ADL: DLL do driver de vídeo já instalado, em modo usuário (nenhum driver novo).

A DLL é carregada só pelo caminho absoluto em System32 (evita sequestro de DLL).
Nos APUs Ryzen (CPU + Radeon no mesmo chip) o driver expõe temperatura da CPU, da GPU e do SoC.
"""
from __future__ import annotations

import ctypes
import os
from ctypes import CFUNCTYPE, Structure, byref, c_char, c_int, c_void_p
from pathlib import Path

DLL = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "atiadlxx.dll"

# Índices de ADL_PMLOG_SENSORS (adl_defines.h)
TEMP_EDGE, TEMP_GFX, TEMP_SOC, TEMP_CPU, CLK_CPU = 8, 28, 29, 32, 34


class _AdapterInfo(Structure):
    _fields_ = [("iSize", c_int), ("iAdapterIndex", c_int), ("strUDID", c_char * 256), ("iBusNumber", c_int),
                ("iDeviceNumber", c_int), ("iFunctionNumber", c_int), ("iVendorID", c_int),
                ("strAdapterName", c_char * 256), ("strDisplayName", c_char * 256), ("iPresent", c_int),
                ("iExist", c_int), ("strDriverPath", c_char * 256), ("strDriverPathExt", c_char * 256),
                ("strPNPString", c_char * 256), ("iOSDisplayIndex", c_int)]


class _Sensor(Structure):
    _fields_ = [("supported", c_int), ("value", c_int)]


class _PMLog(Structure):
    _fields_ = [("size", c_int), ("sensors", _Sensor * 256)]


def _temp_valida(v: int | None) -> int | None:
    return v if v is not None and 0 < v < 150 else None


def interpretar(sensores: dict[int, int]) -> dict[str, int | None]:
    """Recebe {índice: valor} dos sensores suportados e devolve os que o app usa."""
    gpu = _temp_valida(sensores.get(TEMP_GFX)) or _temp_valida(sensores.get(TEMP_EDGE))
    return {
        "cpu": _temp_valida(sensores.get(TEMP_CPU)),
        "gpu": gpu,
        "soc": _temp_valida(sensores.get(TEMP_SOC)),
        "clk_cpu": sensores.get(CLK_CPU) or None,
    }


class AmdAdl:
    """Abre o contexto ADL uma vez e reaproveita. Levanta OSError se não houver AMD com sensores."""

    def __init__(self) -> None:
        if not DLL.exists():
            raise OSError("driver AMD (atiadlxx.dll) não encontrado")
        self._dll = ctypes.CDLL(str(DLL))
        self._buffers: list = []
        tipo_malloc = CFUNCTYPE(c_void_p, c_int)

        def alocar(n: int) -> int:
            b = ctypes.create_string_buffer(n)
            self._buffers.append(b)
            return ctypes.addressof(b)

        self._malloc = tipo_malloc(alocar)  # referência mantida: a DLL chama de volta
        self._ctx = c_void_p()
        if self._dll.ADL2_Main_Control_Create(self._malloc, 1, byref(self._ctx)) != 0:
            raise OSError("ADL não inicializou")
        self._log = _PMLog()
        self.indice = self._achar_adaptador()
        self.nome = ""
        if self.indice is None:
            self.fechar()
            raise OSError("nenhum adaptador AMD expõe sensores")

    def _achar_adaptador(self) -> int | None:
        n = c_int()
        self._dll.ADL2_Adapter_NumberOfAdapters_Get(self._ctx, byref(n))
        if n.value <= 0:
            return None
        infos = (_AdapterInfo * n.value)()
        self._dll.ADL2_Adapter_AdapterInfo_Get(self._ctx, infos, ctypes.sizeof(infos))
        vistos: set[int] = set()
        for a in infos:
            if a.iBusNumber in vistos:
                continue
            vistos.add(a.iBusNumber)
            if self._dll.ADL2_New_QueryPMLogData_Get(self._ctx, a.iAdapterIndex, byref(self._log)) == 0:
                self.nome = a.strAdapterName.decode(errors="ignore").strip()
                return a.iAdapterIndex
        return None

    def ler(self) -> dict[str, int | None]:
        if self._dll.ADL2_New_QueryPMLogData_Get(self._ctx, self.indice, byref(self._log)) != 0:
            raise OSError("leitura ADL falhou")
        s = self._log.sensors
        return interpretar({i: s[i].value for i in range(256) if s[i].supported})

    def fechar(self) -> None:
        try:
            self._dll.ADL2_Main_Control_Destroy(self._ctx)
        except Exception:
            pass
