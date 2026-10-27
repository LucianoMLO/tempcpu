"""Testes de interface da Lição 2 (anomalia): treinam de verdade, com dados sintéticos de 21 dias."""
import sys
import tkinter as tk
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _base  # noqa: E402,F401

import numpy as np  # noqa: E402

from lab import textos as T  # noqa: E402
from lab.dados import Conjunto  # noqa: E402
from lab.sintetico import ParametrosSinteticos as P, gerar  # noqa: E402
from test_ui import BaseUI, achar_atributo, todos_os_textos  # noqa: E402

NL = chr(10)


def texto(w) -> str:
    return NL.join(todos_os_textos(w))


class TestLicao2(BaseUI):
    def abrir(self, lab=None):
        lab = lab or self.novo_lab()
        lab.abrir_licao(2)
        self.raiz.update()
        return lab, lab.atual

    def ir_ate(self, lic, passo, atributo):
        lic.mostrar(passo)
        self.assertTrue(self.esperar(lambda: achar_atributo(lic.area, atributo) is not None, 120), f"passo {passo + 1} não terminou")
        return achar_atributo(lic.area, atributo)

    def real_curto(self, lab, dias=10):
        """Um 'histórico real' com poucos dias (acima do mínimo da lição, abaixo das 3 semanas da tendência)."""
        c = gerar(P(dias=dias))
        lab.estado.definir_real(Conjunto("real", c.ts.copy(), {k: v.copy() for k, v in c.dados.items()}), None)
        lab.estado.trocar_fonte("real")

    # ---------- passos ----------
    def test_inicio_oferece_a_licao_2(self):
        lab = self.novo_lab()
        self.assertIn(T.LICOES[2][0], texto(lab.atual))

    def test_passo1_explica_a_ideia_e_diz_o_que_ha_de_escondido(self):
        lab, lic = self.abrir()
        t = texto(lic.area)
        self.assertIn("Depende do que o computador está fazendo", t)
        self.assertIn("21 dias", t)
        self.assertIn("0,2 °C por dia", t)
        self.assertIn("10 episódios", t)
        self.assertGreater(len(lic.area.winfo_children()), 3)

    def test_passo2_treina_o_normal_e_mostra_o_erro_tipico(self):
        lab, lic = self.abrir()
        corpo = self.ir_ate(lic, 1, "erro_tipico")
        self.assertTrue(1.0 < corpo.erro_tipico < 5.0, corpo.erro_tipico)
        t = texto(lic.area)
        self.assertIn("não entra", t)                       # a ventoinha fica de fora
        self.assertIn("nunca viu", t)
        self.assertIn("5 blocos de tempo", t)

    def test_passo3_dia_com_episodio_abre_marcado_e_todos_os_dias_desenham(self):
        lab, lic = self.abrir()
        corpo = self.ir_ate(lic, 2, "combo_dia")
        self.assertIn("marcou", corpo.resumo_dia.get("1.0", "end"))         # abre num dia com episódio
        for i, dia in enumerate(corpo.dias):
            corpo.combo_dia.current(i)
            corpo.mudou_dia()
            self.raiz.update()
        self.assertGreaterEqual(len(corpo.dias), 5)

    def test_passo4_sensibilidade_troca_alarme_perdido_por_falso_alarme(self):
        lab, lic = self.abrir()
        corpo = self.ir_ate(lic, 3, "escala")
        achou, n, falsos, eps = corpo.metricas
        self.assertEqual(n, 10)
        self.assertGreaterEqual(achou / n, 0.8)                             # A7 na sensibilidade padrão
        self.assertLessEqual(falsos, 3.0)
        self.assertIn("Ponto de equilíbrio", texto(corpo))
        corpo.escala.set(50)                                                # limite alto: deixa passar
        self.raiz.update()
        achou_alto, _, _, _ = corpo.metricas
        self.assertLess(achou_alto, achou)
        self.assertIn("alarme perdido", texto(corpo))
        corpo.escala.set(15)                                                # limite baixo: acha tudo, mais minutos
        self.raiz.update()
        achou_baixo, _, falsos_baixo, eps_baixo = corpo.metricas
        self.assertGreaterEqual(achou_baixo, achou)
        self.assertGreaterEqual(falsos_baixo, falsos)
        self.assertIn("Sensibilidade: limite = 1,5×", texto(corpo))

    def test_passo5_tendencia_semanal_com_poeira(self):
        lab, lic = self.abrir()
        corpo = self.ir_ate(lic, 4, "inclinacao")
        self.assertTrue(1.0 <= corpo.inclinacao <= 1.9, corpo.inclinacao)
        t = texto(lic.area)
        self.assertIn("por semana", t)
        self.assertIn("esquentando mais", t)
        self.assertIn("não um diagnóstico", t)

    def test_passo5_historico_real_curto_explica_e_oferece_poeira_simulada(self):
        lab = self.novo_lab()
        self.real_curto(lab)
        lab, lic = self.abrir(lab)
        self.assertIn("não existe gabarito", texto(lic.area))
        corpo = self.ir_ate(lic, 3, "escala")
        self.assertIn("Olhe cada um no gráfico", texto(corpo))                # sem gabarito no real
        self.assertIsNone(corpo.metricas[0])
        corpo5 = self.ir_ate(lic, 4, "sem_tendencia")
        self.assertIn("pelo menos 3 semanas", texto(lic.area))
        botao = next(b for b in _botoes(lic.area) if b.cget("text") == T.L2_P5_BOTAO_POEIRA)
        botao.invoke()
        self.raiz.update()
        self.assertEqual(lab.estado.fonte, "sintetico")
        self.assertTrue(lab.faixa_visivel)
        self.assertIn("21 dias", texto(lab.atual.area))                       # lição reaberta com os dados sintéticos

    def test_passo6_perguntas_e_conclusao(self):
        lab, lic = self.abrir()
        lic.mostrar(5)
        self.raiz.update()
        quiz = achar_atributo(lic.area, "quiz").quiz
        self.assertEqual(len(quiz.perguntas), 3)
        for i, q in enumerate(quiz.perguntas):
            quiz.vars[i].set(q["correta"])
            quiz.responder(i)
        self.assertEqual(quiz.placar.cget("text"), "Você acertou 3 de 3.")
        self.assertEqual(lab.estado.progresso.acertos(2), (3, 3))
        lic.ir(1)
        self.raiz.update()
        self.assertTrue(lab.estado.progresso.concluida(2))
        self.assertFalse(lab.estado.progresso.concluida(1))
        self.assertIn(T.LICAO_CONCLUIDA, texto(lab.atual))

    def test_poucos_dados_reais_para_a_licao_2_oferecem_sintetico(self):
        lab = self.novo_lab()
        self.real_curto(lab, dias=4)                                          # 3.600 minutos: serve à lição 1, não à 2
        lab.abrir_licao(2)
        self.raiz.update()
        t = texto(lab.atual)
        self.assertIn("pelo menos 7 dias", t)
        self.assertIn(T.BOTAO_USAR_SINTETICOS, t)

    def test_resultado_em_cache_e_o_mesmo_nos_passos_2_a_5(self):
        lab, lic = self.abrir()
        self.ir_ate(lic, 1, "erro_tipico")
        chaves = [k for k in lab.estado.cache if k[0] == "anomalia"]
        self.assertEqual(len(chaves), 1)
        lic.mostrar(3)
        self.raiz.update()
        self.assertIsNotNone(achar_atributo(lic.area, "escala"))              # sem retreinar
        self.assertEqual(len([k for k in lab.estado.cache if k[0] == "anomalia"]), 1)


def _botoes(w):
    if isinstance(w, tk.Button):
        yield w
    for f in w.winfo_children():
        yield from _botoes(f)


class TestDadosDaLicao2(unittest.TestCase):
    def test_estado_usa_21_dias_poeira_e_episodios_na_licao_2(self):
        from lab.estado import Estado
        from lab.progresso import Progresso
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            est = Estado(Progresso(Path(d) / "p.json"))
            p1, p2 = est.params_licao(None), est.params_licao(2)
            self.assertEqual((p1.dias, p1.episodios, p1.poeira_por_dia), (14, 0, 0.0))
            self.assertEqual((p2.dias, p2.episodios, p2.poeira_por_dia), (21, 10, 0.2))
            self.assertNotEqual(est.chave_dados(None), est.chave_dados(2))         # padrões diferentes: caches separados
            self.assertTrue(est.conjunto(2).anomalia.sum() > 0)
            est.params = P(dias=28, episodios=5, poeira_por_dia=0.1)               # escolhido na lição 3: é respeitado
            p3 = est.params_licao(2)
            self.assertEqual((p3.dias, p3.episodios, p3.poeira_por_dia), (28, 5, 0.1))
            self.assertEqual(est.chave_dados(None), est.chave_dados(2))            # agora os dois usam os mesmos dados


if __name__ == "__main__":
    unittest.main()
