"""Análise da qualidade dos dados: cálculo (puro) e telas ("Meus dados", Início e aviso nas lições)."""
import sys
import tempfile
import time
import tkinter as tk
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _base  # noqa: E402,F401
from _base import gravar_minuto  # noqa: E402

import numpy as np  # noqa: E402

from historico import Historico  # noqa: E402
from lab import textos as T  # noqa: E402
from lab.dados import Conjunto, carregar_real, verificar_minimos  # noqa: E402
from lab.qualidade import analisar, frase_da_prontidao, resumo_curto  # noqa: E402
from lab.sintetico import ParametrosSinteticos as P, gerar  # noqa: E402
from test_ui import BaseUI, achar_atributo, todos_os_textos  # noqa: E402

NL = chr(10)


def como_real(c: Conjunto, **dados) -> Conjunto:
    d = {k: v.copy() for k, v in c.dados.items()}
    d.update(dados)
    return Conjunto("real", c.ts.copy(), d)


def notas(rel):
    return {i.chave: i.nota for i in rel.itens}


class TestCalculo(unittest.TestCase):
    def test_dados_padrao_14_dias_sao_regulares_so_pelo_periodo(self):
        rel = analisar(gerar(P()))
        n = notas(rel)
        self.assertEqual((n["minutos"], n["uso"], n["temperatura"], n["tomada"], n["horas"], n["cobertura"]), ("boa",) * 6)
        self.assertEqual(n["periodo"], "regular")            # 14 dias: abaixo das 3 semanas da tendência
        self.assertEqual(rel.geral, "regular")
        self.assertTrue(rel.prontidao[1].recomendada)
        self.assertTrue(rel.prontidao[2].pode and rel.prontidao[2].recomendada)       # 14 dias: serve, com a ressalva da tendência
        self.assertIn("3 semanas", " ".join(rel.prontidao[2].motivos))

    def test_21_dias_sao_bons_e_recomendam_as_duas_licoes(self):
        rel = analisar(gerar(P(dias=21)))
        self.assertEqual(rel.geral, "boa")
        self.assertEqual(notas(rel)["periodo"], "boa")
        self.assertTrue(rel.prontidao[1].recomendada and rel.prontidao[2].recomendada)
        self.assertEqual(rel.prontidao[2].motivos, [])          # 21 dias do calendário bastam para a tendência
        self.assertIn("21 dias", rel.item("periodo").valor)

    def test_poucos_dias_sao_fracos_e_explicam_o_que_falta(self):
        rel = analisar(gerar(P(dias=3)))
        self.assertEqual(rel.geral, "fraca")
        self.assertTrue(rel.prontidao[1].pode)                  # 3 dias e 2.700 minutos: o mínimo da lição 1
        self.assertFalse(rel.prontidao[1].recomendada)
        self.assertFalse(rel.prontidao[2].pode)
        motivos = " ".join(rel.prontidao[2].motivos)
        self.assertIn("ela pede 7 dias e 5.000 minutos", motivos)
        self.assertIn("você tem 3 dias e 2.700 minutos", motivos)
        self.assertIn("mais alguns dias", rel.item("periodo").sugestao)

    def test_uso_sem_variedade_e_apontado_com_o_que_fazer(self):
        c = gerar(P())
        rel = analisar(como_real(c, uso=np.full(c.n, 10.0) + np.random.default_rng(1).normal(0, 1, c.n)))
        i = rel.item("uso")
        self.assertEqual(i.nota, "fraca")
        self.assertIn("Inclua tarefas mais pesadas", i.sugestao)
        self.assertIn("entre", i.valor)
        self.assertEqual(rel.geral, "fraca")                     # o núcleo derruba a nota geral

    def test_sempre_na_tomada_avisa_que_a_entrada_sera_ignorada(self):
        c = gerar(P())
        rel = analisar(como_real(c, tomada=np.ones(c.n)))
        i = rel.item("tomada")
        self.assertEqual(i.nota, "fraca")
        self.assertIn("100%", i.valor)
        self.assertIn("vai ignorar essa", i.sugestao)
        self.assertEqual(rel.geral, "regular")                   # item secundário: derruba no máximo até "regular"

    def test_poucas_horas_do_dia(self):
        c = gerar(P(dias=21))
        manha = np.isin(c.dados["hora"], [9, 10, 11])
        sub = Conjunto("real", c.ts[manha], {k: v[manha] for k, v in c.dados.items()})
        rel = analisar(sub)
        self.assertEqual(rel.item("horas").nota, "fraca")
        self.assertIn("3 das 24", rel.item("horas").valor)
        self.assertEqual(int((np.array(rel.horas) > 0).sum()), 3)

    def test_aproveitamento_conta_o_que_foi_descartado(self):
        c = como_real(gerar(P()))
        c.filtragem = {"util": 400, "acpi": 500, "poucas_amostras": 60, "sem_uso": 30, "sem_freq_tomada": 10, "total": 1000}
        i = analisar(c).item("aproveitamento")
        self.assertEqual(i.nota, "fraca")
        self.assertIn("400 de 1.000", i.valor)
        self.assertIn("leitura parada: 500", i.valor)
        self.assertIn("sem uso: 40", i.valor)                    # soma dos sem uso e sem frequência/tomada
        self.assertIn("ACPI", i.explicacao)

    def test_sem_filtragem_nao_ha_item_de_aproveitamento(self):
        self.assertNotIn("aproveitamento", [i.chave for i in analisar(gerar(P())).itens])

    def test_ventoinha_e_so_informativa(self):
        c = gerar(P())
        com = analisar(como_real(c)).item("ventoinha")
        sem = analisar(como_real(c, ventoinha=np.full(c.n, np.nan))).item("ventoinha")
        self.assertIsNone(com.nota)
        self.assertIn("Disponível", com.sugestao)
        self.assertIn("Indisponível", sem.sugestao)
        self.assertIn("0%", sem.valor)

    def test_conjunto_vazio_nao_tem_relatorio(self):
        vazio = Conjunto("real", np.array([], dtype=np.int64), {k: np.array([]) for k in gerar(P()).dados})
        self.assertIsNone(analisar(vazio))

    def test_graficos_somam_os_minutos(self):
        rel = analisar(gerar(P()))
        self.assertEqual(sum(rel.horas), rel.n)
        self.assertEqual(sum(q for _, q in rel.faixas_uso), rel.n)
        self.assertEqual(len(rel.faixas_uso), 10)

    def test_frases_de_prontidao_e_resumo(self):
        rel = analisar(gerar(P(dias=3)))
        self.assertIn("pode fazer, mas com ressalvas", frase_da_prontidao(rel.prontidao[1]))
        self.assertIn("ainda não, faltam dados", frase_da_prontidao(rel.prontidao[2]))
        self.assertIn("sempre dados sintéticos", frase_da_prontidao(rel.prontidao[3]))
        self.assertIn("fraca", resumo_curto(rel))
        self.assertIn("2.700 minutos úteis em 3 dias", resumo_curto(rel))

    def test_toda_nota_tem_explicacao_e_sugestao_quando_nao_e_boa(self):
        for chave, (titulo, explicacao, sugestoes) in T.QUAL_ITENS.items():
            self.assertTrue(titulo and len(explicacao) > 30, chave)
            if chave != "ventoinha":
                self.assertTrue(sugestoes.get("regular") and sugestoes.get("fraca"), chave)


class TestDiasDoCalendario(unittest.TestCase):
    def conjunto(self, ini, fim):
        ts = np.array([int(time.mktime(ini)), int(time.mktime(fim))], dtype=np.int64)
        return Conjunto("real", ts, {k: np.zeros(2) for k in gerar(P()).dados})

    def test_segunda_de_manha_a_quarta_a_noite_sao_tres_dias(self):
        c = self.conjunto((2026, 1, 5, 7, 0, 0, 0, 0, -1), (2026, 1, 7, 21, 59, 0, 0, 0, -1))
        self.assertEqual(c.dias_calendario, 3)
        self.assertLess(c.dias, 3)                               # dias corridos: 2,6

    def test_mesmo_dia_e_um_dia_e_virada_de_ano(self):
        self.assertEqual(self.conjunto((2026, 1, 5, 7, 0, 0, 0, 0, -1), (2026, 1, 5, 22, 0, 0, 0, 0, -1)).dias_calendario, 1)
        self.assertEqual(self.conjunto((2025, 12, 30, 8, 0, 0, 0, 0, -1), (2026, 1, 2, 8, 0, 0, 0, 0, -1)).dias_calendario, 4)

    def test_minimos_usam_dias_do_calendario(self):
        c = gerar(P(dias=3))
        real = Conjunto("real", c.ts, c.dados)
        self.assertTrue(verificar_minimos(real, 1)[0])


class TestFiltragemNoBanco(unittest.TestCase):
    def test_conta_cada_minuto_em_um_unico_motivo(self):
        with tempfile.TemporaryDirectory() as d:
            caminho = Path(d) / "historico.db"
            h = Historico(caminho)
            t0 = int(time.mktime((2026, 1, 5, 8, 0, 0, 0, 0, -1)))
            casos = [dict(), dict(), dict(), dict(fonte="ACPI"), dict(fonte="ACPI"), dict(n_temp=2), dict(n_uso=0), dict(freq=None)]
            try:
                for i, kw in enumerate(casos):
                    gravar_minuto(h, t0 + 60 * i, **kw)
            finally:
                h.fechar()
            c = carregar_real(caminho)
            self.assertEqual(c.filtragem, {"util": 3, "acpi": 2, "poucas_amostras": 1, "sem_uso": 1, "sem_freq_tomada": 1, "total": 8})
            self.assertEqual(c.n, 3)

    def test_banco_vazio_traz_filtragem_zerada(self):
        with tempfile.TemporaryDirectory() as d:
            caminho = Path(d) / "historico.db"
            Historico(caminho).fechar()
            c = carregar_real(caminho)
            self.assertEqual((c.n, c.filtragem["total"]), (0, 0))


def _botoes(w):
    if isinstance(w, tk.Button):
        yield w
    for f in w.winfo_children():
        yield from _botoes(f)


class TestTelas(BaseUI):
    def lab_com_real(self, dias):
        lab = self.novo_lab()
        c = gerar(P(dias=dias))
        real = como_real(c)
        real.filtragem = {"util": c.n, "acpi": 0, "poucas_amostras": 0, "sem_uso": 0, "sem_freq_tomada": 0, "total": c.n}
        lab.estado.definir_real(real, None)
        lab.estado.trocar_fonte("real")
        lab.atualizar_faixa()
        return lab

    def clicar(self, lab, texto, onde=None):
        for b in _botoes(onde or lab.atual):
            if b.cget("text") == texto:
                b.invoke()
                self.raiz.update()
                return
        self.fail(f"botão {texto!r} não encontrado")

    def test_tela_meus_dados_mostra_nota_itens_graficos_e_licoes(self):
        lab = self.lab_com_real(5)
        self.clicar(lab, T.NAV_QUALIDADE, lab.topo)
        self.raiz.update()
        t = NL.join(todos_os_textos(lab.atual))
        self.assertIn(T.QUAL_TITULO, t)
        self.assertIn("Qualidade geral: Fraca", t)
        for titulo in ("Quantidade de dados", "Período coberto", "Variedade do uso da CPU", "Tomada e bateria", "Rotação da ventoinha"):
            self.assertIn(titulo, t)
        self.assertIn("O que fazer", t)
        self.assertIn("Lição 2: ainda não, faltam dados", t)
        self.assertIn("Lição 3: usa sempre dados sintéticos", t)
        self.assertIn(T.QUAL_GRAFICO_HORAS.upper(), t)
        canvases = [w for w in _todos(lab.atual) if isinstance(w, tk.Canvas) and w.winfo_class() == "Canvas" and len(w.find_all()) > 20]
        self.assertGreaterEqual(len(canvases), 2)

    def test_sem_historico_real_explica_e_oferece_ler_de_novo(self):
        lab = self.novo_lab()
        lab.estado.real_carregado = True
        lab.estado.erro_real = "Nenhum histórico encontrado em X."
        self.clicar(lab, T.NAV_QUALIDADE, lab.topo)
        t = NL.join(todos_os_textos(lab.atual))
        self.assertIn("Não há histórico real para analisar", t)
        self.assertIn("Nenhum histórico encontrado em X.", t)
        self.assertIn(T.QUAL_LER_DE_NOVO, t)

    def test_inicio_mostra_o_resumo_e_leva_ao_relatorio(self):
        lab = self.lab_com_real(5)
        lab.mostrar_inicio()
        self.raiz.update()
        t = NL.join(todos_os_textos(lab.atual))
        self.assertIn("Qualidade dos seus dados: fraca", t)
        self.assertIn("4.500 minutos úteis em 5 dias", t)
        self.clicar(lab, T.QUAL_VER)
        self.assertIn(T.QUAL_TITULO, NL.join(todos_os_textos(lab.atual)))

    def test_inicio_sem_historico_nao_mostra_resumo(self):
        lab = self.novo_lab()
        self.assertNotIn("Qualidade dos seus dados:", NL.join(todos_os_textos(lab.atual)))

    def test_licao_com_dados_reais_fracos_mostra_aviso_e_botao(self):
        lab = self.lab_com_real(5)                              # serve à lição 1, mas a qualidade é fraca
        lab.abrir_licao(1)
        self.raiz.update()
        caixa = achar_atributo(lab.atual.area, "aviso_qualidade")
        self.assertEqual(caixa.aviso_qualidade, "fraca")
        t = NL.join(todos_os_textos(lab.atual.area))
        self.assertIn("a qualidade dos seus dados é fraca", t)
        self.assertIn("Os resultados desta lição podem oscilar", t)
        self.clicar(lab, T.QUAL_VER, caixa)
        self.assertIn(T.QUAL_TITULO, NL.join(todos_os_textos(lab.atual)))

    def test_licao_com_dados_bons_ou_sinteticos_nao_mostra_aviso(self):
        lab = self.lab_com_real(21)
        lab.abrir_licao(1)
        self.raiz.update()
        self.assertIsNone(achar_atributo(lab.atual.area, "aviso_qualidade"))
        lab2 = self.novo_lab()
        lab2.abrir_licao(1)
        self.raiz.update()
        self.assertIsNone(achar_atributo(lab2.atual.area, "aviso_qualidade"))

    def test_tela_de_poucos_dados_oferece_ver_a_qualidade(self):
        lab = self.lab_com_real(3)                              # 3 dias, mas só 300 minutos: abaixo do mínimo da lição 1
        n = 300
        c = lab.estado.real
        lab.estado.definir_real(Conjunto('real', c.ts[:n], {k: v[:n] for k, v in c.dados.items()}), None)
        lab.estado.trocar_fonte('real')
        lab.abrir_licao(1)
        self.raiz.update()
        t = NL.join(todos_os_textos(lab.atual))
        self.assertIn(T.BOTAO_USAR_SINTETICOS, t)
        self.assertIn(T.QUAL_VER, t)
        self.clicar(lab, T.QUAL_VER)
        self.assertIn("Quantidade de dados", NL.join(todos_os_textos(lab.atual)))


def _todos(w):
    yield w
    for f in w.winfo_children():
        yield from _todos(f)


if __name__ == "__main__":
    unittest.main()
