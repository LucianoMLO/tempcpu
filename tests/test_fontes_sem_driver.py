import re
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from amd import TEMP_CPU, TEMP_EDGE, TEMP_GFX, TEMP_SOC, CLK_CPU, interpretar  # noqa: E402
from app import CONFIG_PADRAO  # noqa: E402
from asus import IDS_LEITURA, AsusAtk, decodificar_rpm  # noqa: E402
from diagnostico import Retrato, analisar  # noqa: E402
from sensores import DetectorParada, Leitura  # noqa: E402

CFG = {**CONFIG_PADRAO, "DANO_C": 101.0}


class TestAmd(unittest.TestCase):
    def test_leitura_real_do_4800hs(self):
        s = {TEMP_EDGE: 65, TEMP_GFX: 57, TEMP_SOC: 68, TEMP_CPU: 74, CLK_CPU: 3696}
        self.assertEqual(interpretar(s), {"cpu": 74, "gpu": 57, "soc": 68, "clk_cpu": 3696})

    def test_gpu_cai_para_edge_e_descarta_lixo(self):
        r = interpretar({TEMP_EDGE: 60, TEMP_GFX: 0, TEMP_CPU: 255})
        self.assertEqual((r["gpu"], r["cpu"]), (60, None))


class FakeAtk:
    def __init__(self):
        self.chamadas = []

    def DSTS(self, Device_ID):
        self.chamadas.append(("DSTS", Device_ID))
        return (0x0001001C,)

    def __getattr__(self, nome):  # qualquer outro método = falha do teste
        raise AssertionError(f"método proibido chamado: {nome}")


class FakeWmi:
    def __init__(self, atk):
        self.atk = atk

    def AsusAtkWmi_WMNB(self):
        return [self.atk]


class TestAsus(unittest.TestCase):
    def test_decodifica(self):
        self.assertEqual(decodificar_rpm(0x0001001C), 2800)
        self.assertIsNone(decodificar_rpm(0x00000000))   # sem bit de presença
        self.assertIsNone(decodificar_rpm(0xFFFFFFFE))   # não suportado
        self.assertIsNone(decodificar_rpm(None))

    def test_so_chama_dsts_com_id_fixo(self):
        atk = FakeAtk()
        self.assertEqual(AsusAtk(FakeWmi(atk)).ventoinha_cpu_rpm(), 2800)
        self.assertEqual(atk.chamadas, [("DSTS", 0x00110013)])
        self.assertTrue(all(i in IDS_LEITURA.values() for _, i in atk.chamadas))

    def test_codigo_nao_usa_metodo_de_escrita(self):
        fonte = (RAIZ / "asus.py").read_text(encoding="utf-8")
        codigo = "\n".join(l for l in fonte.splitlines() if not l.strip().startswith(("#", "-", '"""')))
        self.assertEqual(set(re.findall(r"self\._obj\.(\w+)\(", codigo)), {"DSTS"})
        self.assertNotIn("DEVS(", codigo)


class TestDetectorParada(unittest.TestCase):
    def test_acpi_congelada_vira_parada(self):
        d = DetectorParada(minutos=3)
        l = Leitura(86.1, "ACPI", "THRM_0", carimbo=17)
        self.assertFalse(d.atualizar(l, agora=0))
        self.assertFalse(d.atualizar(l, agora=179))
        self.assertTrue(d.atualizar(l, agora=180))

    def test_mudanca_zera_a_contagem(self):
        d = DetectorParada(minutos=3)
        d.atualizar(Leitura(86.1, "ACPI", "Z", carimbo=17), agora=0)
        self.assertFalse(d.atualizar(Leitura(86.1, "ACPI", "Z", carimbo=18), agora=200))
        self.assertFalse(d.atualizar(Leitura(86.1, "ACPI", "Z", carimbo=18), agora=300))

    def test_fonte_sem_carimbo_nunca_para(self):
        d = DetectorParada(minutos=0)
        l = Leitura(70, "AMD", "CPU")
        self.assertFalse(d.atualizar(l, agora=0))
        self.assertFalse(d.atualizar(l, agora=999))


class TestRegrasNovas(unittest.TestCase):
    def textos(self, itens):
        return " | ".join(i.texto for i in itens)

    def test_parada_suspende_conclusoes_por_temperatura(self):
        causas, _ = analisar(Retrato(uso_cpu=5, estado_max_ac=100), 86.1, CFG, parada=True)
        t = self.textos(causas)
        self.assertIn("parada", t)
        self.assertNotIn("refrigeração", t)
        self.assertNotIn("Turbo", t)

    def test_ventoinha_parada_com_carga(self):
        causas, sug = analisar(Retrato(uso_cpu=90), 80, CFG, rpm=0)
        self.assertEqual(causas[0].prioridade, "alta")
        self.assertIn("Ventoinha da CPU parada", causas[0].texto)

    def test_ventoinha_alta(self):
        causas, _ = analisar(Retrato(uso_cpu=30), 70, CFG, rpm=5200)
        self.assertIn("5.200 RPM", self.textos(causas))

    def test_ventoinha_normal_sem_alerta(self):
        causas, _ = analisar(Retrato(uso_cpu=10), 60, CFG, rpm=2800)
        self.assertNotIn("Ventoinha", self.textos(causas))


if __name__ == "__main__":
    unittest.main()
