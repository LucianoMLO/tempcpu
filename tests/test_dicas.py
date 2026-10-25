import tkinter as tk
import unittest

from dicas import Dica, texto_dos_termos


class TestTextoDosTermos(unittest.TestCase):
    def test_so_explica_o_que_aparece_na_linha(self):
        t = texto_dos_termos("GPU 52 °C  ·  SoC 48 °C  ·  CPU a 3.200 MHz")
        self.assertIn("System on Chip", t)
        self.assertIn("Placa de vídeo", t)
        self.assertIn("MHz", t)
        self.assertNotIn("Ventoinha:", t)

    def test_linha_vazia_nao_tem_legenda(self):
        self.assertEqual(texto_dos_termos(""), "")

    def test_ventoinha_indisponivel_tambem_explica(self):
        self.assertIn("Ventoinha:", texto_dos_termos("Ventoinha indisponível: sem ASUS"))


class TestDica(unittest.TestCase):
    def setUp(self):
        try:
            self.raiz = tk.Tk()
        except tk.TclError:
            self.skipTest("sem ambiente gráfico")
        self.raiz.withdraw()
        self.rotulo = tk.Label(self.raiz, text="x")
        self.rotulo.pack()
        self.raiz.update()

    def tearDown(self):
        self.raiz.destroy()

    def test_mostra_e_esconde(self):
        d = Dica(self.rotulo, lambda: "olá", atraso=1)
        d.mostrar()
        self.assertIsNotNone(d.janela)
        d._esconder()
        self.assertIsNone(d.janela)

    def test_texto_vazio_nao_abre_janela(self):
        d = Dica(self.rotulo, lambda: "")
        d.mostrar()
        self.assertIsNone(d.janela)

    def test_destruir_o_widget_fecha_a_dica_sem_erro(self):
        d = Dica(self.rotulo, "oi")
        d.mostrar()
        self.rotulo.destroy()
        self.raiz.update()
        self.assertIsNone(d.janela)


if __name__ == "__main__":
    unittest.main()
