"""Trabalho pesado em segundo plano, com progresso e cancelamento, sem travar a janela (tkinter só na thread principal)."""
from __future__ import annotations

import queue
import threading
from typing import Callable

from lab.modelos import Cancelado


class Tarefa:
    """Roda `funcao(progresso=, cancelar=)` numa thread e avisa a janela por `after`.

    `ao_concluir(resultado)`, `ao_erro(excecao)`, `ao_cancelar()` e `ao_progresso(fracao, texto)` rodam na thread
    da janela. Depois de `cancelar()` nenhum callback de resultado é chamado, só `ao_cancelar`."""

    def __init__(self, raiz, funcao: Callable, ao_concluir: Callable, ao_erro: Callable | None = None,
                 ao_progresso: Callable[[float, str], None] | None = None,
                 ao_cancelar: Callable[[], None] | None = None) -> None:
        self.raiz = raiz
        self.funcao = funcao
        self.ao_concluir, self.ao_erro, self.ao_progresso, self.ao_cancelar = ao_concluir, ao_erro, ao_progresso, ao_cancelar
        self._fila: queue.Queue = queue.Queue()
        self._parar = threading.Event()
        self._thread = threading.Thread(target=self._rodar, daemon=True)
        self._terminou = False

    def iniciar(self) -> "Tarefa":
        self._thread.start()
        self.raiz.after(60, self._ler)
        return self

    def cancelar(self) -> None:
        self._parar.set()

    @property
    def ativa(self) -> bool:
        return not self._terminou

    def _rodar(self) -> None:
        try:
            r = self.funcao(progresso=lambda f, t: self._fila.put(("p", f, t)), cancelar=self._parar.is_set)
            self._fila.put(("ok", r))
        except Cancelado:
            self._fila.put(("cancelado",))
        except Exception as e:                     # o erro volta para a janela, que mostra em português
            self._fila.put(("erro", e))

    def _ler(self) -> None:
        try:
            while True:
                msg = self._fila.get_nowait()
                tipo = msg[0]
                if tipo == "p":
                    if self.ao_progresso and not self._parar.is_set():
                        self.ao_progresso(msg[1], msg[2])
                    continue
                self._terminou = True
                if self._parar.is_set() or tipo == "cancelado":
                    if self.ao_cancelar:
                        self.ao_cancelar()
                elif tipo == "ok":
                    self.ao_concluir(msg[1])
                elif self.ao_erro:
                    self.ao_erro(msg[1])
                return
        except queue.Empty:
            pass
        self.raiz.after(60, self._ler)
