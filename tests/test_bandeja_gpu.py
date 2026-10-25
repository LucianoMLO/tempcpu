import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from bandeja import desenhar_icone  # noqa: E402
from sensores import escolher_sensor_gpu  # noqa: E402


class TestGpu(unittest.TestCase):
    def test_prefere_gpu_core_e_ignora_cpu(self):
        s = [("/amdcpu/0/temperature/2", "Core (Tctl/Tdie)", 80.0),
             ("/gpu-nvidia/0/temperature/0", "GPU Core", 62.0),
             ("/gpu-nvidia/0/temperature/2", "GPU Hot Spot", 75.0)]
        self.assertEqual(escolher_sensor_gpu(s), ("GPU Core", 62.0))

    def test_sem_gpu(self):
        self.assertIsNone(escolher_sensor_gpu([("/amdcpu/0/temperature/2", "Core (Tctl/Tdie)", 80.0)]))


class TestIcone(unittest.TestCase):
    def test_cor_de_fundo_e_tamanho(self):
        img = desenhar_icone("86", "#b8902f")
        self.assertEqual(img.size, (64, 64))
        self.assertEqual(img.getpixel((32, 4))[:3], (0xb8, 0x90, 0x2f))
        self.assertEqual(img.getpixel((0, 0))[3], 0)  # canto transparente (arredondado)

    def test_tres_digitos_cabe(self):
        img = desenhar_icone("105", "#8f68b0")
        brancos = [x for x in range(64) if img.getpixel((x, 33))[:3] == (255, 255, 255)]
        self.assertTrue(brancos and min(brancos) > 0 and max(brancos) < 63)


if __name__ == "__main__":
    unittest.main()
