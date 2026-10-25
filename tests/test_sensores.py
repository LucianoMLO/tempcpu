import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sensores import acpi_para_celsius, escolher_sensor_lhm, zona_mais_quente  # noqa: E402


class TestConversao(unittest.TestCase):
    def test_decimos_de_kelvin(self):
        self.assertEqual(acpi_para_celsius(3592), 86.1)
        self.assertEqual(acpi_para_celsius(2732), 0.1)


class TestZonaAcpi(unittest.TestCase):
    def test_pega_a_mais_quente(self):
        zonas = [("ACPI\\ThermalZone\\TZ00_0", 3132), ("ACPI\\ThermalZone\\THRM_0", 3592)]
        self.assertEqual(zona_mais_quente(zonas), ("ACPI\\ThermalZone\\THRM_0", 86.1))

    def test_descarta_valores_absurdos(self):
        self.assertIsNone(zona_mais_quente([("Z", 0), ("Z2", 9999)]))
        self.assertIsNone(zona_mais_quente([]))


class TestSensorLhm(unittest.TestCase):
    def test_prefere_package(self):
        s = [("/intelcpu/0/temperature/0", "Core #1", 70.0),
             ("/intelcpu/0/temperature/8", "CPU Package", 72.0)]
        self.assertEqual(escolher_sensor_lhm(s), ("CPU Package", 72.0))

    def test_amd_tctl(self):
        s = [("/amdcpu/0/temperature/2", "Core (Tctl/Tdie)", 65.5),
             ("/gpu-amd/0/temperature/0", "GPU Core", 90.0)]
        self.assertEqual(escolher_sensor_lhm(s), ("Core (Tctl/Tdie)", 65.5))

    def test_ignora_gpu_e_disco(self):
        s = [("/gpu-amd/0/temperature/0", "GPU Core", 90.0), ("/nvme/0/temperature/0", "Temperature", 40.0)]
        self.assertIsNone(escolher_sensor_lhm(s))

    def test_nome_desconhecido_usa_o_maior(self):
        s = [("/amdcpu/0/temperature/5", "CCD1 (Tdie)", 60.0), ("/amdcpu/0/temperature/6", "CCD2 (Tdie)", 63.0)]
        self.assertEqual(escolher_sensor_lhm(s), ("CCD2 (Tdie)", 63.0))


if __name__ == "__main__":
    unittest.main()
