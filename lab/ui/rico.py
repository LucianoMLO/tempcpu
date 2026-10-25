"""Texto com termos do glossário (sublinhados; a definição aparece ao passar o mouse) e **negrito**."""
from __future__ import annotations

import re
import tkinter as tk
from typing import Callable

from lab.glossario import segmentos
from tema import CARTAO, FONTE, TEXTO

COR_TERMO = "#3f6fb0"


class TextoRico(tk.Text):
    def __init__(self, pai, ao_termo: Callable[[str | None], None] | None = None, fonte: tuple = (FONTE, 10),
                 cor: str = TEXTO, fundo: str = CARTAO, **kw) -> None:
        super().__init__(pai, wrap="word", bg=fundo, fg=cor, relief="flat", font=fonte, height=1, padx=0, pady=0,
                         cursor="arrow", highlightthickness=0, borderwidth=0, spacing3=3, **kw)
        self.ao_termo = ao_termo
        self.tag_configure("negrito", font=(fonte[0], fonte[1], "bold"))
        self.bind("<Configure>", lambda _e: self.after_idle(self.ajustar_altura))
        self.configure(state="disabled")
        self.termos_no_texto: list[str] = []

    def definir(self, texto: str) -> "TextoRico":
        self.configure(state="normal")
        self.delete("1.0", "end")
        for t in self.tag_names():
            if t.startswith("termo_"):
                self.tag_delete(t)
        self.termos_no_texto = []
        n = 0
        for pedaco, chave in segmentos(texto):
            if chave is None:
                for i, parte in enumerate(re.split(r"\*\*", pedaco)):
                    if parte:
                        self.insert("end", parte, ("negrito",) if i % 2 else ())
                continue
            tag = f"termo_{n}"
            n += 1
            self.tag_configure(tag, foreground=COR_TERMO, underline=True)
            self.tag_bind(tag, "<Enter>", lambda _e, c=chave: self._termo(c))
            self.tag_bind(tag, "<Leave>", lambda _e: self._termo(None))
            self.tag_bind(tag, "<Button-1>", lambda _e, c=chave: self._termo(c))
            self.insert("end", pedaco, (tag,))
            self.termos_no_texto.append(chave)
        self.configure(state="disabled")
        self.after_idle(self.ajustar_altura)
        return self

    def _termo(self, chave: str | None) -> None:
        self.configure(cursor="hand2" if chave else "arrow")
        if self.ao_termo:
            self.ao_termo(chave)

    def ajustar_altura(self) -> None:
        try:
            if self.winfo_width() < 40:        # ainda sem largura: cada caractere viraria uma linha
                return
            linhas = self.count("1.0", "end", "displaylines")
            self.configure(height=max(1, (linhas[0] if linhas else 1)))
        except tk.TclError:
            pass
