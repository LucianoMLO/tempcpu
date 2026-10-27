"""Testes da interface do Laboratório: abrem janelas reais (tkinter) e percorrem as telas."""
import os
import sys
import tempfile
import time
import tkinter as tk
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _base  # noqa: E402,F401

import numpy as np  # noqa: E402

from lab import textos as T  # noqa: E402
from lab.dados import VARIAVEIS, Conjunto  # noqa: E402
from lab.estado import Estado  # noqa: E402
from lab.glossario import chaves_usadas, segmentos, TERMOS  # noqa: E402
from lab.modelos import Cancelado  # noqa: E402
from lab.progresso import Progresso  # noqa: E402
from lab.tarefa import Tarefa  # noqa: E402
from lab.ui.janela import Laboratorio  # noqa: E402
from lab.ui.passos import PainelProgresso  # noqa: E402
from lab.ui.rico import TextoRico  # noqa: E402


def todos_os_textos(w: tk.Misc):
    if isinstance(w, (tk.Label, tk.Button)):
        yield str(w.cget("text"))
    elif isinstance(w, tk.Text):
        yield w.get("1.0", "end")
    for f in w.winfo_children():
        yield from todos_os_textos(f)


def achar(w: tk.Misc, tipo, **attrs):
    if isinstance(w, tipo) and all(getattr(w, k, None) == v for k, v in attrs.items()):
        return w
    for f in w.winfo_children():
        r = achar(f, tipo)
        if r is not None and (not attrs or all(getattr(r, k, None) == v for k, v in attrs.items())):
            return r
    return None


def achar_atributo(w: tk.Misc, nome: str):
    if hasattr(w, nome):
        return w
    for f in w.winfo_children():
        r = achar_atributo(f, nome)
        if r is not None:
            return r
    return None


class BaseUI(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        os.environ["TEMPCPU_LAB_DADOS"] = self._tmp.name
        self.raiz = tk.Tk()
        self.raiz.geometry("1120x800+40+40")

    def tearDown(self):
        try:
            self.raiz.destroy()
        except tk.TclError:
            pass
        os.environ.pop("TEMPCPU_LAB_DADOS", None)
        self._tmp.cleanup()

    def novo_lab(self) -> Laboratorio:
        est = Estado(Progresso(Path(self._tmp.name) / "progresso.json"))
        est.fonte = "sintetico"
        lab = Laboratorio(self.raiz, est, carregar_real=False)
        self.raiz.update()
        return lab

    def esperar(self, condicao, limite=60.0):
        fim = time.time() + limite
        while time.time() < fim:
            self.raiz.update()
            if condicao():
                return True
            time.sleep(0.02)
        return False

    def texto_da_tela(self, lab: Laboratorio) -> str:
        return "\n".join(todos_os_textos(lab.atual))


class TestInicio(BaseUI):
    def test_mostra_as_tres_licoes_e_a_faixa_de_dados_sinteticos(self):
        lab = self.novo_lab()
        t = self.texto_da_tela(lab)
        for n in (1, 2, 3):
            self.assertIn(T.LICOES[n][0], t)
        self.assertTrue(lab.faixa_visivel)
        self.assertIn("DADOS SINTÉTICOS", lab.faixa.cget("text"))

    def test_as_tres_licoes_estao_disponiveis_e_nenhuma_concluida_no_comeco(self):
        lab = self.novo_lab()
        t = self.texto_da_tela(lab)
        self.assertEqual(t.count(T.LICAO_EM_BREVE), 0)
        self.assertEqual(t.count(T.LICAO_NAO_INICIADA), 3)

    def test_glossario_na_barra_inferior(self):
        lab = self.novo_lab()
        lab.definir_termo("modelo")
        self.assertIn("Uma fórmula que o computador aprende", lab.barra.cget("text"))
        lab.definir_termo(None)
        self.assertEqual(lab.barra.cget("text"), T.BARRA_GLOSSARIO_VAZIA)

    def test_ler_de_novo_le_o_historico_outra_vez_e_mostra_orientacao_se_nao_ha_banco(self):
        pasta = Path(self._tmp.name) / "sem_historico"
        pasta.mkdir()
        original = os.environ.get("LOCALAPPDATA")
        os.environ["LOCALAPPDATA"] = str(pasta)               # nenhum TempCPU\historico.db aqui
        try:
            lab = self.novo_lab()
            lab.estado.real_carregado = True
            botao = next(b for b in _botoes(lab.atual) if b.cget("text") == T.INICIO_LER_DE_NOVO)
            botao.invoke()
            self.assertFalse(lab.estado.real_carregado)                          # mostra "Lendo o histórico…"
            self.assertIn(T.INICIO_REAL_LENDO, self.texto_da_tela(lab))
            self.assertTrue(self.esperar(lambda: lab.estado.real_carregado, 10))
            t = self.texto_da_tela(lab)
            self.assertIn("Nenhum histórico encontrado", t)
            self.assertIn("deixe-o rodar alguns dias", t)
            self.assertIn("Nada foi alterado", t)
            self.assertEqual(str(lab.atual.rb_real.cget("state")), "disabled")
            self.assertEqual(lab.estado.fonte, "sintetico")
        finally:
            if original is None:
                os.environ.pop("LOCALAPPDATA", None)
            else:
                os.environ["LOCALAPPDATA"] = original

    def test_historico_real_ausente_desabilita_a_opcao(self):
        lab = self.novo_lab()
        tela = lab.atual
        self.assertEqual(str(tela.rb_real.cget("state")), "disabled")
        self.assertIn("Nenhum histórico utilizável", "\n".join(todos_os_textos(tela)))


class TestLicao1(BaseUI):
    def abrir(self):
        lab = self.novo_lab()
        lab.abrir_licao(1)
        self.raiz.update()
        return lab, lab.atual

    def test_passos_1_e_2_desenham_sem_erro(self):
        lab, lic = self.abrir()
        for i in (0, 1):
            lic.mostrar(i)
            self.raiz.update()
            self.assertIn(T.L1_PASSOS[i], self.texto_da_tela(lab))
            cv = achar(lic.area, tk.Canvas)
            self.assertIsNotNone(cv)
            self.raiz.update()
            self.assertGreater(len(cv.find_all()), 10)       # algo foi desenhado

    def test_passo_3_treina_em_segundo_plano_e_responde_ao_controle(self):
        lab, lic = self.abrir()
        lic.mostrar(2)
        self.assertTrue(self.esperar(lambda: achar_atributo(lic.area, "escala") is not None), "o treino não terminou")
        corpo = achar_atributo(lic.area, "escala")
        self.assertIn("Profundidade 3", "\n".join(todos_os_textos(corpo)))
        corpo.escala.set(9)
        self.raiz.update()
        t = "\n".join(todos_os_textos(corpo))
        self.assertIn("Profundidade 9", t)
        self.assertIn("menor", t)                               # a profundidade 9 é o ponto de equilíbrio
        corpo.escala.set(18)
        self.raiz.update()
        self.assertIn("decorou", "\n".join(todos_os_textos(corpo)))   # sobreajuste
        corpo.escala.set(1)
        self.raiz.update()
        self.assertIn("simples demais", "\n".join(todos_os_textos(corpo)))   # subajuste

    def test_resultado_fica_em_cache_e_a_segunda_visita_e_imediata(self):
        lab, lic = self.abrir()
        lic.mostrar(2)
        self.assertTrue(self.esperar(lambda: achar_atributo(lic.area, "escala") is not None))
        self.assertIsNotNone(lab.estado.buscar("curva1", (tuple(__import__("lab.ui.licao1", fromlist=["x"]).ENTRADAS), "tempo", 7)))
        lic.mostrar(1)
        lic.mostrar(2)
        self.raiz.update()
        self.assertIsNotNone(achar_atributo(lic.area, "escala"))           # sem passar pelo "Treinando…"
        self.assertIsNone(achar(lic.area, PainelProgresso))

    def test_voltar_ao_inicio_cancela_o_treino_em_andamento(self):
        lab, lic = self.abrir()
        lic.mostrar(2)
        self.raiz.update()
        lab.mostrar_inicio()
        self.raiz.update()
        self.assertIn(T.INICIO_TITULO, self.texto_da_tela(lab))

    def test_botoes_anterior_e_proximo(self):
        lab, lic = self.abrir()
        self.assertEqual(str(lic.btn_ant.cget("state")), "disabled")
        lic.ir(1)
        self.assertEqual(lic.indice, 1)
        lic.ir(-1)
        self.assertEqual(lic.indice, 0)
        lic.mostrar(2)
        self.assertEqual(lic.btn_prox.cget("text"), T.BOTAO_PROXIMO)       # ainda há passos depois
        lic.mostrar(5)
        self.assertEqual(lic.btn_prox.cget("text"), T.BOTAO_CONCLUIR)


class TestLicao1Completa(BaseUI):
    def abrir(self):
        lab = self.novo_lab()
        lab.abrir_licao(1)
        self.raiz.update()
        return lab, lab.atual

    def ir_ate(self, lic, passo, atributo):
        lic.mostrar(passo)
        self.assertTrue(self.esperar(lambda: achar_atributo(lic.area, atributo) is not None, 90), f"passo {passo + 1} não terminou")
        return achar_atributo(lic.area, atributo)

    def test_passo2_embaralhar_mostra_a_nota_falsa(self):
        lab, lic = self.abrir()
        lic.mostrar(1)
        self.raiz.update()
        area = achar_atributo(lic.area, "embaralhar")
        self.assertIsNotNone(area)
        antes = len(achar(lic.area, tk.Canvas).find_all())
        area.embaralhar.set(True)
        area.alternar_embaralhar()
        self.assertTrue(self.esperar(lambda: "é falsa" in "\n".join(todos_os_textos(lic.area)), 90))
        t = "\n".join(todos_os_textos(lic.area))
        self.assertIn("vizinho", t)
        self.assertIn("Melhor erro no teste", t)
        self.assertIn("marcas laranja", " ".join(str(achar(lic.area, tk.Canvas).itemcget(i, "text")) for i in achar(lic.area, tk.Canvas).find_all()
                                                if achar(lic.area, tk.Canvas).type(i) == "text"))
        area.embaralhar.set(False)
        area.alternar_embaralhar()
        self.raiz.update()
        self.assertNotIn("é falsa", "\n".join(todos_os_textos(lic.area)))
        self.assertGreater(antes, 10)

    def test_passo4_compara_com_chutar_a_media(self):
        lab, lic = self.abrir()
        corpo = self.ir_ate(lic, 3, "barras")
        (r1, media, _), (r2, linear, _), (r3, arvore, _) = corpo.barras
        self.assertIn("Chutar a média", r1)
        self.assertGreater(media, 2 * arvore)
        self.assertLess(linear, media)
        t = "\n".join(todos_os_textos(lic.area))
        self.assertIn("modelo linear foi igual ou melhor", t)         # no mundo sintético linear a reta empata com a árvore
        self.assertIn("nota R² no teste", t)

    def test_passo5_importancia_e_a_armadilha_da_ventoinha(self):
        lab, lic = self.abrir()
        corpo = self.ir_ate(lic, 4, "importancias")
        self.assertEqual(corpo.importancias[0][0], "uso")
        t = "\n".join(todos_os_textos(lic.area))
        self.assertIn("A entrada mais importante foi Uso da CPU", t)
        self.assertNotIn("armadilha", t)
        corpo.ventoinha.set(True)
        corpo.alternar_ventoinha()
        self.assertTrue(self.esperar(lambda: hasattr(corpo.bloco_ventoinha, "resultado"), 90))
        mae_sem, mae_com, r2_sem, r2_com = corpo.bloco_ventoinha.resultado
        self.assertGreater(r2_com, r2_sem + 0.04)
        self.assertLess(mae_com, 0.7 * mae_sem)
        t = "\n".join(todos_os_textos(lic.area))
        self.assertIn("É uma armadilha", t.replace("é uma armadilha", "É uma armadilha"))
        self.assertIn("consequência", t)
        corpo.ventoinha.set(False)
        corpo.alternar_ventoinha()
        self.raiz.update()
        self.assertNotIn("armadilha", "\n".join(todos_os_textos(lic.area)))

    def test_passo5_sem_ventoinha_no_historico_real_explica(self):
        lab = self.novo_lab()
        sint = lab.estado.conjunto()
        dados = {k: v.copy() for k, v in sint.dados.items()}
        dados["ventoinha"][:] = np.nan
        lab.estado.definir_real(Conjunto("real", sint.ts.copy(), dados), None)
        lab.estado.trocar_fonte("real")
        lab.abrir_licao(1)
        self.raiz.update()
        lic = lab.atual
        corpo = self.ir_ate(lic, 4, "importancias")
        corpo.ventoinha.set(True)
        corpo.alternar_ventoinha()
        self.raiz.update()
        self.assertIn("poucas leituras de ventoinha", "\n".join(todos_os_textos(lic.area)))

    def test_passo6_perguntas_placar_e_conclusao(self):
        lab, lic = self.abrir()
        lic.mostrar(5)
        self.raiz.update()
        quiz = achar_atributo(lic.area, "quiz").quiz
        self.assertEqual(len(quiz.perguntas), 3)
        quiz.responder(0)                                          # sem escolher: nada acontece
        self.assertEqual(quiz.respondidas, {})
        quiz.vars[0].set(1)
        quiz.responder(0)
        self.assertTrue(quiz.respondidas[0])
        self.assertIn("Correto", quiz.feedbacks[0].get("1.0", "end"))
        quiz.vars[1].set(0)
        quiz.responder(1)
        self.assertFalse(quiz.respondidas[1])
        self.assertIn("Não foi dessa vez", quiz.feedbacks[1].get("1.0", "end"))
        quiz.vars[1].set(1)
        quiz.responder(1)                                          # já respondida: não muda
        self.assertFalse(quiz.respondidas[1])
        quiz.vars[2].set(1)
        quiz.responder(2)
        self.assertEqual(quiz.placar.cget("text"), "Você acertou 2 de 3.")
        self.assertEqual(lab.estado.progresso.acertos(1), (2, 3))
        self.assertEqual(str(quiz.botoes[0].cget("state")), "disabled")
        self.assertFalse(lab.estado.progresso.concluida(1))
        lic.ir(1)                                                  # "Concluir lição"
        self.raiz.update()
        self.assertTrue(lab.estado.progresso.concluida(1))
        self.assertIn(T.INICIO_TITULO, self.texto_da_tela(lab))
        self.assertIn(T.LICAO_CONCLUIDA, self.texto_da_tela(lab))

    def test_passo6_e_rolavel_quando_passa_da_altura(self):
        lab, lic = self.abrir()
        lic.mostrar(5)

        def convergiu() -> bool:                 # a rolagem se reajusta a cada 250 ms
            altura_regiao = int(str(lic.tela.cget("scrollregion")).split()[3])
            return altura_regiao >= lic.area.winfo_reqheight() > 0

        self.assertTrue(self.esperar(convergiu, 5))
        self.assertTrue(self.esperar(lambda: lic.rolagem.winfo_ismapped() == (lic.area.winfo_reqheight() > lic.tela.winfo_height() + 2), 5))

    def test_todos_os_passos_cabem_numa_janela_menor_sem_erro(self):
        self.raiz.geometry("900x660+40+40")
        lab, lic = self.abrir()
        for i in range(6):
            lic.mostrar(i)
            self.raiz.update()
        self.assertEqual(lic.indice, 5)


class TestEstadosDeTela(BaseUI):
    def pai(self):
        lab = self.novo_lab()
        f = tk.Frame(lab.conteudo)
        f.pack()
        return lab, f

    def test_treino_cancelado_mostra_a_tela_de_cancelado(self):
        lab, f = self.pai()

        def lento(progresso, cancelar):
            for i in range(200):
                progresso(i / 200, "contando")
                if cancelar():
                    raise Cancelado()
                time.sleep(0.02)

        lab.treinar(f, "x", (), lento, ao_pronto=lambda r: None, refazer=lambda: None)
        self.assertTrue(self.esperar(lambda: achar(f, PainelProgresso) is not None, 5))
        lab.cancelar_tarefa()
        self.assertTrue(self.esperar(lambda: T.ESTADO_CANCELADO in "\n".join(todos_os_textos(f)), 10))
        self.assertIn(T.BOTAO_TENTAR_DE_NOVO, "\n".join(todos_os_textos(f)))
        self.assertIsNone(lab.estado.buscar("x"))          # cancelado não vai para o cache

    def test_erro_no_treino_mostra_mensagem_em_portugues_e_nao_trava(self):
        lab, f = self.pai()

        def quebra(progresso, cancelar):
            raise ValueError("Poucos dados: 12 minutos")

        lab.treinar(f, "y", (), quebra, ao_pronto=lambda r: None, refazer=lambda: None)
        self.assertTrue(self.esperar(lambda: "Poucos dados: 12 minutos" in "\n".join(todos_os_textos(f)), 10))
        t = "\n".join(todos_os_textos(f))
        self.assertIn("Nada foi alterado no seu histórico", t)
        self.assertIn(T.BOTAO_TENTAR_DE_NOVO, t)

    def test_progresso_aparece_durante_o_treino(self):
        lab, f = self.pai()
        vistos = []

        def com_progresso(progresso, cancelar):
            for i in range(5):
                progresso(i / 5, f"passo {i}")
                time.sleep(0.15)
            return 42

        resultado = []
        lab.treinar(f, "z", (), com_progresso, ao_pronto=resultado.append, refazer=lambda: None)
        self.assertTrue(self.esperar(lambda: achar(f, PainelProgresso) is not None, 5))
        self.assertTrue(self.esperar(lambda: bool(resultado), 10))
        self.assertEqual(resultado, [42])
        self.assertEqual(lab.estado.buscar("z"), 42)

    def test_poucos_dados_reais_oferecem_dados_sinteticos(self):
        lab = self.novo_lab()
        n = 300
        ts = (np.arange(n) * 60).astype(np.int64)
        lab.estado.definir_real(Conjunto("real", ts, {k: np.ones(n) for k in VARIAVEIS}), None)
        lab.estado.trocar_fonte("real")
        lab.atualizar_faixa()
        self.assertFalse(lab.faixa_visivel)                     # dados reais: sem a faixa de mentira
        lab.abrir_licao(1)
        self.raiz.update()
        t = self.texto_da_tela(lab)
        self.assertIn("pelo menos 3 dias", t)
        self.assertIn(T.BOTAO_USAR_SINTETICOS, t)
        for w in _botoes(lab.atual):
            if w.cget("text") == T.BOTAO_USAR_SINTETICOS:
                w.invoke()
                break
        self.raiz.update()
        self.assertEqual(lab.estado.fonte, "sintetico")
        self.assertTrue(lab.faixa_visivel)
        self.assertIn(T.INICIO_TITULO, self.texto_da_tela(lab))


def _botoes(w):
    if isinstance(w, tk.Button):
        yield w
    for f in w.winfo_children():
        yield from _botoes(f)


class TestTarefaEProgresso(BaseUI):
    def test_tarefa_entrega_o_resultado_na_thread_da_janela(self):
        saida = []
        Tarefa(self.raiz, lambda progresso, cancelar: 7, saida.append).iniciar()
        self.assertTrue(self.esperar(lambda: bool(saida), 5))
        self.assertEqual(saida, [7])

    def test_progresso_grava_e_le_e_sobrevive_a_arquivo_corrompido(self):
        caminho = Path(self._tmp.name) / "p.json"
        p = Progresso(caminho)
        p.marcar_concluida(1)
        p.registrar_acerto(1, 0, True)
        p.registrar_acerto(1, 1, False)
        p.fonte = "sintetico"
        q = Progresso(caminho)
        self.assertTrue(q.concluida(1) and not q.concluida(2))
        self.assertEqual(q.acertos(1), (1, 2))
        self.assertEqual(q.fonte, "sintetico")
        caminho.write_text("{ isto nao e json", encoding="utf-8")
        self.assertFalse(Progresso(caminho).concluida(1))       # começa do zero, sem quebrar


class TestTextos(unittest.TestCase):
    def test_todo_termo_marcado_existe_no_glossario(self):
        def varrer(v):
            if isinstance(v, str):
                segmentos(v)                                     # levanta KeyError se houver termo fora do glossário
            elif isinstance(v, (list, tuple)):
                for item in v:
                    varrer(item)
            elif isinstance(v, dict):
                for item in v.values():
                    varrer(item)

        textos_vistos = 0
        for nome in dir(T):
            if nome.startswith("_"):
                continue                                         # __doc__ cita ⟦chave⟧ só como exemplo
            varrer(getattr(T, nome))
            textos_vistos += 1
        self.assertGreater(textos_vistos, 100)

    def test_glossario_tem_nome_ingles_definicao_e_exemplo(self):
        for chave, (nome, ingles, defin, exemplo) in TERMOS.items():
            self.assertTrue(nome and ingles and len(defin) > 20 and exemplo, chave)

    def test_texto_formatavel_mantem_os_marcadores_de_valor(self):
        self.assertIn("{tr}", T.L1_P3_SOBRE)
        self.assertIn("sobreajuste", chaves_usadas(T.L1_P3_SOBRE))


if __name__ == "__main__":
    unittest.main()
