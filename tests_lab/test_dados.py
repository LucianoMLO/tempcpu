import hashlib
import sqlite3
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _base  # noqa: E402,F401
from _base import gravar_minuto  # noqa: E402

import numpy as np  # noqa: E402

from historico import Historico  # noqa: E402
from lab import dados  # noqa: E402
from lab.dados import (BancoIlegivel, Conjunto, SemBanco, carregar_real, dividir_embaralhado,  # noqa: E402
                       dividir_por_tempo, verificar_minimos)

T0 = int(time.mktime((2026, 1, 5, 8, 0, 0, 0, 0, -1)))


def banco(pasta: Path, linhas: list[dict]) -> Path:
    caminho = pasta / "historico.db"
    h = Historico(caminho)
    try:
        for i, kw in enumerate(linhas):
            gravar_minuto(h, T0 + i * 60, **kw)
    finally:
        h.fechar()
    return caminho


class TestLeitura(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.pasta = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_so_minutos_uteis_e_em_ordem(self):
        caminho = banco(self.pasta, [
            dict(temp=50, uso=10),                      # útil
            dict(temp=60, uso=20, fonte="ACPI"),        # ACPI pode ficar parada: fora
            dict(temp=70, uso=30, n_temp=3),            # poucas amostras de temperatura: fora
            dict(temp=55, uso=15, n_uso=0),             # sem uso medido: fora
            dict(temp=65, uso=25, freq=None),           # sem frequência: fora
            dict(temp=75, uso=35, rpm=None),            # útil (ventoinha ausente = NaN)
        ])
        c = carregar_real(caminho)
        self.assertEqual(c.origem, "real")
        self.assertEqual(list(c.dados["temperatura"]), [50.0, 75.0])
        self.assertTrue(np.all(np.diff(c.ts) > 0))
        self.assertTrue(np.isnan(c.dados["ventoinha"][1]))
        self.assertFalse(np.isnan(c.dados["ventoinha"][0]))
        self.assertTrue(np.array_equal(c.mascara(["uso", "freq", "tomada", "hora"]), [True, True]))
        self.assertTrue(np.array_equal(c.mascara(["uso", "ventoinha"]), [True, False]))

    def test_nome_de_programa_nunca_e_lido(self):
        c = carregar_real(banco(self.pasta, [dict(), dict()]))
        self.assertFalse(any("programa" in k for k in c.dados))
        self.assertEqual(set(c.dados), set(dados.VARIAVEIS))

    def test_hora_e_dia_derivados_do_tempo(self):
        c = carregar_real(banco(self.pasta, [dict()] * 3))
        self.assertEqual(c.dados["hora"][0], 8.0)
        self.assertEqual(c.dados["dia"][0], 0.0)
        self.assertAlmostEqual(c.dados["dia"][2], 120 / 86400)

    def test_limita_aos_mais_recentes(self):
        caminho = banco(self.pasta, [dict(temp=40 + i) for i in range(80)])
        antigo, dados.MAX_MINUTOS_REAIS = dados.MAX_MINUTOS_REAIS, 50
        try:
            c = carregar_real(caminho)
        finally:
            dados.MAX_MINUTOS_REAIS = antigo
        self.assertEqual(c.n, 50)
        self.assertEqual(c.dados["temperatura"][-1], 119.0)   # o minuto mais novo ficou
        self.assertEqual(c.dados["temperatura"][0], 70.0)

    def test_banco_ausente_e_ilegivel(self):
        with self.assertRaises(SemBanco):
            carregar_real(self.pasta / "nao_existe.db")
        lixo = self.pasta / "lixo.db"
        lixo.write_bytes(b"isto nao e um banco sqlite" * 100)
        with self.assertRaises(BancoIlegivel):
            carregar_real(lixo)

    def test_banco_sem_a_tabela_e_ilegivel(self):
        vazio = self.pasta / "vazio.db"
        sqlite3.connect(vazio).close()
        with self.assertRaises(BancoIlegivel):
            carregar_real(vazio)

    def test_a9_banco_identico_e_escrita_impossivel(self):
        caminho = banco(self.pasta, [dict(temp=50 + i) for i in range(20)])
        antes = hashlib.sha256(caminho.read_bytes()).hexdigest()
        carregar_real(caminho)
        con = dados._abrir_somente_leitura(caminho)
        with self.assertRaises(sqlite3.OperationalError):
            con.execute("DELETE FROM minuto")
        with self.assertRaises(sqlite3.OperationalError):
            con.execute("INSERT INTO minuto_motivo (ts, motivo) VALUES (1, 'x')")
        con.close()
        carregar_real(caminho)
        self.assertEqual(hashlib.sha256(caminho.read_bytes()).hexdigest(), antes)

    def test_banco_vazio_vira_conjunto_vazio(self):
        c = carregar_real(banco(self.pasta, []))
        self.assertEqual((c.n, c.dias), (0, 0.0))


class TestMinimos(unittest.TestCase):
    def conjunto(self, n, dias):
        ts = np.linspace(0, dias * 86400, n).astype(np.int64)
        return Conjunto("real", ts, {k: np.zeros(n) for k in dados.VARIAVEIS})

    def test_real_com_poucos_dados_explica(self):
        ok, msg = verificar_minimos(self.conjunto(100, 0.1), 1)
        self.assertFalse(ok)
        self.assertIn("3 dias", msg)
        self.assertIn("100 minutos", msg)

    def test_real_suficiente(self):
        self.assertEqual(verificar_minimos(self.conjunto(2500, 4), 1), (True, ""))
        self.assertFalse(verificar_minimos(self.conjunto(2500, 4), 2)[0])   # lição 2 pede 7 dias e 5.000

    def test_sintetico_sempre_basta(self):
        c = self.conjunto(10, 0.0)
        c.origem = "sintetico"
        self.assertTrue(verificar_minimos(c, 2)[0])


class TestDivisao(unittest.TestCase):
    def test_por_tempo(self):
        tr, te = dividir_por_tempo(np.arange(100))
        self.assertEqual((len(tr), len(te)), (70, 30))
        self.assertLess(tr.max(), te.min())          # treino sempre antes do teste

    def test_embaralhado_mistura_e_e_reprodutivel(self):
        a = dividir_embaralhado(np.arange(100), 3)
        b = dividir_embaralhado(np.arange(100), 3)
        self.assertTrue(np.array_equal(a[0], b[0]))
        self.assertGreater(a[0].max(), a[1].min())   # vizinhos misturados
        self.assertEqual(len(set(a[0]) & set(a[1])), 0)
        self.assertEqual(len(a[0]) + len(a[1]), 100)


class TestMatriz(unittest.TestCase):
    def test_hora_circular(self):
        n = 24
        c = Conjunto("sintetico", np.arange(n, dtype=np.int64), {**{k: np.zeros(n) for k in dados.VARIAVEIS},
                                                                  "hora": np.arange(n, dtype=float)})
        X, nomes = c.matriz(["uso", "hora"], circular=True)
        self.assertEqual(nomes, ["uso", "hora_sen", "hora_cos"])
        self.assertAlmostEqual(float(np.hypot(X[5, 1], X[5, 2])), 1.0)
        cru, nomes2 = c.matriz(["uso", "hora"])
        self.assertEqual(nomes2, ["uso", "hora"])
        self.assertEqual(cru.shape, (n, 2))


if __name__ == "__main__":
    unittest.main()
