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


class Progresso:
    def __init__(self, caminho: Path | None = None) -> None:
        self.caminho = caminho or pasta_lab() / "progresso.json"
        self.dados: dict = {"concluidas": [], "acertos": {}, "fonte": None}
        try:
            lido = json.loads(self.caminho.read_text(encoding="utf-8"))
            if isinstance(lido, dict):
                if isinstance(lido.get("concluidas"), list):
                    self.dados["concluidas"] = [n for n in lido["concluidas"] if isinstance(n, int) and not isinstance(n, bool)]
                if isinstance(lido.get("acertos"), dict):
                    self.dados["acertos"] = {str(k): bool(v) for k, v in lido["acertos"].items() if isinstance(v, bool)}
                if lido.get("fonte") in ("real", "sintetico"):
                    self.dados["fonte"] = lido["fonte"]
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

    @property
    def fonte(self) -> str | None:
        return self.dados["fonte"]

    @fonte.setter
    def fonte(self, valor: str) -> None:
        self.dados["fonte"] = valor
        self._gravar()
