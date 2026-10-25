import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import CONFIG_PADRAO, zona_de  # noqa: E402

CFG = {**CONFIG_PADRAO, "DANO_C": 105.0}


class TestZonas(unittest.TestCase):
    def test_limites(self):
        c = CFG
        self.assertEqual(zona_de(50, c), "normal")
        self.assertEqual(zona_de(74.9, c), "normal")
        self.assertEqual(zona_de(75, c), "atencao")
        self.assertEqual(zona_de(90, c), "quente")
        self.assertEqual(zona_de(104.9, c), "quente")
        self.assertEqual(zona_de(105, c), "dano")


if __name__ == "__main__":
    unittest.main()
