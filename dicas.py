"""Legendas que aparecem ao parar o mouse sobre um item (tooltip), só com a biblioteca padrão."""
from __future__ import annotations

import tkinter as tk
from typing import Callable

from tema import BORDA, CARTAO, FONTE, TEXTO

ATRASO_MS = 500
LARGURA = 320

TERMOS = {
    "GPU": "Placa de vídeo integrada ou dedicada. É o chip que desenha as imagens da tela.",
    "SoC": "System on Chip: a parte do chip que não são os núcleos do processador nem a GPU. "
           "Reúne memória, USB, PCIe e vídeo.",
    "frequência": "Velocidade atual dos núcleos, em MHz. Sobe quando há trabalho e desce quando o computador descansa.",
    "ventoinha": "Rotação do ventilador de refrigeração, em RPM (voltas por minuto). Mais RPM, mais ar passando.",
}


def texto_dos_termos(texto_da_linha: str) -> str:
    """Legenda só dos termos que aparecem na linha de extras (GPU, SoC, frequência, ventoinha)."""
    baixo = texto_da_linha.lower()
    achados = []
    if "gpu" in baixo:
        achados.append(("GPU", TERMOS["GPU"]))
    if "soc" in baixo:
        achados.append(("SoC", TERMOS["SoC"]))
    if " mhz" in baixo:
        achados.append(("CPU a … MHz", TERMOS["frequência"]))
    if "ventoinha" in baixo:
        achados.append(("Ventoinha", TERMOS["ventoinha"]))
    return "\n\n".join(f"{nome}: {desc}" for nome, desc in achados)


class Dica:
    """Mostra `texto` (ou o que `texto` devolver, se for função) perto do mouse depois de um instante parado."""

    def __init__(self, widget: tk.Widget, texto: str | Callable[[], str], atraso: int = ATRASO_MS) -> None:
        self.widget = widget
        self.texto = texto
        self.atraso = atraso
        self.janela: tk.Toplevel | None = None
        self._id: str | None = None
        widget.bind("<Enter>", self._agendar, add="+")
        widget.bind("<Leave>", self._esconder, add="+")
        widget.bind("<ButtonPress>", self._esconder, add="+")
        widget.bind("<Destroy>", self._esconder, add="+")

    def conteudo(self) -> str:
        return self.texto() if callable(self.texto) else self.texto

    def _agendar(self, _e=None) -> None:
        self._cancelar()
        try:
            self._id = self.widget.after(self.atraso, self.mostrar)
        except tk.TclError:
            self._id = None

    def _cancelar(self) -> None:
        if self._id is not None:
            try:
                self.widget.after_cancel(self._id)
            except tk.TclError:
                pass
            self._id = None

    def mostrar(self) -> None:
        self._id = None
        if self.janela is not None:
            return
        texto = self.conteudo()
        if not texto:
            return
        try:
            x = self.widget.winfo_pointerx() + 12
            y = self.widget.winfo_pointery() + 18
            self.janela = tk.Toplevel(self.widget)
            self.janela.wm_overrideredirect(True)
            self.janela.wm_geometry(f"+{x}+{y}")
            tk.Label(self.janela, text=texto, justify="left", wraplength=LARGURA, bg=CARTAO, fg=TEXTO,
                     font=(FONTE, 9), padx=8, pady=6, highlightthickness=1, highlightbackground=BORDA).pack()
        except tk.TclError:
            self.janela = None

    def _esconder(self, _e=None) -> None:
        self._cancelar()
        if self.janela is not None:
            try:
                self.janela.destroy()
            except tk.TclError:
                pass
            self.janela = None
