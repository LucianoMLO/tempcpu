"""Critério A11: todo termo técnico usado nas telas tem definição no Glossário; nenhum jargão solto."""
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _base  # noqa: E402,F401

from lab import textos as T  # noqa: E402
from lab.glossario import TERMOS, chaves_usadas, segmentos, texto_puro  # noqa: E402

# termo do glossário -> expressão que o reconhece no texto corrido
VIGIADOS = {
    "modelo": r"\bmodelos?\b", "alvo": r"\balvo\b", "entradas": r"\bentradas?\b", "treino": r"\btreino\b", "teste": r"\bteste\b",
    "arvore": r"\bárvores?\b", "profundidade": r"\bprofundidade\b", "erro_medio": r"\berro médio\b",
    "subajuste": r"\bsubajuste\b", "sobreajuste": r"\bsobreajuste\b", "ruido": r"\bruído\b",
    "baseline": r"palpite de referência|\bbaseline\b", "r2": r"R²", "importancia": r"\bimportância\b",
    "correlacao": r"\bcorrelação\b", "consequencia": r"\bconsequência\b", "vazamento": r"\bvazamento\b",
    "anomalia": r"\banomalia\b", "esperado": r"temperatura esperada", "residuo": r"\bresíduo\b",
    "erro_tipico": r"\berro típico\b", "falso_alarme": r"\bfalsos? alarmes?\b", "alarme_perdido": r"\balarme perdido\b",
    "mediana": r"\bmediana\b", "tendencia": r"\btendência\b", "gabarito": r"\bgabarito\b",
    "coeficiente": r"\bcoeficientes?\b", "colinearidade": r"\bcolinearidade\b", "semente": r"\bsemente\b",
    "dados_sinteticos": r"\bdados sintéticos\b",
}
JARGAO_PROIBIDO = [r"\boverfitting\b", r"\bunderfitting\b", r"\bfeatures?\b", r"\btarget\b", r"\bdataset\b", r"\btest set\b",
                   r"\baccuracy\b", r"\bregress[ãa]o\b", r"\bhiperpar", r"\bvalida[çc][ãa]o cruzada\b", r"\bcross.?validation\b"]
MARCADOR = re.compile(r"⟦[^⟧]*⟧")


def achatar(v):
    if isinstance(v, str):
        yield v
    elif isinstance(v, dict):
        for x in v.values():
            yield from achatar(x)
    elif isinstance(v, (list, tuple)):
        for x in v:
            yield from achatar(x)


def todos_os_textos() -> dict[str, list[str]]:
    return {n: list(achatar(getattr(T, n))) for n in dir(T) if not n.startswith("_") and n.isupper()}


def grupos() -> dict[str, list[str]]:
    """Textos agrupados por lição (L1_, L2_, L3_) e o restante (inicio, estados, sobre)."""
    saida: dict[str, list[str]] = {"L1": [], "L2": [], "L3": [], "geral": []}
    for nome, textos in todos_os_textos().items():
        chave = nome[:2] if nome[:2] in ("L1", "L2", "L3") else "geral"
        saida[chave] += textos
    return saida


class TestA11(unittest.TestCase):
    def test_todo_termo_vigiado_usado_num_grupo_esta_marcado_nesse_grupo(self):
        faltas = []
        for grupo, textos in grupos().items():
            marcados = set().union(*(chaves_usadas(t) for t in textos)) if textos else set()
            sem_marcas = [MARCADOR.sub(" ", t) for t in textos]
            for chave, rx in VIGIADOS.items():
                usa_no_texto = any(re.search(rx, t, re.IGNORECASE) for t in sem_marcas)
                if (usa_no_texto or chave in marcados) and chave not in marcados:
                    faltas.append(f"{grupo}: '{chave}' aparece sem ser marcado como termo do glossário")
        self.assertEqual(faltas, [])

    def test_nenhum_jargao_em_ingles_solto_nas_telas(self):
        achados = []
        for nome, textos in todos_os_textos().items():
            for t in textos:
                for rx in JARGAO_PROIBIDO:
                    if re.search(rx, texto_puro(t), re.IGNORECASE):
                        achados.append(f"{nome}: {rx}")
        self.assertEqual(achados, [])

    def test_todo_termo_do_glossario_e_usado_em_algum_lugar(self):
        usados = set()
        for textos in todos_os_textos().values():
            for t in textos:
                usados |= chaves_usadas(t)
        self.assertEqual(sorted(set(TERMOS) - usados), [], "definições que nenhuma tela usa")

    def test_toda_marcacao_aponta_para_termo_existente(self):
        for nome, textos in todos_os_textos().items():
            for t in textos:
                segmentos(t)                                   # KeyError se a chave não existir

    def test_exemplos_do_glossario_nao_sao_vazios_nem_dados_reais_do_usuario(self):
        for chave, (nome, ingles, definicao, exemplo) in TERMOS.items():
            self.assertGreater(len(definicao), 25, chave)
            self.assertGreater(len(exemplo), 8, chave)
            self.assertNotRegex(definicao + exemplo, r"[A-Z]:\\|\\Users\\", chave)


if __name__ == "__main__":
    unittest.main()
