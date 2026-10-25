"""Abre o Laboratório:  python -m lab   (no ambiente do Laboratório).

Opções de desenvolvimento:
  --sintetico        começa com dados sintéticos e não lê o histórico
  --licao N          abre direto a lição N
  --passo K          vai direto ao passo K (a partir de 1) da lição aberta
  --foto ARQUIVO     tira uma captura da janela, grava em ARQUIVO e fecha (conferência visual)
  --espera MS        tempo antes da captura (padrão 2500)
"""
from __future__ import annotations

import argparse
import sys
import tkinter as tk
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:          # os módulos tema.py e linha_do_tempo.py (visual e gráficos) vivem na pasta do app
    sys.path.insert(0, str(RAIZ))

from lab.estado import Estado  # noqa: E402
from lab.progresso import Progresso  # noqa: E402
from lab.ui.janela import Laboratorio  # noqa: E402


def foto(raiz: tk.Tk, caminho: str) -> None:
    from PIL import ImageGrab
    raiz.attributes("-topmost", True)
    raiz.lift()
    raiz.update()
    x, y, w, h = raiz.winfo_rootx(), raiz.winfo_rooty(), raiz.winfo_width(), raiz.winfo_height()
    ImageGrab.grab(bbox=(x, y, x + w, y + h)).save(caminho)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="lab")
    ap.add_argument("--sintetico", action="store_true")
    ap.add_argument("--licao", type=int)
    ap.add_argument("--passo", type=int, default=1)
    ap.add_argument("--foto")
    ap.add_argument("--espera", type=int, default=2500)
    args = ap.parse_args(argv)

    raiz = tk.Tk()
    estado = Estado(Progresso())
    if args.sintetico:
        estado.fonte = "sintetico"
    lab = Laboratorio(raiz, estado, carregar_real=not args.sintetico)
    if args.licao:
        lab.abrir_licao(args.licao)
        if args.passo > 1 and hasattr(lab.atual, "mostrar"):
            lab.atual.mostrar(args.passo - 1)
    if args.foto:
        def tirar_e_fechar() -> None:
            try:
                foto(raiz, args.foto)
            finally:
                raiz.destroy()
        raiz.after(args.espera, tirar_e_fechar)
    raiz.mainloop()


if __name__ == "__main__":
    main()
