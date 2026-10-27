"""Gera as capturas da página de apresentação com DADOS DE DEMONSTRAÇÃO.

Nada vem do computador de quem roda: o banco é criado numa pasta temporária (LOCALAPPDATA aponta para ela),
o leitor de temperatura, a GPU, o SoC, a ventoinha e o retrato do sistema (processos, plano de energia) são
falsos e usam nomes genéricos. Uso:

    .venv\\Scripts\\python tools\\gerar_capturas.py            # tempcpu e historico
    python -m lab --sintetico --licao 1 --foto site\\img\\lab1.png   # o Laboratório já usa dados sintéticos
"""
from __future__ import annotations

import math
import os
import random
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "site" / "img"
PASTA = Path(tempfile.mkdtemp(prefix="tempcpu_demo_"))
os.environ["LOCALAPPDATA"] = str(PASTA)          # antes de importar o app: o histórico vai para a pasta temporária
sys.path.insert(0, str(RAIZ))

import tkinter as tk  # noqa: E402

import app as modulo_app  # noqa: E402
from diagnostico import Retrato  # noqa: E402
from historico import AcumuladorMinuto, Historico  # noqa: E402
from motivos import Motivo  # noqa: E402
from sensores import Leitura  # noqa: E402
from tema import zona_de  # noqa: E402

random.seed(11)
PROGRAMAS = ["navegador.exe", "editor_de_video.exe", "planilha.exe", "compilador.exe"]


class LeitorFalso:
    """Temperatura em ciclo suave (nunca lê sensor real)."""
    amd_ultimo = {"gpu": 47, "soc": 52, "clk_cpu": 3650}

    def __init__(self) -> None:
        self.t0 = time.time()

    def ler(self) -> Leitura:
        t = time.time() - self.t0
        return Leitura(58 + 9 * math.sin(t / 7) + random.uniform(-0.6, 0.6), "AMD", "CPU (demonstração)")

    def ler_gpu(self):
        return Leitura(47.0, "AMD", "GPU integrada")

    def limites_firmware(self):
        return (101.1, 103.1)

    def conexao_root_wmi(self):
        return None


class AsusFalso:
    def __init__(self, *_a) -> None:
        pass

    def ventoinha_cpu_rpm(self) -> int:
        return 2840 + random.randint(-40, 40)


class ColetorFalso:
    def coletar(self) -> Retrato:
        return Retrato(uso_cpu=34.0, processos=[(PROGRAMAS[0], 18.0), (PROGRAMAS[1], 9.5), (PROGRAMAS[2], 3.2), (PROGRAMAS[3], 1.4)],
                       plano_energia="Equilibrado", estado_max_ac=100, estado_max_dc=100, na_tomada=True, bateria=100,
                       horas_ligado=5.5, software_asus=False, coletado_em=time.time())


def semear(h: Historico, cfg) -> None:
    agora = int(time.time() // 60 * 60)
    inicio = agora - 4 * 86400
    rajadas, t = [], inicio
    while t < agora:
        t += random.randint(90, 400) * 60
        rajadas.append((t, t + random.randint(15, 45) * 60, random.choice(PROGRAMAS)))
    for ts in range(inicio, agora, 60):
        hora = datetime.fromtimestamp(ts).hour
        base = 50 + 5 * math.sin((hora - 9) / 24 * 2 * math.pi)
        raj = next((r for r in rajadas if r[0] <= ts < r[1]), None)
        alvo = base + (random.uniform(28, 42) if raj else 0)
        acc = AcumuladorMinuto(ts)
        for i in range(30):
            acc.amostras += 1
            acc.valor("cpu_c", round(alvo + random.gauss(0, 2 if raj else 1.2)), ts + i * 2)
            acc.valor("gpu_c", round(alvo - 10 + random.gauss(0, 1)))
            acc.valor("soc_c", round(alvo - 6 + random.gauss(0, 1)))
            acc.valor("clk_mhz", 3900 - (alvo - 50) * 18 + random.gauss(0, 40))
            acc.fontes["AMD"] += 1
        for _ in range(2):
            acc.valor("uso_cpu", (70 if raj else 12) + random.gauss(0, 6))
        for _ in range(6):
            acc.valor("ventoinha_rpm", 2600 + max(0, alvo - 52) * 70 + random.gauss(0, 60))
        acc.valor("bateria_pct", 100)
        acc.valor("tomada", 1.0)
        acc.planos["Equilibrado"] += 1
        acc.estado_max = 100
        if raj:
            acc.motivos[Motivo.PROCESSO_PESADO.value] += 1
            acc.principais[Motivo.PROCESSO_PESADO.value] += 1
            acc.programas[raj[2]] += 1
            acc.pct_programa[raj[2]] = random.uniform(25, 55)
        h.gravar_minuto(acc.fechar(lambda c: zona_de(c, cfg)))


def foto(janela: tk.Misc, nome: str) -> None:
    from PIL import ImageGrab
    janela.attributes("-topmost", True)
    janela.lift()
    janela.update()
    x, y, w, h = janela.winfo_rootx(), janela.winfo_rooty(), janela.winfo_width(), janela.winfo_height()
    SAIDA.mkdir(parents=True, exist_ok=True)
    ImageGrab.grab(bbox=(x, y, x + w, y + h)).save(SAIDA / nome)
    print("gravado", SAIDA / nome, flush=True)


def main() -> None:
    modulo_app.LeitorTemperatura = LeitorFalso
    modulo_app.Coletor = ColetorFalso
    modulo_app.eh_admin = lambda: True
    import asus
    asus.AsusAtk = AsusFalso
    cfg = modulo_app.carregar_config()
    cfg["DANO_AUTO"] = False
    cfg["DANO_C"] = 101.1
    (PASTA / "TempCPU").mkdir(parents=True, exist_ok=True)
    h = Historico(PASTA / "TempCPU" / "historico.db")
    semear(h, cfg)
    h.fechar()

    raiz = tk.Tk()
    raiz.withdraw()
    ap = modulo_app.App(raiz, cfg)
    ap.bandeja = None
    ap.abrir_janela()
    # enche o gráfico com uma série plausível de ~10 min e deixa as leituras falsas rodarem
    for i in range(300):
        ap.historico.append(56 + 8 * math.sin(i / 25) + random.uniform(-0.8, 0.8))

    def tirar_principal():
        foto(raiz, "tempcpu.png")
        ap.abrir_historico()
        raiz.after(1800, tirar_historico)

    def tirar_historico():
        j = ap.janela_historico
        foto(j.top, "historico.png")
        raiz.after(200, lambda: (ap.sair() if hasattr(ap, "sair") else raiz.destroy()))

    raiz.after(6000, tirar_principal)
    raiz.mainloop()


if __name__ == "__main__":
    main()
