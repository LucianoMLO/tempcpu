"""Janela principal do Laboratório: navegação, faixa de dados sintéticos, barra do glossário e treino em segundo plano."""
from __future__ import annotations

import tkinter as tk
from typing import Callable

from lab import textos as T
from lab.dados import verificar_minimos
from lab.estado import Estado, carregar_historico
from lab.glossario import definicao
from lab.progresso import Progresso
from lab.tarefa import Tarefa
from lab.ui.passos import PainelProgresso, tela_mensagem
from tema import BORDA, CARTAO, FONTE, FUNDO, SUAVE, TEXTO, ZONAS


class Laboratorio:
    def __init__(self, raiz: tk.Tk, estado: Estado | None = None, progresso: Progresso | None = None,
                 carregar_real: bool = True) -> None:
        self.raiz = raiz
        self.estado = estado or Estado(progresso)
        self.tarefa_atual: Tarefa | None = None
        raiz.title(T.TITULO_JANELA)
        raiz.configure(bg=FUNDO)
        raiz.geometry("1120x800")
        raiz.minsize(900, 660)

        self.topo = tk.Frame(raiz, bg=CARTAO, highlightbackground=BORDA, highlightthickness=1)
        self.topo.pack(side="top", fill="x")
        for texto, acao in ((T.NAV_INICIO, self.mostrar_inicio), (T.NAV_QUALIDADE, self.mostrar_qualidade),
                            (T.NAV_GLOSSARIO, self.mostrar_glossario), (T.NAV_SOBRE, self.mostrar_sobre)):
            tk.Button(self.topo, text=texto, command=acao, relief="flat", bd=0, bg=CARTAO, fg=TEXTO, activebackground=BORDA,
                      font=(FONTE, 10), padx=14, pady=6, cursor="hand2").pack(side="left")
        tk.Label(self.topo, text="TempCPU · Laboratório", bg=CARTAO, fg=SUAVE, font=(FONTE, 9)).pack(side="right", padx=14)

        self.faixa = tk.Label(raiz, text=T.FAIXA_SINTETICA, bg="#fbeedd", fg="#9a6a2f", font=(FONTE, 9, "bold"), pady=4)
        self.conteudo = tk.Frame(raiz, bg=FUNDO)
        self.barra = tk.Label(raiz, text=T.BARRA_GLOSSARIO_VAZIA, bg=CARTAO, fg=SUAVE, font=(FONTE, 9), anchor="w",
                              justify="left", wraplength=1060, padx=16, pady=6, relief="flat", highlightbackground=BORDA,
                              highlightthickness=1)
        self.barra.pack(side="bottom", fill="x")
        self.faixa_visivel = False
        self.faixa_forcada = False                 # a lição 3 só usa dados de mentira, mesmo com a fonte "real" escolhida
        self.conteudo.pack(fill="both", expand=True)
        raiz.bind("<Configure>", lambda e: self.barra.config(wraplength=max(300, raiz.winfo_width() - 32)) if e.widget is raiz else None)

        self.atual: tk.Frame | None = None
        if carregar_real:
            self.iniciar_leitura_real()
        else:
            self.estado.real_carregado = True
            self.estado.erro_real = "a leitura do histórico está desligada nesta execução."
        self.mostrar_inicio()

    # ---------- navegação ----------
    def _trocar(self, frame: tk.Frame) -> None:
        self.cancelar_tarefa()
        self.faixa_forcada = False
        if self.atual is not None:
            self.atual.destroy()
        self.atual = frame
        frame.pack(fill="both", expand=True)
        self.atualizar_faixa()

    def atualizar_faixa(self) -> None:
        """A faixa "DADOS DE MENTIRA" fica visível sempre que os dados em uso são sintéticos."""
        precisa = self.faixa_forcada or self.estado.conjunto().origem == "sintetico"
        if precisa and not self.faixa_visivel:
            self.faixa.pack(side="top", fill="x", before=self.conteudo)
            self.faixa_visivel = True
        elif not precisa and self.faixa_visivel:
            self.faixa.pack_forget()
            self.faixa_visivel = False

    def mostrar_inicio(self) -> None:
        from lab.ui.tela_inicio import TelaInicio
        self._trocar(TelaInicio(self))

    def mostrar_qualidade(self) -> None:
        from lab.ui.tela_qualidade import TelaQualidade
        self._trocar(TelaQualidade(self))

    def mostrar_glossario(self) -> None:
        from lab.ui.telas_info import TelaGlossario
        self._trocar(TelaGlossario(self))

    def mostrar_sobre(self) -> None:
        from lab.ui.telas_info import TelaSobre
        self._trocar(TelaSobre(self))

    def abrir_licao(self, numero: int) -> None:
        conj = self.estado.conjunto(numero if numero == 2 else None)
        ok, msg = verificar_minimos(conj, numero) if numero in (1, 2) else (True, "")
        if not ok:
            self._trocar(self._tela_poucos_dados(msg))
            return
        if numero == 1:
            from lab.ui.licao1 import criar
        elif numero == 2:
            from lab.ui.licao2 import criar
        else:
            from lab.ui.licao3 import criar
        self._trocar(criar(self))
        if numero == 3:
            self.faixa_forcada = True
            self.atualizar_faixa()

    def _tela_poucos_dados(self, mensagem: str) -> tk.Frame:
        f = tk.Frame(self.conteudo, bg=FUNDO)
        tela_mensagem(f, T.ESTADO_POUCOS_DADOS.format(mensagem=mensagem), [
            (T.BOTAO_USAR_SINTETICOS, self._usar_sinteticos_e_voltar, True),
            (T.QUAL_VER, self.mostrar_qualidade, False),
            (T.BOTAO_VOLTAR_INICIO, self.mostrar_inicio, False)]).pack(fill="both", expand=True, padx=20, pady=20)
        return f

    def _usar_sinteticos_e_voltar(self) -> None:
        self.estado.usar_sintetico()
        self.mostrar_inicio()

    # ---------- glossário ----------
    def definir_termo(self, chave: str | None) -> None:
        if not chave:
            self.barra.config(text=T.BARRA_GLOSSARIO_VAZIA, fg=SUAVE)
            return
        nome, ingles, defin, exemplo = definicao(chave)
        self.barra.config(text=f"{nome} ({ingles}): {defin} Exemplo: {exemplo}", fg=TEXTO)

    # ---------- histórico real ----------
    def iniciar_leitura_real(self) -> None:
        def pronto(r):
            self.estado.definir_real(*r, escolher_fonte=hasattr(self.atual, "ao_real_carregado"))
            if isinstance(self.atual, tk.Frame) and hasattr(self.atual, "ao_real_carregado"):
                self.atual.ao_real_carregado()
        Tarefa(self.raiz, carregar_historico, pronto, ao_erro=lambda e: pronto((None, f"{type(e).__name__}: {e}"))).iniciar()

    # ---------- treino em segundo plano ----------
    def cancelar_tarefa(self) -> None:
        if self.tarefa_atual and self.tarefa_atual.ativa:
            self.tarefa_atual.cancelar()
        self.tarefa_atual = None

    def treinar(self, pai: tk.Frame, nome: str, chave_extra: tuple, funcao: Callable, ao_pronto: Callable,
                refazer: Callable[[], None], licao: int | None = None) -> None:
        """Usa o resultado em cache ou treina em segundo plano mostrando progresso e Cancelar.

        `funcao(progresso=, cancelar=)` devolve o resultado; `ao_pronto(resultado)` roda quando ele existe;
        `refazer()` reconstrói o passo (botão Tentar de novo)."""
        em_cache = self.estado.buscar(nome, chave_extra, licao)
        if em_cache is not None:
            ao_pronto(em_cache)
            return
        self.cancelar_tarefa()                       # nunca deixa um treino antigo gastando CPU em segundo plano
        chave_dados = self.estado.chave_dados(licao)  # fixada agora, na largada
        painel = PainelProgresso(pai, ao_cancelar=self.cancelar_tarefa)
        painel.pack(fill="both", expand=True)
        vivo = lambda: painel.winfo_exists()

        def concluir(r):
            self.estado.guardar(nome, chave_extra, r, licao, chave_dados)
            if vivo():
                painel.destroy()
                ao_pronto(r)

        def erro(e):
            if vivo():
                painel.destroy()
                tela_mensagem(pai, T.ESTADO_ERRO.format(mensagem=str(e)), [
                    (T.BOTAO_TENTAR_DE_NOVO, refazer, True), (T.BOTAO_VOLTAR_INICIO, self.mostrar_inicio, False)],
                    cor=ZONAS["quente"][1]).pack(fill="both", expand=True)

        def cancelado():
            if vivo():
                painel.destroy()
                tela_mensagem(pai, T.ESTADO_CANCELADO, [
                    (T.BOTAO_TENTAR_DE_NOVO, refazer, True), (T.BOTAO_VOLTAR_INICIO, self.mostrar_inicio, False)]
                ).pack(fill="both", expand=True)

        self.tarefa_atual = Tarefa(self.raiz, funcao, concluir, ao_erro=erro,
                                   ao_progresso=lambda f, t: painel.atualizar(f, t) if vivo() else None,
                                   ao_cancelar=cancelado).iniciar()
