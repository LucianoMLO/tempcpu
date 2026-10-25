"""Três perguntas de fixação ao final de cada lição: alternativas, resposta com explicação e placar."""
from __future__ import annotations

import tkinter as tk

from lab import textos as T
from lab.ui.passos import botao
from lab.ui.rico import TextoRico
from tema import CARTAO, FONTE, SUAVE, TEXTO, ZONAS


class Quiz(tk.Frame):
    def __init__(self, pai, janela, licao: int, perguntas: list[dict]) -> None:
        super().__init__(pai, bg=CARTAO)
        self.janela, self.licao, self.perguntas = janela, licao, perguntas
        self.respondidas: dict[int, bool] = {}
        self.vars: list[tk.IntVar] = []
        self.botoes: list[tk.Button] = []
        self.feedbacks: list[TextoRico] = []
        self.opcoes: list[list[tk.Radiobutton]] = []
        tk.Label(self, text=T.QUIZ_TITULO, bg=CARTAO, fg=TEXTO, font=(FONTE, 11, "bold"), anchor="w").pack(fill="x", pady=(6, 4))
        for i, q in enumerate(perguntas):
            bloco = tk.Frame(self, bg=CARTAO)
            bloco.pack(fill="x", pady=(2, 6))
            TextoRico(bloco, ao_termo=janela.definir_termo, fonte=(FONTE, 10, "bold")).definir(f"{i + 1}. {q['pergunta']}").pack(fill="x")
            var = tk.IntVar(value=-1)
            self.vars.append(var)
            radios = []
            for k, opcao in enumerate(q["opcoes"]):
                linha = tk.Frame(bloco, bg=CARTAO)
                linha.pack(fill="x")
                rb = tk.Radiobutton(linha, variable=var, value=k, bg=CARTAO, activebackground=CARTAO, selectcolor=CARTAO)
                rb.pack(side="left", anchor="n")
                TextoRico(linha, ao_termo=janela.definir_termo, fonte=(FONTE, 10)).definir(opcao).pack(side="left", fill="x", expand=True)
                radios.append(rb)
            self.opcoes.append(radios)
            linha = tk.Frame(bloco, bg=CARTAO)
            linha.pack(fill="x", pady=(2, 0))
            b = botao(linha, T.BOTAO_RESPONDER, lambda n=i: self.responder(n))
            b.pack(side="left")
            self.botoes.append(b)
            fb = TextoRico(linha, ao_termo=janela.definir_termo, fonte=(FONTE, 10))
            fb.pack(side="left", fill="x", expand=True, padx=10)
            self.feedbacks.append(fb)
        self.placar = tk.Label(self, text="", bg=CARTAO, fg=SUAVE, font=(FONTE, 10, "bold"), anchor="w")
        self.placar.pack(fill="x", pady=(2, 0))

    def responder(self, i: int) -> None:
        escolha = self.vars[i].get()
        if escolha < 0 or i in self.respondidas:
            return
        q = self.perguntas[i]
        acertou = escolha == q["correta"]
        self.respondidas[i] = acertou
        self.janela.estado.progresso.registrar_acerto(self.licao, i, acertou)
        prefixo = T.QUIZ_ACERTOU if acertou else T.QUIZ_ERROU
        self.feedbacks[i].definir(f"**{prefixo}**{q['explicacao']}")
        self.feedbacks[i].configure(fg=ZONAS["normal"][1] if acertou else ZONAS["quente"][1])
        self.botoes[i].config(state="disabled")
        for rb in self.opcoes[i]:
            rb.config(state="disabled")
        certas = sum(1 for v in self.respondidas.values() if v)
        self.placar.config(text=T.QUIZ_PLACAR.format(a=certas, n=len(self.perguntas)) if len(self.respondidas) == len(self.perguntas) else "")
