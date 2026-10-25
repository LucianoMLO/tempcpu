"""Testes da navegação, do Glossário e da tela Sobre e privacidade."""
import sys
import tkinter as tk
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _base  # noqa: E402,F401

from lab import VERSAO  # noqa: E402
from lab import textos as T  # noqa: E402
from lab.glossario import TERMOS  # noqa: E402
from test_ui import BaseUI, todos_os_textos  # noqa: E402

NL = chr(10)


def botoes(w):
    if isinstance(w, tk.Button):
        yield w
    for f in w.winfo_children():
        yield from botoes(f)


class TestNavegacaoEInformacao(BaseUI):
    def clicar_no_topo(self, lab, texto):
        for b in botoes(lab.topo):
            if b.cget("text") == texto:
                b.invoke()
                self.raiz.update()
                return
        self.fail(f"botão {texto} não encontrado")

    def test_barra_do_topo_leva_as_tres_telas(self):
        lab = self.novo_lab()
        self.assertEqual([b.cget("text") for b in botoes(lab.topo)], [T.NAV_INICIO, T.NAV_QUALIDADE, T.NAV_GLOSSARIO, T.NAV_SOBRE])
        self.clicar_no_topo(lab, T.NAV_GLOSSARIO)
        self.assertIn(T.GLOSSARIO_TITULO, NL.join(todos_os_textos(lab.atual)))
        self.clicar_no_topo(lab, T.NAV_SOBRE)
        self.assertIn(T.SOBRE_TITULO, NL.join(todos_os_textos(lab.atual)))
        self.clicar_no_topo(lab, T.NAV_INICIO)
        self.assertIn(T.INICIO_TITULO, NL.join(todos_os_textos(lab.atual)))

    def test_navegar_durante_uma_licao_cancela_o_treino_e_nao_quebra(self):
        lab = self.novo_lab()
        lab.abrir_licao(1)
        lab.atual.mostrar(2)
        self.raiz.update()
        self.clicar_no_topo(lab, T.NAV_GLOSSARIO)
        self.esperar(lambda: False, 1.0)                        # deixa o treino cancelado terminar
        self.assertIn(T.GLOSSARIO_TITULO, NL.join(todos_os_textos(lab.atual)))

    def test_glossario_lista_todos_os_termos_em_ordem_e_com_definicao_e_exemplo(self):
        lab = self.novo_lab()
        lab.mostrar_glossario()
        self.raiz.update()
        tela = lab.atual
        self.assertEqual(len(tela.visiveis), len(TERMOS))
        nomes = [TERMOS[k][0].lower() for k in tela.visiveis]
        self.assertEqual(nomes, sorted(nomes))
        t = NL.join(todos_os_textos(tela))
        self.assertIn("sobreajuste  (overfitting)", t)
        self.assertIn("Exemplo:", t)

    def test_glossario_filtra_pela_busca(self):
        lab = self.novo_lab()
        lab.mostrar_glossario()
        tela = lab.atual
        tela.busca.set("colinear")
        self.raiz.update()
        self.assertEqual(tela.visiveis, ["colinearidade"])
        tela.busca.set("overfitting")                           # também acha pelo nome em inglês
        self.raiz.update()
        self.assertEqual(tela.visiveis, ["sobreajuste"])
        tela.busca.set("zzzz")
        self.raiz.update()
        self.assertEqual(tela.visiveis, [])
        self.assertIn(T.GLOSSARIO_NADA, NL.join(todos_os_textos(tela)))
        tela.busca.set("")
        self.raiz.update()
        self.assertEqual(len(tela.visiveis), len(TERMOS))

    def test_sobre_diz_o_que_le_o_que_grava_e_o_que_nao_faz(self):
        lab = self.novo_lab()
        lab.mostrar_sobre()
        self.raiz.update()
        t = NL.join(todos_os_textos(lab.atual))
        for trecho in ("somente para leitura", "Nomes de programas nunca são lidos", "arquivo pequeno de progresso",
                       "Não envia nada pela internet", "não diagnóstico".replace("não ", ""), "DADOS DE MENTIRA",
                       f"versão {VERSAO}"):
            self.assertIn(trecho, t, trecho)


if __name__ == "__main__":
    unittest.main()
