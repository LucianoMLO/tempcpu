import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _base  # noqa: E402,F401

import numpy as np  # noqa: E402

from lab import modelos as M  # noqa: E402
from lab.dados import VARIAVEIS, Conjunto  # noqa: E402
from lab.sintetico import ParametrosSinteticos as P, gerar  # noqa: E402


class TestLicao1(unittest.TestCase):
    """Critérios A1–A4 (calibrados na fase 2: com os parâmetros padrão e semente 7 a profundidade ótima é 9)."""

    @classmethod
    def setUpClass(cls):
        cls.c = gerar(P())
        cls.r = M.curva_profundidade(cls.c)

    def test_a1_treino_so_melhora_e_teste_tem_formato_de_u(self):
        r = self.r
        self.assertEqual(r.profundidades, list(range(1, 21)))
        self.assertTrue(all(r.mae_treino[i + 1] <= r.mae_treino[i] + 1e-9 for i in range(19)))
        self.assertTrue(5 <= r.melhor_profundidade <= 12, r.melhor_profundidade)
        self.assertGreaterEqual(r.mae_teste[-1], 1.15 * min(r.mae_teste))     # sobreajuste visível
        self.assertLess(r.mae_treino[-1], 0.2 * r.mae_teste[-1])              # decorou o treino

    def test_a2_o_modelo_ganha_de_chutar_a_media(self):
        r = self.r
        self.assertLess(min(r.mae_teste), 0.5 * r.mae_media)
        self.assertGreater(r.r2_teste[r.melhor_profundidade - 1], 0.85)

    def test_modelo_linear_serve_de_referencia_e_vence_num_mundo_linear(self):
        self.assertLess(self.r.mae_linear, self.r.mae_media)
        self.assertLessEqual(self.r.mae_linear, min(self.r.mae_teste) + 0.2)

    def test_a3_embaralhar_da_nota_falsamente_melhor(self):
        emb = M.curva_profundidade(self.c, divisao="embaralhado")
        self.assertLess(min(emb.mae_teste), 0.97 * min(self.r.mae_teste))
        self.assertLess(emb.mae_teste[-1], self.r.mae_teste[-1])

    def test_a4_ventoinha_infla_a_nota_porque_e_consequencia(self):
        com = M.curva_profundidade(self.c, entradas=["uso", "freq", "tomada", "hora", "ventoinha"])
        sem_r2 = self.r.r2_teste[self.r.melhor_profundidade - 1]
        com_r2 = com.r2_teste[com.melhor_profundidade - 1]
        self.assertGreater(com_r2, sem_r2 + 0.04)
        self.assertLess(min(com.mae_teste), 0.7 * min(self.r.mae_teste))

    def test_importancia_o_uso_domina_e_a_frequencia_nao_conta(self):
        imp = M.importancia(self.c, self.r.entradas, self.r.melhor_profundidade)
        self.assertEqual(max(imp, key=imp.get), "uso")
        self.assertGreater(imp["uso"], 3 * imp["tomada"])
        self.assertLess(imp["freq"], 0.3)     # a frequência só anda junto com o uso: efeito verdadeiro zero

    def test_previsto_x_real_no_periodo_de_teste(self):
        ts, real, prev = M.previsto_x_real(self.c, self.r.entradas, 5)
        self.assertEqual(len(ts), self.r.n_teste)
        self.assertEqual((len(real), len(prev)), (len(ts), len(ts)))
        self.assertTrue(np.all(np.diff(ts) > 0))
        self.assertGreaterEqual(int(ts[0]), int(self.c.ts[int(self.c.n * 0.7) - 1]))   # a prova é sempre no futuro

    def test_progresso_e_cancelamento(self):
        passos = []
        M.curva_profundidade(self.c, profundidade_max=3, progresso=lambda f, t: passos.append((f, t)))
        self.assertGreaterEqual(len(passos), 4)
        self.assertTrue(all(0 <= f <= 1 for f, _ in passos))
        with self.assertRaises(M.Cancelado):
            M.curva_profundidade(self.c, cancelar=lambda: True)

    def test_poucos_dados_dao_erro_claro(self):
        pequeno = Conjunto("sintetico", np.arange(50, dtype=np.int64), {k: np.zeros(50) for k in VARIAVEIS})
        with self.assertRaises(ValueError) as e:
            M.curva_profundidade(pequeno)
        self.assertIn("Poucos dados", str(e.exception))


class TestLicao3(unittest.TestCase):
    def test_a5_coeficiente_do_uso_fica_perto_do_gabarito(self):
        c = gerar(P())
        aj = M.ajustar_linear(c)
        linhas = {l["nome"]: l for l in M.comparar_gabarito(aj.coeficientes, c.gabarito)}
        self.assertLessEqual(linhas["uso"]["erro_pct"], 15.0)
        self.assertLessEqual(linhas["tomada"]["erro_pct"], 15.0)
        self.assertLess(abs(linhas["freq"]["descoberto"]), 0.01)       # a frequência não esquenta nada
        self.assertAlmostEqual(aj.correlacao_uso_freq, 0.6, delta=0.08)
        self.assertGreater(aj.r2_teste, 0.85)

    def test_ruido_alto_piora_a_descoberta_na_media_de_varias_sementes(self):
        def erro_medio(ruido):
            e = []
            for s in range(1, 9):
                c = gerar(P(ruido_c=ruido, dias=3, semente=s))
                e.append({l["nome"]: l for l in M.comparar_gabarito(M.ajustar_linear(c).coeficientes, c.gabarito)}["uso"]["erro_abs"])
            return float(np.mean(e))
        self.assertLess(erro_medio(0.5), erro_medio(6.0))

    def test_poucos_dias_pioram_a_descoberta_na_media_de_varias_sementes(self):
        def erro_medio(dias):
            e = []
            for s in range(1, 7):
                c = gerar(P(dias=dias, semente=s))
                e.append({l["nome"]: l for l in M.comparar_gabarito(M.ajustar_linear(c).coeficientes, c.gabarito)}["dia"]["erro_abs"])
            return float(np.mean(e))
        self.assertLess(erro_medio(28), erro_medio(4))

    def test_comparar_gabarito_trata_verdadeiro_zero(self):
        l = M.comparar_gabarito({"a": 0.2, "b": 2.0}, {"a": 0.0, "b": 2.5})
        self.assertIsNone(l[0]["erro_pct"])
        self.assertAlmostEqual(l[1]["erro_pct"], 20.0)


class TestLicao2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = gerar(P(dias=21, episodios=10, poeira_por_dia=0.2))
        cls.r = M.treinar_anomalia(cls.c)

    def test_formato_do_resultado(self):
        r = self.r
        n = len(r.ts)
        self.assertEqual((len(r.medido), len(r.esperado), len(r.residuo), len(r.no_treino)), (n, n, n, n))
        self.assertTrue(np.allclose(r.residuo, r.medido - r.esperado))
        self.assertAlmostEqual(float(r.no_treino.mean()), 0.7, delta=0.01)
        self.assertTrue(r.no_treino[0] and not r.no_treino[-1])
        self.assertTrue(1.0 < r.erro_tipico < 5.0, r.erro_tipico)

    def test_a6_tendencia_semanal_acompanha_a_poeira(self):
        self.assertEqual(len(self.r.semanas), 3)
        self.assertTrue(1.0 <= self.r.inclinacao <= 1.9, self.r.inclinacao)     # verdade: 0,2 × 7 = 1,4 °C/semana
        medianas = [m for _, m, _ in self.r.semanas]
        self.assertTrue(medianas[0] < medianas[1] < medianas[2])

    def test_a6_sem_poeira_nao_ha_tendencia(self):
        for s in (1, 2):
            r = M.treinar_anomalia(gerar(P(dias=21, semente=s)), semente=s)
            self.assertLess(abs(r.inclinacao), 0.6, (s, r.inclinacao))

    def test_tendencia_pede_tres_semanas(self):
        r = M.treinar_anomalia(gerar(P(dias=14)))
        self.assertIsNone(r.inclinacao)
        self.assertEqual(len(r.semanas), 2)

    def test_a7_deteccao_na_sensibilidade_padrao(self):
        """Média de 4 sementes, sem poeira: recall ≥ 80% e falsos alarmes ≤ 3% (calibrado: ~91% e ~0,04%)."""
        rec, fal = [], []
        for s in (1, 2, 3, 4):
            r = M.treinar_anomalia(gerar(P(dias=21, episodios=10, semente=s)), semente=s)
            l = M.varredura_sensibilidade(r, [M.SENSIBILIDADE_PADRAO])[0]
            rec.append(l["recall"])
            fal.append(l["falsos_alarmes"])
        self.assertGreaterEqual(float(np.mean(rec)), 0.80, rec)
        self.assertLessEqual(max(fal), 3.0, fal)

    def test_a7_com_poeira_tambem_detecta(self):
        l = M.varredura_sensibilidade(self.r, [M.SENSIBILIDADE_PADRAO])[0]
        self.assertGreaterEqual(l["recall"], 0.8)
        self.assertLessEqual(l["falsos_alarmes"], 3.0)

    def test_maior_sensibilidade_acha_mais_e_alarma_mais(self):
        l = M.varredura_sensibilidade(self.r, [1.5, 2.5, 4.0, 6.0])
        self.assertGreaterEqual(l[0]["minutos"], l[1]["minutos"])
        self.assertGreaterEqual(l[1]["minutos"], l[2]["minutos"])
        self.assertGreaterEqual(l[2]["minutos"], l[3]["minutos"])
        self.assertGreaterEqual(l[0]["falsos_alarmes"], l[3]["falsos_alarmes"])
        self.assertEqual(l[3]["minutos"], 0)

    def test_so_o_lado_quente_conta_e_minutos_isolados_sao_ruido(self):
        ts = np.arange(100) * 60
        res = np.zeros(100)
        res[10] = 50          # minuto isolado: ruído
        res[30:45] = 20       # episódio de 15 min
        res[60:70] = -20      # frio: não conta
        marcado, eps = M.detectar(ts, res, 2.0, k=2.5, janela=1)
        self.assertEqual(eps, [(30, 45)])
        self.assertTrue(marcado[30:45].all() and not marcado[10] and not marcado[60:70].any())

    def test_lacuna_de_tempo_separa_episodios(self):
        ts = np.r_[np.arange(10) * 60, 10_000 + np.arange(10) * 60]      # dois blocos de 10 minutos com um buraco
        _, eps = M.detectar(ts, np.full(20, 20.0), 2.0, k=2.5, janela=1)
        self.assertEqual(eps, [(0, 10), (10, 20)])

    def test_suavizar(self):
        x = np.r_[np.zeros(10), 10.0, np.zeros(10)]
        s = M.suavizar(x, 5)
        self.assertEqual(len(s), len(x))
        self.assertAlmostEqual(float(s[10]), 2.0)
        self.assertTrue(np.array_equal(M.suavizar(x, 1), x))

    def test_ventoinha_nao_entra_na_anomalia(self):
        with self.assertRaises(ValueError):
            M.treinar_anomalia(self.c, entradas=["uso", "ventoinha"])

    def test_cancelar_treino(self):
        with self.assertRaises(M.Cancelado):
            M.treinar_anomalia(self.c, cancelar=lambda: True)


if __name__ == "__main__":
    unittest.main()
