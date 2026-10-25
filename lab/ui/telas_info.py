"""Telas de informação: Glossário (com busca) e Sobre e privacidade."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from lab import VERSAO
from lab import textos as T
from lab.glossario import TERMOS
from lab.ui.rico import TextoRico
from tema import CARTAO, FONTE, FUNDO, SUAVE, TEXTO, cartao


class Rolavel(tk.Frame):
    """Área com rolagem vertical; coloque os widgets em `.interno`."""

    def __init__(self, pai, fundo: str = FUNDO) -> None:
        super().__init__(pai, bg=fundo)
        self.tela = tk.Canvas(self, bg=fundo, highlightthickness=0)
        self.barra = ttk.Scrollbar(self, orient="vertical", command=self.tela.yview)
        self.tela.configure(yscrollcommand=self.barra.set)
        self.barra.pack(side="right", fill="y")
        self.tela.pack(side="left", fill="both", expand=True)
        self.interno = tk.Frame(self.tela, bg=fundo)
        self._id = self.tela.create_window((0, 0), window=self.interno, anchor="nw")
        self.interno.bind("<Configure>", lambda _e: self.tela.configure(scrollregion=self.tela.bbox("all")))
        self.tela.bind("<Configure>", lambda e: self.tela.itemconfigure(self._id, width=e.width))
        self.tela.bind("<Enter>", lambda _e: self.tela.bind_all("<MouseWheel>", self._roda))
        self.tela.bind("<Leave>", lambda _e: self.tela.unbind_all("<MouseWheel>"))

    def _roda(self, e) -> None:
        self.tela.yview_scroll(-1 * (e.delta // 120), "units")


class TelaGlossario(tk.Frame):
    def __init__(self, janela) -> None:
        super().__init__(janela.conteudo, bg=FUNDO)
        self.janela = janela
        tk.Label(self, text=T.GLOSSARIO_TITULO, bg=FUNDO, fg=TEXTO, font=(FONTE, 18, "bold"), anchor="w").pack(fill="x", padx=24, pady=(18, 2))
        tk.Label(self, text=T.GLOSSARIO_INTRO, bg=FUNDO, fg=SUAVE, font=(FONTE, 10), anchor="w").pack(fill="x", padx=24)
        linha = tk.Frame(self, bg=FUNDO)
        linha.pack(fill="x", padx=24, pady=8)
        tk.Label(linha, text=T.GLOSSARIO_BUSCA, bg=FUNDO, fg=TEXTO, font=(FONTE, 10, "bold")).pack(side="left")
        self.busca = tk.StringVar()
        self.entrada = ttk.Entry(linha, textvariable=self.busca, width=34, font=(FONTE, 10))
        self.entrada.pack(side="left", padx=8)
        self.busca.trace_add("write", lambda *_: self.montar())
        self.lista = Rolavel(self)
        self.lista.pack(fill="both", expand=True, padx=24, pady=(0, 12))
        self.montar()

    def termos_visiveis(self) -> list[str]:
        q = self.busca.get().strip().lower()
        chaves = sorted(TERMOS, key=lambda k: TERMOS[k][0].lower())
        if not q:
            return chaves
        return [k for k in chaves if q in " ".join(TERMOS[k]).lower()]

    def montar(self) -> None:
        for w in self.lista.interno.winfo_children():
            w.destroy()
        visiveis = self.termos_visiveis()
        if not visiveis:
            tk.Label(self.lista.interno, text=T.GLOSSARIO_NADA, bg=FUNDO, fg=SUAVE, font=(FONTE, 10)).pack(anchor="w", pady=10)
        for chave in visiveis:
            nome, ingles, definicao, exemplo = TERMOS[chave]
            c = cartao(self.lista.interno, "")
            c.pack(fill="x", pady=4)
            tk.Label(c, text=f"{nome}  ({ingles})", bg=CARTAO, fg=TEXTO, font=(FONTE, 11, "bold"), anchor="w").pack(fill="x")
            tk.Label(c, text=definicao, bg=CARTAO, fg=TEXTO, font=(FONTE, 10), anchor="w", justify="left", wraplength=900).pack(fill="x", pady=(2, 0))
            tk.Label(c, text=T.GLOSSARIO_EXEMPLO.format(exemplo=exemplo), bg=CARTAO, fg=SUAVE, font=(FONTE, 9), anchor="w",
                     justify="left", wraplength=900).pack(fill="x")
        self.visiveis = visiveis                 # usado pelos testes de interface


class TelaSobre(tk.Frame):
    def __init__(self, janela) -> None:
        super().__init__(janela.conteudo, bg=FUNDO)
        tk.Label(self, text=T.SOBRE_TITULO, bg=FUNDO, fg=TEXTO, font=(FONTE, 18, "bold"), anchor="w").pack(fill="x", padx=24, pady=(18, 8))
        area = Rolavel(self)
        area.pack(fill="both", expand=True, padx=24, pady=(0, 12))
        for titulo, corpo in T.SOBRE_BLOCOS:
            c = cartao(area.interno, titulo)
            c.pack(fill="x", pady=5)
            TextoRico(c, ao_termo=janela.definir_termo).definir(corpo).pack(fill="x", pady=(4, 0))
        tk.Label(area.interno, text=T.SOBRE_VERSAO.format(versao=VERSAO), bg=FUNDO, fg=SUAVE, font=(FONTE, 9), anchor="w").pack(fill="x", pady=8)
