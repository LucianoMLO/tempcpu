"""Interface dos passos novos (lições 1 a 3) e das lições 4 e 5. Nenhuma exceção pode ficar escondida num callback."""
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


class BaseNovas(BaseUI):
    def setUp(self):
        super().setUp()
        self.erros = []
        self.raiz.report_callback_exception = lambda *a: self.erros.append(a[1])

    def tearDown(self):
        erros = self.erros
        super().tearDown()
        self.assertEqual(erros, [], "exceção escondida num callback do tkinter")

    def abrir(self, n, lab=None):
        lab = lab or self.novo_lab()
        lab.abrir_licao(n)
        self.raiz.update()
        return lab, lab.atual

    def ir_ate(self, lic, passo, atributo, limite=180):
        lic.mostrar(passo)
        self.assertTrue(self.esperar(lambda: achar_atributo(lic.area, atributo) is not None, limite), f"passo {passo + 1} não terminou")
        return achar_atributo(lic.area, atributo)


class TestPassosNovosDasLicoes(BaseNovas):
    def test_as_licoes_1_a_3_ganharam_passos_antes_do_resumo(self):
        for n, titulos in ((1, T.L1_PASSOS), (2, T.L2_PASSOS), (3, T.L3_PASSOS)):
            _, lic = self.abrir(n)
            self.assertEqual([p.titulo for p in lic.passos], titulos)
            self.assertEqual(titulos[-1], "Resumo e perguntas")
        self.assertEqual(len(T.L1_PASSOS), 8)
        self.assertEqual((len(T.L2_PASSOS), len(T.L3_PASSOS)), (7, 7))

    def test_a_trilha_de_oito_passos_quebra_em_duas_linhas_e_cabe(self):
        _, lic = self.abrir(1)
        linhas = lic.trilha.winfo_children()
        self.assertEqual(len(linhas), 2)
        self.raiz.update()
        self.assertLessEqual(max(l.winfo_reqwidth() for l in linhas), self.raiz.winfo_width())

    def test_validacao_cruzada_escolhe_sem_o_teste_e_so_depois_revela(self):
        _, lic = self.abrir(1)
        corpo = self.ir_ate(lic, 5, "revelar")
        t = texto(lic.area)
        self.assertIn("A validação cruzada escolheu a profundidade", t)
        self.assertNotIn("Abrindo o teste", t)
        corpo.revelar()
        self.raiz.update()
        t = texto(lic.area)
        self.assertIn("Abrindo o teste: com a profundidade", t)
        self.assertEqual(str(corpo.texto_revela.cget("state")), "disabled")      # TextoRico é só leitura
        r = corpo.resultado
        self.assertTrue(5 <= r.escolhida <= 12)

    def test_boosting_responde_ao_numero_de_rodadas_e_compara_com_os_outros_modelos(self):
        _, lic = self.abrir(1)
        corpo = self.ir_ate(lic, 6, "escala")
        self.assertIn("Com 10 rodadas", texto(lic.area))
        corpo.escala.definir(100)
        self.raiz.update()
        t = texto(lic.area)
        self.assertIn("Com 100 rodadas", t)
        self.assertIn("melhor árvore única", t)
        self.assertIn("floresta", t)
        self.assertIn("modelo linear", t)

    def test_isolation_forest_compara_com_o_residuo_e_mostra_o_gabarito_no_sintetico(self):
        _, lic = self.abrir(2)
        corpo = self.ir_ate(lic, 5, "escala")
        t = texto(lic.area)
        self.assertIn("Método do resíduo:", t)
        self.assertIn("Isolation Forest:", t)
        self.assertIn("episódios reais", t)
        antes = t
        corpo.escala.definir(12)
        self.esperar(lambda: "12%" in texto(lic.area), 10)
        self.raiz.update()
        self.assertIn("12%", texto(lic.area))
        self.assertNotEqual(antes, texto(lic.area))

    def test_regularizacao_mostra_ridge_lasso_e_responde_a_forca_e_aos_minutos(self):
        _, lic = self.abrir(3)
        lic.mostrar(5)
        self.raiz.update()
        area = lic.area
        self.assertIn("Força da regularização: 0,03", texto(area))
        self.assertIn("ridge", texto(area))
        self.assertIn("lasso", texto(area))
        antes = area.texto_valores.get("1.0", "end")
        area.escala_forca.definir(1.0)
        self.raiz.update()
        self.assertIn("Força da regularização: 1", texto(area))
        self.assertNotEqual(antes, area.texto_valores.get("1.0", "end"))
        area.escala_minutos.definir(300)
        self.assertTrue(self.esperar(lambda: area.estado_reg["minutos"] == 300, 10))
        self.assertIn("Minutos de dados: 300", texto(area))
        s = area.estado_reg["semente"]
        area.botao_nova()
        self.raiz.update()
        self.assertEqual(area.estado_reg["semente"], s + 1)

    def test_regularizacao_com_forca_enorme_avisa_que_regularizar_demais_piora(self):
        _, lic = self.abrir(3)
        lic.mostrar(5)
        self.raiz.update()
        lic.area.escala_forca.definir(10.0)
        self.raiz.update()
        t = texto(lic.area)
        self.assertIn("regularizar demais", t)
        self.assertIn("O lasso zerou", t)

    def test_os_quizzes_ganharam_perguntas_dos_passos_novos(self):
        self.assertEqual((len(T.L1_QUIZ), len(T.L2_QUIZ), len(T.L3_QUIZ)), (5, 4, 4))
        for n, passo in ((1, 7), (2, 6), (3, 6)):
            _, lic = self.abrir(n)
            lic.mostrar(passo)
            self.raiz.update()
            quiz = achar_atributo(lic.area, "quiz").quiz
            self.assertEqual(len(quiz.perguntas), {1: 5, 2: 4, 3: 4}[n])


class TestLicao4(BaseNovas):
    def test_inicio_oferece_cinco_licoes(self):
        lab = self.novo_lab()
        t = texto(lab.atual)
        for n in (4, 5):
            self.assertIn(T.LICOES[n][0], t)
        self.assertEqual(t.count(T.LICAO_EM_BREVE), 0)

    def test_passo1_limite_muda_o_percentual_acima(self):
        _, lic = self.abrir(4)
        self.assertEqual([p.titulo for p in lic.passos], T.L4_PASSOS)
        area = lic.area
        self.assertIn("Limite de temperatura:", texto(area))
        antes = area.texto_resumo.get("1.0", "end")
        area.escala.definir(area.escala.valores[-1])
        self.raiz.update()
        depois = area.texto_resumo.get("1.0", "end")
        self.assertNotEqual(antes, depois)
        self.assertIn("minutos", depois)

    def test_todos_os_passos_abrem_sem_erro_e_mostram_numeros_medidos(self):
        _, lic = self.abrir(4)
        lic.mostrar(1)
        self.raiz.update()
        self.assertRegex(texto(lic.area), r"Ela acertou \d+%")
        lic.mostrar(2)
        self.raiz.update()
        t = texto(lic.area)
        self.assertRegex(t, r"preguiçoso tem \d+% de acurácia e acha 0% do calor")
        lic.mostrar(3)
        self.raiz.update()
        t = texto(lic.area)
        for rotulo in T.L4_P4_CELULAS:
            self.assertIn(rotulo, t)
        self.assertRegex(t, r"Dos [\d.]+ minutos quentes, o modelo avisou")

    def test_limite_de_decisao_troca_precisao_por_revocacao(self):
        _, lic = self.abrir(4)
        lic.mostrar(4)
        self.raiz.update()
        area = lic.area
        area.escala.definir(0.1)
        self.raiz.update()
        baixo = area.texto_valores.get("1.0", "end")
        area.escala.definir(0.9)
        self.raiz.update()
        alto = area.texto_valores.get("1.0", "end")
        self.assertNotEqual(baixo, alto)
        c = {round(x["limiar"], 2): x for x in area.curva}
        self.assertGreater(c[0.9]["precisao"], c[0.1]["precisao"])
        self.assertLess(c[0.9]["revocacao"], c[0.1]["revocacao"])

    def test_outros_classificadores_aparecem_em_tabela_e_k_responde(self):
        _, lic = self.abrir(4)
        lic.mostrar(5)
        self.raiz.update()
        area = lic.area
        t = texto(area)
        for nome in T.L4_P6_NOMES.values():
            self.assertIn(nome, t)
        area.escala.definir(1)
        self.assertTrue(self.esperar(lambda: "k (quantos vizinhos votam): 1" in texto(area), 10))
        self.esperar(lambda: area.tabela.winfo_children() != [], 10)
        self.assertGreaterEqual(len(area.tabela.winfo_children()), 1)

    def test_resumo_conclui_e_marca_a_licao(self):
        lab, lic = self.abrir(4)
        lic.mostrar(6)
        self.raiz.update()
        quiz = achar_atributo(lic.area, "quiz").quiz
        self.assertEqual(len(quiz.perguntas), 3)
        for i, q in enumerate(quiz.perguntas):
            quiz.vars[i].set(q["correta"])
            quiz.responder(i)
        lic.ir(1)
        self.raiz.update()
        self.assertTrue(lab.estado.progresso.concluida(4))
        self.assertIn(T.INICIO_TITULO, texto(lab.atual))

    def test_limite_alto_demais_explica_e_nao_quebra(self):
        lab, lic = self.abrir(4)
        lic.local["limite"] = 300
        lic.mostrar(1)
        self.raiz.update()
        self.assertIn("poucos minutos quentes", texto(lic.area))

    def test_com_historico_real_curto_a_licao_pede_mais_dados(self):
        lab = self.novo_lab()
        c = gerar(P(dias=3))
        lab.estado.definir_real(Conjunto("real", c.ts, c.dados), None)
        lab.estado.trocar_fonte("real")
        lab.abrir_licao(4)
        self.raiz.update()
        t = texto(lab.atual)
        self.assertIn("pelo menos 5 dias", t)
        self.assertIn(T.BOTAO_USAR_SINTETICOS, t)


class TestLicao5(BaseNovas):
    def test_passos_e_primeira_tela(self):
        _, lic = self.abrir(5)
        self.assertEqual([p.titulo for p in lic.passos], T.L5_PASSOS)
        self.assertIn("Cada ponto é um minuto", texto(lic.area))
        self.assertIn("Não existe resposta certa", texto(lic.area))

    def test_kmeans_responde_ao_numero_de_grupos(self):
        _, lic = self.abrir(5)
        lic.mostrar(1)
        self.raiz.update()
        area = lic.area
        self.assertIn("Número de grupos (k): 3", texto(area))
        t3 = texto(area)
        area.escala.definir(5)
        self.assertTrue(self.esperar(lambda: "Tamanho dos grupos" in texto(area) and texto(area).count("%") >= 5, 10))
        self.assertNotEqual(t3, texto(area))

    def test_quantos_grupos_mostra_inercia_e_silhueta_e_nao_dá_um_k_certo(self):
        _, lic = self.abrir(5)
        corpo = self.ir_ate(lic, 2, "varredura")
        v = corpo.varredura
        self.assertEqual(len(v["inercia"]), 7)
        t = texto(lic.area)
        self.assertIn("Não existe um k certo", t)
        self.assertIn("A silhueta é maior com k = 2", t)

    def test_dar_nome_aos_grupos_com_nomes_sugeridos_e_editaveis(self):
        _, lic = self.abrir(5)
        lic.mostrar(3)
        self.raiz.update()
        corpo = lic.area.corpo
        nomes = [e.get() for e in corpo.entradas]
        self.assertEqual(nomes, ["quase parado", "trabalho leve", "carga pesada"])
        corpo.entradas[0].delete(0, "end")
        corpo.entradas[0].insert(0, "descanso")
        corpo.entradas[0].focus_force()
        self.raiz.update()
        corpo.entradas[0].event_generate("<KeyRelease>")
        self.raiz.update()
        self.assertEqual(lic.local["nomes"][3][corpo.resultado.ordem_uso[0]], "descanso")

    def test_gabarito_no_sintetico_mostra_pureza_e_matriz_de_regimes(self):
        _, lic = self.abrir(5)
        corpo = self.ir_ate(lic, 4, "pureza")
        t = texto(lic.area)
        self.assertRegex(t, r"Com k = 3 a pureza é de \d+%")
        for regime in T.L5_P5_REGIMES:
            self.assertIn(regime, t)

    def test_gabarito_no_real_explica_que_nao_existe(self):
        lab = self.novo_lab()
        c = gerar(P(dias=21))
        lab.estado.definir_real(Conjunto("real", c.ts, c.dados), None)
        lab.estado.trocar_fonte("real")
        lab.abrir_licao(5)
        self.raiz.update()
        lic = lab.atual
        lic.mostrar(4)
        self.raiz.update()
        self.assertIn("não há gabarito", texto(lic.area))

    def test_componentes_principais_mostram_variancia_e_cargas(self):
        _, lic = self.abrir(5)
        lic.mostrar(5)
        self.raiz.update()
        t = texto(lic.area)
        self.assertRegex(t, r"O 1º componente explica \d+% da variação")
        self.assertIn("mistura: uso", t)
        self.assertIn("mesmo sinal", t)

    def test_resumo_conclui_e_marca_a_licao(self):
        lab, lic = self.abrir(5)
        lic.mostrar(6)
        self.raiz.update()
        quiz = achar_atributo(lic.area, "quiz").quiz
        self.assertEqual(len(quiz.perguntas), 3)
        for i, q in enumerate(quiz.perguntas):
            quiz.vars[i].set(q["correta"])
            quiz.responder(i)
        lic.ir(1)
        self.raiz.update()
        self.assertTrue(lab.estado.progresso.concluida(5))

    def test_historico_real_curto_pede_mais_dados(self):
        lab = self.novo_lab()
        c = gerar(P(dias=3))
        lab.estado.definir_real(Conjunto("real", c.ts[:300], {k: v[:300] for k, v in c.dados.items()}), None)
        lab.estado.trocar_fonte("real")
        lab.abrir_licao(5)
        self.raiz.update()
        self.assertIn("pelo menos 3 dias", texto(lab.atual))


class TestEstadoDasLicoesNovas(unittest.TestCase):
    def test_licoes_4_e_5_usam_21_dias_sem_episodios_nem_poeira_a_menos_que_o_aprendiz_escolha(self):
        import tempfile
        from lab.estado import Estado
        from lab.progresso import Progresso
        with tempfile.TemporaryDirectory() as d:
            est = Estado(Progresso(Path(d) / "p.json"))
            for n in (4, 5):
                p = est.params_licao(n)
                self.assertEqual((p.dias, p.episodios, p.poeira_por_dia), (21, 0, 0.0), n)
            est.params = P(dias=28, episodios=5, poeira_por_dia=0.1)
            est.params_do_aprendiz = True
            p = est.params_licao(4)
            self.assertEqual((p.dias, p.episodios, p.poeira_por_dia), (28, 5, 0.1))
            self.assertEqual(est.chave_dados(4), est.chave_dados(5))

    def test_a_qualidade_dos_dados_cobre_as_cinco_licoes(self):
        from lab.qualidade import analisar
        rel = analisar(gerar(P(dias=21)))
        self.assertEqual(sorted(rel.prontidao), [1, 2, 3, 4, 5])
        self.assertTrue(rel.prontidao[4].recomendada and rel.prontidao[5].recomendada)
        curto = analisar(gerar(P(dias=3)))
        self.assertFalse(curto.prontidao[4].pode)                 # a lição 4 pede 5 dias e 4.000 minutos
        self.assertTrue(curto.prontidao[5].pode)

    def test_o_progresso_aceita_as_licoes_novas(self):
        import tempfile
        from lab.progresso import Progresso
        with tempfile.TemporaryDirectory() as d:
            p = Progresso(Path(d) / "p.json")
            p.marcar_concluida(4)
            p.marcar_concluida(5)
            q = Progresso(Path(d) / "p.json")
            self.assertTrue(q.concluida(4) and q.concluida(5))


if __name__ == "__main__":
    unittest.main()
