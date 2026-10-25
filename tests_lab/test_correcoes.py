"""Testes das correções da revisão independente: leitura do banco, núcleo de ML, estado/cache, progresso e interface."""
import json
import hashlib
import sys
import tempfile
import time
import tkinter as tk
import unittest
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _base  # noqa: E402,F401
from _base import gravar_minuto  # noqa: E402

import numpy as np  # noqa: E402

from historico import Historico  # noqa: E402
from lab import dados, modelos as M  # noqa: E402
from lab.dados import Conjunto, carregar_real  # noqa: E402
from lab.estado import Estado  # noqa: E402
from lab.progresso import Progresso  # noqa: E402
from lab.sintetico import ParametrosSinteticos as P, gerar  # noqa: E402
from test_ui import BaseUI, achar_atributo  # noqa: E402

T0 = int(time.mktime((2026, 1, 5, 8, 0, 0, 0, 0, -1)))


class TestLeituraDoBanco(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.caminho = Path(self._tmp.name) / "historico.db"

    def tearDown(self):
        self._tmp.cleanup()

    def test_nenhuma_consulta_menciona_programa(self):
        h = Historico(self.caminho)
        for i in range(10):
            gravar_minuto(h, T0 + 60 * i)
        h.fechar()
        consultas = []
        original = dados._abrir_somente_leitura

        def com_rastro(caminho):
            con = original(caminho)
            con.set_trace_callback(consultas.append)
            return con

        dados._abrir_somente_leitura = com_rastro
        try:
            carregar_real(self.caminho)
        finally:
            dados._abrir_somente_leitura = original
        self.assertTrue(consultas)
        for sql in consultas:
            self.assertNotIn("programa", sql.lower())

    def test_hash_do_banco_nao_muda_com_escritor_vivo_em_wal(self):
        h = Historico(self.caminho)                         # o app continua aberto e gravando
        try:
            for i in range(30):
                gravar_minuto(h, T0 + 60 * i)
            antes = hashlib.sha256(self.caminho.read_bytes()).hexdigest()
            c = carregar_real(self.caminho)
            self.assertEqual(c.n, 30)                       # enxerga os minutos que ainda estão só no WAL
            gravar_minuto(h, T0 + 60 * 30)                  # e o escritor segue funcionando depois da leitura
            c2 = carregar_real(self.caminho)
            self.assertEqual(c2.n, 31)
            self.assertEqual(hashlib.sha256(self.caminho.read_bytes()).hexdigest(), antes)
        finally:
            h.fechar()


class TestNucleo(unittest.TestCase):
    def test_modelo_linear_empata_com_a_melhor_arvore_num_mundo_linear(self):
        r = M.curva_profundidade(gerar(P()))
        self.assertLessEqual(r.mae_linear, min(r.mae_teste) * 1.05)

    def test_sem_poeira_nenhuma_semente_acusa_tendencia(self):
        for s in (1, 2, 3, 4, 5):
            r = M.treinar_anomalia(gerar(P(dias=21, semente=s, poeira_por_dia=0.0, episodios=0)), semente=s)
            self.assertLess(abs(r.inclinacao), 0.75, (s, r.inclinacao))

    def test_ruido_do_sintetico_fica_na_faixa_calibrada(self):
        for s in (1, 2, 3):
            c = gerar(P(dias=14, semente=s))
            g, d = c.gabarito, c.dados
            conhecida = (g["intercepto"] + g["uso"] * d["uso"] + g["tomada"] * d["tomada"]
                         + g["hora_sen"] * np.sin(2 * np.pi * d["hora"] / 24) + g["hora_cos"] * np.cos(2 * np.pi * d["hora"] / 24))
            desvio = float((d["temperatura"] - conhecida).std())
            self.assertTrue(2.2 <= desvio <= 2.9, (s, desvio))

    def test_episodios_de(self):
        v = np.array([0, 1, 1, 0, 0, 1, 0, 1, 1, 1], dtype=bool)
        self.assertEqual(M.episodios_de(v), [(1, 3), (5, 6), (7, 10)])
        self.assertEqual(M.episodios_de(np.zeros(5, dtype=bool)), [])
        self.assertEqual(M.episodios_de(np.ones(4, dtype=bool)), [(0, 4)])
        self.assertEqual(M.episodios_de(np.array([], dtype=bool)), [])

    def test_avaliar_deteccao_conta_recall_e_falsos_alarmes(self):
        n = 100
        verdade = np.zeros(n, dtype=bool)
        verdade[10:20] = True
        verdade[50:60] = True
        marcado = np.zeros(n, dtype=bool)
        marcado[12:15] = True                                 # acha o primeiro (basta um minuto)
        marcado[80:84] = True                                 # 4 falsos alarmes
        regiao = np.ones(n, dtype=bool)
        recall, falsos = M.avaliar_deteccao(verdade, marcado, regiao)
        self.assertEqual(recall, 0.5)
        self.assertAlmostEqual(falsos, 4 / 80 * 100)

    def test_avaliar_deteccao_so_olha_a_regiao_e_sem_episodios_nao_ha_recall(self):
        n = 100
        verdade = np.zeros(n, dtype=bool)
        verdade[10:20] = True
        regiao = np.zeros(n, dtype=bool)
        regiao[50:] = True                                    # o episódio está fora da região avaliada
        marcado = np.zeros(n, dtype=bool)
        recall, falsos = M.avaliar_deteccao(verdade, marcado, regiao)
        self.assertIsNone(recall)
        self.assertEqual(falsos, 0.0)

    def test_tendencia_semanal_direta(self):
        dia = 86400
        ts = np.arange(0, 21 * dia, 60, dtype=np.int64)
        semana = ts // (7 * dia)
        residuo = semana * 1.5 + 0.0                          # mediana sobe 1,5 por semana
        semanas, incl = M.tendencia_semanal(ts, residuo)
        self.assertEqual([s for s, _, _ in semanas], [0, 1, 2])
        self.assertAlmostEqual(incl, 1.5, places=6)

    def test_tendencia_semanal_ignora_semana_com_poucos_minutos_e_pede_tres(self):
        dia = 86400
        ts = np.concatenate([np.arange(0, 7 * dia, 60), np.arange(7 * dia, 7 * dia + 100 * 60, 60)]).astype(np.int64)
        semanas, incl = M.tendencia_semanal(ts, np.zeros(len(ts)))
        self.assertEqual(len(semanas), 1)                     # a segunda semana só tem 100 minutos
        self.assertIsNone(incl)


class TestEstado(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.est = Estado(Progresso(Path(self._tmp.name) / "p.json"))

    def tearDown(self):
        self._tmp.cleanup()

    def real_grande(self):
        c = gerar(P(dias=7))
        return Conjunto("real", c.ts, c.dados)

    def test_resultado_de_dados_antigos_nao_vai_para_a_chave_dos_novos(self):
        chave_larga = self.est.chave_dados(1)                 # calculada quando o treino começou
        self.est.params = replace(self.est.params, dias=21)   # os dados mudam enquanto o treino roda
        self.est.guardar("curva", (), "velho", licao=1, chave_dados=chave_larga)
        self.assertIsNone(self.est.buscar("curva", (), licao=1))
        self.est.guardar("curva", (), "novo", licao=1)
        self.assertEqual(self.est.buscar("curva", (), licao=1), "novo")
        self.assertEqual(self.est.cache[("curva", chave_larga, ())], "velho")

    def test_definir_real_no_inicio_escolhe_o_real_e_no_meio_da_licao_nao(self):
        self.est.definir_real(self.real_grande(), None, escolher_fonte=False)
        self.assertEqual(self.est.fonte, "sintetico")         # a lição em curso não muda por baixo do aprendiz
        self.assertTrue(self.est.real_carregado)
        self.est.definir_real(self.real_grande(), None)
        self.assertEqual(self.est.fonte, "real")

    def test_escolha_de_sintetico_do_aprendiz_e_respeitada(self):
        self.est.trocar_fonte("sintetico")
        self.est.definir_real(self.real_grande(), None)
        self.assertEqual(self.est.fonte, "sintetico")


class TestProgressoValidado(unittest.TestCase):
    def carregar(self, conteudo):
        with tempfile.TemporaryDirectory() as d:
            caminho = Path(d) / "p.json"
            caminho.write_text(json.dumps(conteudo) if not isinstance(conteudo, str) else conteudo, encoding="utf-8")
            return Progresso(caminho).dados

    def test_tipos_errados_sao_descartados(self):
        d = self.carregar({"concluidas": [1, "2", True, 3.5, None, 3], "acertos": {"1.1": True, "1.2": "sim", "1.3": 1}, "fonte": "nuvem"})
        self.assertEqual(d["concluidas"], [1, 3])
        self.assertEqual(d["acertos"], {"1.1": True})
        self.assertIsNone(d["fonte"])

    def test_estrutura_inesperada_vira_padrao(self):
        for lixo in ([1, 2], "texto", {"concluidas": 5, "acertos": [], "fonte": 3}, "{quebrado"):
            d = self.carregar(lixo)
            self.assertEqual(d, {"concluidas": [], "acertos": {}, "fonte": None, "provas": []})

    def test_arquivo_valido_e_lido(self):
        d = self.carregar({"concluidas": [2], "acertos": {"2.1": False}, "fonte": "real"})
        self.assertEqual((d["concluidas"], d["acertos"], d["fonte"]), ([2], {"2.1": False}, "real"))


class TestInterface(BaseUI):
    def setUp(self):
        super().setUp()
        self.erros = []
        self.raiz.report_callback_exception = lambda *a: self.erros.append(a[1])

    def tearDown(self):
        erros = self.erros
        super().tearDown()
        self.assertEqual(erros, [], "exceção escondida num callback do tkinter")

    def test_spinbox_da_semente_volta_ao_valor_anterior_com_texto_invalido(self):
        lab = self.novo_lab()
        lab.abrir_licao(3)
        self.raiz.update()
        from tkinter import ttk
        caixa = next(w for w in _todos(lab.atual) if isinstance(w, ttk.Spinbox))
        antes = lab.estado.params.semente
        for lixo in ("abc", "", "12,5", "-"):
            caixa.set(lixo)
            caixa.focus_force()
            self.raiz.update()
            caixa.event_generate("<Return>")
            self.raiz.update()
            self.assertEqual(int(caixa.get()), antes, lixo)
            self.assertEqual(lab.estado.params.semente, antes)
        caixa.set("99999")
        caixa.focus_force()
        caixa.event_generate("<Return>")
        self.raiz.update()
        self.assertEqual(lab.estado.params.semente, 9999)     # limitado à faixa

    def test_excecao_em_callback_e_capturada_pelo_gancho(self):
        capturados = []
        self.raiz.report_callback_exception = lambda *a: capturados.append(a[1])
        self.raiz.after(1, lambda: 1 / 0)
        self.esperar(lambda: bool(capturados), 5)
        self.assertIsInstance(capturados[0], ZeroDivisionError)
        self.erros = []

    def test_licao2_sem_episodios_explica_em_vez_de_quebrar(self):
        lab = self.novo_lab()
        lab.estado.params = P(dias=21, episodios=0, poeira_por_dia=0.0)
        lab.estado.params_do_aprendiz = True                  # a lição 2 respeita os controles escolhidos na lição 3
        lab.abrir_licao(2)
        self.raiz.update()
        lic = lab.atual
        lic.mostrar(3)
        self.assertTrue(self.esperar(lambda: achar_atributo(lic.area, "escala") is not None, 120))
        self.assertEqual(int(lab.estado.conjunto(2).anomalia.sum()), 0)
        self.assertTrue(lab.atual.winfo_exists())

    def test_licao3_slider_de_episodios_chega_aos_dados(self):
        lab = self.novo_lab()
        lab.abrir_licao(3)
        self.raiz.update()
        area = achar_atributo(lab.atual.area, "escalas")
        area.escalas["episodios"].set(7)
        self.raiz.update()
        self.assertTrue(self.esperar(lambda: lab.estado.params.episodios == 7, 10))
        self.assertTrue(lab.estado.params_do_aprendiz)


def _todos(w):
    yield w
    for f in w.winfo_children():
        yield from _todos(f)


if __name__ == "__main__":
    unittest.main()
