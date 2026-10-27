"""Tela inicial: de onde vêm os dados e a lista de lições."""
from __future__ import annotations

import tkinter as tk

from lab import textos as T
from lab.dados import verificar_minimos
from lab.qualidade import analisar, resumo_curto
from lab.ui.passos import botao
from lab.ui.rico import TextoRico
from tema import BORDA, CARTAO, FONTE, FUNDO, GRADE, SUAVE, TEXTO, ZONAS, cartao

LICOES_PRONTAS = {1, 2, 3, 4, 5}
COR_NOTA = {"boa": ZONAS["normal"][1], "regular": ZONAS["atencao"][1], "fraca": ZONAS["quente"][1]}


class TelaInicio(tk.Frame):
    def __init__(self, janela) -> None:
        super().__init__(janela.conteudo, bg=FUNDO)
        self.janela = janela
        self.estado = janela.estado
        self.var_fonte = tk.StringVar(value=self.estado.fonte)

        tk.Label(self, text=T.INICIO_TITULO, bg=FUNDO, fg=TEXTO, font=(FONTE, 18, "bold"), anchor="w").pack(fill="x", padx=24, pady=(18, 2))
        intro = TextoRico(self, ao_termo=janela.definir_termo, fundo=FUNDO)
        intro.definir(T.INICIO_INTRO)
        intro.pack(fill="x", padx=24, pady=(0, 8))

        fonte = cartao(self, T.INICIO_FONTE)
        fonte.pack(fill="x", padx=24, pady=(4, 8))
        linha = tk.Frame(fonte, bg=CARTAO)
        linha.pack(fill="x", pady=(6, 0))
        self.rb_real = tk.Radiobutton(linha, text=T.INICIO_FONTE_REAL, variable=self.var_fonte, value="real", command=self._mudou,
                                      bg=CARTAO, fg=TEXTO, selectcolor=CARTAO, activebackground=CARTAO, font=(FONTE, 10, "bold"))
        self.rb_real.pack(side="left")
        self.rb_sint = tk.Radiobutton(linha, text=T.INICIO_FONTE_SINT, variable=self.var_fonte, value="sintetico", command=self._mudou,
                                      bg=CARTAO, fg=TEXTO, selectcolor=CARTAO, activebackground=CARTAO, font=(FONTE, 10, "bold"))
        self.rb_sint.pack(side="left", padx=(24, 0))
        self.btn_reler = botao(linha, T.INICIO_LER_DE_NOVO, self._reler)
        self.btn_reler.pack(side="right")
        self.info = TextoRico(fonte, ao_termo=janela.definir_termo, fonte=(FONTE, 9), cor=SUAVE)
        self.info.pack(fill="x", pady=(6, 0))
        self.linha_qualidade = tk.Frame(fonte, bg=CARTAO)
        self.lbl_qualidade = tk.Label(self.linha_qualidade, text="", bg=CARTAO, font=(FONTE, 10, "bold"), anchor="w")
        self.lbl_qualidade.pack(side="left")
        botao(self.linha_qualidade, T.QUAL_VER, janela.mostrar_qualidade).pack(side="left", padx=12)

        self.cartoes: dict[int, tuple[tk.Label, tk.Button]] = {}
        for n, (titulo, sub) in T.LICOES.items():
            c = cartao(self, "")
            c.pack(fill="x", padx=24, pady=5)
            linha = tk.Frame(c, bg=CARTAO)
            linha.pack(fill="x")
            texto = tk.Frame(linha, bg=CARTAO)
            texto.pack(side="left", fill="x", expand=True)
            tk.Label(texto, text=titulo, bg=CARTAO, fg=TEXTO, font=(FONTE, 12, "bold"), anchor="w").pack(fill="x")
            tk.Label(texto, text=sub, bg=CARTAO, fg=SUAVE, font=(FONTE, 9), anchor="w").pack(fill="x")
            status = tk.Label(linha, text="", bg=CARTAO, fg=SUAVE, font=(FONTE, 9, "bold"))
            status.pack(side="right", padx=12)
            b = botao(linha, T.BOTAO_ABRIR, lambda k=n: janela.abrir_licao(k), destaque=n in LICOES_PRONTAS)
            b.pack(side="right")
            self.cartoes[n] = (status, b)
        self.atualizar()

    def ao_real_carregado(self) -> None:
        if self.winfo_exists():
            self.var_fonte.set(self.estado.fonte)
            self.atualizar()
            self.janela.atualizar_faixa()

    def _reler(self) -> None:
        """Lê o histórico outra vez (o TempCPU pode ter gravado mais minutos, ou o banco estava em uso)."""
        self.estado.real_carregado = False
        self.atualizar()
        self.janela.iniciar_leitura_real()

    def _mudou(self) -> None:
        self.estado.trocar_fonte(self.var_fonte.get())
        self.atualizar()
        self.janela.atualizar_faixa()

    def atualizar(self) -> None:
        est = self.estado
        real = est.real
        tem_real = real is not None and real.n > 0
        self.rb_real.config(state="normal" if tem_real else "disabled")
        if est.fonte == "real" and not tem_real:
            est.fonte = "sintetico"
            self.var_fonte.set("sintetico")
        if not est.real_carregado:
            info = T.INICIO_REAL_LENDO
        elif tem_real:
            ok, _ = verificar_minimos(real, 1)
            modelo = T.INICIO_REAL_INFO if ok else T.INICIO_REAL_POUCO
            info = modelo.format(minutos=f"{real.n:,}".replace(",", "."), dias=f"{real.dias:.1f}".replace(".", ","))
        else:
            erro = (est.erro_real or "o histórico está vazio").rstrip(". ") + "."
            info = T.INICIO_REAL_NENHUM.format(erro=erro)
        if est.fonte == "sintetico":
            info += "\n" + T.INICIO_SINT_INFO
        self.info.definir(info)
        rel = analisar(real) if tem_real else None
        if rel is not None:
            self.lbl_qualidade.config(text=resumo_curto(rel), fg=COR_NOTA[rel.geral])
            self.linha_qualidade.pack(fill="x", pady=(8, 0))
        else:
            self.linha_qualidade.pack_forget()
        self.relatorio = rel                      # usado pelos testes de interface
        prog = est.progresso
        for n, (status, b) in self.cartoes.items():
            if n not in LICOES_PRONTAS:
                status.config(text=T.LICAO_EM_BREVE)
                b.config(state="disabled", bg=GRADE, fg=SUAVE)
            elif prog.concluida(n):
                status.config(text=T.LICAO_CONCLUIDA, fg=ZONAS["normal"][1])
            else:
                status.config(text=T.LICAO_NAO_INICIADA, fg=SUAVE)
