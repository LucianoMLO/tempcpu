import json
import statistics
import sys
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from diagnostico import Item, Retrato  # noqa: E402
from historico import (AcumuladorMinuto, Gravador, Historico, combinar, fim_periodo,  # noqa: E402
                       inicio_periodo, resumo_texto)
from motivos import Categoria, Motivo, categoria_de, rotulo_de  # noqa: E402

DIA = int(datetime(2026, 10, 21, 0, 0).timestamp())  # quarta-feira


def zona(c):
    return "normal" if c < 75 else "atencao" if c < 90 else "quente"


def minuto(ts, temps, **kw):
    acc = AcumuladorMinuto(ts)
    for i, t in enumerate(temps):
        acc.amostras += 1
        acc.valor("cpu_c", t, ts + i)
    for k, v in kw.items():
        for x in (v if isinstance(v, list) else [v]):
            acc.valor(k, x)
    return acc


class TestAcumulador(unittest.TestCase):
    def test_estatisticas_do_minuto(self):
        temps = [60, 62, 70, 64, 61, 90]
        reg = minuto(DIA, temps).fechar(zona)
        self.assertEqual((reg["cpu_c_min"], reg["cpu_c_max"], reg["cpu_c_n"]), (60, 90, 6))
        self.assertAlmostEqual(reg["cpu_c_med"], statistics.mean(temps), places=2)
        self.assertAlmostEqual(reg["cpu_c_dp"], statistics.pstdev(temps), places=2)
        self.assertEqual((reg["zona"], reg["z_quente"], reg["z_normal"]), ("quente", 1, 0))
        self.assertEqual(reg["pico_ts"], DIA + 5)

    def test_variavel_sem_dado_fica_nula(self):
        reg = minuto(DIA, [60]).fechar(zona)
        self.assertEqual(reg["gpu_c_n"], 0)
        self.assertIsNone(reg["gpu_c_med"])


class TestCombinar(unittest.TestCase):
    def test_desvio_agregado_igual_ao_dos_dados_brutos(self):
        a, b = [50, 52, 51, 53], [80, 82, 85, 79, 81, 84, 83]
        regs = [minuto(DIA, a).fechar(zona), minuto(DIA + 60, b).fechar(zona)]
        out = combinar(regs)
        tudo = a + b
        self.assertEqual(out["cpu_c_n"], len(tudo))
        self.assertAlmostEqual(out["cpu_c_med"], statistics.mean(tudo), places=2)
        self.assertAlmostEqual(out["cpu_c_dp"], statistics.pstdev(tudo), places=2)
        self.assertEqual((out["cpu_c_min"], out["cpu_c_max"]), (50, 85))
        self.assertEqual(out["pico_ts"], DIA + 60 + 2)  # 85 é a terceira amostra do 2º minuto

    def test_media_das_medias_seria_errada(self):
        regs = [minuto(DIA, [50]).fechar(zona), minuto(DIA + 60, [80] * 9).fechar(zona)]
        self.assertAlmostEqual(combinar(regs)["cpu_c_med"], 77.0, places=2)  # (50 + 9·80)/10, não 65


class TestBanco(unittest.TestCase):
    def setUp(self):
        self.h = Historico(":memory:", retencao_dias=365)

    def grava(self, ts, temps, motivos=(), programa=None, **kw):
        acc = minuto(ts, temps, **kw)
        for m in motivos:
            acc.motivos[m.value] += 1
        if motivos:
            acc.principais[motivos[0].value] += 1
        if programa:
            acc.programas[programa] += 1
            acc.pct_programa[programa] = 40.0
        self.h.gravar_minuto(acc.fechar(zona))

    def test_um_registro_por_minuto_e_regravar_substitui(self):
        self.grava(DIA, [60, 61])
        self.grava(DIA, [70, 71])
        self.assertEqual(self.h.contagem()["minuto"], 1)
        self.assertEqual(self.h.serie("cpu_c", DIA, DIA + 60, "minuto")[0]["med"], 70.5)

    def test_rollups_hora_dia_semana_mes(self):
        self.grava(DIA + 10 * 3600, [60, 62], [Motivo.PROCESSO_PESADO], "chrome.exe")
        self.grava(DIA + 10 * 3600 + 60, [88, 90], [Motivo.TURBO_LIBERADO, Motivo.PROCESSO_PESADO], "chrome.exe")
        self.grava(DIA + 15 * 3600, [55])
        self.grava(DIA + 86400 + 3600, [65])  # dia seguinte (quinta), mesma semana e mês
        c = self.h.contagem()
        self.assertEqual((c["minuto"], c["hora"], c["dia"], c["semana"], c["mes"]), (4, 3, 2, 1, 1))
        dia = self.h.linhas("dia", DIA, DIA + 86400)[0]
        self.assertEqual(dia["minutos"], 3)
        self.assertEqual(dia["cpu_c_max"], 90)
        self.assertEqual(dia["motivos_dict"], {"processo_pesado": 2, "turbo_liberado": 1})
        self.assertEqual(dia["programas_dict"], {"chrome.exe": 2})
        sem = self.h.linhas("semana", DIA, DIA + 7 * 86400)[0]
        self.assertEqual(sem["minutos"], 4)
        self.assertEqual(sem["cpu_c_n"], 6)  # 2 + 2 + 1 + 1 amostras de temperatura

    def test_retencao_apaga_minutos_mas_mantem_resumos(self):
        antigo = DIA - 400 * 86400
        self.grava(antigo, [60])
        self.grava(DIA, [70])
        apagados = self.h.limpar(agora=DIA + 3600, forcar=True)
        self.assertEqual(apagados, 1)
        c = self.h.contagem()
        self.assertEqual(c["minuto"], 1)
        self.assertEqual(c["dia"], 2)  # o resumo do dia antigo continua
        self.assertEqual(self.h.serie("cpu_c", antigo, antigo + 86400, "dia")[0]["med"], 60)

    def test_limpeza_so_uma_vez_por_dia(self):
        self.grava(DIA - 400 * 86400, [60])
        self.assertEqual(self.h.limpar(agora=DIA, forcar=True), 1)
        self.grava(DIA - 401 * 86400, [61])
        self.assertEqual(self.h.limpar(agora=DIA + 100), 0)

    def test_serie_traz_motivo_e_ignora_variavel_sem_dado(self):
        self.grava(DIA, [60], [Motivo.CPU_CARGA_ALTA], uso_cpu=[70, 80])
        p = self.h.serie("uso_cpu", DIA, DIA + 60, "minuto")
        self.assertEqual((p[0]["med"], p[0]["motivo"]), (75.0, "cpu_carga_alta"))
        self.assertEqual(self.h.serie("gpu_c", DIA, DIA + 60, "minuto"), [])

    def test_motivos_em_tabela_de_classe(self):
        self.grava(DIA, [60], [Motivo.PROCESSO_PESADO, Motivo.TURBO_LIBERADO])
        linhas = self.h.con.execute("SELECT motivo FROM minuto_motivo ORDER BY motivo").fetchall()
        self.assertEqual([l[0] for l in linhas], ["processo_pesado", "turbo_liberado"])
        reg = self.h.con.execute("SELECT motivo_principal, categoria_motivo FROM minuto").fetchone()
        self.assertEqual((reg[0], reg[1]), ("processo_pesado", "carga"))

    def test_resumo_do_periodo(self):
        self.grava(DIA, [60, 62], [Motivo.PROCESSO_PESADO], "chrome.exe", ventoinha_rpm=[2800, 3000])
        self.grava(DIA + 60, [91], [Motivo.PROCESSO_PESADO])
        txt = self.h.resumir(DIA, DIA + 3600, "minuto")
        self.assertIn("CPU 71,0 °C em média", txt)
        self.assertIn("Programa pesado (2 min)", txt)
        self.assertIn("chrome.exe (1 min)", txt)
        self.assertIn("Normal 50% · Quente 50%", txt)
        self.assertIn("Ventoinha: média 2.900 RPM", txt)
        self.assertEqual(self.h.resumir(DIA + 9999, DIA + 10000, "minuto"), "Sem dados neste período.")


class TestPeriodos(unittest.TestCase):
    def test_limites_locais(self):
        ts = int(datetime(2026, 10, 21, 15, 42, 30).timestamp())  # quarta
        self.assertEqual(datetime.fromtimestamp(inicio_periodo(ts, "hora")), datetime(2026, 10, 21, 15, 0))
        self.assertEqual(datetime.fromtimestamp(inicio_periodo(ts, "dia")), datetime(2026, 10, 21))
        self.assertEqual(datetime.fromtimestamp(inicio_periodo(ts, "semana")), datetime(2026, 10, 19))  # segunda
        self.assertEqual(datetime.fromtimestamp(inicio_periodo(ts, "mes")), datetime(2026, 10, 1))
        self.assertEqual(datetime.fromtimestamp(fim_periodo(inicio_periodo(ts, "mes"), "mes")), datetime(2026, 11, 1))
        dez = int(datetime(2026, 12, 15).timestamp())
        self.assertEqual(datetime.fromtimestamp(fim_periodo(inicio_periodo(dez, "mes"), "mes")), datetime(2027, 1, 1))


class TestGravador(unittest.TestCase):
    def test_virada_de_minuto_grava_um_registro_completo(self):
        h = Historico(":memory:")
        g = Gravador(h, zona)
        t0 = DIA + 100 * 60
        for i in range(30):  # 30 amostras de 2 s no minuto
            g.amostra(t0 + i * 2, 60 + i % 5, "AMD", False, gpu_c=50, rpm=2800)
        self.assertEqual(h.contagem()["minuto"], 0)  # minuto ainda aberto
        r = Retrato(uso_cpu=35, processos=[("chrome.exe", 22.0)], plano_energia="Equilibrado", na_tomada=True,
                    bateria=100, estado_max_ac=100, coletado_em=t0 + 10)
        g.diagnostico(t0 + 10, r, [Item("x", "alta", Motivo.PROCESSO_PESADO), Item("y", "media", Motivo.TURBO_LIBERADO)])
        g.diagnostico(t0 + 11, r, [Item("x", "alta", Motivo.PROCESSO_PESADO)])  # mesmo retrato: ignorado
        g.amostra(t0 + 61, 70, "AMD", False)  # vira o minuto
        self.assertEqual(h.contagem()["minuto"], 1)
        reg = dict(h.con.execute("SELECT * FROM minuto").fetchone())
        self.assertEqual((reg["cpu_c_n"], reg["gpu_c_n"], reg["uso_cpu_n"]), (30, 30, 1))
        self.assertEqual((reg["motivo_principal"], reg["programa_principal"], reg["fonte"]), ("processo_pesado", "chrome.exe", "AMD"))
        self.assertEqual((reg["plano"], reg["estado_max_ac"], reg["tomada_med"]), ("Equilibrado", 100, 1.0))

    def test_leitura_parada_nao_entra_nas_estatisticas(self):
        h = Historico(":memory:")
        g = Gravador(h, zona)
        for i in range(5):
            g.amostra(DIA + i * 2, 86.1, "ACPI", True, rpm=3000)
        g.fechar()
        reg = dict(h.con.execute("SELECT * FROM minuto").fetchone())
        self.assertEqual((reg["cpu_c_n"], reg["descartadas"], reg["ventoinha_rpm_n"]), (0, 5, 5))
        self.assertIsNone(reg["zona"])

    def test_sem_programas_quando_desligado(self):
        h = Historico(":memory:")
        g = Gravador(h, zona, salvar_programas=False)
        g.amostra(DIA, 60, "AMD", False)
        g.diagnostico(DIA + 1, Retrato(processos=[("chrome.exe", 50.0)], coletado_em=1.0), [])
        g.fechar()
        self.assertIsNone(h.con.execute("SELECT programa_principal FROM minuto").fetchone()[0])

    def test_minuto_vazio_nao_grava(self):
        h = Historico(":memory:")
        Gravador(h, zona).fechar()
        self.assertEqual(h.contagem()["minuto"], 0)


class TestMotivos(unittest.TestCase):
    def test_todo_motivo_tem_categoria_e_rotulo(self):
        for m in Motivo:
            self.assertIsInstance(m.categoria, Categoria)
            self.assertTrue(m.rotulo)

    def test_codigos_estaveis(self):
        self.assertEqual(Motivo("processo_pesado"), Motivo.PROCESSO_PESADO)
        self.assertEqual(categoria_de("ventoinha_parada"), Categoria.REFRIGERACAO)
        self.assertEqual(rotulo_de("codigo_novo_desconhecido"), "codigo_novo_desconhecido")
        self.assertIsNone(categoria_de("desconhecido"))


class TestResumo(unittest.TestCase):
    def test_sem_dados(self):
        self.assertEqual(resumo_texto({}), "Sem dados neste período.")


if __name__ == "__main__":
    unittest.main()
