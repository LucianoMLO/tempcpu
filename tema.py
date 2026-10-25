"""Paleta, zonas e pequenos formatadores compartilhados pelas janelas."""
from __future__ import annotations

import tkinter as tk

# Paleta suave (clara, tons pastel)
FUNDO, CARTAO, BORDA = "#f4f6f9", "#ffffff", "#e3e8ef"
TEXTO, SUAVE, GRADE, LINHA = "#3b4656", "#8a96a8", "#e9edf2", "#5b6b80"
# zona: (rótulo, cor de texto/destaque, cor da faixa)
ZONAS = {
    "normal":  ("Normal",                  "#4f9d6e", "#e4f3ea"),
    "atencao": ("Atenção",                 "#b8902f", "#faf1d6"),
    "quente":  ("Quente",                  "#c8695d", "#f9e2de"),
    "dano":    ("Crítico — risco de dano", "#8f68b0", "#eee5f6"),
}
PRIORIDADE = {"alta": ("●", "#c8695d"), "media": ("●", "#b8902f"), "dica": ("●", "#8fb3a0")}
FONTE = "Segoe UI"
CINZA_ICONE = "#9aa5b4"


def br(c: float, casas: int = 1) -> str:
    return f"{c:.{casas}f}".replace(".", ",")


def zona_de(c: float, cfg: dict) -> str:
    if c >= cfg["DANO_C"]:
        return "dano"
    if c >= cfg["QUENTE_C"]:
        return "quente"
    if c >= cfg["ALERTA_C"]:
        return "atencao"
    return "normal"


def cartao(pai: tk.Widget, titulo: str) -> tk.Frame:
    caixa = tk.Frame(pai, bg=CARTAO, highlightbackground=BORDA, highlightthickness=1, padx=16, pady=12)
    if titulo:
        tk.Label(caixa, text=titulo.upper(), font=(FONTE, 9, "bold"), bg=CARTAO, fg=SUAVE).pack(anchor="w")
    return caixa
