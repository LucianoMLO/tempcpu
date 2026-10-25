import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bandeja import desenhar_icone  # noqa: E402


class TestIconeSuave(unittest.TestCase):
    def test_fundo_pastel_e_tira_na_cor_da_faixa(self):
        img = desenhar_icone("86", "#b8902f", "suave")
        fundo = img.getpixel((8, 8))[:3]
        self.assertTrue(all(c >= 200 for c in fundo), fundo)          # pastel, bem claro
        self.assertEqual(img.getpixel((32, 60))[:3], (0xb8, 0x90, 0x2f))  # tira inferior na cor forte
        self.assertEqual(img.getpixel((0, 0))[3], 0)                   # canto transparente

    def test_estilo_forte_continua_igual(self):
        self.assertEqual(desenhar_icone("86", "#b8902f").getpixel((32, 4))[:3], (0xb8, 0x90, 0x2f))


if __name__ == "__main__":
    unittest.main()
