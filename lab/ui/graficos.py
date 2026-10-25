"""Gráficos em Canvas (mesmo estilo do histórico do app): área com eixos, linhas, pontos, faixas e legenda."""
from __future__ import annotations

import tkinter as tk

import numpy as np

from linha_do_tempo import ticks_bonitos
from tema import CARTAO, FONTE, GRADE, SUAVE, TEXTO

COR_TREINO = "#6b8fc4"
COR_TESTE = "#d08a4e"
COR_REAL = "#3f4f66"
COR_PREVISTO = "#d08a4e"
COR_FAIXA_TREINO = "#e8eef7"
COR_FAIXA_TESTE = "#fbeedd"
COR_ALERTA_FAIXA = "#f9e2de"
COR_BOM = "#4f9d6e"


def reduzir(x: np.ndarray, y: np.ndarray, n: int = 700) -> tuple[np.ndarray, np.ndarray]:
    """No máximo `n` pontos para desenhar: pega o máximo de cada bloco (preserva picos) e mantém a ordem."""
    if len(x) <= n:
        return x, y
    bloco = int(np.ceil(len(x) / n))
    k = (len(x) // bloco) * bloco
    ys = y[:k].reshape(-1, bloco)
    xs = x[:k].reshape(-1, bloco)
    pos = np.argmax(ys, axis=1)
    linhas = np.arange(len(pos))
    return xs[linhas, pos], ys[linhas, pos]


def reduzir_media(x: np.ndarray, y: np.ndarray, n: int = 700) -> tuple[np.ndarray, np.ndarray]:
    """No máximo `n` pontos para desenhar, usando a média de cada bloco (para comparar linhas sem favorecer picos)."""
    if len(x) <= n:
        return x, y
    bloco = int(np.ceil(len(x) / n))
    k = (len(x) // bloco) * bloco
    return x[:k].reshape(-1, bloco).mean(axis=1), y[:k].reshape(-1, bloco).mean(axis=1)


class Area:
    """Converte coordenadas de dados em pixels e desenha eixos e séries num Canvas."""

    def __init__(self, cv: tk.Canvas, margem: tuple[int, int, int, int] = (54, 14, 16, 36)) -> None:
        self.cv = cv
        self.esq, self.dir_, self.topo, self.base = margem
        self.x0, self.x1, self.y0, self.y1 = 0.0, 1.0, 0.0, 1.0

    # ---- geometria ----
    @property
    def largura(self) -> float:
        return self.cv.winfo_width() - self.esq - self.dir_

    @property
    def altura(self) -> float:
        return self.cv.winfo_height() - self.topo - self.base

    def pronto(self) -> bool:
        return self.cv.winfo_width() > 120 and self.cv.winfo_height() > 90

    def definir(self, x0: float, x1: float, y0: float, y1: float) -> None:
        self.x0, self.x1, self.y0, self.y1 = x0, (x1 if x1 > x0 else x0 + 1), y0, (y1 if y1 > y0 else y0 + 1)

    def px(self, x) -> float:
        return self.esq + (x - self.x0) / (self.x1 - self.x0) * self.largura

    def py(self, y) -> float:
        return self.topo + (self.y1 - y) / (self.y1 - self.y0) * self.altura

    # ---- desenho ----
    def eixos(self, x_ticks: list[tuple[float, str]] | None = None, rotulo_y: str = "", casas_y: int = 0,
              grade: bool = True) -> None:
        cv = self.cv
        for v in ticks_bonitos(self.y0, self.y1, 5):
            if grade:
                cv.create_line(self.esq, self.py(v), self.esq + self.largura, self.py(v), fill=GRADE)
            cv.create_text(self.esq - 6, self.py(v), text=f"{v:.{casas_y}f}".replace(".", ","), anchor="e", fill=SUAVE,
                           font=(FONTE, 8))
        for v, rotulo in (x_ticks or []):
            x = self.px(v)
            cv.create_line(x, self.topo + self.altura, x, self.topo + self.altura + 4, fill=SUAVE)
            cv.create_text(x, self.topo + self.altura + 15, text=rotulo, fill=SUAVE, font=(FONTE, 8))
        if rotulo_y:
            cv.create_text(6, self.topo - 4, text=rotulo_y, anchor="nw", fill=SUAVE, font=(FONTE, 8, "bold"))
        cv.create_line(self.esq, self.topo, self.esq, self.topo + self.altura, fill=SUAVE)
        cv.create_line(self.esq, self.topo + self.altura, self.esq + self.largura, self.topo + self.altura, fill=SUAVE)

    def faixa_x(self, xa: float, xb: float, cor: str, rotulo: str = "", cor_texto: str = SUAVE) -> None:
        a, b = self.px(max(xa, self.x0)), self.px(min(xb, self.x1))
        if b <= a:
            return
        self.cv.create_rectangle(a, self.topo, b, self.topo + self.altura, fill=cor, width=0)
        if rotulo:
            self.cv.create_text((a + b) / 2, self.topo + 10, text=rotulo, fill=cor_texto, font=(FONTE, 8, "bold"))

    def linha(self, xs, ys, cor: str, largura: int = 2, tracejado: tuple[int, ...] | None = None) -> None:
        if len(xs) < 2:
            return
        pts = [c for x, y in zip(xs, ys) for c in (self.px(x), self.py(y))]
        self.cv.create_line(*pts, fill=cor, width=largura, dash=tracejado)

    def linha_com_quebras(self, xs, ys, cor: str, largura: int = 2, lacuna: float = 120.0) -> None:
        """Como `linha`, mas não liga pontos separados por um buraco maior que `lacuna` no eixo x (noites, pausas)."""
        inicio = 0
        for i in range(1, len(xs) + 1):
            if i == len(xs) or xs[i] - xs[i - 1] > lacuna:
                self.linha(xs[inicio:i], ys[inicio:i], cor, largura)
                inicio = i

    def pontos(self, xs, ys, cor: str, raio: float = 2.0) -> None:
        for x, y in zip(xs, ys):
            px, py = self.px(x), self.py(y)
            self.cv.create_oval(px - raio, py - raio, px + raio, py + raio, fill=cor, outline="")

    def vertical(self, x: float, cor: str, largura: int = 1, tracejado: tuple[int, ...] | None = None) -> None:
        self.cv.create_line(self.px(x), self.topo, self.px(x), self.topo + self.altura, fill=cor, width=largura, dash=tracejado)

    def horizontal(self, y: float, cor: str, largura: int = 1, tracejado: tuple[int, ...] | None = None) -> None:
        self.cv.create_line(self.esq, self.py(y), self.esq + self.largura, self.py(y), fill=cor, width=largura, dash=tracejado)

    def legenda(self, itens: list[tuple[str, str]], x: float | None = None, y: float = 8) -> None:
        x = self.esq + 4 if x is None else x
        for cor, texto in itens:
            self.cv.create_line(x, y, x + 16, y, fill=cor, width=3)
            t = self.cv.create_text(x + 21, y, text=texto, anchor="w", fill=TEXTO, font=(FONTE, 8, "bold"))
            x = self.cv.bbox(t)[2] + 16

    def mensagem(self, texto: str) -> None:
        self.cv.create_text(self.cv.winfo_width() / 2, self.cv.winfo_height() / 2, text=texto, fill=SUAVE,
                            font=(FONTE, 10))


def novo_canvas(pai: tk.Widget, altura: int = 260) -> tk.Canvas:
    return tk.Canvas(pai, bg=CARTAO, highlightthickness=0, height=altura)


def barras_horizontais(cv: tk.Canvas, itens: list[tuple[str, float, str]], formato=lambda v: f"{v:.1f}".replace(".", ","),
                       rotulo_largura: int = 190) -> None:
    """Barras horizontais com rótulo à esquerda e valor à direita: itens = (rótulo, valor, cor)."""
    cv.delete("all")
    w, h = cv.winfo_width(), cv.winfo_height()
    if w < 200 or h < 60 or not itens:
        return
    topo = max(v for _, v, _ in itens) or 1.0
    linha = (h - 16) / len(itens)
    larg = w - rotulo_largura - 70
    for i, (rotulo, valor, cor) in enumerate(itens):
        y = 8 + i * linha
        cv.create_text(rotulo_largura - 8, y + linha / 2, text=rotulo, anchor="e", fill=TEXTO, font=(FONTE, 9))
        comp = max(2.0, larg * max(valor, 0) / topo)
        cv.create_rectangle(rotulo_largura, y + linha * 0.2, rotulo_largura + comp, y + linha * 0.8, fill=cor, width=0)
        cv.create_text(rotulo_largura + comp + 6, y + linha / 2, text=formato(valor), anchor="w", fill=TEXTO,
                       font=(FONTE, 9, "bold"))


def barras_verticais(cv: tk.Canvas, valores: list[float], rotulos: list[str], cor: str = COR_TREINO, passo_rotulo: int = 1) -> None:
    """Barras verticais com grade e rótulos embaixo (a cada `passo_rotulo` barras)."""
    cv.delete("all")
    w, h = cv.winfo_width(), cv.winfo_height()
    if w < 120 or h < 80 or not valores:
        return
    esq, dir_, topo, base = 46, 8, 10, 26
    teto = max(max(valores), 1)
    ticks = ticks_bonitos(0, teto, 4)
    teto = max(ticks[-1], teto)
    altura = h - topo - base
    for v in ticks:
        y = topo + altura * (1 - v / teto)
        cv.create_line(esq, y, w - dir_, y, fill=GRADE)
        cv.create_text(esq - 5, y, text=f"{v:,.0f}".replace(",", "."), anchor="e", fill=SUAVE, font=(FONTE, 8))
    larg = (w - esq - dir_) / len(valores)
    for i, v in enumerate(valores):
        x0 = esq + i * larg + larg * 0.15
        x1 = esq + (i + 1) * larg - larg * 0.15
        y = topo + altura * (1 - v / teto)
        cv.create_rectangle(x0, y, x1, topo + altura, fill=cor, width=0)
        if i % passo_rotulo == 0:
            cv.create_text((x0 + x1) / 2, h - base + 12, text=rotulos[i], fill=SUAVE, font=(FONTE, 8))
    cv.create_line(esq, topo + altura, w - dir_, topo + altura, fill=SUAVE)
