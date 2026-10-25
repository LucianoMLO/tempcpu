"""Laboratório: levantamento do que o computador já tem (sem rede, sem instalar) e uso de um Python existente."""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import laboratorio as lab
from laboratorio import Achado, Decisao

FIX = {"numpy": "2.5.4", "scipy": "1.18.1", "scikit-learn": "1.9.1"}


def sonda(py=(3, 14, 3), bits=64, tk=True, numpy="2.5.4", scipy="1.18.1", sk="1.9.1", prefixo="X"):
    return {"versao": list(py), "bits": bits, "tkinter": tk, "prefixo": prefixo,
            "pacotes": {"numpy": numpy, "scipy": scipy, "scikit-learn": sk}}


class ParsePy0p(unittest.TestCase):
    def test_formato_novo_e_antigo(self):
        texto = ("Installed Pythons found by py Launcher for Windows\n"
                 " -V:3.14[-64] *   C:\\Py\\pythoncore-3.14-64\\python.exe\n"
                 " -V:3.12          C:\\Py\\Python312\\python.exe\n"
                 " -3.11-64        C:\\Py\\Python311\\python.exe *\n"
                 " -V:Foo/Bar       C:\\Outro\\py.exe\n"
                 "lixo sem traço\n")
        self.assertEqual([str(p) for p in lab.parse_py_0p(texto)], [
            "C:\\Py\\pythoncore-3.14-64\\python.exe", "C:\\Py\\Python312\\python.exe",
            "C:\\Py\\Python311\\python.exe", "C:\\Outro\\py.exe"])

    def test_vazio_e_sem_python(self):
        self.assertEqual(lab.parse_py_0p(""), [])
        self.assertEqual(lab.parse_py_0p("No installed Pythons found!\n"), [])

    def test_parse_versao(self):
        self.assertEqual(lab.parse_versao("2.5.4"), (2, 5, 4))
        self.assertEqual(lab.parse_versao("1.26.0rc1"), (1, 26, 0))
        self.assertLess(lab.parse_versao("1.9.1"), lab.parse_versao("1.10"))   # não é comparação de texto
        self.assertEqual(lab.parse_versao("abc"), ())


class Limites(unittest.TestCase):
    def pronto(self, **kw):
        return lab.avaliar_sonda(sonda(**kw), FIX).pronto

    def test_aceita_o_testado(self):
        a = lab.avaliar_sonda(sonda(), FIX)
        self.assertTrue(a.pronto)
        self.assertFalse(a.divergente)
        self.assertEqual(a.python, "3.14.3")

    def test_python(self):
        self.assertFalse(self.pronto(py=(3, 9, 18)))
        self.assertTrue(self.pronto(py=(3, 10, 0)))
        self.assertFalse(self.pronto(bits=32))

    def test_tkinter(self):
        self.assertFalse(self.pronto(tk=False))

    def test_numpy(self):
        self.assertFalse(self.pronto(numpy="1.25.2"))
        self.assertTrue(self.pronto(numpy="1.26.0"))
        self.assertFalse(self.pronto(numpy=None))

    def test_scipy(self):
        self.assertFalse(self.pronto(scipy="1.10.1"))
        self.assertTrue(self.pronto(scipy="1.11.0"))

    def test_sklearn(self):
        self.assertFalse(self.pronto(sk="1.3.2"))
        self.assertTrue(self.pronto(sk="1.4.0"))
        self.assertFalse(self.pronto(sk=None))

    def test_texto_diz_o_que_falta(self):
        a = lab.avaliar_sonda(sonda(numpy="1.25.0", sk=None, tk=False), FIX)
        d = {n: (e, t) for n, e, t in a.itens}
        self.assertEqual(d["numpy"][0], "antiga")
        self.assertIn("1.25.0", d["numpy"][1])
        self.assertIn("1.26", d["numpy"][1])
        self.assertEqual(d["scikit-learn"], ("ausente", "ausente"))
        self.assertEqual(d["tkinter"][0], "ausente")
        self.assertEqual(d["Python"][0], "ok")

    def test_versoes_diferentes_das_testadas_avisam(self):
        self.assertTrue(lab.avaliar_sonda(sonda(sk="1.8.0"), FIX).divergente)
        self.assertTrue(lab.avaliar_sonda(sonda(py=(3, 12, 1)), FIX).divergente)
        self.assertFalse(lab.avaliar_sonda(sonda(py=(3, 14, 9)), FIX).divergente)   # só maior.menor conta
        self.assertIn("1.9.1", lab.aviso_divergente(FIX))
        self.assertIn("variar", lab.aviso_divergente(FIX))

    def test_resposta_com_erro(self):
        for info in ({"erro": "não respondeu em 15 s"}, None, {}, "x"):
            a = lab.avaliar_sonda(info, FIX)
            self.assertFalse(a.pronto)
            self.assertEqual(a.itens[0][1], "erro")

    def test_versoes_fixadas_do_arquivo_real(self):
        f = lab.versoes_fixadas()
        self.assertEqual(f["scikit-learn"], "1.9.1")
        self.assertEqual(f["numpy"], "2.5.4")


class Sonda(unittest.TestCase):
    def fake(self, stdout="", erro=None):
        def rodar(py, timeout):
            if erro:
                raise erro
            return subprocess.CompletedProcess([str(py)], 0, stdout, "")
        return rodar

    def test_le_o_json_da_ultima_linha_SONDA(self):
        saida = "aviso qualquer\nSONDA=" + json.dumps(sonda()) + "\n"
        self.assertEqual(lab.sondar_interpretador(Path("p.exe"), self.fake(saida))["bits"], 64)

    def test_timeout_oserror_e_lixo(self):
        r = lab.sondar_interpretador(Path("p.exe"), self.fake(erro=subprocess.TimeoutExpired("p", 15)))
        self.assertIn("15", r["erro"])
        self.assertIn("erro", lab.sondar_interpretador(Path("p.exe"), self.fake(erro=FileNotFoundError(2, "sumiu"))))
        self.assertIn("erro", lab.sondar_interpretador(Path("p.exe"), self.fake("nada util")))
        self.assertIn("erro", lab.sondar_interpretador(Path("p.exe"), self.fake("SONDA={quebrado")))

    def test_sonda_nao_usa_isolamento_e_nao_importa_pacotes_pesados(self):
        with mock.patch.object(lab.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "", "")) as r:
            lab._rodar_sonda(Path("p.exe"), 15)
        cmd = r.call_args.args[0]
        self.assertEqual(cmd[0], "p.exe")
        self.assertNotIn("-I", cmd)                         # sem isolamento: enxerga pacotes instalados com --user
        self.assertEqual(r.call_args.kwargs["timeout"], 15)
        self.assertEqual(r.call_args.kwargs["creationflags"], lab.SEM_JANELA)
        for pesado in ("import numpy", "import scipy", "import sklearn"):
            self.assertNotIn(pesado, lab.SONDA_CODIGO)

    def test_sonda_de_verdade_no_python_do_app(self):
        """Sonda real, local: o venv do app não tem numpy/scipy/sklearn e deve ser recusado dizendo o que falta."""
        info = lab.sondar_interpretador(Path(sys.executable))
        a = lab.avaliar_sonda(info, FIX)
        self.assertEqual(info["versao"][:2], list(sys.version_info[:2]))
        self.assertTrue(info["tkinter"])
        self.assertFalse(a.pronto)
        faltando = {n for n, e, _t in a.itens if e != "ok"}
        self.assertEqual(faltando, {"numpy", "scipy", "scikit-learn"})

    def test_sonda_de_verdade_no_ambiente_de_desenvolvimento_do_lab(self):
        py = lab.pasta_app() / ".venv-lab" / "Scripts" / "python.exe"
        if not py.is_file():
            self.skipTest("sem .venv-lab nesta máquina")
        a = lab.avaliar_sonda(lab.sondar_interpretador(py), lab.versoes_fixadas())
        self.assertTrue(a.pronto, a.itens)


class Candidatos(unittest.TestCase):
    def test_junta_sem_repetir_e_ignora_inexistentes(self):
        py0p = ("-V:3.14[-64] *  C:\\A\\python.exe\n-V:3.12  C:\\B\\python.exe\n-V:3.11  C:\\Falta\\python.exe\n")
        existe = lambda p: "Falta" not in str(p)  # noqa: E731
        r = lab.candidatos(lambda: py0p, Path("c:\\a\\PYTHON.exe"), "C:\\C\\python.exe", existe)
        self.assertEqual([str(p) for p in r], ["C:\\A\\python.exe", "C:\\B\\python.exe", "C:\\C\\python.exe"])

    def test_sem_nada(self):
        self.assertEqual(lab.candidatos(lambda: "", Path("nao-existe.exe"), "", lambda p: False), [])

    def test_levantar_junta_o_mesmo_python_por_dois_caminhos(self):
        infos = {"a.exe": sonda(prefixo="C:\\P"), "b.exe": sonda(prefixo="c:\\p"), "c.exe": sonda(prefixo="C:\\Q")}
        r = lab.levantar(lambda p: infos[p.name], [Path("a.exe"), Path("b.exe"), Path("c.exe")], FIX)
        self.assertEqual([a.caminho.name for a in r], ["a.exe", "c.exe"])

    def test_escolha_do_melhor(self):
        mk = lambda n, **kw: Achado(Path(n), sonda(**kw), lab.avaliar_sonda(sonda(**kw), FIX))  # noqa: E731
        a = [mk("velho.exe", py=(3, 12, 0)), mk("div.exe", sk="1.8.0"), mk("exato.exe"), mk("falta.exe", sk=None)]
        self.assertEqual(lab.melhor_pronto(a).caminho.name, "exato.exe")        # versões testadas primeiro
        self.assertEqual(lab.melhor_pronto([a[0], a[1]]).caminho.name, "div.exe")  # depois o Python mais novo
        self.assertIsNone(lab.melhor_pronto([a[3]]))
        self.assertEqual(lab.melhor_parcial([a[3]]).caminho.name, "falta.exe")
        self.assertIsNone(lab.melhor_parcial([]))


class Escolha(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.arq = Path(self.tmp.name) / "lab" / "interpretador.json"

    def test_ida_e_volta(self):
        self.assertTrue(lab.gravar_escolha(self.arq, Path("C:\\Py\\python.exe"), {"numpy": "2.5.4"}))
        self.assertEqual(lab.ler_escolha(self.arq), {"python": "C:\\Py\\python.exe", "versoes": {"numpy": "2.5.4"}})

    def test_ausente_e_corrompido(self):
        self.assertIsNone(lab.ler_escolha(self.arq))
        self.arq.parent.mkdir(parents=True)
        for ruim in ("{quebrado", "[]", "{}", '{"python": 5}', '{"python": ""}', "", "\x00\x01"):
            self.arq.write_text(ruim, encoding="utf-8")
            self.assertIsNone(lab.ler_escolha(self.arq), ruim)

    def test_esquecer_apaga_so_o_json(self):
        py = Path(self.tmp.name) / "python.exe"
        py.write_bytes(b"")
        lab.gravar_escolha(self.arq, py, {})
        self.assertTrue(lab.esquecer_escolha(self.arq))
        self.assertFalse(self.arq.exists())
        self.assertTrue(py.exists())
        self.assertFalse(lab.esquecer_escolha(self.arq))   # já não existe: sem erro


class Decidir(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pasta = Path(self.tmp.name) / "lab-env"
        self.arq = Path(self.tmp.name) / "lab" / "interpretador.json"
        self.sondadas: list[str] = []
        self.infos = {"bom.exe": sonda(prefixo="A"), "sem.exe": sonda(sk=None, numpy=None, scipy=None, prefixo="B")}

    def sondar(self, p):
        self.sondadas.append(p.name)
        return self.infos.get(p.name, {"erro": "sumiu"})

    def d(self, cands):
        return lab.decidir(self.pasta, self.arq, self.sondar, lambda: [Path(c) for c in cands], FIX)

    def test_a_ambiente_proprio_pronto_nao_sonda_nada(self):
        (self.pasta / "Scripts").mkdir(parents=True)
        lab.pythonw_do_ambiente(self.pasta).write_bytes(b"")
        (self.pasta / lab.MARCADOR).write_text(lab.PRONTO, encoding="utf-8")
        self.assertEqual(self.d(["bom.exe"]).tipo, "ambiente")
        self.assertEqual(self.sondadas, [])

    def test_b_existente_e_oferecido(self):
        r = self.d(["sem.exe", "bom.exe"])
        self.assertEqual((r.tipo, r.python.name), ("oferecer", "bom.exe"))
        self.assertEqual(len(r.achados), 2)
        self.assertFalse(self.arq.exists())          # só grava depois da escolha do usuário

    def test_c_nada_serve_vai_para_o_preparo_com_lista(self):
        r = self.d(["sem.exe"])
        self.assertEqual(r.tipo, "preparar")
        self.assertIsNone(r.python)
        self.assertEqual(r.achados[0].caminho.name, "sem.exe")
        self.assertEqual(self.d([]).tipo, "preparar")

    def test_escolha_anterior_valida_abre_sem_procurar(self):
        lab.gravar_escolha(self.arq, Path("bom.exe"), {})
        r = self.d(["sem.exe"])
        self.assertEqual((r.tipo, r.python.name), ("existente", "bom.exe"))
        self.assertEqual(self.sondadas, ["bom.exe"])   # revalidou só ela

    def test_revalidacao_que_falha_volta_a_perguntar_e_esquece(self):
        lab.gravar_escolha(self.arq, Path("sumiu.exe"), {})
        r = self.d(["bom.exe"])
        self.assertEqual(r.tipo, "oferecer")
        self.assertFalse(self.arq.exists())

    def test_escolha_que_perdeu_o_sklearn(self):
        lab.gravar_escolha(self.arq, Path("sem.exe"), {})
        self.assertEqual(self.d([]).tipo, "preparar")
        self.assertFalse(self.arq.exists())

    def test_json_corrompido_e_ignorado(self):
        self.arq.parent.mkdir(parents=True)
        self.arq.write_text("{lixo", encoding="utf-8")
        self.assertEqual(self.d(["bom.exe"]).tipo, "oferecer")


class Menu:
    def __init__(self):
        self.itens = []

    def add_command(self, label, state="normal", command=None):
        self.itens.append((label, state))


class TelasEFluxo(unittest.TestCase):
    """acionar/Dialogo com fakes nos três caminhos. Precisa de tkinter com tela."""

    def setUp(self):
        import tkinter as tk
        try:
            self.raiz = tk.Tk()
        except tk.TclError:
            self.skipTest("sem tela para o tkinter")
        self.raiz.withdraw()
        self.addCleanup(self.raiz.destroy)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env = Path(self.tmp.name) / "lab-env"
        p = mock.patch.dict(os.environ, {lab.VAR_AMBIENTE: str(self.env)})
        p.start()
        self.addCleanup(p.stop)
        self.abertos: list = []
        self.fechou: list = []

    def abrir(self, raiz, pasta=None, python=None):
        self.abertos.append(python)
        return True

    def bombear(self, ate, d=None, segundos=5):
        fim = time.monotonic() + segundos
        while time.monotonic() < fim:
            self.raiz.update()
            if ate():
                return
            time.sleep(0.02)
        self.fail("a tela não chegou ao estado esperado")

    def botao(self, d, texto):
        def achar(w):
            for f in w.winfo_children():
                if f.winfo_class() == "Button" and texto in f.cget("text"):
                    return f
                r = achar(f)
                if r:
                    return r
        b = achar(d.corpo)
        self.assertIsNotNone(b, f"sem botão {texto!r}")
        return b

    def textos(self, d):
        def todos(w):
            for f in w.winfo_children():
                if f.winfo_class() in ("Label", "Button"):
                    yield f.cget("text")
                yield from todos(f)
        return "\n".join(todos(d.corpo))

    def test_a_ambiente_pronto_abre_direto_sem_janela(self):
        (self.env / "Scripts").mkdir(parents=True)
        lab.pythonw_do_ambiente(self.env).write_bytes(b"")
        (self.env / lab.MARCADOR).write_text(lab.PRONTO, encoding="utf-8")
        self.assertIsNone(lab.acionar(self.raiz, lambda: None, abrir=self.abrir))
        self.assertEqual(self.abertos, [None])

    def test_b_oferta_usar_existente_grava_escolha_e_nao_instala(self):
        bom = Achado(Path("C:\\Py\\python.exe"), sonda(sk="1.8.0"), lab.avaliar_sonda(sonda(sk="1.8.0"), FIX))
        dec = Decisao("oferecer", bom.caminho, bom, [bom])
        d = lab.acionar(self.raiz, lambda: self.fechou.append(1), decidir_fn=lambda: dec, abrir=self.abrir)
        self.assertEqual(d.tela, "verificando")
        self.bombear(lambda: d.tela == "oferta")
        t = self.textos(d)
        self.assertIn("Encontrei o Python 3.14.3", t)
        self.assertIn("Usar sem instalar nada?", t)
        self.assertIn("podem variar", t)                    # versões diferentes das testadas
        self.assertIn("Usar o que já tem (recomendado)", t)
        self.assertIn("Instalar um ambiente separado", t)
        self.botao(d, "Usar o que já tem").invoke()
        self.assertEqual(self.abertos, [Path("C:\\Py\\python.exe")])
        self.assertIsNone(d.preparo)                        # nada de download/instalação
        self.assertEqual(lab.ler_escolha(lab.arquivo_escolha())["python"], "C:\\Py\\python.exe")
        self.assertEqual(self.fechou, [1])
        self.assertFalse(self.env.exists())

    def test_b_oferta_agora_nao_nao_grava_nada(self):
        bom = Achado(Path("C:\\Py\\python.exe"), sonda(), lab.avaliar_sonda(sonda(), FIX))
        d = lab.acionar(self.raiz, lambda: self.fechou.append(1), lambda: Decisao("oferecer", bom.caminho, bom, [bom]),
                        self.abrir)
        self.bombear(lambda: d.tela == "oferta")
        self.assertNotIn("podem variar", self.textos(d))
        self.botao(d, "Agora não").invoke()
        self.assertEqual((self.abertos, self.fechou), ([], [1]))
        self.assertFalse(lab.arquivo_escolha().exists())

    def test_b_oferta_instalar_separado_vai_para_a_confirmacao(self):
        bom = Achado(Path("C:\\Py\\python.exe"), sonda(), lab.avaliar_sonda(sonda(), FIX))
        d = lab.acionar(self.raiz, lambda: None, lambda: Decisao("oferecer", bom.caminho, bom, [bom]), self.abrir)
        self.bombear(lambda: d.tela == "oferta")
        self.botao(d, "Instalar um ambiente separado").invoke()
        self.assertEqual(d.tela, "confirmacao")
        self.assertIsNone(d.preparo)                        # só instala depois de "Preparar Laboratório"

    def test_b_escolha_anterior_valida_abre_e_fecha_sozinha(self):
        p = Path("C:\\Py\\python.exe")
        ach = Achado(p, sonda(), lab.avaliar_sonda(sonda(), FIX))
        d = lab.acionar(self.raiz, lambda: self.fechou.append(1), lambda: Decisao("existente", p, ach), self.abrir)
        self.bombear(lambda: self.fechou)
        self.assertEqual(self.abertos, [p])

    def test_c_confirmacao_lista_o_que_existe_e_o_que_sera_instalado(self):
        sem = sonda(sk=None, numpy="1.25.0", scipy=None, tk=False)
        ach = Achado(Path("C:\\Py\\python.exe"), sem, lab.avaliar_sonda(sem, FIX))
        d = lab.acionar(self.raiz, lambda: None, lambda: Decisao("preparar", None, None, [ach]), self.abrir)
        self.bombear(lambda: d.tela == "confirmacao")
        t = self.textos(d)
        self.assertIn("O que já existe no seu computador", t)
        self.assertIn("numpy: versão antiga (1.25.0", t)
        self.assertIn("scikit-learn: ausente", t)
        self.assertIn("tkinter: ausente", t)
        self.assertIn("O que será instalado", t)
        self.assertIn("240 MB", t)
        self.assertIn("Espaço livre no disco", t)
        self.assertIn(str(self.env), t)
        self.assertIn("Preparar Laboratório", t)
        self.assertIsNone(d.preparo)
        self.assertFalse(self.env.exists())                 # nada criado antes da confirmação

    def test_c_sem_python_nenhum(self):
        d = lab.acionar(self.raiz, lambda: None, lambda: Decisao("preparar"), self.abrir)
        self.bombear(lambda: d.tela == "confirmacao")
        self.assertIn("Python: não encontrado", self.textos(d))

    def test_falha_na_verificacao_cai_na_confirmacao(self):
        def quebra():
            raise RuntimeError("falha qualquer")
        d = lab.acionar(self.raiz, lambda: None, quebra, self.abrir)
        self.bombear(lambda: d.tela == "confirmacao")

    def test_menu_oferece_esquecer_so_com_escolha(self):
        m = Menu()
        lab.montar_menu(m, self.raiz)
        self.assertEqual([i[0] for i in m.itens], ["Remover Laboratório…"])
        self.assertEqual(m.itens[0][1], "disabled")
        lab.gravar_escolha(lab.arquivo_escolha(), Path("C:\\Py\\python.exe"), {})
        m = Menu()
        lab.montar_menu(m, self.raiz)
        self.assertEqual([i[0] for i in m.itens], ["Remover Laboratório…", "Esquecer o Python escolhido"])


class AbrirComPythonExistente(unittest.TestCase):
    def test_comando_usa_pythonw_ao_lado(self):
        with tempfile.TemporaryDirectory() as d:
            py = Path(d) / "python.exe"
            py.write_bytes(b"")
            self.assertEqual(lab.comando_abrir_com(py), [str(py), "-m", "lab"])   # sem pythonw: o próprio
            (Path(d) / "pythonw.exe").write_bytes(b"")
            self.assertEqual(lab.comando_abrir_com(py), [str(Path(d) / "pythonw.exe"), "-m", "lab"])


if __name__ == "__main__":
    unittest.main()
