"""Núcleo do nivelamento e da avaliação final: sorteio, correção, aprovação e código de conferência.

Sem interface e sem rede. É a referência das regras de docs/SPEC-avaliacao.md; o servidor (Cloudflare) repete as mesmas
regras. Todas as questões são de múltipla escolha com uma única alternativa correta. O banco é passado como argumento
(padrão: `lab.questoes.QUESTOES`, que não é versionado), então os testes usam um banco próprio.
"""
from __future__ import annotations

import hashlib
import random
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Mapping, Sequence

NOTA_MINIMA_PCT = 80                 # aprovação: pelo menos 80% de acertos na final
MINIMO_POR_TEMA_PCT = 50             # e pelo menos metade das questões de cada tema (2 de 4)
POR_TEMA_NA_FINAL = 4                 # até 5 temas: 20 questões
POR_TEMA_NA_FINAL_MUITOS_TEMAS = 3    # 6 temas ou mais: 3 por tema (8 temas = 24 questões)
FAIXA_DOMINADO_PCT = 75
FAIXA_REVISAR_PCT = 50
LICAO_DO_TEMA = {"T1": 1, "T2": 1, "T3": 1, "T4": 2, "T5": 3, "T6": 4, "T7": 5, "T8": 3}
NOME_MIN, NOME_MAX = 3, 80


def banco_padrao() -> list[dict]:
    from lab.questoes import QUESTOES
    return QUESTOES


def versao_do_banco() -> str:
    from lab.questoes import VERSAO_BANCO
    return VERSAO_BANCO


@dataclass(frozen=True)
class ItemProva:
    id: str
    tema: str
    pergunta: str
    opcoes: tuple[str, ...]
    correta: int                      # posição da correta NA ORDEM SORTEADA desta prova
    explicacao: str
    revisar: tuple[int, int]

    def publico(self) -> dict:
        """O que o aluno recebe: nunca a resposta nem a explicação."""
        return {"id": self.id, "pergunta": self.pergunta, "opcoes": list(self.opcoes)}


@dataclass(frozen=True)
class Prova:
    tipo: str                         # "nivelamento" | "final"
    semente: int
    itens: tuple[ItemProva, ...]
    versao_banco: str = ""

    def publica(self) -> dict:
        return {"tipo": self.tipo, "semente": self.semente, "versao_banco": self.versao_banco,
                "itens": [i.publico() for i in self.itens]}


@dataclass(frozen=True)
class Erro:
    id: str
    tema: str
    pergunta: str
    marcada: int | None               # None = em branco
    correta: int
    opcoes: tuple[str, ...]
    explicacao: str
    revisar: tuple[int, int]


@dataclass(frozen=True)
class Resultado:
    tipo: str
    acertos: int
    total: int
    em_branco: int
    por_tema: dict[str, tuple[int, int]]
    erradas: tuple[Erro, ...]
    aprovado: bool | None             # None no nivelamento (nunca reprova)
    motivos: tuple[str, ...] = field(default_factory=tuple)

    @property
    def nota_pct(self) -> float:
        return 100.0 * self.acertos / self.total if self.total else 0.0


# ---------------------------------------------------------------- sorteio
def _montar(q: dict, rng: random.Random) -> ItemProva:
    ordem = list(range(len(q["opcoes"])))
    rng.shuffle(ordem)
    return ItemProva(q["id"], q["tema"], q["pergunta"], tuple(q["opcoes"][i] for i in ordem),
                     ordem.index(q["correta"]), q["explicacao"], tuple(q["revisar"]))


def _validar_banco(banco: Sequence[dict]) -> None:
    ids = [q["id"] for q in banco]
    if len(set(ids)) != len(ids):
        raise ValueError("banco com ids repetidos")
    for q in banco:
        if not 0 <= q["correta"] < len(q["opcoes"]):
            raise ValueError(f"{q['id']}: índice da correta fora das opções")


def sortear_nivelamento(semente: int, banco: Sequence[dict] | None = None) -> Prova:
    """Todas as questões marcadas para o nivelamento, em ordem e alternativas sorteadas pela semente."""
    banco = banco_padrao() if banco is None else banco
    _validar_banco(banco)
    escolhidas = [q for q in banco if q["uso"] == "nivelamento"]
    if not escolhidas:
        raise ValueError("o banco não tem questões de nivelamento")
    rng = random.Random(semente)
    rng.shuffle(escolhidas)
    itens = tuple(_montar(q, rng) for q in escolhidas)
    return Prova("nivelamento", semente, itens, _versao(banco))


def por_tema_padrao(n_temas: int) -> int:
    """4 por tema até 5 temas (20 questões); 3 por tema a partir de 6 (8 temas = 24 questões)."""
    return POR_TEMA_NA_FINAL if n_temas <= 5 else POR_TEMA_NA_FINAL_MUITOS_TEMAS


def sortear_final(semente: int, anteriores: Sequence[str] = (), banco: Sequence[dict] | None = None,
                  por_tema: int | None = None) -> Prova:
    """`por_tema` questões de cada tema (padrão: `por_tema_padrao`), sem repetir as ids de `anteriores` enquanto houver
    outras, com pelo menos uma de nível 2 ou 3 por tema."""
    banco = banco_padrao() if banco is None else banco
    _validar_banco(banco)
    rng = random.Random(semente)
    evitar = set(anteriores)
    temas = sorted({q["tema"] for q in banco if q["uso"] == "final"})
    if not temas:
        raise ValueError("o banco não tem questões da avaliação final")
    por_tema = por_tema_padrao(len(temas)) if por_tema is None else por_tema
    escolhidas: list[dict] = []
    for tema in temas:
        pool = [q for q in banco if q["uso"] == "final" and q["tema"] == tema]
        if len(pool) < por_tema:
            raise ValueError(f"tema {tema}: só {len(pool)} questões para sortear {por_tema}")
        novas = [q for q in pool if q["id"] not in evitar]
        repetidas = [q for q in pool if q["id"] in evitar]
        rng.shuffle(novas)
        rng.shuffle(repetidas)
        ordenadas = novas + repetidas                   # só recorre às repetidas se faltar
        pegas = ordenadas[:por_tema]
        if not any(q["nivel"] >= 2 for q in pegas):
            reforco = next((q for q in ordenadas[por_tema:] if q["nivel"] >= 2), None)
            if reforco is not None:
                pegas[-1] = reforco
        escolhidas += pegas
    rng.shuffle(escolhidas)
    itens = tuple(_montar(q, rng) for q in escolhidas)
    return Prova("final", semente, itens, _versao(banco))


def _versao(banco: Sequence[dict]) -> str:
    try:
        return versao_do_banco() if banco is banco_padrao() else ""
    except ImportError:
        return ""


# ---------------------------------------------------------------- correção
def faixa(acertos: int, total: int) -> str:
    """"dominado" (≥ 75%), "revisar" (50 a 74%) ou "refazer" (< 50%)."""
    if total <= 0:
        return "refazer"
    if acertos * 100 >= FAIXA_DOMINADO_PCT * total:
        return "dominado"
    if acertos * 100 >= FAIXA_REVISAR_PCT * total:
        return "revisar"
    return "refazer"


def corrigir(prova: Prova, respostas: Mapping[str, int | None]) -> Resultado:
    """Corrige uma prova. `respostas` mapeia a id da questão à posição marcada; ausente ou None = em branco (errada).
    Id desconhecida ou posição fora das alternativas é erro de quem chamou (ValueError), nunca nota silenciosa."""
    por_id = {i.id: i for i in prova.itens}
    for qid, marcada in respostas.items():
        if qid not in por_id:
            raise ValueError(f"resposta para questão que não está na prova: {qid}")
        if marcada is not None and (isinstance(marcada, bool) or not isinstance(marcada, int)
                                    or not 0 <= marcada < len(por_id[qid].opcoes)):
            raise ValueError(f"{qid}: alternativa inválida: {marcada!r}")
    acertos = 0
    em_branco = 0
    por_tema: dict[str, list[int]] = {}
    erradas: list[Erro] = []
    for item in prova.itens:
        marcada = respostas.get(item.id)
        contagem = por_tema.setdefault(item.tema, [0, 0])
        contagem[1] += 1
        if marcada is None:
            em_branco += 1
        if marcada == item.correta:
            acertos += 1
            contagem[0] += 1
        else:
            erradas.append(Erro(item.id, item.tema, item.pergunta, marcada, item.correta, item.opcoes,
                                item.explicacao, item.revisar))
    temas = {t: (a, n) for t, (a, n) in sorted(por_tema.items())}
    aprovado, motivos = None, ()
    if prova.tipo == "final":
        aprovado, motivos = _aprovacao(acertos, len(prova.itens), temas)
    return Resultado(prova.tipo, acertos, len(prova.itens), em_branco, temas, tuple(erradas), aprovado, motivos)


def _aprovacao(acertos: int, total: int, por_tema: Mapping[str, tuple[int, int]]) -> tuple[bool, tuple[str, ...]]:
    motivos = []
    if acertos * 100 < NOTA_MINIMA_PCT * total:
        motivos.append(f"A nota geral precisa ser de pelo menos {NOTA_MINIMA_PCT}%.")
    for tema, (a, n) in por_tema.items():
        if a * 100 < MINIMO_POR_TEMA_PCT * n:
            motivos.append(f"Tema {tema}: é preciso acertar pelo menos metade das questões ({a} de {n}).")
    return (not motivos), tuple(motivos)


def recomendar_licao(resultado: Resultado) -> int | None:
    """Do nivelamento: a primeira lição cujo conjunto de temas teve menos de 75% de acertos; `None` se todas ≥ 75%."""
    por_licao: dict[int, list[int]] = {}
    for tema, (a, n) in resultado.por_tema.items():
        c = por_licao.setdefault(LICAO_DO_TEMA.get(tema, 1), [0, 0])
        c[0] += a
        c[1] += n
    for licao in sorted(por_licao):
        a, n = por_licao[licao]
        if faixa(a, n) != "dominado":
            return licao
    return None


# ---------------------------------------------------------------- certificado (regras puras)
def validar_nome(nome: str) -> str:
    """Nome para o certificado: sem caracteres de controle, espaços normalizados, de 3 a 80 caracteres e com letras."""
    texto = re.sub(r"[\t\n\r\f\v]", " ", unicodedata.normalize("NFC", str(nome)))
    limpo = "".join(c for c in texto if unicodedata.category(c)[0] != "C")
    limpo = re.sub(r"\s+", " ", limpo).strip()
    if len(limpo) < NOME_MIN:
        raise ValueError(f"O nome precisa ter pelo menos {NOME_MIN} caracteres.")
    if len(limpo) > NOME_MAX:
        raise ValueError(f"O nome pode ter no máximo {NOME_MAX} caracteres.")
    if not any(c.isalpha() for c in limpo):
        raise ValueError("O nome precisa ter letras.")
    return limpo


def codigo_conferencia(nome: str, data_iso: str, nota_pct: float, versao_lab: str, versao_banco: str, semente: int) -> str:
    """12 caracteres (SHA-256 truncado) que mudam se qualquer campo mudar. Detecta erro de cópia, não fraude."""
    campos = [validar_nome(nome), data_iso, f"{nota_pct:.1f}", versao_lab, versao_banco, str(int(semente))]
    return hashlib.sha256("|".join(campos).encode("utf-8")).hexdigest()[:12].upper()
