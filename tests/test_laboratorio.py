"""Launcher do Laboratório: lógica pura, máquina de estados e limpeza (sem rede e sem instalar nada)."""
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

import laboratorio as lab
from laboratorio import AUSENTE, FALHOU, MARCADOR, PREPARANDO, PRONTO, Preparo

OK_PY = lambda: ""  # noqa: E731  (Python suportado)


class Caminhos(unittest.TestCase):
    def test_variavel_de_ambiente_sobrescreve(self):
        self.assertEqual(lab.pasta_ambiente({lab.VAR_AMBIENTE: r"X:\teste\env"}), Path(r"X:\teste\env"))

    def test_padrao_em_localappdata(self):
        p = lab.pasta_ambiente({"LOCALAPPDATA": r"C:\Dados"})
        self.assertEqual(p, Path(r"C:\Dados") / "TempCPU" / "lab-env")

    def test_executaveis_do_ambiente(self):
        p = Path(r"C:\env")
        self.assertEqual(lab.pythonw_do_ambiente(p), p / "Scripts" / "pythonw.exe")
        self.assertEqual(lab.python_do_ambiente(p), p / "Scripts" / "python.exe")


class Comandos(unittest.TestCase):
    def test_instalacao_exige_hashes_e_so_binarios(self):
        cmd = lab.comando_instalar(Path("py.exe"), Path("req.txt"))
        self.assertIn("--require-hashes", cmd)
        self.assertIn("--only-binary=:all:", cmd)
        self.assertEqual(cmd[cmd.index("-r") + 1], "req.txt")

    def test_abrir_usa_pythonw_e_modulo_lab(self):
        cmd = lab.comando_abrir(Path(r"C:\env"))
        self.assertTrue(cmd[0].endswith("pythonw.exe"))
        self.assertEqual(cmd[1:], ["-m", "lab"])

    def test_verificacao_importa_sklearn_e_tkinter(self):
        self.assertIn("import sklearn, tkinter", lab.comando_verificar(Path("py.exe")))

    def test_venv_vem_do_python_base(self):
        self.assertEqual(lab.comando_criar_venv(Path("base.exe"), Path("env"))[:3], ["base.exe", "-m", "venv"])

    def test_requisitos_fixados_com_hash(self):
        linhas = [ln for ln in lab.arquivo_requisitos().read_text(encoding="utf-8").splitlines()
                  if ln and not ln.startswith("#")]
        pacotes = [ln for ln in linhas if "==" in ln]
        self.assertGreaterEqual(len(pacotes), 5)
        texto = "\n".join(linhas)
        self.assertEqual(texto.count("--hash=sha256:"), len(pacotes))
        for nome in ("scikit-learn==1.9.1", "numpy==2.5.4", "scipy==1.18.1", "joblib", "threadpoolctl"):
            self.assertIn(nome, texto)


class PythonSuportado(unittest.TestCase):
    def test_3_14_64_bits_serve(self):
        self.assertEqual(lab.motivo_python_nao_suportado((3, 14, 3), 64, "win32", False), "")

    def test_outra_versao_recebe_mensagem_clara(self):
        m = lab.motivo_python_nao_suportado((3, 12, 1), 64, "win32", False)
        self.assertIn("3.14", m)
        self.assertIn("3.12", m)

    def test_32_bits_e_outro_sistema_e_empacotado(self):
        self.assertTrue(lab.motivo_python_nao_suportado((3, 14, 0), 32, "win32", False))
        self.assertTrue(lab.motivo_python_nao_suportado((3, 14, 0), 64, "linux", False))
        self.assertIn("empacotado", lab.motivo_python_nao_suportado((3, 14, 0), 64, "win32", True))


class ErrosDoPip(unittest.TestCase):
    def test_classificacao(self):
        c = lab.classificar_erro_pip
        self.assertIn("internet", c("WARNING: Retrying ... NewConnectionError getaddrinfo failed"))
        self.assertIn("espaço", c("OSError: [Errno 28] No space left on device"))
        self.assertIn("hash", c("THESE PACKAGES DO NOT MATCH THE HASHES FROM THE REQUIREMENTS FILE"))
        self.assertIn("negou", c("PermissionError: [WinError 5] Access is denied"))
        self.assertIn("pip", c("ERROR: algo inesperado\nlinha final do erro"))
        self.assertIn("linha final do erro", c("ERROR: algo inesperado\nlinha final do erro"))


class Estado(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pasta = Path(self.tmp.name) / "env"
        self.addCleanup(self.tmp.cleanup)

    def test_ausente_sem_pasta(self):
        self.assertEqual(lab.estado_ambiente(self.pasta), AUSENTE)

    def test_marcador_em_preparo_e_sobra_de_falha(self):
        self.pasta.mkdir()
        (self.pasta / MARCADOR).write_text(PREPARANDO, encoding="utf-8")
        self.assertEqual(lab.estado_ambiente(self.pasta), FALHOU)

    def test_pronto_exige_marcador_e_executavel(self):
        (self.pasta / "Scripts").mkdir(parents=True)
        (self.pasta / MARCADOR).write_text(PRONTO, encoding="utf-8")
        self.assertEqual(lab.estado_ambiente(self.pasta), FALHOU)  # sem pythonw.exe
        lab.pythonw_do_ambiente(self.pasta).write_bytes(b"")
        self.assertEqual(lab.estado_ambiente(self.pasta), PRONTO)

    def test_remover_so_apaga_pasta_nossa(self):
        self.pasta.mkdir()
        (self.pasta / "dados.txt").write_text("importante", encoding="utf-8")
        self.assertIn("nada foi apagado", lab.remover_pasta(self.pasta))
        self.assertTrue((self.pasta / "dados.txt").exists())
        (self.pasta / MARCADOR).write_text(PRONTO, encoding="utf-8")
        self.assertEqual(lab.remover_pasta(self.pasta), "")
        self.assertFalse(self.pasta.exists())

    def test_remover_pasta_inexistente_e_ok(self):
        self.assertEqual(lab.remover_pasta(self.pasta), "")


class MaquinaDePreparo(unittest.TestCase):
    """Fakes no lugar do venv/pip: `executar` registra o comando e simula o resultado de cada etapa."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pasta = Path(self.tmp.name) / "lab-env"
        self.req = Path(self.tmp.name) / "req.txt"
        self.req.write_text("x==1\n", encoding="utf-8")
        self.cmds: list[list[str]] = []
        self.eventos: list[tuple] = []

    def preparo(self, resultados, livre=10**12, motivo=OK_PY, base=Path("base.exe"), reqs=None):
        resultados = list(resultados)

        def executar(cmd, cancelado):
            self.cmds.append(cmd)
            r = resultados.pop(0)
            if callable(r):
                r = r(cmd)
            if cmd[1:3] == ["-m", "venv"]:      # o venv de mentira cria a pasta com um arquivo dentro
                (self.pasta / "Scripts").mkdir(parents=True, exist_ok=True)
            return r

        return Preparo(self.pasta, base, reqs or self.req, executar=executar, livre=lambda _p: livre,
                       ao_evento=lambda t, d: self.eventos.append((t, d)), motivo_python=motivo)

    def test_caminho_feliz(self):
        p = self.preparo([(0, ""), (0, ""), (0, "")])
        self.assertEqual(p.executar(), PRONTO)
        self.assertEqual(len(self.cmds), 3)
        self.assertIn("--require-hashes", self.cmds[1])
        self.assertIn("import sklearn, tkinter", self.cmds[2])
        self.assertEqual((self.pasta / MARCADOR).read_text(encoding="utf-8"), PRONTO)
        self.assertEqual([e[0] for e in self.eventos], ["etapa", "etapa", "etapa", "fim"])

    def test_falha_do_pip_limpa_a_pasta_e_explica(self):
        p = self.preparo([(0, ""), (1, "WARNING: Retrying: NewConnectionError getaddrinfo failed"), ])
        self.assertEqual(p.executar(), FALHOU)
        self.assertIn("internet", p.mensagem)
        self.assertFalse(self.pasta.exists())
        self.assertEqual(len(self.cmds), 2)

    def test_falha_na_verificacao_limpa_a_pasta(self):
        p = self.preparo([(0, ""), (0, ""), (1, "ModuleNotFoundError: No module named 'tkinter'")])
        self.assertEqual(p.executar(), FALHOU)
        self.assertIn("verificação", p.mensagem)
        self.assertFalse(self.pasta.exists())

    def test_falha_ao_criar_venv(self):
        p = self.preparo([(1, "erro ao criar")])
        self.assertEqual(p.executar(), FALHOU)
        self.assertFalse(self.pasta.exists())

    def test_cancelar_durante_a_instalacao_volta_a_ausente_sem_pasta(self):
        def cancelando(_cmd):
            p.cancelar()
            return (-1, "cancelado")
        p = self.preparo([(0, ""), cancelando])
        self.assertEqual(p.executar(), AUSENTE)
        self.assertIn("Cancelado", p.mensagem)
        self.assertFalse(self.pasta.exists())
        self.assertEqual(lab.estado_ambiente(self.pasta), AUSENTE)

    def test_cancelar_antes_de_comecar_etapa(self):
        p = self.preparo([(0, "")])
        p.cancelar()
        self.assertEqual(p.executar(), AUSENTE)
        self.assertEqual(self.cmds, [])
        self.assertFalse(self.pasta.exists())

    def test_sem_espaco_nao_cria_nada(self):
        p = self.preparo([], livre=10 * 1024 * 1024)
        self.assertEqual(p.executar(), FALHOU)
        self.assertIn("espaço", p.mensagem)
        self.assertFalse(self.pasta.exists())
        self.assertEqual(self.cmds, [])

    def test_python_nao_suportado_nao_cria_nada(self):
        p = self.preparo([], motivo=lambda: "só 3.14")
        self.assertEqual(p.executar(), FALHOU)
        self.assertEqual(p.mensagem, "só 3.14")
        self.assertFalse(self.pasta.exists())

    def test_sem_python_base(self):
        p = self.preparo([], base=None)
        self.assertEqual(p.executar(), FALHOU)
        self.assertFalse(self.pasta.exists())

    def test_requisitos_ausentes(self):
        p = self.preparo([], reqs=Path(self.tmp.name) / "nao-existe.txt")
        self.assertEqual(p.executar(), FALHOU)
        self.assertFalse(self.pasta.exists())

    def test_nao_apaga_pasta_alheia(self):
        self.pasta.mkdir()
        (self.pasta / "meu.txt").write_text("meu", encoding="utf-8")
        p = self.preparo([])
        self.assertEqual(p.executar(), FALHOU)
        self.assertTrue((self.pasta / "meu.txt").exists())
        self.assertEqual(self.cmds, [])

    def test_sobra_de_tentativa_anterior_e_refeita(self):
        self.pasta.mkdir()
        (self.pasta / MARCADOR).write_text(PREPARANDO, encoding="utf-8")
        (self.pasta / "lixo.bin").write_bytes(b"x")
        p = self.preparo([(0, ""), (0, ""), (0, "")])
        self.assertEqual(p.executar(), PRONTO)
        self.assertFalse((self.pasta / "lixo.bin").exists())

    def test_thread_nao_bloqueia_quem_chama(self):
        parar = threading.Event()

        def lento(cmd, cancelado):
            parar.wait(5)
            return (0, "")
        p = Preparo(self.pasta, Path("b.exe"), self.req, executar=lento, livre=lambda _p: 10**12,
                    motivo_python=OK_PY)
        p.iniciar()                      # volta na hora, mesmo com o passo travado
        self.assertEqual(p.estado, PREPARANDO)
        p.cancelar()
        parar.set()
        p._thread.join(5)
        self.assertEqual(p.estado, AUSENTE)
        self.assertFalse(self.pasta.exists())


class ProcessoReal(unittest.TestCase):
    """executar_processo de verdade, com o próprio Python (barato)."""

    def test_codigo_e_saida(self):
        import sys
        codigo, saida = lab.executar_processo([sys.executable, "-c", "print('oi'); raise SystemExit(3)"],
                                              threading.Event())
        self.assertEqual(codigo, 3)
        self.assertIn("oi", saida)

    def test_cancelamento_mata_o_processo(self):
        import sys
        import time
        ev = threading.Event()
        threading.Timer(0.5, ev.set).start()
        t0 = time.monotonic()
        codigo, _ = lab.executar_processo([sys.executable, "-c", "import time; time.sleep(30)"], ev)
        self.assertEqual(codigo, -1)
        self.assertLess(time.monotonic() - t0, 10)


class Revisao(unittest.TestCase):
    """Problemas achados na revisão independente (cada um com seu teste)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.pasta = Path(self.tmp.name) / "lab-env"
        self.req = Path(self.tmp.name) / "req.txt"
        self.req.write_text("x==1\n", encoding="utf-8")

    def preparo(self, executar):
        return Preparo(self.pasta, Path("base.exe"), self.req, executar=executar, livre=lambda _p: 10**12,
                       motivo_python=OK_PY)

    # 1) pasta do ambiente já existe e está vazia
    def test_pasta_vazia_preexistente_nao_atrapalha(self):
        self.pasta.mkdir()

        def ok(cmd, cancelado):
            (self.pasta / "Scripts").mkdir(exist_ok=True)
            return (0, "")
        p = self.preparo(ok)
        self.assertEqual(p.executar(), PRONTO, p.mensagem)
        self.assertTrue((self.pasta / 'Scripts').is_dir())
        self.assertEqual((self.pasta / MARCADOR).read_text(encoding="utf-8"), PRONTO)

    # 2) exceção inesperada (ex.: antivírus negando o Popen) não deixa "preparando" para sempre
    def test_excecao_no_processo_termina_em_falhou_e_limpa(self):
        def nega(cmd, cancelado):
            raise PermissionError(13, "Acesso negado")
        p = self.preparo(nega)
        self.assertEqual(p.executar(), FALHOU)
        self.assertNotEqual(p.estado, PREPARANDO)
        self.assertIn("Acesso negado", p.mensagem)
        self.assertIn("antivírus", p.mensagem)
        self.assertFalse(self.pasta.exists())

    def test_excecao_na_thread_tambem_termina(self):
        def nega(cmd, cancelado):
            raise PermissionError(13, "Acesso negado")
        p = self.preparo(nega)
        eventos = []
        p._evento = lambda t, d: eventos.append(t)
        p.iniciar()
        p._thread.join(10)
        self.assertEqual(p.estado, FALHOU)
        self.assertEqual(eventos[-1], "fim")               # o diálogo recebe o fim e pode fechar
        self.assertFalse(self.pasta.exists())

    def test_excecao_ate_na_limpeza(self):
        def nega(cmd, cancelado):
            raise RuntimeError("boom")
        p = Preparo(self.pasta, Path("b.exe"), self.req, executar=nega, livre=lambda _p: 10**12,
                    remover=lambda _p: (_ for _ in ()).throw(OSError("trava")), motivo_python=OK_PY)
        self.assertEqual(p.executar(), FALHOU)
        self.assertIn("boom", p.mensagem)

    def test_remover_seguro_nunca_levanta(self):
        with mock.patch.object(lab, "remover_pasta", side_effect=PermissionError(13, "Acesso negado")):
            r = lab.remover_seguro(self.pasta)
        self.assertIn("Acesso negado", r)
        self.assertEqual(lab.remover_seguro(self.pasta), "")   # pasta inexistente: ok

    # 3) marcador com bytes inválidos
    def test_marcador_corrompido_nao_levanta(self):
        self.pasta.mkdir()
        (self.pasta / MARCADOR).write_bytes(b"\xff\xfe\x00\x80\x81")
        self.assertEqual(lab.estado_ambiente(self.pasta), AUSENTE)

    def test_processar_pedidos_sobrevive_a_um_pedido_com_erro(self):
        import queue
        import app

        class Rotulo:
            texto = ""

            def config(self, **kw):
                self.texto = kw.get("text", "")

        class Raiz:
            agendados: list = []

            def after(self, ms, fn):
                self.agendados.append((ms, fn))

        class Falso:
            pedidos = queue.Queue()
            raiz = Raiz()
            lbl_gpu = Rotulo()
            chamados: list = []

            def processar_pedidos(self):
                pass

            def abrir_laboratorio(self):
                raise RuntimeError("quebrou")

            def alternar_monitor(self):
                self.chamados.append("monitor")

        f = Falso()
        f.pedidos.put("laboratorio")
        f.pedidos.put("monitor")                           # o pedido seguinte ainda é atendido
        app.App.processar_pedidos(f)
        self.assertEqual(f.chamados, ["monitor"])
        self.assertIn("quebrou", f.lbl_gpu.texto)
        self.assertEqual([ms for ms, _ in f.raiz.agendados], [250])   # reagendou: o laço continua vivo

    # 4) um Laboratório só
    def test_nao_abre_outro_se_o_primeiro_esta_vivo(self):
        class Proc:
            pid = 4321
            codigo = None

            def poll(self):
                return self.codigo

        class Raiz:
            def after(self, ms, fn):
                pass

        proc = Proc()
        with mock.patch.object(lab, "_processo_lab", None), \
                mock.patch.object(lab, "tem_janela_do_laboratorio", return_value=True), \
                mock.patch.object(lab, "abrir_processo", return_value=proc) as abrir, \
                mock.patch.object(lab, "trazer_janela_do_processo", return_value=True) as trazer:
            self.assertTrue(lab.abrir_com_aviso(Raiz(), self.pasta))
            self.assertTrue(lab.abrir_com_aviso(Raiz(), self.pasta))
            self.assertTrue(lab.abrir_com_aviso(Raiz(), self.pasta))
            self.assertEqual(abrir.call_count, 1)           # cliques seguintes não abrem outro
            trazer.assert_called_with(4321)
            self.assertEqual(trazer.call_count, 2)
            proc.codigo = 0                                 # o usuário fechou o Laboratório
            self.assertTrue(lab.abrir_com_aviso(Raiz(), self.pasta))
            self.assertEqual(abrir.call_count, 2)           # agora abre de novo

    def test_trazer_janela_de_processo_inexistente_devolve_false(self):
        self.assertFalse(lab.trazer_janela_do_processo(0x7FFFFFF0))

    # 5) sem __pycache__ na pasta do app
    def test_processo_filho_nao_grava_bytecode(self):
        with mock.patch.dict(os.environ, {lab.VAR_AMBIENTE: str(self.pasta)}), \
                mock.patch.object(lab.subprocess, "Popen") as popen:
            lab.abrir_processo()
        env = popen.call_args.kwargs["env"]
        self.assertEqual(env["PYTHONDONTWRITEBYTECODE"], "1")
        self.assertEqual(popen.call_args.kwargs["cwd"], str(lab.pasta_app()))
        self.assertEqual(popen.call_args.kwargs["creationflags"], lab.SEM_JANELA)


if __name__ == "__main__":
    unittest.main()
