import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _base  # noqa: E402,F401

import numpy as np  # noqa: E402

from lab.sintetico import MIN_POR_DIA, ParametrosSinteticos as P, gabarito_de, gerar  # noqa: E402


class TestGerador(unittest.TestCase):
    def test_mesma_semente_mesmos_dados_e_outra_semente_outros(self):
        a, b, c = gerar(P()), gerar(P()), gerar(P(semente=8))
        self.assertTrue(np.array_equal(a.dados["temperatura"], b.dados["temperatura"]))
        self.assertFalse(np.array_equal(a.dados["temperatura"], c.dados["temperatura"]))

    def test_forma_dos_dados(self):
        c = gerar(P(dias=5))
        self.assertEqual(c.n, 5 * MIN_POR_DIA)
        self.assertTrue(np.all(np.diff(c.ts) > 0))
        self.assertEqual((c.origem, c.semente), ("sintetico", 7))
        for nome, v in c.dados.items():
            self.assertEqual(len(v), c.n, nome)
            self.assertFalse(np.isnan(v).any(), nome)
        self.assertTrue(((c.dados["hora"] >= 7) & (c.dados["hora"] <= 21)).all())
        self.assertTrue(set(np.unique(c.dados["tomada"])) <= {0.0, 1.0})
        self.assertTrue(((c.dados["uso"] >= 1) & (c.dados["uso"] <= 100)).all())

    def test_parametros_fora_da_faixa_sao_recusados(self):
        for kw in ({"dias": 2}, {"dias": 31}, {"ruido_c": 0.1}, {"correlacao_uso_freq": 0.99}, {"episodios": 31}):
            with self.assertRaises(ValueError, msg=str(kw)):
                gerar(P(**kw))

    def test_gabarito_corresponde_aos_parametros(self):
        g = gabarito_de(P(efeito_uso=0.5, efeito_tomada=3.0, poeira_por_dia=0.1))
        self.assertEqual((g["uso"], g["tomada"], g["dia"], g["freq"], g["intercepto"]), (0.5, 3.0, 0.1, 0.0, 38.0))
        self.assertAlmostEqual(float(np.hypot(g["hora_sen"], g["hora_cos"])), 4.0)   # amplitude da hora

    def test_temperatura_menos_a_parte_conhecida_e_so_ruido_e_deriva(self):
        """O que sobra depois de tirar a fórmula conhecida é ruído + deriva lenta: média perto de 0 e desvio < 3 °C."""
        c = gerar(P(dias=14))
        g = c.gabarito
        d = c.dados
        conhecida = (g["intercepto"] + g["uso"] * d["uso"] + g["tomada"] * d["tomada"]
                     + g["hora_sen"] * np.sin(2 * np.pi * d["hora"] / 24) + g["hora_cos"] * np.cos(2 * np.pi * d["hora"] / 24))
        resto = d["temperatura"] - conhecida
        self.assertLess(abs(float(resto.mean())), 0.6)      # a deriva lenta (σ 1,5 °C, ~3 h) deixa a média flutuar
        self.assertLess(float(resto.std()), 3.0)

    def test_correlacao_uso_freq_segue_o_parametro(self):
        for rho in (0.0, 0.6, 0.9):
            d = gerar(P(correlacao_uso_freq=rho)).dados
            self.assertAlmostEqual(float(np.corrcoef(d["uso"], d["freq"])[0, 1]), rho, delta=0.08, msg=str(rho))

    def test_ventoinha_e_consequencia_da_temperatura(self):
        d = gerar(P()).dados
        self.assertGreater(float(np.corrcoef(d["ventoinha"], d["temperatura"])[0, 1]), 0.95)

    def test_poeira_sobe_a_temperatura_ao_longo_dos_dias(self):
        limpo, sujo = gerar(P(dias=20)), gerar(P(dias=20, poeira_por_dia=0.3))
        dif = sujo.dados["temperatura"] - limpo.dados["temperatura"]
        dia = np.repeat(np.arange(20), MIN_POR_DIA)
        self.assertAlmostEqual(float(dif[dia == 19].mean()), 0.3 * 19, delta=0.01)   # mesma semente: só a poeira difere
        self.assertAlmostEqual(float(dif[dia == 0].mean()), 0.0, delta=0.01)


class TestEpisodios(unittest.TestCase):
    def test_episodios_so_no_periodo_de_prova_e_dentro_do_dia(self):
        c = gerar(P(dias=21, episodios=10, episodio_min=15))
        marcados = np.flatnonzero(c.anomalia)
        self.assertEqual(len(marcados), 10 * 15)
        self.assertGreaterEqual(marcados.min(), int(c.n * 0.7))
        # cada episódio cabe num dia só
        inicios = marcados[np.r_[True, np.diff(marcados) > 1]]
        for i in inicios:
            self.assertEqual(i // MIN_POR_DIA, (i + 14) // MIN_POR_DIA)

    def test_episodio_eleva_a_temperatura_exatamente_pelo_valor_pedido(self):
        """As posições são sorteadas depois da temperatura: a diferença para o conjunto sem episódios é exata."""
        sem, com = gerar(P(dias=21)), gerar(P(dias=21, episodios=5, episodio_c=12.0))
        dif = com.dados["temperatura"] - sem.dados["temperatura"]
        self.assertTrue(np.allclose(dif[com.anomalia], 12.0))
        self.assertTrue(np.allclose(dif[~com.anomalia], 0.0))

    def test_sem_episodios_nenhum_minuto_marcado(self):
        self.assertFalse(gerar(P()).anomalia.any())

    def test_pedido_que_nao_cabe_gera_aviso(self):
        c = gerar(P(dias=3, episodios=30, episodio_min=60))
        self.assertTrue(c.avisos)
        self.assertLess(int(c.anomalia.sum()) // 60, 30)


if __name__ == "__main__":
    unittest.main()
