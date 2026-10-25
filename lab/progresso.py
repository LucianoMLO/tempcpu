"""Progresso do aprendiz: arquivo local pequeno (lições concluídas, acertos, última fonte de dados).

Fica em `%LOCALAPPDATA%\\TempCPU\\lab\\progresso.json` (ou em `TEMPCPU_LAB_DADOS`, usado nos testes).
Apagar o arquivo reinicia tudo. Nunca guarda dados do histórico.
"""
from __future__ import annotations

import json
import os
from pathlib import Path


def pasta_lab() -> Path:
    base = os.environ.get("TEMPCPU_LAB_DADOS")
    if base:
        return Path(base)
    return Path(os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")) / "TempCPU" / "lab"


MAX_PROVAS = 20


def _inteiro(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _prova_valida(p) -> dict | None:
    """Aceita só um resumo bem formado; qualquer outra coisa no arquivo é descartada."""
    if not isinstance(p, dict) or p.get("tipo") not in ("nivelamento", "final"):
        return None
    if not (_inteiro(p.get("semente")) and _inteiro(p.get("acertos")) and _inteiro(p.get("total")) and isinstance(p.get("data"), str)):
        return None
    if p["total"] <= 0 or not 0 <= p["acertos"] <= p["total"] or p.get("aprovado") not in (True, False, None):
        return None
    por_tema = p.get("por_tema")
    if not isinstance(por_tema, dict):
        return None
    limpo = {}
    for tema, v in por_tema.items():
        if not (isinstance(tema, str) and isinstance(v, (list, tuple)) and len(v) == 2 and all(_inteiro(x) for x in v)
                and 0 <= v[0] <= v[1]):
            return None
        limpo[tema] = [v[0], v[1]]
    return {"tipo": p["tipo"], "semente": p["semente"], "acertos": p["acertos"], "total": p["total"],
            "aprovado": p.get("aprovado"), "por_tema": limpo, "data": p["data"][:32]}


class Progresso:
    def __init__(self, caminho: Path | None = None) -> None:
        self.caminho = caminho or pasta_lab() / "progresso.json"
        self.dados: dict = {"concluidas": [], "acertos": {}, "fonte": None, "provas": []}
        try:
            lido = json.loads(self.caminho.read_text(encoding="utf-8"))
            if isinstance(lido, dict):
                if isinstance(lido.get("concluidas"), list):
                    self.dados["concluidas"] = [n for n in lido["concluidas"] if isinstance(n, int) and not isinstance(n, bool)]
                if isinstance(lido.get("acertos"), dict):
                    self.dados["acertos"] = {str(k): bool(v) for k, v in lido["acertos"].items() if isinstance(v, bool)}
                if lido.get("fonte") in ("real", "sintetico"):
                    self.dados["fonte"] = lido["fonte"]
                if isinstance(lido.get("provas"), list):
                    self.dados["provas"] = [p for p in map(_prova_valida, lido["provas"]) if p][-MAX_PROVAS:]
        except (OSError, ValueError):
            pass                                     # arquivo ausente ou corrompido: começa do zero

    def _gravar(self) -> None:
        try:
            self.caminho.parent.mkdir(parents=True, exist_ok=True)
            self.caminho.write_text(json.dumps(self.dados, ensure_ascii=False, indent=1), encoding="utf-8")
        except OSError:
            pass                                     # sem permissão: o progresso só vale nesta sessão

    def concluida(self, licao: int) -> bool:
        return licao in self.dados["concluidas"]

    def marcar_concluida(self, licao: int) -> None:
        if licao not in self.dados["concluidas"]:
            self.dados["concluidas"].append(licao)
            self._gravar()

    def registrar_acerto(self, licao: int, pergunta: int, acertou: bool) -> None:
        self.dados["acertos"][f"{licao}.{pergunta}"] = bool(acertou)
        self._gravar()

    def acertos(self, licao: int) -> tuple[int, int]:
        """(acertos, respondidas) da lição."""
        mine = [v for k, v in self.dados["acertos"].items() if k.startswith(f"{licao}.")]
        return sum(mine), len(mine)

    def registrar_prova(self, tipo: str, semente: int, acertos: int, total: int, aprovado: bool | None,
                        por_tema: dict, data_iso: str) -> None:
        """Guarda o resumo de uma prova (sem nome e sem respostas). Mantém as últimas MAX_PROVAS."""
        registro = _prova_valida({"tipo": tipo, "semente": semente, "acertos": acertos, "total": total, "aprovado": aprovado,
                                  "por_tema": {k: list(v) for k, v in por_tema.items()}, "data": data_iso})
        if registro is None:
            raise ValueError("resumo de prova inválido")
        self.dados["provas"] = (self.dados["provas"] + [registro])[-MAX_PROVAS:]
        self._gravar()

    @property
    def fonte(self) -> str | None:
        return self.dados["fonte"]

    @fonte.setter
    def fonte(self, valor: str) -> None:
        self.dados["fonte"] = valor
        self._gravar()
