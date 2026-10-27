"""Estado compartilhado da janela do Laboratório: fonte de dados, conjuntos carregados e resultados em cache."""
from __future__ import annotations

from lab.dados import BancoIlegivel, Conjunto, SemBanco, carregar_real, verificar_minimos
from dataclasses import replace

from lab.progresso import Progresso
from lab.sintetico import ParametrosSinteticos, gerar


def carregar_historico(progresso=None, cancelar=None) -> tuple[Conjunto | None, str | None]:
    """Para rodar em `Tarefa`: devolve (conjunto, None) ou (None, mensagem de erro em português)."""
    if progresso:
        progresso(0.2, "Lendo o histórico (somente leitura)")
    try:
        return carregar_real(), None
    except (SemBanco, BancoIlegivel) as e:
        return None, str(e)


class Estado:
    def __init__(self, progresso: Progresso | None = None) -> None:
        self.progresso = progresso or Progresso()
        self.real: Conjunto | None = None
        self.erro_real: str | None = None
        self.real_carregado = False
        self.params = ParametrosSinteticos()
        self.params_do_aprendiz = False          # True depois que ele mexe nos controles da lição 3
        self._sint: dict[int | None, tuple[tuple, Conjunto]] = {}
        self.fonte = "sintetico"
        self.cache: dict[tuple, object] = {}

    # ---- fontes ----
    def definir_real(self, conj: Conjunto | None, erro: str | None, escolher_fonte: bool = True) -> None:
        """Guarda o histórico lido. Só troca a fonte para "real" quando `escolher_fonte` (na tela Início); no meio de uma
        lição os dados em uso não mudam por baixo do aprendiz."""
        self.real, self.erro_real, self.real_carregado = conj, erro, True
        # padrão: histórico real se ele bastar para a lição 1, a menos que o aprendiz já tenha escolhido sintético
        if escolher_fonte and conj is not None and verificar_minimos(conj, 1)[0] and self.progresso.fonte != "sintetico":
            self.fonte = "real"

    def trocar_fonte(self, fonte: str) -> None:
        if fonte not in ("real", "sintetico"):
            raise ValueError(fonte)
        self.fonte = fonte
        self.progresso.fonte = fonte

    def params_licao(self, licao: int | None) -> ParametrosSinteticos:
        """Parâmetros sintéticos para a lição. A lição 2 precisa de ≥ 21 dias, episódios escondidos para achar e
        poeira para a tendência: se o aprendiz não escolheu valores na lição 3, usa os padrões da lição (21 dias, 0,2 °C/dia
        e 10 episódios). Se ele escolheu, os valores dele valem, inclusive zero."""
        if licao not in (2, 4, 5) or self.params_do_aprendiz:
            return self.params
        p = self.params
        if licao == 2:
            return replace(p, dias=max(p.dias, 21), episodios=p.episodios or 10,
                           poeira_por_dia=p.poeira_por_dia or 0.2)
        # lições 4 e 5: 21 dias, sem episódios nem poeira (a classe rara vem do calor do próprio uso, e os grupos não se misturam com a deriva)
        return replace(p, dias=max(p.dias, 21), episodios=0, poeira_por_dia=0.0)

    def conjunto(self, licao: int | None = None) -> Conjunto:
        if self.fonte == "real" and self.real is not None:
            return self.real
        return self.sintetico(licao)

    def sintetico(self, licao: int | None = None) -> Conjunto:
        """Dados sintéticos com os parâmetros atuais, sempre (a lição 3 só trabalha com eles)."""
        params = self.params_licao(licao)
        chave = tuple(sorted(params.como_dicionario().items()))
        if licao not in self._sint or self._sint[licao][0] != chave:
            self._sint[licao] = (chave, gerar(params))
        return self._sint[licao][1]

    def chave_dados(self, licao: int | None = None) -> tuple:
        """Identifica os dados atuais para o cache de resultados."""
        c = self.conjunto(licao)
        if c.origem == "real":
            return ("real", c.n, int(c.ts[-1]) if c.n else 0)
        return ("sintetico", tuple(sorted(self.params_licao(licao).como_dicionario().items())))

    def usar_sintetico(self, params: ParametrosSinteticos | None = None) -> None:
        if params is not None:
            params.validar()
            self.params = params
        self.trocar_fonte("sintetico")

    def descricao_fonte(self, licao: int | None = None) -> str:
        c = self.conjunto(licao)
        origem = "Meu histórico" if c.origem == "real" else "Dados sintéticos"
        return f"{origem} · {c.n:,} minutos · {c.dias:.0f} dias".replace(",", ".")

    # ---- cache ----
    def guardar(self, nome: str, chave_extra: tuple, valor, licao: int | None = None, chave_dados: tuple | None = None) -> None:
        """`chave_dados` deve ser a chave calculada na LARGADA do treino: se os dados mudarem enquanto ele roda,
        o resultado não pode ser guardado sob a chave dos dados novos."""
        self.cache[(nome, chave_dados or self.chave_dados(licao), chave_extra)] = valor

    def buscar(self, nome: str, chave_extra: tuple = (), licao: int | None = None):
        return self.cache.get((nome, self.chave_dados(licao), chave_extra))
