"""Integrações com o Windows: instância única, liberação de memória e início automático."""
from __future__ import annotations

import ctypes
import subprocess
import sys
import threading
from pathlib import Path
from typing import Callable

PASTA = Path(__file__).resolve().parent
NOME_TAREFA = "TempCPU"
SEM_JANELA = 0x08000000

_k32 = ctypes.windll.kernel32
_k32.CreateMutexW.restype = ctypes.c_void_p
_k32.CreateEventW.restype = ctypes.c_void_p
_k32.OpenEventW.restype = ctypes.c_void_p
_k32.GetCurrentProcess.restype = ctypes.c_void_p
_k32.SetEvent.argtypes = [ctypes.c_void_p]
_k32.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
_k32.CloseHandle.argtypes = [ctypes.c_void_p]
_k32.SetProcessWorkingSetSize.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_size_t]
ERRO_JA_EXISTE = 183
EVENTO_MODIFICAR = 0x0002


class InstanciaUnica:
    """Mutex nomeado. A segunda cópia só avisa a primeira para abrir a janela e sai."""

    def __init__(self, nome: str = "TempCPU") -> None:
        self._nome_evento = f"Local\\{nome}_abrir"
        self._mutex = _k32.CreateMutexW(None, False, f"Local\\{nome}_mutex")
        self.primeira = ctypes.GetLastError() != ERRO_JA_EXISTE
        self._evento = _k32.CreateEventW(None, False, False, self._nome_evento) if self.primeira else None

    def avisar_primeira(self) -> bool:
        h = _k32.OpenEventW(EVENTO_MODIFICAR, False, self._nome_evento)
        if not h:
            return False
        _k32.SetEvent(h)
        _k32.CloseHandle(h)
        return True

    def ao_ser_chamada(self, acao: Callable[[], None]) -> None:
        def esperar() -> None:
            while True:
                if _k32.WaitForSingleObject(self._evento, 0xFFFFFFFF) == 0:
                    acao()
        threading.Thread(target=esperar, daemon=True).start()


def definir_app_id(app_id: str = "MASolucoes.TempCPU") -> None:
    """Separa o app do agrupamento do Python na barra de tarefas: o botão usa o ícone da própria janela."""
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        pass


def liberar_memoria() -> None:
    """Devolve ao Windows as páginas não usadas (o processo recarrega o que precisar)."""
    try:
        _k32.SetProcessWorkingSetSize(_k32.GetCurrentProcess(), ctypes.c_size_t(-1), ctypes.c_size_t(-1))
    except Exception:
        pass


# ---------------- início automático ----------------
# Tarefa agendada no logon com privilégio elevado: a zona ACPI exige administrador e,
# por tarefa, o Windows não mostra o aviso do UAC a cada logon. As opções de energia
# são liberadas porque, por padrão, tarefas não iniciam na bateria e morrem após 72 h.
def _pythonw() -> str:
    exe = Path(sys.executable)
    candidato = exe.with_name("pythonw.exe")
    return str(candidato if candidato.exists() else exe)


def _powershell(script: str) -> subprocess.CompletedProcess:
    return subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                          capture_output=True, timeout=30, creationflags=SEM_JANELA)


def inicio_automatico_ativo() -> bool:
    r = subprocess.run(["schtasks", "/Query", "/TN", NOME_TAREFA], capture_output=True,
                       timeout=15, creationflags=SEM_JANELA)
    return r.returncode == 0


def ativar_inicio_automatico() -> tuple[bool, str]:
    script = (
        f"$a = New-ScheduledTaskAction -Execute '{_pythonw()}' -Argument '\"{PASTA / 'app.py'}\"' "
        f"-WorkingDirectory '{PASTA}';"
        "$t = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME;"
        "$t.Delay = 'PT20S';"
        "$s = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries "
        "-ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew;"
        "$p = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest;"
        f"Register-ScheduledTask -TaskName '{NOME_TAREFA}' -Action $a -Trigger $t -Settings $s "
        "-Principal $p -Description 'TempCPU: temperatura na bandeja' -Force | Out-Null"
    )
    r = _powershell(script)
    return r.returncode == 0, r.stderr.decode("cp850", errors="ignore").strip()


def desativar_inicio_automatico() -> tuple[bool, str]:
    r = subprocess.run(["schtasks", "/Delete", "/TN", NOME_TAREFA, "/F"], capture_output=True,
                       timeout=15, creationflags=SEM_JANELA)
    return r.returncode == 0, r.stderr.decode("cp850", errors="ignore").strip()
