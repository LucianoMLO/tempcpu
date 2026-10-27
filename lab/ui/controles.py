"""Controles pequenos reutilizados pelas lições novas: escala com rótulo e atraso, e tabela simples."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Sequence

from tema import CARTAO, FONTE, GRADE, SUAVE, TEXTO


class Escala(tk.Frame):
    """Rótulo + barra deslizante sobre uma lista de valores.

    `ao_mudar(valor)` roda `atraso` ms depois da última mudança (0 = na hora); o rótulo muda sempre na hora. O `after`
    pendente é cancelado quando a tela é destruída (trocar de passo destrói a área)."""

    def __init__(self, pai, valores: Sequence, inicial, rotular: Callable[[object], str], ao_mudar: Callable[[object], None],
                 atraso: int = 0, comprimento: int = 420) -> None:
        super().__init__(pai, bg=CARTAO)
        self.valores = list(valores)
        self.rotular = rotular
        self.ao_mudar = ao_mudar
        self.atraso = atraso
        self._pendente: str | None = None
        self._indice = self.valores.index(inicial) if inicial in self.valores else 0
        self.rotulo = tk.Label(self, text="", bg=CARTAO, fg=TEXTO, font=(FONTE, 10, "bold"), anchor="w")
        self.rotulo.pack(fill="x")
        self.escala = ttk.Scale(self, from_=0, to=len(self.valores) - 1, orient="horizontal", length=comprimento, command=self._mudou)
        self.escala.set(self._indice)
        self.escala.pack(anchor="w", pady=(0, 4))
        self._atualizar_rotulo()
        self.bind("<Destroy>", self._ao_destruir)

    @property
    def valor(self):
        return self.valores[self._indice]

    def definir(self, valor) -> None:
        """Move a barra para `valor` (dispara `ao_mudar` como se o usuário tivesse mexido)."""
        self.escala.set(self.valores.index(valor))

    def _atualizar_rotulo(self) -> None:
        self.rotulo.config(text=self.rotular(self.valor))

    def _mudou(self, bruto: str) -> None:
        i = int(round(float(bruto)))
        if abs(float(bruto) - i) > 1e-6:
            self.escala.set(i)                      # encaixa nos valores possíveis
            return
        if i == self._indice:
            return
        self._indice = i
        self._atualizar_rotulo()
        if self.atraso <= 0:
            self.ao_mudar(self.valor)
            return
        if self._pendente is not None:
            self.after_cancel(self._pendente)
        self._pendente = self.after(self.atraso, self._disparar)

    def _disparar(self) -> None:
        self._pendente = None
        if self.winfo_exists():
            self.ao_mudar(self.valor)

    def _ao_destruir(self, evento) -> None:
        if evento.widget is self and self._pendente is not None:
            try:
                self.after_cancel(self._pendente)
            except tk.TclError:
                pass
            self._pendente = None


def tabela(pai, colunas: Sequence[str], linhas: Sequence[Sequence[str]], larguras: Sequence[int] | None = None) -> tk.Frame:
    """Tabela de rótulos (cabeçalho em negrito, linhas alternadas)."""
    q = tk.Frame(pai, bg=CARTAO)
    for j, c in enumerate(colunas):
        tk.Label(q, text=c, bg=GRADE, fg=TEXTO, font=(FONTE, 9, "bold"), anchor="w", padx=8, pady=3,
                 width=(larguras[j] if larguras else 0)).grid(row=0, column=j, sticky="ew")
    for i, linha in enumerate(linhas, start=1):
        for j, v in enumerate(linha):
            tk.Label(q, text=v, bg=CARTAO, fg=TEXTO if j else TEXTO, font=(FONTE, 9, "bold" if j == 0 else "normal"), anchor="w",
                     padx=8, pady=2, width=(larguras[j] if larguras else 0)).grid(row=i, column=j, sticky="ew")
    for j in range(len(colunas)):
        q.columnconfigure(j, weight=1)
    return q


def titulo_pequeno(pai, texto: str) -> tk.Label:
    return tk.Label(pai, text=texto, bg=CARTAO, fg=SUAVE, font=(FONTE, 9, "bold"), anchor="w")
