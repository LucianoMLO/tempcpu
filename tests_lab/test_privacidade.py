"""O Laboratório não tem como enviar o histórico para fora: nenhum módulo de rede é importado."""
import ast
import unittest
from pathlib import Path

PROIBIDOS = {"socket", "urllib", "http", "requests", "ftplib", "smtplib", "ssl", "xmlrpc", "webbrowser", "telnetlib"}


class TestSemRede(unittest.TestCase):
    def test_lab_nao_importa_modulos_de_rede(self):
        achados = []
        for arq in (Path(__file__).resolve().parent.parent / "lab").rglob("*.py"):
            for no in ast.walk(ast.parse(arq.read_text(encoding="utf-8"))):
                nomes = [a.name for a in no.names] if isinstance(no, ast.Import) else [no.module or ""] if isinstance(no, ast.ImportFrom) else []
                achados += [f"{arq.name}: {n}" for n in nomes if n.split(".")[0] in PROIBIDOS]
        self.assertEqual(achados, [])


if __name__ == "__main__":
    unittest.main()
