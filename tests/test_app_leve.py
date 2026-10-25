"""A8: o app (e o launcher do Laboratório) nunca carregam numpy nem scikit-learn."""
import subprocess
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

SCRIPT = """
import sys
sys.path.insert(0, {raiz!r})
import {modulo}
pesados = [m for m in ("numpy", "sklearn", "scipy", "pandas") if m in sys.modules]
print("PESADOS=" + ",".join(pesados))
"""


class AppLeve(unittest.TestCase):
    def _rodar(self, modulo: str) -> str:
        r = subprocess.run([sys.executable, "-E", "-c", SCRIPT.format(modulo=modulo, raiz=str(RAIZ))], cwd=str(RAIZ),
                           capture_output=True, text=True, timeout=120,
                           env={"PYTHONPATH": str(RAIZ), "SYSTEMROOT": "C:\\Windows"})
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout.strip().splitlines()[-1]

    def test_import_app_nao_carrega_numpy_nem_sklearn(self):
        self.assertEqual(self._rodar("app"), "PESADOS=")

    def test_import_laboratorio_nao_carrega_numpy_nem_sklearn(self):
        self.assertEqual(self._rodar("laboratorio"), "PESADOS=")

    def test_codigo_do_app_nao_importa_bibliotecas_de_ml(self):
        for nome in ("app.py", "bandeja.py", "laboratorio.py"):
            texto = (RAIZ / nome).read_text(encoding="utf-8")
            for lib in ("numpy", "sklearn", "scipy"):
                self.assertNotRegex(texto, rf"(?m)^\s*(import|from)\s+{lib}\b", f"{nome} importa {lib}")


if __name__ == "__main__":
    unittest.main()
