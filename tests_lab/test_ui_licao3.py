"""Testes de interface da Lição 3 (dados sintéticos com gabarito)."""
import sys
import tkinter as tk
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _base  # noqa: E402,F401

import numpy as np  # noqa: E402

from lab import modelos as M  # noqa: E402
from lab import textos as T  # noqa: E402
from lab.dados import Conjunto  # noqa: E402
from lab.sintetico import ParametrosSinteticos as P, gerar  # noqa: E402
from test_ui import BaseUI, achar_atributo, todos_os_textos  # noqa: E402

NL = chr(10)


def texto(w) -> str:
    return NL.join(todos_os_textos(w))


class TestLicao3(BaseUI):
    def abrir(self, lab=None):
        lab = lab or self.novo_lab()
        lab.abrir_licao(3)
        self.raiz.update()
        return lab, lab.atual

    def ir_ate(self, lic, passo, atributo, limite=120):
        lic.mostrar(passo)
        self.assertTrue(self.esperar(lambda: achar_atributo(lic.area, atributo) is not None, limite), f"passo {passo + 1} não terminou")
        return achar_atributo(lic.area, atributo)

    def test_todas_as_licoes_estao_prontas_no_inicio(self):
        lab = self.novo_lab()
        self.assertEqual(texto(lab.atual).count(T.LICAO_EM_BREVE), 0)

    def test_faixa_de_dados_de_mentira_fica_mesmo_com_fonte_real_e_some_ao_sair(self):
        lab = self.novo_lab()
        c = gerar(P(dias=10))
        lab.estado.definir_real(Conjunto("real", c.ts.copy(), {k: v.copy() for k, v in c.dados.items()}), None)
        lab.estado.trocar_fonte("real")
        lab.atualizar_faixa()
        self.assertFalse(lab.faixa_visivel)
        lab.abrir_licao(3)
        self.raiz.update()
        self.assertTrue(lab.faixa_visivel)                       # a lição 3 só usa dados sintéticos
        lab.mostrar_inicio()
        self.raiz.update()
        self.assertFalse(lab.faixa_visivel)
        self.assertEqual(lab.estado.fonte, "real")               # a escolha do aprendiz não foi alterada

    def test_passo1_controles_mudam_os_dados_e_o_gabarito(self):
        lab, lic = self.abrir()
        area = achar_atributo(lic.area, "escalas")
        self.assertEqual(set(area.escalas), {"dias", "ruido_c", "efeito_uso", "efeito_tomada", "poeira_por_dia", "correlacao_uso_freq", "episodios"})
        self.assertIn("0,35", area.gabarito_txt.get("1.0", "end"))
        area.escalas["efeito_uso"].set(40)                       # 0,10 + 40 × 0,01 = 0,50
        area.escalas["ruido_c"].set(55)                          # 0,5 + 55 × 0,1 = 6,0
        self.esperar(lambda: "0,50" in area.gabarito_txt.get("1.0", "end"), 5)
        g = area.gabarito_txt.get("1.0", "end")
        self.assertIn("0,50", g)
        self.assertIn("6,0 °C", g)
        self.assertEqual(lab.estado.params.efeito_uso, 0.5)
        self.assertEqual(lab.estado.params.ruido_c, 6.0)
        self.assertEqual(lab.estado.sintetico().gabarito["uso"], 0.5)
        area.padrao()
        self.esperar(lambda: "0,35" in area.gabarito_txt.get("1.0", "end"), 5)
        self.assertEqual(lab.estado.params, P())

    def test_novo_sorteio_troca_a_semente_e_gera_outros_dados(self):
        lab, lic = self.abrir()
        area = achar_atributo(lic.area, "novo_sorteio")
        antes = lab.estado.sintetico().dados["temperatura"].copy()
        semente = lab.estado.params.semente
        area.novo_sorteio()
        self.raiz.update()
        self.assertNotEqual(lab.estado.params.semente, semente)
        self.assertFalse(np.array_equal(antes, lab.estado.sintetico().dados["temperatura"]))

    def test_passo2_tabela_compara_verdade_e_descoberta(self):
        lab, lic = self.abrir()
        lic.mostrar(1)
        self.raiz.update()
        area = achar_atributo(lic.area, "tabela")
        linhas = area.tabela
        self.assertEqual(set(linhas), set(T.L3_TAB_LINHAS))
        self.assertLessEqual(linhas["uso"]["erro_pct"], 5)
        self.assertLessEqual(linhas["tomada"]["erro_pct"], 15)
        self.assertTrue(area.perto)
        t = texto(lic.area)
        self.assertIn("erro médio foi de", t)
        self.assertIn("Temperatura base", t)
        self.assertIn("Verdade", t)
        self.assertIn("perto do gabarito", t)

    def test_passo3_cada_estrago_tem_o_efeito_que_o_texto_afirma(self):
        lab, lic = self.abrir()
        corpo = self.ir_ate(lic, 2, "cenarios")
        padrao, ruido, poucos, colinear = corpo.cenarios
        self.assertGreater(ruido["mae"], 1.8 * padrao["mae"])                 # ruído: erro de previsão sobe
        self.assertLess(ruido["erro_uso_pct"], 3.0)                           # …mas com muitos dados o coeficiente ainda é achado
        self.assertGreater(poucos["erro_uso_pct"], 4 * padrao["erro_uso_pct"])  # poucos dados: coeficiente piora
        self.assertGreater(colinear["erro_uso_pct"], 1.5 * poucos["erro_uso_pct"])   # colinearidade piora ainda mais
        self.assertGreater(colinear["freq_efeito"], 2 * poucos["freq_efeito"])      # a frequência "esquenta" sem esquentar
        self.assertLess(abs(colinear["mae"] - poucos["mae"]) / poucos["mae"], 0.1)  # mas a previsão continua igual
        t = texto(lic.area)
        self.assertIn("Entradas que andam juntas", t)
        self.assertIn("praticamente não mudou", t)
        self.assertIn("Padrão (14 dias)", t)

    def test_passo4_poeira_escondida_e_achada_pelos_dois_modelos(self):
        lab, lic = self.abrir()
        lic.mostrar(3)
        self.raiz.update()
        area = achar_atributo(lic.area, "treinar_poeira")
        area.escala_poeira.set(20)
        area.treinar_poeira()
        self.assertTrue(self.esperar(lambda: hasattr(area.resultado_poeira, "medidas"), 120))
        verdade, achada, dia = area.resultado_poeira.medidas
        self.assertAlmostEqual(verdade, 1.4, places=6)
        self.assertTrue(1.0 <= achada <= 2.0, achada)
        self.assertGreater(dia, 0.05)                                        # o modelo linear com a coluna "dia" também enxerga a poeira
        self.assertLess(dia, 0.4)                                            # (a incerteza é de ~0,1 °C/dia: o acaso mexe nos números)
        self.assertIn("por semana", texto(lic.area))

    def test_passo5_leva_as_lições_1_e_2_com_os_dados_escolhidos(self):
        lab, lic = self.abrir()
        achar_atributo(lic.area, "escalas").escalas["ruido_c"].set(30)       # 3,5 °C
        lic.mostrar(4)
        self.raiz.update()
        area = achar_atributo(lic.area, "abrir")
        area.abrir(1)
        self.raiz.update()
        self.assertEqual(lab.atual.numero, 1)
        self.assertEqual(lab.estado.params.ruido_c, 3.5)
        self.assertEqual(lab.estado.fonte, "sintetico")

    def test_passo6_perguntas_e_conclusao(self):
        lab, lic = self.abrir()
        lic.mostrar(5)
        self.raiz.update()
        quiz = achar_atributo(lic.area, "quiz").quiz
        for i, q in enumerate(quiz.perguntas):
            quiz.vars[i].set(q["correta"])
            quiz.responder(i)
        self.assertEqual(lab.estado.progresso.acertos(3), (3, 3))
        lic.ir(1)
        self.raiz.update()
        self.assertTrue(lab.estado.progresso.concluida(3))
        self.assertIn(T.LICAO_CONCLUIDA, texto(lab.atual))


class TestDescoberta(unittest.TestCase):
    def test_avaliar_descoberta_e_deterministico_e_aceita_poucos_minutos(self):
        a = M.avaliar_descoberta(P(), range(1, 4), 60)
        b = M.avaliar_descoberta(P(), range(1, 4), 60)
        self.assertEqual(a, b)
        self.assertGreater(a["erro_uso_pct"], 0)

    def test_amostra_mantem_a_ordem_do_tempo_e_o_gabarito(self):
        c = gerar(P())
        s = M.amostra_de(c, 100, 3)
        self.assertEqual(s.n, 100)
        self.assertTrue(np.all(np.diff(s.ts) > 0))
        self.assertEqual(s.gabarito, c.gabarito)


if __name__ == "__main__":
    unittest.main()
