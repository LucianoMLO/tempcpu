"""Núcleo da avaliação: sorteio, correção, aprovação, recomendação, nome e código de conferência (critérios B6 a B8, B11, B13).
Usa um banco de mentira próprio: o banco real (com as respostas) não é versionado."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _base  # noqa: E402,F401

from lab import avaliacao as A  # noqa: E402
from lab.progresso import Progresso  # noqa: E402

TEMAS = ["T1", "T2", "T3", "T4", "T5"]


def banco_falso(n_final=8, n_niv=2, temas=TEMAS):
    banco = []
    for t in temas:
        for i in range(1, n_niv + n_final + 1):
            niv = i <= n_niv
            banco.append({"id": f"{t}-{i:02d}", "tema": t, "uso": "nivelamento" if niv else "final", "nivel": 1 if niv else (1 + i % 3),
                          "pergunta": f"Pergunta {t}-{i}?", "opcoes": [f"{t}-{i} a", f"{t}-{i} b", f"{t}-{i} c", f"{t}-{i} d"][:3 + i % 2],
                          "correta": i % 3, "explicacao": f"Explicação longa o bastante de {t}-{i}.", "revisar": (1, 2)})
    return banco


BANCO = banco_falso()


def responder_certo(prova, erros=()):
    """Marca a correta de cada item, errando de propósito nos ids de `erros`."""
    r = {}
    for item in prova.itens:
        r[item.id] = (item.correta + 1) % len(item.opcoes) if item.id in erros else item.correta
    return r


class TestSorteio(unittest.TestCase):
    def test_b6_final_tem_quatro_por_tema_e_e_reprodutivel(self):
        p = A.sortear_final(123, banco=BANCO)
        self.assertEqual(len(p.itens), 20)
        for t in TEMAS:
            self.assertEqual(sum(i.tema == t for i in p.itens), 4)
        self.assertEqual(len({i.id for i in p.itens}), 20)
        q = A.sortear_final(123, banco=BANCO)
        self.assertEqual(p, q)                                  # mesma semente: mesmas questões, ordem e alternativas
        self.assertNotEqual([i.id for i in p.itens], [i.id for i in A.sortear_final(124, banco=BANCO).itens])

    def test_so_questoes_de_final_entram_na_final_e_de_nivelamento_no_nivelamento(self):
        niv_ids = {q["id"] for q in BANCO if q["uso"] == "nivelamento"}
        fin = A.sortear_final(1, banco=BANCO)
        niv = A.sortear_nivelamento(1, banco=BANCO)
        self.assertFalse(niv_ids & {i.id for i in fin.itens})
        self.assertEqual({i.id for i in niv.itens}, niv_ids)
        self.assertEqual(len(niv.itens), 10)

    def test_b6_nao_repete_a_tentativa_anterior_quando_ha_outras(self):
        primeira = A.sortear_final(1, banco=BANCO)
        ids = [i.id for i in primeira.itens]
        for semente in range(2, 12):
            seg = A.sortear_final(semente, anteriores=ids, banco=BANCO)
            self.assertFalse(set(ids) & {i.id for i in seg.itens}, semente)

    def test_repete_so_o_que_falta_quando_o_banco_nao_tem_mais(self):
        pequeno = banco_falso(n_final=5)
        primeira = A.sortear_final(1, banco=pequeno)
        ids = [i.id for i in primeira.itens]
        seg = A.sortear_final(2, anteriores=ids, banco=pequeno)
        repetidas = {i.id for i in seg.itens} & set(ids)
        self.assertEqual(len(repetidas), 15)                    # 5 por tema só têm 1 nova cada; completa com repetidas
        self.assertEqual(len(seg.itens), 20)

    def test_tema_com_poucas_questoes_e_erro_claro(self):
        with self.assertRaisesRegex(ValueError, "só 3 questões"):
            A.sortear_final(1, banco=banco_falso(n_final=3))

    def test_cada_tema_tem_questao_de_nivel_2_ou_3(self):
        for semente in range(1, 40):
            p = A.sortear_final(semente, banco=BANCO)
            por_id = {q["id"]: q for q in BANCO}
            for t in TEMAS:
                self.assertTrue(any(por_id[i.id]["nivel"] >= 2 for i in p.itens if i.tema == t), (semente, t))

    def test_a_correta_acompanha_o_embaralhamento_das_alternativas(self):
        por_id = {q["id"]: q for q in BANCO}
        posicoes = set()
        for semente in range(1, 30):
            for item in A.sortear_final(semente, banco=BANCO).itens:
                q = por_id[item.id]
                self.assertEqual(item.opcoes[item.correta], q["opcoes"][q["correta"]])
                self.assertCountEqual(item.opcoes, q["opcoes"])
                posicoes.add(item.correta)
        self.assertGreaterEqual(len(posicoes), 3)               # a posição da correta varia entre provas

    def test_prova_publica_nao_vaza_resposta_nem_explicacao(self):
        p = A.sortear_final(5, banco=BANCO)
        texto = json.dumps(p.publica(), ensure_ascii=False)
        self.assertNotIn("correta", texto)
        self.assertNotIn("explicacao", texto)
        self.assertNotIn("Explicação longa", texto)
        for i in p.publica()["itens"]:
            self.assertEqual(set(i), {"id", "pergunta", "opcoes"})

    def test_banco_invalido_e_recusado(self):
        ruim = banco_falso()
        ruim[0]["correta"] = 9
        with self.assertRaises(ValueError):
            A.sortear_final(1, banco=ruim)
        repetido = banco_falso()
        repetido[1]["id"] = repetido[0]["id"]
        with self.assertRaises(ValueError):
            A.sortear_nivelamento(1, banco=repetido)


TEMAS8 = TEMAS + ["T6", "T7", "T8"]


class TestOitoTemas(unittest.TestCase):
    """Com 6 temas ou mais a final tem 3 questões por tema (8 temas = 24 questões)."""

    def setUp(self):
        self.banco = banco_falso(temas=TEMAS8)

    def test_a_final_tem_24_questoes_3_por_tema(self):
        self.assertEqual(A.por_tema_padrao(5), 4)
        self.assertEqual(A.por_tema_padrao(8), 3)
        p = A.sortear_final(9, banco=self.banco)
        self.assertEqual(len(p.itens), 24)
        for t in TEMAS8:
            self.assertEqual(sum(i.tema == t for i in p.itens), 3)
        self.assertEqual(len(A.sortear_nivelamento(9, banco=self.banco).itens), 16)

    def test_aprovacao_20_de_24_e_2_de_3_por_tema(self):
        p = A.sortear_final(9, banco=self.banco)

        def erros(por_tema):
            return [i.id for t, n in por_tema.items() for i in [x for x in p.itens if x.tema == t][:n]]

        self.assertEqual(A.corrigir(p, responder_certo(p)).aprovado, True)
        ok = A.corrigir(p, responder_certo(p, erros({"T1": 1, "T2": 1, "T3": 1, "T4": 1})))
        self.assertEqual((ok.acertos, ok.aprovado), (20, True))
        nota = A.corrigir(p, responder_certo(p, erros({"T1": 1, "T2": 1, "T3": 1, "T4": 1, "T5": 1})))
        self.assertEqual((nota.acertos, nota.aprovado), (19, False))
        tema = A.corrigir(p, responder_certo(p, erros({"T7": 2})))
        self.assertEqual((tema.acertos, tema.por_tema["T7"], tema.aprovado), (22, (1, 3), False))
        self.assertIn("T7", tema.motivos[0])

    def test_nao_repete_a_tentativa_anterior_e_recomenda_licoes_novas(self):
        a = A.sortear_final(1, banco=self.banco)
        b = A.sortear_final(2, anteriores=[i.id for i in a.itens], banco=self.banco)
        self.assertFalse({i.id for i in a.itens} & {i.id for i in b.itens})
        niv = A.sortear_nivelamento(3, banco=self.banco)
        ids = lambda t: [i.id for i in niv.itens if i.tema == t]
        self.assertIsNone(A.recomendar_licao(A.corrigir(niv, responder_certo(niv))))
        self.assertEqual(A.recomendar_licao(A.corrigir(niv, responder_certo(niv, ids("T6")))), 4)
        self.assertEqual(A.recomendar_licao(A.corrigir(niv, responder_certo(niv, ids("T7")))), 5)
        self.assertEqual(A.recomendar_licao(A.corrigir(niv, responder_certo(niv, ids("T8")))), 3)


class TestCorrecaoEAprovacao(unittest.TestCase):
    def setUp(self):
        self.prova = A.sortear_final(7, banco=BANCO)

    def erros_em(self, por_tema):
        """ids a errar: `por_tema` = {tema: quantos}."""
        ids = []
        for t, n in por_tema.items():
            ids += [i.id for i in self.prova.itens if i.tema == t][:n]
        return ids

    def test_tudo_certo(self):
        r = A.corrigir(self.prova, responder_certo(self.prova))
        self.assertEqual((r.acertos, r.total, r.nota_pct, r.aprovado), (20, 20, 100.0, True))
        self.assertEqual(r.erradas, ())
        self.assertEqual(r.motivos, ())

    def test_b7_16_de_20_equilibrado_aprova(self):
        r = A.corrigir(self.prova, responder_certo(self.prova, self.erros_em({"T1": 1, "T2": 1, "T3": 1, "T4": 1})))
        self.assertEqual((r.acertos, r.aprovado), (16, True))

    def test_b7_15_de_20_reprova_pela_nota(self):
        r = A.corrigir(self.prova, responder_certo(self.prova, self.erros_em({"T1": 1, "T2": 1, "T3": 1, "T4": 1, "T5": 1})))
        self.assertEqual((r.acertos, r.aprovado), (15, False))
        self.assertTrue(any("80%" in m for m in r.motivos))

    def test_b7_16_de_20_com_um_tema_em_1_de_4_reprova_pelo_tema(self):
        r = A.corrigir(self.prova, responder_certo(self.prova, self.erros_em({"T3": 3, "T1": 1})))
        self.assertEqual(r.acertos, 16)
        self.assertEqual(r.por_tema["T3"], (1, 4))
        self.assertFalse(r.aprovado)
        self.assertEqual(len(r.motivos), 1)
        self.assertIn("T3", r.motivos[0])

    def test_2_de_4_em_cada_tema_e_o_limite(self):
        r = A.corrigir(self.prova, responder_certo(self.prova, self.erros_em({"T3": 2})))
        self.assertEqual((r.acertos, r.aprovado), (18, True))

    def test_em_branco_conta_como_errada(self):
        respostas = responder_certo(self.prova)
        del respostas[self.prova.itens[0].id]
        respostas[self.prova.itens[1].id] = None
        r = A.corrigir(self.prova, respostas)
        self.assertEqual((r.acertos, r.em_branco), (18, 2))
        marcadas = {e.id: e.marcada for e in r.erradas}
        self.assertIsNone(marcadas[self.prova.itens[0].id])

    def test_erradas_trazem_explicacao_e_destino_de_revisao(self):
        alvo = self.prova.itens[3]
        r = A.corrigir(self.prova, responder_certo(self.prova, {alvo.id}))
        e = r.erradas[0]
        self.assertEqual((e.id, e.correta, e.revisar), (alvo.id, alvo.correta, (1, 2)))
        self.assertIn("Explicação", e.explicacao)
        self.assertNotEqual(e.marcada, e.correta)

    def test_por_tema_soma_o_total(self):
        r = A.corrigir(self.prova, responder_certo(self.prova, self.erros_em({"T2": 2, "T5": 1})))
        self.assertEqual(sum(a for a, _ in r.por_tema.values()), r.acertos)
        self.assertEqual(sum(n for _, n in r.por_tema.values()), r.total)

    def test_respostas_invalidas_sao_erro_de_quem_chama(self):
        item = self.prova.itens[0]
        for ruim in (len(item.opcoes), -1, "1", 1.0, True):
            with self.assertRaises(ValueError, msg=repr(ruim)):
                A.corrigir(self.prova, {item.id: ruim})
        with self.assertRaises(ValueError):
            A.corrigir(self.prova, {"X-99": 0})

    def test_faixas(self):
        self.assertEqual(A.faixa(3, 4), "dominado")
        self.assertEqual(A.faixa(2, 4), "revisar")
        self.assertEqual(A.faixa(1, 4), "refazer")
        self.assertEqual(A.faixa(0, 0), "refazer")


class TestNivelamento(unittest.TestCase):
    def setUp(self):
        self.prova = A.sortear_nivelamento(3, banco=BANCO)

    def test_b8_nunca_reprova_nem_aprova(self):
        for erros in ([], [i.id for i in self.prova.itens]):
            r = A.corrigir(self.prova, responder_certo(self.prova, erros))
            self.assertIsNone(r.aprovado)
            self.assertEqual(r.motivos, ())

    def test_recomenda_a_primeira_licao_com_menos_de_75_por_cento(self):
        ids = lambda t: [i.id for i in self.prova.itens if i.tema == t]
        r = A.corrigir(self.prova, responder_certo(self.prova))
        self.assertIsNone(A.recomendar_licao(r))                # acertou tudo: pode ir à final
        r = A.corrigir(self.prova, responder_certo(self.prova, ids("T4") + ids("T5")))
        self.assertEqual(A.recomendar_licao(r), 2)              # Lição 1 (T1 a T3) dominada, Lição 2 não
        r = A.corrigir(self.prova, responder_certo(self.prova, ids("T5")))
        self.assertEqual(A.recomendar_licao(r), 3)
        r = A.corrigir(self.prova, responder_certo(self.prova, ids("T1") + ids("T2") + ids("T3")))
        self.assertEqual(A.recomendar_licao(r), 1)


class TestNomeECodigo(unittest.TestCase):
    def test_b13_validar_nome(self):
        self.assertEqual(A.validar_nome("  Maria   Exemplo \n"), "Maria Exemplo")
        self.assertEqual(A.validar_nome("Maria\x00 Ex\x07emplo"), "Maria Exemplo")
        self.assertEqual(A.validar_nome("José d'Ávila"), "José d'Ávila")
        for ruim, msg in (("", "pelo menos"), ("ab", "pelo menos"), (" a ", "pelo menos"), ("x" * 81, "no máximo"), ("123 456", "letras"),
                          ("\x00\x01\x02\x03", "pelo menos")):
            with self.assertRaisesRegex(ValueError, msg, msg=repr(ruim)):
                A.validar_nome(ruim)
        self.assertEqual(len(A.validar_nome("x" * 80)), 80)

    def test_b11_codigo_estavel_e_sensivel_a_cada_campo(self):
        base = ("Maria Exemplo", "2026-10-25", 85.0, "0.1", "1.1", 123)
        c = A.codigo_conferencia(*base)
        self.assertRegex(c, r"^[0-9A-F]{12}$")
        self.assertEqual(c, A.codigo_conferencia(*base))
        self.assertEqual(c, A.codigo_conferencia("  Maria   Exemplo ", *base[1:]))      # nome normalizado
        variacoes = [("Maria Exemplos",) + base[1:], (base[0], "2026-10-26") + base[2:], base[:2] + (80.0,) + base[3:],
                     base[:3] + ("0.2",) + base[4:], base[:4] + ("1.2",) + base[5:], base[:5] + (124,)]
        for v in variacoes:
            self.assertNotEqual(c, A.codigo_conferencia(*v), v)

    def test_codigo_recusa_nome_invalido(self):
        with self.assertRaises(ValueError):
            A.codigo_conferencia("a", "2026-10-25", 85.0, "0.1", "1.1", 1)


class TestProgressoDeProvas(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.caminho = Path(self._tmp.name) / "p.json"

    def tearDown(self):
        self._tmp.cleanup()

    def test_registra_sem_nome_e_sobrevive_a_recarregar(self):
        p = Progresso(self.caminho)
        p.registrar_prova("final", 7, 17, 20, True, {"T1": (4, 4), "T2": (3, 4)}, "2026-10-25")
        q = Progresso(self.caminho)
        self.assertEqual(q.dados["provas"], [{"tipo": "final", "semente": 7, "acertos": 17, "total": 20, "aprovado": True,
                                              "por_tema": {"T1": [4, 4], "T2": [3, 4]}, "data": "2026-10-25"}])
        bruto = self.caminho.read_text(encoding="utf-8")
        self.assertNotIn("nome", bruto)

    def test_mantem_so_as_ultimas_20(self):
        p = Progresso(self.caminho)
        for i in range(25):
            p.registrar_prova("nivelamento", i, 5, 10, None, {"T1": (1, 2)}, "2026-10-25")
        self.assertEqual([x["semente"] for x in Progresso(self.caminho).dados["provas"]], list(range(5, 25)))

    def test_resumo_malformado_e_recusado_e_o_do_arquivo_e_descartado(self):
        p = Progresso(self.caminho)
        for args in (("outro", 1, 1, 2, None, {}, "x"), ("final", 1, 3, 2, None, {}, "x"), ("final", 1, 1, 0, None, {}, "x"),
                     ("final", "1", 1, 2, None, {}, "x"), ("final", 1, 1, 2, "sim", {}, "x"), ("final", 1, 1, 2, None, {"T1": (3, 2)}, "x")):
            with self.assertRaises(ValueError, msg=repr(args)):
                p.registrar_prova(*args)
        self.caminho.write_text(json.dumps({"provas": [{"tipo": "final"}, "lixo", {"tipo": "final", "semente": 1, "acertos": 1, "total": 2,
                                                                                     "aprovado": None, "por_tema": {"T1": [1, 2]}, "data": "d"}]}),
                                encoding="utf-8")
        self.assertEqual(len(Progresso(self.caminho).dados["provas"]), 1)


if __name__ == "__main__":
    unittest.main()
