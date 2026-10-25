import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import CONFIG_PADRAO  # noqa: E402
from diagnostico import Retrato, analisar  # noqa: E402

CFG = {**CONFIG_PADRAO, "DANO_C": 105.0}


def textos(itens):
    return " | ".join(i.texto for i in itens)


class TestAnalise(unittest.TestCase):
    def test_processo_pesado_vira_causa_e_sugestao(self):
        r = Retrato(uso_cpu=45, processos=[("chrome.exe", 30.0), ("python.exe", 3.0)])
        causas, sug = analisar(r, 88, CFG)
        self.assertIn("chrome.exe está usando 30%", textos(causas))
        self.assertEqual(causas[0].prioridade, "alta")
        self.assertIn("Feche ou pause chrome.exe", textos(sug))
        self.assertIn("Navegador pesado", textos(sug))
        self.assertNotIn("python.exe", textos(causas))

    def test_quente_e_ociosa_aponta_refrigeracao(self):
        causas, sug = analisar(Retrato(uso_cpu=5), 86, CFG)
        self.assertIn("refrigeração deficiente", textos(causas))
        self.assertIn("poeira", textos(sug))

    def test_turbo_so_sugerido_quando_quente(self):
        r = Retrato(uso_cpu=30, estado_max_ac=100)
        _, frio = analisar(r, 55, CFG)
        _, quente = analisar(r, 92, CFG)
        self.assertNotIn("99%", textos(frio))
        self.assertIn("99%", textos(quente))
        self.assertEqual(quente[0].prioridade, "alta")

    def test_plano_alto_desempenho(self):
        causas, sug = analisar(Retrato(plano_energia="Alto desempenho"), 70, CFG)
        self.assertIn("Alto desempenho", textos(causas))
        self.assertIn("Equilibrado", textos(sug))

    def test_zona_de_dano(self):
        causas, sug = analisar(Retrato(uso_cpu=90), 106, CFG)
        self.assertIn("limite de proteção", causas[0].texto)
        self.assertIn("desligue", sug[0].texto)

    def test_normal_sem_causa(self):
        causas, sug = analisar(Retrato(uso_cpu=8), 50, CFG)
        self.assertEqual(textos(causas), "Nada fora do normal agora.")
        self.assertTrue(all(i.prioridade == "dica" for i in sug))


if __name__ == "__main__":
    unittest.main()
