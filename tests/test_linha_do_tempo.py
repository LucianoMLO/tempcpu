import sys
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from linha_do_tempo import (agrupar_unidades, escala_y, escolher_nivel, formatar_x,  # noqa: E402
                            ponto_mais_proximo, ticks_bonitos)


class TestNivel(unittest.TestCase):
    def test_automatica_mantem_poucos_pontos(self):
        self.assertEqual(escolher_nivel(3600, "Automática"), ("minuto", ""))
        self.assertEqual(escolher_nivel(86400, "Automática")[0], "minuto")        # 1.440 pontos
        self.assertEqual(escolher_nivel(7 * 86400, "Automática")[0], "hora")      # 168
        self.assertEqual(escolher_nivel(365 * 86400, "Automática")[0], "dia")     # 8.760 horas > 1.500 pontos
        self.assertEqual(escolher_nivel(3 * 365 * 86400, "Automática")[0], "dia")
        self.assertEqual(escolher_nivel(5 * 365 * 86400, "Automática")[0], "semana")  # 1.825 dias > 1.500

    def test_manual_sobe_de_nivel_se_tiver_pontos_demais(self):
        nivel, aviso = escolher_nivel(30 * 86400, "Minuto")  # 43.200 pontos
        self.assertEqual(nivel, "hora")
        self.assertIn("pontos demais", aviso)
        self.assertEqual(escolher_nivel(86400, "Hora"), ("hora", ""))


class TestEixos(unittest.TestCase):
    def test_ticks_redondos(self):
        self.assertEqual(ticks_bonitos(40, 100, 6), [40, 50, 60, 70, 80, 90, 100])
        self.assertEqual(ticks_bonitos(0, 1, 5), [0, 0.2, 0.4, 0.6, 0.8, 1.0])
        self.assertEqual(ticks_bonitos(0, 6000, 5), [0, 2000, 4000, 6000])

    def test_formato_do_tempo_conforme_a_duracao(self):
        ts = datetime(2026, 10, 21, 15, 42).timestamp()
        self.assertEqual(formatar_x(ts, 3600), "15:42")
        self.assertEqual(formatar_x(ts, 7 * 86400), "21/10 15h")
        self.assertEqual(formatar_x(ts, 365 * 86400), "21/10/26")

    def test_escala_de_temperatura_inclui_a_faixa_de_atencao(self):
        dados = [{"min": 45.0, "max": 60.0}]
        baixo, alto = escala_y("cpu_c", dados)
        self.assertLessEqual(baixo, 40)
        self.assertGreaterEqual(alto, 80)
        self.assertEqual(escala_y("uso_cpu", dados), (0.0, 100.0))
        self.assertEqual(escala_y("ventoinha_rpm", [{"min": 2600, "max": 5800}])[0], 0.0)

    def test_eixo_nunca_fica_abaixo_do_maior_valor(self):
        """Bug real: RPM de 3.100 com eixo até 3.000 deixava a linha fora do gráfico."""
        for var in ("ventoinha_rpm", "clk_mhz"):
            for mx in (130, 1100, 2100, 2999, 3100, 4200, 4499, 5800, 7000, 12345):
                baixo, alto = escala_y(var, [{"min": 1, "max": mx}])
                self.assertGreaterEqual(alto, mx, (var, mx, alto))


class TestVariasVariaveis(unittest.TestCase):
    def test_agrupa_por_unidade_na_ordem_escolhida(self):
        grupos, rejeitadas = agrupar_unidades(["cpu_c", "ventoinha_rpm", "gpu_c"])
        self.assertEqual(grupos, [("°C", ["cpu_c", "gpu_c"]), ("RPM", ["ventoinha_rpm"])])
        self.assertEqual(rejeitadas, [])

    def test_terceira_unidade_e_rejeitada(self):
        grupos, rejeitadas = agrupar_unidades(["cpu_c", "uso_cpu", "ventoinha_rpm", "soc_c"])
        self.assertEqual([g[0] for g in grupos], ["°C", "%"])
        self.assertEqual(grupos[0][1], ["cpu_c", "soc_c"])
        self.assertEqual(rejeitadas, ["ventoinha_rpm"])

    def test_tomada_tem_unidade_propria(self):
        self.assertEqual(agrupar_unidades(["tomada"])[0], [("fração", ["tomada"])])

    def test_ponto_mais_proximo_respeita_a_tolerancia(self):
        pts = [{"ts": 100}, {"ts": 160}, {"ts": 220}]
        self.assertEqual(ponto_mais_proximo(pts, 170, 30)["ts"], 160)
        self.assertEqual(ponto_mais_proximo(pts, 100, 30)["ts"], 100)
        self.assertIsNone(ponto_mais_proximo(pts, 400, 30))
        self.assertIsNone(ponto_mais_proximo([], 100, 30))


if __name__ == "__main__":
    unittest.main()
