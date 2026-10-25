"""Ícone na área de notificação: temperatura em número sobre a cor da zona."""
from __future__ import annotations

from typing import Callable

import pystray
from PIL import Image, ImageDraw, ImageFont

CINZA = "#9aa5b4"
_fontes: dict[int, ImageFont.FreeTypeFont] = {}


def _fonte(tamanho: int) -> ImageFont.FreeTypeFont:
    if tamanho not in _fontes:
        try:
            _fontes[tamanho] = ImageFont.truetype("segoeuib.ttf", tamanho)
        except OSError:
            _fontes[tamanho] = ImageFont.load_default(tamanho)
    return _fontes[tamanho]


def _misturar(cor: str, com: tuple[int, int, int], parte: float) -> tuple[int, int, int]:
    """Mistura `cor` (#rrggbb) com `com`; parte=0.8 deixa 80% de `com`."""
    r, g, b = (int(cor[i:i + 2], 16) for i in (1, 3, 5))
    return tuple(round(c * (1 - parte) + k * parte) for c, k in zip((r, g, b), com))


def desenhar_icone(texto: str, cor: str, estilo: str = "forte") -> Image.Image:
    """64×64. "forte": quadrado na cor da zona com número branco (bandeja, 16 px).
    "suave" (barra de tarefas): fundo pastel, número na cor da zona e uma tira colorida na base."""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    tamanho = 44 if len(texto) <= 2 else 32
    if estilo == "suave":
        d.rounded_rectangle((0, 0, 63, 63), radius=14, fill=cor)                              # tira da base
        d.rounded_rectangle((0, 0, 63, 53), radius=14, fill=_misturar(cor, (255, 255, 255), 0.82))
        d.rectangle((0, 40, 63, 53), fill=_misturar(cor, (255, 255, 255), 0.82))
        d.text((32, 27), texto, font=_fonte(tamanho - 6), fill=_misturar(cor, (0, 0, 0), 0.3), anchor="mm")
    else:
        d.rounded_rectangle((0, 0, 63, 63), radius=14, fill=cor)
        d.text((32, 33), texto, font=_fonte(tamanho), fill="white", anchor="mm")
    return img


class Bandeja:
    """Envolve o pystray. Callbacks rodam na thread do pystray: quem chama deve repassar à janela."""

    def __init__(self, ao_abrir: Callable[[], None], ao_alternar_monitor: Callable[[], None],
                 monitor_ativo: Callable[[], bool], ao_alternar_inicio: Callable[[], None],
                 inicio_ativo: Callable[[], bool], ao_sair: Callable[[], None],
                 ao_historico: Callable[[], None] | None = None,
                 ao_laboratorio: Callable[[], None] | None = None) -> None:
        menu = pystray.Menu(
            pystray.MenuItem("Abrir TempCPU", lambda: ao_abrir(), default=True),
            pystray.MenuItem("Histórico", lambda: (ao_historico or ao_abrir)()),
            pystray.MenuItem("Laboratório", lambda: (ao_laboratorio or ao_abrir)()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Monitoramento ativo", lambda: ao_alternar_monitor(),
                             checked=lambda _i: monitor_ativo()),
            pystray.MenuItem("Iniciar com o Windows", lambda: ao_alternar_inicio(),
                             checked=lambda _i: inicio_ativo()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Sair", lambda: ao_sair()),
        )
        self._chave = ("--", CINZA)
        self.icone = pystray.Icon("TempCPU", desenhar_icone("--", CINZA), "TempCPU — iniciando…", menu)

    def iniciar(self) -> None:
        self.icone.run_detached()

    def mostrar(self, texto: str, cor: str, dica: str) -> None:
        """Só redesenha quando número ou cor mudam (evita trabalho de GDI a cada leitura)."""
        if (texto, cor) != self._chave:
            self._chave = (texto, cor)
            self.icone.icon = desenhar_icone(texto, cor)
        if self.icone.title != dica:
            self.icone.title = dica[:127]

    def atualizar_menu(self) -> None:
        self.icone.update_menu()

    def parar(self) -> None:
        self.icone.stop()
