"""Núcleo das lições novas (v1.2): validação cruzada, boosting, Isolation Forest, Ridge e Lasso, classificação, agrupamento e PCA.
Limiares calibrados com o gerador (várias sementes); os números medidos estão em docs/SPEC-licoes-novas.md."""
import sys
import unittest
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _base  # noqa: E402,F401

import numpy as np  # noqa: E402

from lab import modelos as M  # noqa: E402
from lab import modelos2 as M2  # noqa: E402
from lab.dados import Conjunto  # noqa: E402
from lab.sintetico import ParametrosSinteticos as P, gerar  # noqa: E402


class TestGeradorComRegimes(unittest.TestCase):
    def test_regime_por_minuto_e_so_no_sintetico(self):
        c = gerar(P(dias=7))
        self.assertEqual(len(c.regime), c.n)
        self.assertEqual(set(np.unique(c.regime)), {0, 1, 2})
        self.assertGreater(c.dados["uso"][c.regime == 2].mean(), c.dados["uso"][c.regime == 1].mean() + 20)
        self.assertGreater(c.dados["uso"][c.regime == 1].mean(), c.dados["uso"][c.regime == 0].mean() + 10)
        ts = np.arange(10, dtype=np.int64)
        self.assertIsNone(Conjunto("real", ts, {}).regime)

    def test_amostra_mantem_o_regime(self):
        c = M.amostra_de(gerar(P(dias=7)), 300, 1)
        self.assertEqual(len(c.regime), 300)


class TestValidacaoCruzada(unittest.TestCase):
    def test_escolhe_sem_o_teste_e_chega_perto_do_que_o_teste_escolheria(self):
        for s in (1, 2, 3):
            r = M2.validacao_cruzada(gerar(P(semente=s)), semente=s)
            self.assertEqual(r.profundidades, list(range(1, 21)))
            self.assertTrue(5 <= r.escolhida <= 12, (s, r.escolhida))
            self.assertLessEqual(r.erro_teste_escolhida - min(r.erro_teste), 0.1, s)
            self.assertEqual(r.erro_teste_escolhida, r.erro_teste[r.escolhida - 1])
            self.assertTrue(all(d >= 0 for d in r.desvio_validacao))
            self.assertEqual(r.escolhida, r.profundidades[int(np.argmin(r.erro_validacao))])

    def test_e_reprodutivel_e_pede_dados(self):
        c = gerar(P())
        a, b = M2.validacao_cruzada(c, semente=7), M2.validacao_cruzada(c, semente=7)
        self.assertEqual(a.erro_validacao, b.erro_validacao)
        with self.assertRaises(ValueError):
            M2.validacao_cruzada(M.amostra_de(c, 50, 1))

    def test_cancelar(self):
        with self.assertRaises(M.Cancelado):
            M2.validacao_cruzada(gerar(P()), cancelar=lambda: True)


class TestBoosting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rs = [M2.curva_boosting(gerar(P(semente=s)), semente=s) for s in (1, 2, 3)]

    def test_erro_de_treino_so_cai_e_o_de_teste_cai_rapido_no_comeco(self):
        for r in self.rs:
            self.assertEqual(len(r.rodadas), M2.RODADAS_BOOSTING)
            self.assertTrue(all(r.erro_treino[i + 1] <= r.erro_treino[i] + 1e-9 for i in range(len(r.erro_treino) - 1)))
            self.assertGreater(r.erro_teste[0], 2 * min(r.erro_teste))
            self.assertGreaterEqual(r.melhor_rodada, 20)

    def test_ganha_da_melhor_arvore_e_fica_perto_do_linear_num_mundo_linear(self):
        for r in self.rs:
            self.assertLess(min(r.erro_teste), r.erro_arvore)
            self.assertLessEqual(min(r.erro_teste), r.erro_linear * 1.10)
            self.assertLess(min(r.erro_teste), r.erro_floresta * 1.05)

    def test_sem_sobreajuste_forte_em_200_rodadas(self):
        for r in self.rs:
            self.assertLessEqual(r.erro_teste[-1], min(r.erro_teste) * 1.05)


class TestIsolamento(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.casos = []
        for s in (1, 2, 3):
            c = gerar(P(dias=21, episodios=10, poeira_por_dia=0.2, semente=s))
            res = M.treinar_anomalia(c, semente=s)
            cls.casos.append((res, M2.treinar_isolamento(c, res, semente=s)))

    def test_o_residuo_acha_quase_tudo_e_o_isolation_forest_acha_pouco(self):
        for res, iso in self.casos:
            d = M2.comparar_deteccao(res, iso, 5)
            self.assertGreaterEqual(d["res_recall"], 0.9)
            self.assertLessEqual(d["res_falsos"], 3.0)
            self.assertLess(d["iso_recall"], 0.6)
            self.assertLess(d["iso_recall"], d["res_recall"])
            self.assertEqual(d["n_reais"], 10)

    def test_mais_estranhos_marca_mais_minutos(self):
        for res, iso in self.casos:
            total = [int(M2.marcar_isolamento(iso, p)[0].sum()) for p in (1, 3, 5, 10, 15)]
            self.assertEqual(total, sorted(total))
            self.assertGreater(total[-1], total[0])

    def test_so_marca_episodios_com_o_minimo_de_minutos_seguidos(self):
        res, iso = self.casos[0]
        _, eps = M2.marcar_isolamento(iso, 10)
        self.assertTrue(all(b - a >= M.MINIMO_EPISODIO_MIN for a, b in eps))

    def test_resultado_de_outros_dados_e_recusado(self):
        res, iso = self.casos[0]
        outro = gerar(P(dias=14))
        with self.assertRaises(ValueError):
            M2.treinar_isolamento(outro, res)

    def test_sem_gabarito_no_real_nao_ha_recall(self):
        res, iso = self.casos[0]
        sem = M.ResultadoAnomalia(**{**res.__dict__, "verdade": None})
        d = M2.comparar_deteccao(sem, iso, 5)
        self.assertNotIn("iso_recall", d)
        self.assertIn("iso_episodios", d)


class TestRegularizacao(unittest.TestCase):
    def amostras(self, n, sementes=range(1, 9)):
        for s in sementes:
            yield M.amostra_de(gerar(P(correlacao_uso_freq=0.95, semente=s)), n, s), s

    def test_forca_zero_e_o_modelo_linear_e_forca_enorme_zera_tudo_no_lasso(self):
        c, s = next(self.amostras(150))
        r = M2.regularizacao(c, semente=s)
        for nome, v in r.linear.items():
            if nome != "intercepto":
                self.assertAlmostEqual(r.lasso[0][nome], v, places=6)
                self.assertAlmostEqual(r.ridge[0][nome], v, places=3)
        self.assertEqual(len(r.zerados_lasso[-1]), 6)                      # com λ = 10 nenhuma entrada sobrevive
        self.assertEqual(r.zerados_lasso[0], [])

    def test_ridge_encolhe_os_coeficientes_e_regularizar_demais_piora_a_previsao(self):
        c, s = next(self.amostras(150))
        r = M2.regularizacao(c, semente=s)
        uso = [abs(x["uso"]) for x in r.ridge]
        self.assertTrue(all(uso[i + 1] <= uso[i] + 1e-9 for i in range(len(uso) - 1)))
        for modelo in ("ridge", "lasso"):
            self.assertGreater(r.mae_teste[modelo][-1], 2 * r.mae_teste["linear"][0], modelo)

    def test_lasso_chega_mais_perto_do_gabarito_do_uso_que_o_linear_com_300_minutos(self):
        ols, las = [], []
        for c, s in self.amostras(300):
            r = M2.regularizacao(c, semente=s)
            g = c.gabarito["uso"]
            ols.append(abs(r.linear["uso"] - g) / g)
            las.append(abs(r.lasso[M2.FORCAS.index(0.1)]["uso"] - g) / g)
        self.assertLess(np.mean(las), np.mean(ols))

    def test_o_ridge_nao_melhora_o_coeficiente_do_uso_aqui(self):
        """Resultado medido (spec C5 revisto): com entradas quase iguais o ridge reparte o mérito e subestima o uso."""
        ols, rid = [], []
        for c, s in self.amostras(150):
            r = M2.regularizacao(c, semente=s)
            g = c.gabarito["uso"]
            ols.append(abs(r.linear["uso"] - g) / g)
            rid.append(abs(r.ridge[M2.FORCAS.index(0.1)]["uso"] - g) / g)
        self.assertGreater(np.mean(rid), np.mean(ols))


class TestClassificacao(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.casos = []
        for s in (1, 2, 3):
            c = gerar(P(dias=21, semente=s))
            cls.casos.append((c, M2.classificar(c, M2.limite_padrao(c), semente=s)))

    def test_limite_padrao_deixa_uns_10_por_cento_acima(self):
        for c, r in self.casos:
            self.assertTrue(0.06 <= r.taxa_quente_treino <= 0.14, r.taxa_quente_treino)

    def test_o_palpite_preguicoso_tem_acuracia_alta_e_nao_acha_nada_e_o_modelo_acha(self):
        for c, r in self.casos:
            self.assertGreater(r.sempre_normal_acuracia, 0.85)
            self.assertAlmostEqual(r.sempre_normal_acuracia, 1 - r.verdade.mean(), places=9)
            for nome, m in r.modelos.items():
                self.assertGreater(m["acuracia"], r.sempre_normal_acuracia, nome)
                self.assertGreater(m["revocacao"], 0.7, nome)
                self.assertGreater(m["precisao"], 0.7, nome)

    def test_a_matriz_de_confusao_soma_o_teste(self):
        for c, r in self.casos:
            for nome, m in r.modelos.items():
                (vn, fp), (fn, vp) = m["matriz"]
                self.assertEqual(vn + fp + fn + vp, r.n_teste, nome)
                self.assertEqual(vp + fn, int(r.verdade.sum()), nome)

    def test_limite_de_decisao_maior_avisa_menos_e_acha_menos(self):
        for c, r in self.casos:
            v = M2.varrer_limiar(r.probabilidade, r.verdade, [0.1, 0.3, 0.5, 0.7, 0.9])
            alarmes = [x["alarmes"] for x in v]
            revoc = [x["revocacao"] for x in v]
            self.assertEqual(alarmes, sorted(alarmes, reverse=True))
            self.assertTrue(all(revoc[i + 1] <= revoc[i] + 1e-12 for i in range(len(revoc) - 1)))
            self.assertGreater(v[-1]["precisao"], v[0]["precisao"])          # mais certeza, avisos mais certos

    def test_limite_alto_demais_explica_em_vez_de_quebrar(self):
        c, _ = self.casos[0]
        with self.assertRaisesRegex(ValueError, "poucos minutos quentes"):
            M2.classificar(c, 200.0)

    def test_k_vizinhos_muda_o_resultado_do_k_vizinhos_so(self):
        c, r = self.casos[0]
        r1 = M2.classificar(c, r.limite_c, k_vizinhos=1)
        self.assertEqual(r1.modelos["logistica"]["matriz"], r.modelos["logistica"]["matriz"])
        self.assertNotEqual(r1.modelos["vizinhos"]["matriz"], r.modelos["vizinhos"]["matriz"])


class TestAgrupamento(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = gerar(P(dias=21, semente=1))
        cls.v = M2.varrer_k(cls.c, semente=1)

    def test_formato_e_tamanhos(self):
        r = M2.agrupar(self.c, 3, 1)
        self.assertEqual((r.k, r.centros.shape, len(r.rotulos)), (3, (3, 3), len(r.indices)))
        self.assertEqual(sum(r.tamanhos), len(r.indices))
        self.assertEqual(sorted(r.ordem_uso), [0, 1, 2])
        usos = [r.centros[g, 0] for g in r.ordem_uso]
        self.assertEqual(usos, sorted(usos))

    def test_a_inercia_sempre_cai_e_a_silhueta_prefere_dois_grupos(self):
        self.assertTrue(all(self.v["inercia"][i + 1] < self.v["inercia"][i] for i in range(len(self.v["inercia"]) - 1)))
        self.assertEqual(int(self.v["k"][int(np.argmax(self.v["silhueta"]))]), 2)        # mas os regimes verdadeiros são 3

    def test_pureza_sobe_de_2_para_4_grupos_e_com_3_fica_acima_de_65_por_cento(self):
        i = lambda k: int(k) - 2
        self.assertGreater(self.v["pureza"][i(4)], self.v["pureza"][i(2)])
        self.assertGreaterEqual(self.v["pureza"][i(3)], 0.65)

    def test_mais_ruido_piora_a_pureza(self):
        baixo = M2.agrupar(gerar(P(dias=21, ruido_c=2.0, semente=1)), 4, 1).pureza
        alto = M2.agrupar(gerar(P(dias=21, ruido_c=6.0, semente=1)), 4, 1).pureza
        self.assertLess(alto, baixo)

    def test_no_real_nao_ha_pureza(self):
        c = gerar(P(dias=7))
        real = Conjunto("real", c.ts, c.dados)
        self.assertIsNone(M2.agrupar(real, 3, 1).pureza)


class TestComponentes(unittest.TestCase):
    def test_variancia_decrescente_e_uso_frequencia_e_temperatura_com_o_mesmo_sinal(self):
        p = M2.componentes(gerar(P(dias=21, semente=1)))
        self.assertTrue(all(p.variancia[i] >= p.variancia[i + 1] for i in range(len(p.variancia) - 1)))
        self.assertAlmostEqual(sum(p.variancia), 1.0, places=6)
        c1 = p.cargas[0] * (1 if p.cargas[0].sum() >= 0 else -1)
        for v in ("uso", "freq", "temperatura"):
            self.assertGreater(c1[p.variaveis.index(v)], 0.3, v)
        self.assertEqual(p.projecao.shape[1], 2)
        self.assertEqual(len(p.rotulos_amostra), len(p.projecao))


if __name__ == "__main__":
    unittest.main()
