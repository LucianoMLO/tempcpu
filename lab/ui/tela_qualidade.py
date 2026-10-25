"""Tela "Meus dados": qualidade do histórico real, em números e em palavras, e o que fazer para melhorar."""
from __future__ import annotations

import tkinter as tk

from lab import textos as T
from lab.qualidade import Relatorio, analisar, frase_da_prontidao
from lab.ui.graficos import COR_TESTE, COR_TREINO, barras_verticais, novo_canvas
from lab.ui.passos import botao
from lab.ui.rico import TextoRico
from lab.ui.telas_info import Rolavel
from tema import CARTAO, FONTE, FUNDO, SUAVE, TEXTO, ZONAS, cartao

COR_NOTA = {"boa": ZONAS["normal"][1], "regular": ZONAS["atencao"][1], "fraca": ZONAS["quente"][1], None: SUAVE}


class TelaQualidade(tk.Frame):
    def __init__(self, janela) -> None:
        super().__init__(janela.conteudo, bg=FUNDO)
        self.janela = janela
        self.relatorio: Relatorio | None = None
        tk.Label(self, text=T.QUAL_TITULO, bg=FUNDO, fg=TEXTO, font=(FONTE, 18, "bold"), anchor="w").pack(fill="x", padx=24, pady=(18, 2))
        TextoRico(self, ao_termo=janela.definir_termo, fundo=FUNDO).definir(T.QUAL_INTRO).pack(fill="x", padx=24, pady=(0, 6))
        self.area = Rolavel(self)
        self.area.pack(fill="both", expand=True, padx=24, pady=(0, 12))
        self.montar()

    def ao_real_carregado(self) -> None:
        if self.winfo_exists():
            self.montar()

    def montar(self) -> None:
        for w in self.area.interno.winfo_children():
            w.destroy()
        est = self.janela.estado
        real = est.real
        rel = analisar(real) if real is not None and real.n > 0 else None
        self.relatorio = rel
        if rel is None:
            motivo = (est.erro_real or "o histórico está vazio.").rstrip(". ") + "."
            if not est.real_carregado:
                motivo = "ainda lendo o histórico."
            tk.Label(self.area.interno, text=T.QUAL_SEM_DADOS.format(motivo=motivo), bg=FUNDO, fg=TEXTO, font=(FONTE, 11),
                     wraplength=900, justify="left", anchor="w").pack(fill="x", pady=10)
            botao(self.area.interno, T.QUAL_LER_DE_NOVO, self._reler).pack(anchor="w")
            return
        self._geral(rel)
        for item in rel.itens:
            self._item(item)
        self._graficos(rel)
        self._prontidao(rel)

    def _reler(self) -> None:
        self.janela.estado.real_carregado = False
        self.montar()
        self.janela.iniciar_leitura_real()

    def _geral(self, rel: Relatorio) -> None:
        c = cartao(self.area.interno, "")
        c.pack(fill="x", pady=(2, 6))
        linha = tk.Frame(c, bg=CARTAO)
        linha.pack(fill="x")
        tk.Label(linha, text=T.QUAL_GERAL_ROTULO.format(nota=T.QUAL_NOTA[rel.geral]), bg=CARTAO, fg=COR_NOTA[rel.geral],
                 font=(FONTE, 14, "bold")).pack(side="left")
        tk.Label(c, text=T.QUAL_GERAL[rel.geral], bg=CARTAO, fg=TEXTO, font=(FONTE, 10), anchor="w", justify="left",
                 wraplength=900).pack(fill="x", pady=(4, 0))

    def _item(self, item) -> None:
        c = cartao(self.area.interno, "")
        c.pack(fill="x", pady=3)
        linha = tk.Frame(c, bg=CARTAO)
        linha.pack(fill="x")
        tk.Label(linha, text=T.QUAL_SIMBOLO[item.nota], bg=CARTAO, fg=COR_NOTA[item.nota], font=(FONTE, 12, "bold"), width=2).pack(side="left")
        tk.Label(linha, text=item.titulo, bg=CARTAO, fg=TEXTO, font=(FONTE, 11, "bold")).pack(side="left")
        if item.nota:
            tk.Label(linha, text=T.QUAL_NOTA[item.nota], bg=CARTAO, fg=COR_NOTA[item.nota], font=(FONTE, 9, "bold")).pack(side="right")
        tk.Label(c, text=item.valor, bg=CARTAO, fg=TEXTO, font=(FONTE, 10, "bold"), anchor="w", justify="left", wraplength=900).pack(fill="x", pady=(2, 0))
        TextoRico(c, ao_termo=self.janela.definir_termo, fonte=(FONTE, 9), cor=SUAVE).definir(item.explicacao).pack(fill="x")
        if item.sugestao and item.nota != "boa":
            TextoRico(c, ao_termo=self.janela.definir_termo, fonte=(FONTE, 9), cor=COR_NOTA[item.nota]).definir(
                f"**{T.QUAL_O_QUE_FAZER}:** {item.sugestao}").pack(fill="x")

    def _graficos(self, rel: Relatorio) -> None:
        grade = tk.Frame(self.area.interno, bg=FUNDO)
        grade.pack(fill="x", pady=6)
        grade.columnconfigure(0, weight=1, uniform="q")
        grade.columnconfigure(1, weight=1, uniform="q")
        for col, (titulo, valores, rotulos, cor, passo) in enumerate((
                (T.QUAL_GRAFICO_HORAS, rel.horas, [f"{h}h" for h in range(24)], COR_TREINO, 3),
                (T.QUAL_GRAFICO_USO, [q for _, q in rel.faixas_uso], [r.split("–")[0] for r, _ in rel.faixas_uso], COR_TESTE, 1))):
            c = cartao(grade, titulo)
            c.grid(row=0, column=col, sticky="nsew", padx=(0, 6) if col == 0 else (6, 0))
            cv = novo_canvas(c, 170)
            cv.pack(fill="x", pady=(6, 0))
            cv.bind("<Configure>", lambda _e, cv=cv, v=valores, r=rotulos, k=cor, p=passo: barras_verticais(cv, v, r, k, p))

    def _prontidao(self, rel: Relatorio) -> None:
        c = cartao(self.area.interno, T.QUAL_PRONTIDAO_TITULO)
        c.pack(fill="x", pady=6)
        for n in (1, 2, 3):
            p = rel.prontidao[n]
            cor = COR_NOTA["boa" if p.recomendada else "regular" if p.pode else "fraca"]
            tk.Label(c, text=frase_da_prontidao(p), bg=CARTAO, fg=cor, font=(FONTE, 10, "bold"), anchor="w").pack(fill="x", pady=(4, 0))
            for m in p.motivos:
                TextoRico(c, ao_termo=self.janela.definir_termo, fonte=(FONTE, 9), cor=SUAVE).definir("•  " + m).pack(fill="x")
        botao(self.area.interno, T.QUAL_VOLTAR, self.janela.mostrar_inicio).pack(anchor="w", pady=8)
