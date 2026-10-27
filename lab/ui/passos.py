"""Estrutura comum das lições (passos com Anterior/Próximo) e as telas de estado (treinando, erro, poucos dados)."""
from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk
from typing import Callable

from lab import textos as T
from tema import BORDA, CARTAO, FONTE, FUNDO, GRADE, SUAVE, TEXTO, ZONAS, cartao
from lab.ui.rico import TextoRico

COR_ATIVO = "#3f6fb0"
COR_AVISO = ZONAS["atencao"][1]
COR_FEITO = "#4f9d6e"


@dataclass
class Passo:
    titulo: str
    construir: Callable[[tk.Frame, "LicaoPassos"], None]


def botao(pai, texto: str, comando, destaque: bool = False, **kw) -> tk.Button:
    return tk.Button(pai, text=texto, command=comando, relief="flat", bd=0, cursor="hand2", font=(FONTE, 10, "bold" if destaque else "normal"),
                     bg=COR_ATIVO if destaque else GRADE, fg="white" if destaque else TEXTO,
                     activebackground=COR_ATIVO if destaque else BORDA, activeforeground="white" if destaque else TEXTO,
                     padx=14, pady=6, **kw)


class LicaoPassos(tk.Frame):
    """Cabeçalho com os passos numerados, área do passo e botões Anterior / Próximo (Concluir no último)."""

    def __init__(self, janela, numero: int, passos: list[Passo], ao_concluir: Callable[[], None] | None = None) -> None:
        super().__init__(janela.conteudo, bg=FUNDO)
        self.janela = janela
        self.numero = numero
        self.passos = passos
        self.ao_concluir = ao_concluir
        self.indice = 0
        self.visitados = {0}
        titulo, subtitulo = T.LICOES[numero]

        topo = tk.Frame(self, bg=FUNDO)
        topo.pack(fill="x", padx=20, pady=(14, 0))
        tk.Label(topo, text=titulo, bg=FUNDO, fg=TEXTO, font=(FONTE, 15, "bold")).pack(side="left")
        botao(topo, T.BOTAO_VOLTAR_INICIO, janela.mostrar_inicio).pack(side="right")

        self.trilha = tk.Frame(self, bg=FUNDO)
        self.trilha.pack(fill="x", padx=20, pady=(10, 0))
        self.cartao = cartao(self, "")
        self.cartao.pack(fill="both", expand=True, padx=20, pady=10)
        self.titulo_passo = tk.Label(self.cartao, text="", bg=CARTAO, fg=TEXTO, font=(FONTE, 13, "bold"), anchor="w")
        self.titulo_passo.pack(fill="x")
        corpo = tk.Frame(self.cartao, bg=CARTAO)
        corpo.pack(fill="both", expand=True, pady=(8, 0))
        self.rolagem = ttk.Scrollbar(corpo, orient="vertical")
        self.tela = tk.Canvas(corpo, bg=CARTAO, highlightthickness=0, yscrollcommand=self.rolagem.set)
        self.rolagem.config(command=self.tela.yview)
        self.tela.pack(side="left", fill="both", expand=True)
        self.area = tk.Frame(self.tela, bg=CARTAO)
        self._id_area = self.tela.create_window((0, 0), window=self.area, anchor="nw")
        self.area.bind("<Configure>", lambda _e: self._ajustar_rolagem())
        self.tela.bind("<Configure>", lambda _e: self._ajustar_rolagem())
        self.tela.bind("<Enter>", lambda _e: self.tela.bind_all("<MouseWheel>", self._roda))
        self.tela.bind("<Leave>", lambda _e: self.tela.unbind_all("<MouseWheel>"))

        rodape = tk.Frame(self, bg=FUNDO)
        rodape.pack(fill="x", padx=20, pady=(0, 12))
        self.btn_ant = botao(rodape, T.BOTAO_ANTERIOR, lambda: self.ir(-1))
        self.btn_ant.pack(side="left")
        self.btn_prox = botao(rodape, T.BOTAO_PROXIMO, lambda: self.ir(1), destaque=True)
        self.btn_prox.pack(side="right")
        self.mostrar(0)
        self._id_acompanhar = None
        self.bind("<Destroy>", self._parar_acompanhar)
        self._acompanhar()

    def _parar_acompanhar(self, evento=None) -> None:
        if evento is not None and evento.widget is not self:
            return
        if self._id_acompanhar is not None:
            try:
                self.after_cancel(self._id_acompanhar)
            except tk.TclError:
                pass
            self._id_acompanhar = None

    def _acompanhar(self) -> None:
        """Reajusta a rolagem a cada 250 ms: a altura pedida pelo conteúdo muda (textos, resultados que chegam)
        sem gerar evento quando o tamanho da área está forçado."""
        if not self.winfo_exists():
            return
        self._ajustar_rolagem()
        self._id_acompanhar = self.after(250, self._acompanhar)

    def _ajustar_rolagem(self) -> None:
        """A área do passo ocupa a largura toda; se for mais alta que a janela, aparece a barra de rolagem."""
        if not self.tela.winfo_exists():
            return
        largura, altura = self.tela.winfo_width(), self.tela.winfo_height()
        pedida = self.area.winfo_reqheight()
        self.tela.itemconfigure(self._id_area, width=largura, height=max(altura, pedida))
        self.tela.configure(scrollregion=(0, 0, largura, max(altura, pedida)))
        if pedida > altura + 2:
            if not self.rolagem.winfo_ismapped():
                self.rolagem.pack(side="right", fill="y")
        elif self.rolagem.winfo_ismapped():
            self.rolagem.pack_forget()
            self.tela.yview_moveto(0)

    def _roda(self, evento) -> None:
        if self.rolagem.winfo_ismapped():
            self.tela.yview_scroll(-1 * (evento.delta // 120), "units")

    def _desenhar_trilha(self) -> None:
        for w in self.trilha.winfo_children():
            w.destroy()
        por_linha = 7 if len(self.passos) <= 7 else 5            # lições longas quebram a trilha em duas linhas
        linha = None
        for i, p in enumerate(self.passos):
            if i % por_linha == 0:
                linha = tk.Frame(self.trilha, bg=FUNDO)
                linha.pack(anchor="w", pady=(0, 3))
            ativo = i == self.indice
            feito = i in self.visitados and not ativo
            cor = COR_ATIVO if ativo else COR_FEITO if feito else GRADE
            b = tk.Button(linha, text=f"{i + 1}  {p.titulo}", relief="flat", bd=0, cursor="hand2" if i in self.visitados else "arrow",
                          font=(FONTE, 9, "bold" if ativo else "normal"), bg=cor, fg="white" if (ativo or feito) else SUAVE,
                          activebackground=cor, activeforeground="white", padx=10, pady=3,
                          command=(lambda k=i: self.mostrar(k)) if i in self.visitados else (lambda: None))
            b.pack(side="left", padx=(0, 6))

    def mostrar(self, i: int) -> None:
        self.indice = i
        self.visitados.add(i)
        for w in self.area.winfo_children():
            w.destroy()
        passo = self.passos[i]
        self.titulo_passo.config(text=f"{i + 1}. {passo.titulo}")
        self._desenhar_trilha()
        ultimo = i == len(self.passos) - 1
        self.btn_ant.config(state="normal" if i > 0 else "disabled")
        self.btn_prox.config(text=T.BOTAO_CONCLUIR if ultimo else T.BOTAO_PROXIMO)
        self.tela.yview_moveto(0)
        self.janela.cancelar_tarefa()                # trocar de passo encerra o treino do passo anterior
        passo.construir(self.area, self)

    def ir(self, delta: int) -> None:
        novo = self.indice + delta
        if novo >= len(self.passos):
            if self.ao_concluir:
                self.ao_concluir()
            return
        if novo >= 0:
            self.mostrar(novo)

    def aviso_qualidade(self, pai, conj) -> None:
        """Se a lição roda com o histórico real e a qualidade não é boa, avisa e leva ao relatório."""
        if conj.origem != "real":
            return
        from lab.qualidade import analisar
        rel = analisar(conj)
        if rel is None or rel.geral == "boa":
            return
        caixa = tk.Frame(pai, bg=CARTAO)
        caixa.pack(fill="x", pady=(0, 6))
        TextoRico(caixa, ao_termo=self.janela.definir_termo, cor=COR_AVISO).definir(
            T.QUAL_AVISO_LICAO.format(nota=T.QUAL_NOTA[rel.geral].lower(), frase=T.QUAL_GERAL[rel.geral])).pack(fill="x")
        botao(caixa, T.QUAL_VER, self.janela.mostrar_qualidade).pack(anchor="w", pady=(2, 0))
        caixa.aviso_qualidade = rel.geral            # usado pelos testes de interface

    def texto(self, pai, texto: str, **kw) -> TextoRico:
        t = TextoRico(pai, ao_termo=self.janela.definir_termo, **kw).definir(texto)
        t.pack(fill="x", pady=(0, 6))
        return t


# ---------------- telas de estado ----------------
class PainelProgresso(tk.Frame):
    """"Treinando…" com barra de progresso e Cancelar."""

    def __init__(self, pai, ao_cancelar: Callable[[], None]) -> None:
        super().__init__(pai, bg=CARTAO)
        self.rotulo = tk.Label(self, text=T.ESTADO_TREINANDO, bg=CARTAO, fg=TEXTO, font=(FONTE, 11))
        self.rotulo.pack(pady=(40, 8))
        self.barra = ttk.Progressbar(self, length=360, mode="determinate", maximum=100)
        self.barra.pack()
        botao(self, T.BOTAO_CANCELAR, ao_cancelar).pack(pady=14)

    def atualizar(self, fracao: float, texto: str) -> None:
        self.barra["value"] = max(0.0, min(1.0, fracao)) * 100
        self.rotulo.config(text=texto or T.ESTADO_TREINANDO)


def tela_mensagem(pai, texto: str, botoes: list[tuple[str, Callable[[], None], bool]], cor: str = TEXTO) -> tk.Frame:
    """Mensagem centralizada com botões (texto, ação, destaque): usada em erro, cancelado e poucos dados."""
    f = tk.Frame(pai, bg=CARTAO)
    tk.Label(f, text=texto, bg=CARTAO, fg=cor, font=(FONTE, 11), wraplength=620, justify="left").pack(pady=(40, 16))
    linha = tk.Frame(f, bg=CARTAO)
    linha.pack()
    for t, acao, destaque in botoes:
        botao(linha, t, acao, destaque=destaque).pack(side="left", padx=6)
    return f
