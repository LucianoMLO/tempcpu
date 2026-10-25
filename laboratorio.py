"""Launcher do Laboratório (módulo opcional de machine learning didático; ADR 0004).

Roda no ambiente do app e usa só a biblioteca padrão: NUNCA importar numpy/scikit-learn aqui. O Laboratório
em si (pacote `lab/`) roda em outro processo, no ambiente próprio criado por este módulo.

Estados do ambiente: ausente → (confirmação) → preparando → pronto | falhou.
Antes de instalar, o launcher levanta (só localmente, sem rede) se o computador já tem um Python com
as bibliotecas necessárias; nesse caso oferece usá-lo sem baixar nada.
"""
from __future__ import annotations

import json
import os
import queue
import re
import shutil
import stat
import struct
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

SEM_JANELA = 0x08000000          # CREATE_NO_WINDOW (igual a sistema.py)
VAR_AMBIENTE = "TEMPCPU_LAB_ENV"
MARCADOR = ".tempcpu-lab"        # só apagamos pastas que têm este arquivo (criado por nós)
PYTHON_SUPORTADO = (3, 14)
TAMANHO_TEXTO = "cerca de 240 MB"
ESPACO_MINIMO = 700 * 1024 * 1024  # pacotes baixados + instalados com folga
ETAPAS = ("Criando o ambiente", "Baixando e instalando os pacotes", "Verificando a instalação")

AUSENTE, PREPARANDO, PRONTO, FALHOU = "ausente", "preparando", "pronto", "falhou"


# ---------- caminhos ----------
def pasta_app() -> Path:
    return Path(__file__).resolve().parent


def pasta_ambiente(env: dict | None = None) -> Path:
    env = os.environ if env is None else env
    if env.get(VAR_AMBIENTE):
        return Path(env[VAR_AMBIENTE])
    base = env.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    return Path(base) / "TempCPU" / "lab-env"


def pythonw_do_ambiente(pasta: Path) -> Path:
    return pasta / "Scripts" / "pythonw.exe"


def python_do_ambiente(pasta: Path) -> Path:
    return pasta / "Scripts" / "python.exe"


def arquivo_requisitos() -> Path:
    return pasta_app() / "lab-requirements.txt"


def arquivo_log(pasta: Path) -> Path:
    return pasta.parent / "lab" / "ultimo-erro.log"


# ---------- comandos (puros) ----------
def comando_criar_venv(base_python: Path, pasta: Path) -> list[str]:
    return [str(base_python), "-m", "venv", str(pasta)]


def comando_instalar(py_ambiente: Path, requisitos: Path) -> list[str]:
    return [str(py_ambiente), "-m", "pip", "install", "--require-hashes", "--only-binary=:all:",
            "--no-cache-dir", "--disable-pip-version-check", "--no-input", "--timeout", "30",
            "-r", str(requisitos)]


def comando_verificar(py_ambiente: Path) -> list[str]:
    return [str(py_ambiente), "-c", "import sklearn, tkinter"]


def comando_abrir(pasta: Path) -> list[str]:
    return [str(pythonw_do_ambiente(pasta)), "-m", "lab"]


def pythonw_de(python_exe: Path) -> Path:
    """`pythonw.exe` ao lado de um `python.exe` (sem console); se não houver, o próprio executável."""
    w = python_exe.with_name("pythonw.exe")
    return w if w.is_file() else python_exe


def comando_abrir_com(python_exe: Path) -> list[str]:
    return [str(pythonw_de(python_exe)), "-m", "lab"]


# ---------- verificações (puras) ----------
def motivo_python_nao_suportado(versao=None, bits: int | None = None, plataforma: str | None = None,
                                congelado: bool | None = None) -> str:
    """Texto em português se este Python não serve para criar o ambiente; "" se serve."""
    versao = sys.version_info if versao is None else versao
    bits = struct.calcsize("P") * 8 if bits is None else bits
    plataforma = sys.platform if plataforma is None else plataforma
    congelado = bool(getattr(sys, "frozen", False)) if congelado is None else congelado
    if congelado:
        return "Nesta versão o Laboratório precisa do Python instalado no computador; o app empacotado não o inclui."
    if plataforma != "win32" or bits != 64:
        return "O Laboratório desta versão só funciona no Windows de 64 bits."
    if tuple(versao[:2]) != PYTHON_SUPORTADO:
        return (f"O Laboratório desta versão só é compatível com o Python {PYTHON_SUPORTADO[0]}.{PYTHON_SUPORTADO[1]} "
                f"(este é o {versao[0]}.{versao[1]}). Outras versões ainda não são suportadas.")
    return ""


def python_base() -> Path | None:
    """Python que cria o ambiente: o da instalação (sys.base_prefix), nunca o venv do app."""
    p = Path(sys.base_prefix) / "python.exe"
    return p if p.is_file() else None


def estado_ambiente(pasta: Path) -> str:
    """`pronto` só com o marcador final e o executável; marcador em preparo = sobra de uma tentativa interrompida."""
    m = pasta / MARCADOR
    try:
        conteudo = m.read_text(encoding="utf-8").strip()
    except (OSError, ValueError):       # ValueError: bytes inválidos (UnicodeDecodeError)
        return AUSENTE
    if conteudo == PRONTO and pythonw_do_ambiente(pasta).is_file():
        return PRONTO
    return FALHOU


def pasta_e_nossa(pasta: Path) -> bool:
    return (pasta / MARCADOR).is_file()


def classificar_erro_pip(saida: str) -> str:
    """Traduz a saída do pip numa mensagem em português (ordem importa: o mais específico primeiro)."""
    s = saida.lower()
    if "do not match the hashes" in s or "hash" in s and "expected" in s:
        return ("Um arquivo baixado não confere com o hash esperado, então foi recusado por segurança. "
                "Nada foi instalado. Tente de novo mais tarde; se repetir, a versão fixada pode ter sido alterada.")
    if "no space left" in s or "errno 28" in s:
        return "Não há espaço suficiente no disco. Libere pelo menos 700 MB e tente de novo."
    if "access is denied" in s or "winerror 5" in s or "permission denied" in s:
        return ("O Windows (ou um antivírus) negou o acesso à pasta do Laboratório. "
                "Verifique se o antivírus não está bloqueando e tente de novo.")
    if any(t in s for t in ("connection", "getaddrinfo", "timed out", "max retries", "ssl", "proxy",
                            "temporary failure", "network is unreachable", "name resolution")):
        return "Sem conexão com a internet (ou o servidor de pacotes não respondeu). Conecte-se e tente de novo."
    linhas = [ln.strip() for ln in saida.splitlines() if ln.strip()]
    ultima = linhas[-1][:300] if linhas else "sem detalhes"
    return f"O instalador de pacotes (pip) falhou: {ultima}"


def espaco_livre(pasta: Path) -> int:
    alvo = pasta
    while not alvo.exists() and alvo != alvo.parent:
        alvo = alvo.parent
    return shutil.disk_usage(alvo).free


# ---------- execução ----------
def executar_processo(cmd: list[str], cancelado: threading.Event, guardar: int = 6000) -> tuple[int, str]:
    """Roda `cmd` sem janela; mata o processo se `cancelado` for acionado. Devolve (código, fim da saída)."""
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                            creationflags=SEM_JANELA, text=True, encoding="utf-8", errors="replace")
    partes: list[str] = []

    def ler() -> None:
        for linha in proc.stdout:  # type: ignore[union-attr]
            partes.append(linha)
            while sum(map(len, partes)) > guardar * 2 and len(partes) > 1:
                partes.pop(0)

    t = threading.Thread(target=ler, daemon=True)
    t.start()
    while proc.poll() is None:
        if cancelado.is_set():
            proc.kill()
            proc.wait()
            t.join(2)
            proc.stdout.close()
            return -1, "cancelado"
        try:
            proc.wait(0.2)
        except subprocess.TimeoutExpired:
            pass
    t.join(2)
    proc.stdout.close()
    return proc.returncode, "".join(partes)[-guardar:]


def _forcar_remocao(func, caminho, _exc) -> None:
    try:
        os.chmod(caminho, stat.S_IWRITE)
        func(caminho)
    except OSError:
        pass


def remover_pasta(pasta: Path) -> str:
    """Apaga a pasta do ambiente. Só apaga o que tem o nosso marcador. Devolve "" se deu certo, senão o motivo."""
    if not pasta.exists():
        return ""
    if not pasta_e_nossa(pasta):
        return "A pasta não foi criada pelo Laboratório; por segurança nada foi apagado."
    shutil.rmtree(pasta, onerror=_forcar_remocao)
    if pasta.exists():
        return "Não foi possível apagar tudo. Feche o Laboratório (se estiver aberto) e tente de novo."
    return ""


class Preparo:
    """Cria o ambiente do Laboratório. Os efeitos externos são injetáveis, para testar sem rede."""

    def __init__(self, pasta: Path, base: Path | None, requisitos: Path,
                 executar: Callable[[list[str], threading.Event], tuple[int, str]] = executar_processo,
                 livre: Callable[[Path], int] = espaco_livre,
                 remover: Callable[[Path], str] = remover_pasta,
                 ao_evento: Callable[[str, object], None] | None = None,
                 motivo_python: Callable[[], str] = motivo_python_nao_suportado) -> None:
        self.pasta, self.base, self.requisitos = pasta, base, requisitos
        self._executar, self._livre, self._remover = executar, livre, remover
        self._evento = ao_evento or (lambda _t, _d: None)
        self._motivo_python = motivo_python
        self.cancelado = threading.Event()
        self.estado = AUSENTE
        self.mensagem = ""
        self._thread: threading.Thread | None = None

    def iniciar(self) -> None:
        self._thread = threading.Thread(target=self.executar, daemon=True)
        self._thread.start()

    def cancelar(self) -> None:
        self.cancelado.set()

    def _terminar(self, estado: str, mensagem: str) -> str:
        self.estado, self.mensagem = estado, mensagem
        self._evento("fim", (estado, mensagem))
        return estado

    def _limpar(self) -> str:
        """Remove a pasta parcial; devolve texto extra se não conseguiu."""
        erro = self._remover(self.pasta)
        return f" {erro}" if erro else ""

    def executar(self) -> str:
        """Roda tudo na thread atual e devolve o estado final (`pronto`, `falhou` ou `ausente` se cancelado).
        Qualquer exceção inesperada (ex.: antivírus negando o `Popen`) termina em `falhou`, nunca fica `preparando`."""
        self.estado = PREPARANDO
        try:
            return self._passos()
        except Exception as e:
            try:
                extra = self._limpar()
            except Exception:
                extra = ""
            detalhe = getattr(e, "strerror", None) or str(e) or type(e).__name__
            return self._terminar(FALHOU, f"Erro inesperado ao preparar o Laboratório: {detalhe}. "
                                          f"Se um antivírus estiver bloqueando, libere e tente de novo. "
                                          f"Nada foi mantido.{extra}")

    def _passos(self) -> str:
        motivo = self._motivo_python()
        if motivo:
            return self._terminar(FALHOU, motivo)
        if self.base is None:
            return self._terminar(FALHOU, "Não encontrei o Python da instalação para criar o ambiente.")
        if not self.requisitos.is_file():
            return self._terminar(FALHOU, "O arquivo lab-requirements.txt não foi encontrado ao lado do app.")
        existe = self.pasta.exists()
        vazia = existe and not any(self.pasta.iterdir())
        if existe and not vazia and not pasta_e_nossa(self.pasta):
            return self._terminar(FALHOU, "A pasta do ambiente já existe e tem outro conteúdo; nada foi alterado.")
        if self._livre(self.pasta) < ESPACO_MINIMO:
            return self._terminar(FALHOU, "Não há espaço suficiente no disco. Libere pelo menos 700 MB e tente de novo.")
        sobra = self._remover(self.pasta) if existe and not vazia else ""   # vazia: nada a limpar (e sem marcador)
        if sobra:
            return self._terminar(FALHOU, sobra)

        try:
            self.pasta.mkdir(parents=True, exist_ok=True)
            (self.pasta / MARCADOR).write_text(PREPARANDO, encoding="utf-8")
        except OSError as e:
            return self._terminar(FALHOU, f"Não foi possível criar a pasta do ambiente: {e.strerror or e}")

        passos = [
            (comando_criar_venv(self.base, self.pasta), "Não foi possível criar o ambiente do Python"),
            (comando_instalar(python_do_ambiente(self.pasta), self.requisitos), ""),
            (comando_verificar(python_do_ambiente(self.pasta)),
             "A instalação terminou, mas o ambiente não passou na verificação (scikit-learn e tkinter)"),
        ]
        for i, (cmd, falha) in enumerate(passos):
            if self.cancelado.is_set():
                return self._terminar(AUSENTE, "Cancelado. Nada foi mantido." + self._limpar())
            self._evento("etapa", (i, len(passos), ETAPAS[i]))
            codigo, saida = self._executar(cmd, self.cancelado)
            if self.cancelado.is_set():
                return self._terminar(AUSENTE, "Cancelado. Nada foi mantido." + self._limpar())
            if codigo != 0:
                if i == 1:
                    texto = classificar_erro_pip(saida)
                else:
                    ultima = next((ln.strip() for ln in reversed(saida.splitlines()) if ln.strip()), "sem detalhes")
                    texto = f"{falha}: {ultima[:300]}"
                return self._terminar(FALHOU, texto + " Nada foi mantido." + self._limpar())

        try:
            (self.pasta / MARCADOR).write_text(PRONTO, encoding="utf-8")
        except OSError as e:
            return self._terminar(FALHOU, f"Não foi possível concluir o preparo: {e.strerror or e}" + self._limpar())
        return self._terminar(PRONTO, "Laboratório pronto.")


# ---------- levantamento do que o computador já tem (local: sem rede, sem instalar nada) ----------
PACOTES = ("numpy", "scipy", "scikit-learn")
MINIMOS = {"python": (3, 10), "numpy": (1, 26), "scipy": (1, 11), "scikit-learn": (1, 4)}
ARQ_ESCOLHA = "interpretador.json"
SONDA_TIMEOUT_S = 15

# Sem `-I` de propósito: precisa enxergar pacotes instalados com `--user`. Não importa numpy/scipy/sklearn
# (só lê os metadados), então é rápida.
SONDA_CODIGO = "\n".join((
    "import json, struct, sys",
    "r = {'versao': list(sys.version_info[:3]), 'bits': struct.calcsize('P') * 8, 'tkinter': False, 'pacotes': {},",
    "     'prefixo': sys.base_prefix}",
    "try:",
    "    import tkinter",
    "    r['tkinter'] = True",
    "except Exception:",
    "    pass",
    "from importlib import metadata",
    "for n in ('numpy', 'scipy', 'scikit-learn'):",
    "    try:",
    "        r['pacotes'][n] = metadata.version(n)",
    "    except Exception:",
    "        r['pacotes'][n] = None",
    "print('SONDA=' + json.dumps(r))",
))


@dataclass
class Avaliacao:
    pronto: bool
    itens: list[tuple[str, str, str]]       # (nome, estado: ok|ausente|antiga|erro, texto para a tela)
    divergente: bool = False                # pronto, mas com versões diferentes das testadas
    python: str = ""                        # "3.14.3"
    versoes: dict = field(default_factory=dict)


@dataclass
class Achado:
    caminho: Path
    info: dict
    aval: Avaliacao


@dataclass
class Decisao:
    tipo: str                               # ambiente | existente | oferecer | preparar
    python: Path | None = None
    achado: Achado | None = None
    achados: list[Achado] = field(default_factory=list)


def parse_py_0p(texto: str) -> list[Path]:
    """Caminhos dos Pythons listados por `py -0p` (formatos `-V:3.14[-64] * <caminho>` e `-3.12-64  <caminho> *`)."""
    saida: list[Path] = []
    for ln in texto.splitlines():
        s = ln.strip()
        if not s.startswith("-"):
            continue
        partes = s.split(None, 1)
        if len(partes) < 2:
            continue
        resto = partes[1].strip()
        if resto.startswith("*"):
            resto = resto[1:].strip()
        if resto.endswith(" *"):
            resto = resto[:-2].strip()
        if resto.lower().endswith(".exe"):
            saida.append(Path(resto))
    return saida


def parse_versao(txt) -> tuple[int, ...]:
    nums: list[int] = []
    for parte in str(txt).split("."):
        m = re.match(r"\d+", parte)
        if not m:
            break
        nums.append(int(m.group()))
    return tuple(nums)


def _txt_versao(v: tuple[int, ...]) -> str:
    return ".".join(map(str, v))


def versoes_fixadas(texto: str | None = None) -> dict[str, str]:
    """Versões testadas, lidas de lab-requirements.txt ({"numpy": "2.5.4", ...})."""
    if texto is None:
        try:
            texto = arquivo_requisitos().read_text(encoding="utf-8")
        except OSError:
            return {}
    achados = re.findall(r"(?m)^([A-Za-z0-9_.\-]+)==([^\s\\]+)", texto)
    return {nome.lower().replace("_", "-"): ver for nome, ver in achados}


def avaliar_sonda(info, fixadas: dict[str, str] | None = None) -> Avaliacao:
    """Decide, a partir do JSON da sonda, se aquele Python já serve (Python ≥ 3.10 de 64 bits, tkinter,
    numpy ≥ 1.26, scipy ≥ 1.11, scikit-learn ≥ 1.4)."""
    if not isinstance(info, dict) or "versao" not in info:
        motivo = info.get("erro", "não respondeu") if isinstance(info, dict) else "não respondeu"
        return Avaliacao(False, [("Python", "erro", f"não foi possível consultar ({motivo})")])
    ver = tuple(int(x) for x in info["versao"])
    bits = info.get("bits")
    pv = _txt_versao(ver)
    itens: list[tuple[str, str, str]] = []
    if ver[:2] < MINIMOS["python"]:
        itens.append(("Python", "antiga", f"versão antiga ({pv}; precisa {_txt_versao(MINIMOS['python'])} ou mais)"))
    elif bits != 64:
        itens.append(("Python", "antiga", f"{pv} de {bits} bits (precisa 64 bits)"))
    else:
        itens.append(("Python", "ok", f"presente ({pv})"))
    itens.append(("tkinter", "ok", "presente") if info.get("tkinter") else ("tkinter", "ausente", "ausente"))
    pacotes = info.get("pacotes") or {}
    versoes = {"python": pv}
    for nome in PACOTES:
        v = pacotes.get(nome)
        if not v:
            itens.append((nome, "ausente", "ausente"))
            continue
        versoes[nome] = v
        minimo = MINIMOS[nome]
        if parse_versao(v) < minimo:
            itens.append((nome, "antiga", f"versão antiga ({v}; precisa {_txt_versao(minimo)} ou mais)"))
        else:
            itens.append((nome, "ok", f"presente ({v})"))
    pronto = all(estado == "ok" for _n, estado, _t in itens)
    divergente = False
    if pronto and fixadas:
        divergente = ver[:2] != PYTHON_SUPORTADO or any(
            fixadas.get(n) and pacotes.get(n) != fixadas[n] for n in PACOTES)
    return Avaliacao(pronto, itens, divergente, pv, versoes)


def aviso_divergente(fixadas: dict[str, str] | None = None) -> str:
    f = fixadas or {}
    testadas = f"Python {_txt_versao(PYTHON_SUPORTADO)}" + "".join(f", {n} {f[n]}" for n in PACOTES if n in f)
    return (f"As versões encontradas são diferentes das que testamos ({testadas}). "
            "Funciona, mas os números das lições podem variar um pouco.")


def _rodar_sonda(py: Path, timeout: float):
    return subprocess.run([str(py), "-c", SONDA_CODIGO], capture_output=True, text=True, timeout=timeout,
                          creationflags=SEM_JANELA, stdin=subprocess.DEVNULL, encoding="utf-8", errors="replace")


def sondar_interpretador(py: Path, rodar=_rodar_sonda) -> dict:
    """Roda a sonda curta no Python `py`. Devolve o JSON da sonda ou {"erro": "..."}."""
    try:
        r = rodar(py, SONDA_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return {"erro": f"não respondeu em {SONDA_TIMEOUT_S} s"}
    except OSError as e:
        return {"erro": str(e.strerror or e)}
    for ln in reversed((r.stdout or "").splitlines()):
        if ln.startswith("SONDA="):
            try:
                return json.loads(ln[len("SONDA="):])
            except ValueError:
                break
    return {"erro": "resposta inesperada"}


def _py_0p() -> str:
    try:
        r = subprocess.run(["py", "-0p"], capture_output=True, text=True, timeout=10, creationflags=SEM_JANELA,
                           stdin=subprocess.DEVNULL, encoding="utf-8", errors="replace")
        return r.stdout or ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def _candidato_valido(p: Path) -> bool:
    """Existe e não é o atalho vazio da Microsoft Store (que abriria a loja ao ser executado)."""
    try:
        if not p.is_file():
            return False
        return not ("windowsapps" in str(p).lower() and p.stat().st_size == 0)
    except OSError:
        return False


def candidatos(listar: Callable[[], str] = _py_0p, base: Path | None = None, no_path: str | None = None,
               valido: Callable[[Path], bool] = _candidato_valido) -> list[Path]:
    """Interpretadores possíveis: `py -0p`, o Python da instalação do app e o `python` do PATH (sem repetir)."""
    brutos = parse_py_0p(listar())
    base = python_base() if base is None else base
    if base:
        brutos.append(base)
    no_path = shutil.which("python") if no_path is None else no_path
    if no_path:
        brutos.append(Path(no_path))
    vistos: set[str] = set()
    saida: list[Path] = []
    for p in brutos:
        chave = os.path.normcase(os.path.abspath(str(p)))
        if chave in vistos or not valido(p):
            continue
        vistos.add(chave)
        saida.append(p)
    return saida


def levantar(sondar=sondar_interpretador, cands: list[Path] | None = None,
             fixadas: dict[str, str] | None = None) -> list[Achado]:
    cands = candidatos() if cands is None else cands
    fixadas = versoes_fixadas() if fixadas is None else fixadas
    achados: list[Achado] = []
    vistos: set[str] = set()
    for p in cands:
        info = sondar(p)
        prefixo = info.get("prefixo") if isinstance(info, dict) else None
        if prefixo:                          # o mesmo Python por dois caminhos (ex.: atalho do `py`): uma vez só
            chave = os.path.normcase(os.path.abspath(prefixo))
            if chave in vistos:
                continue
            vistos.add(chave)
        achados.append(Achado(p, info, avaliar_sonda(info, fixadas)))
    return achados


def melhor_pronto(achados: list[Achado]) -> Achado | None:
    """Entre os que já servem: os com versões testadas primeiro, depois o Python mais novo."""
    prontos = [a for a in achados if a.aval.pronto]
    prontos.sort(key=lambda a: (a.aval.divergente, tuple(-n for n in parse_versao(a.aval.python))))
    return prontos[0] if prontos else None


def melhor_parcial(achados: list[Achado]) -> Achado | None:
    """Quem tem mais itens presentes (para listar o que já existe quando nenhum serve)."""
    ok = [(sum(e == "ok" for _n, e, _t in a.aval.itens), a) for a in achados if a.aval.itens[0][1] != "erro"]
    if not ok:
        return None
    return max(ok, key=lambda x: (x[0], parse_versao(x[1].aval.python)))[1]


# ---------- escolha de um interpretador existente (interpretador.json) ----------
def arquivo_escolha(pasta: Path | None = None) -> Path:
    return arquivo_log(pasta or pasta_ambiente()).parent / ARQ_ESCOLHA


def ler_escolha(arq: Path) -> dict | None:
    """{"python": caminho, "versoes": {...}} ou None se ausente/ilegível/corrompido."""
    try:
        d = json.loads(arq.read_text(encoding="utf-8"))
        caminho = d["python"]
        if not isinstance(caminho, str) or not caminho:
            return None
        return {"python": caminho, "versoes": d.get("versoes") if isinstance(d.get("versoes"), dict) else {}}
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None


def gravar_escolha(arq: Path, python: Path, versoes: dict) -> bool:
    try:
        arq.parent.mkdir(parents=True, exist_ok=True)
        arq.write_text(json.dumps({"python": str(python), "versoes": versoes}, ensure_ascii=False, indent=2),
                       encoding="utf-8")
        return True
    except OSError:
        return False


def esquecer_escolha(arq: Path) -> bool:
    """Apaga só o interpretador.json (nunca o Python do usuário)."""
    try:
        arq.unlink()
        return True
    except FileNotFoundError:
        return False
    except OSError:
        return False


def decidir(pasta: Path, arq: Path, sondar=sondar_interpretador, listar: Callable[[], list[Path]] = candidatos,
            fixadas: dict[str, str] | None = None) -> Decisao:
    """Caminho do clique em Laboratório. Só consulta o computador (sem rede, sem instalar):
    (a) ambiente próprio pronto → abrir; (b) escolha anterior ainda válida → abrir com ela; senão procura um
    Python que já sirva → oferecer; (c) nada serve → confirmação do preparo."""
    if estado_ambiente(pasta) == PRONTO:
        return Decisao("ambiente")
    fixadas = versoes_fixadas() if fixadas is None else fixadas
    esc = ler_escolha(arq)
    if esc:
        p = Path(esc["python"])
        info = sondar(p)
        av = avaliar_sonda(info, fixadas)
        if av.pronto:
            return Decisao("existente", p, Achado(p, info, av))
        esquecer_escolha(arq)               # a escolha deixou de valer: volta a perguntar
    achados = levantar(sondar, listar(), fixadas)
    bom = melhor_pronto(achados)
    if bom:
        return Decisao("oferecer", bom.caminho, bom, achados)
    return Decisao("preparar", None, None, achados)


# ---------- abrir ----------
def abrir_processo(pasta: Path | None = None, python: Path | None = None) -> subprocess.Popen:
    """Abre o Laboratório em outro processo, sem console, com a pasta do app como diretório de trabalho.
    `python`: interpretador existente escolhido pelo usuário; sem ele, o do ambiente próprio."""
    pasta = pasta or pasta_ambiente()
    log = arquivo_log(pasta)
    try:
        log.parent.mkdir(parents=True, exist_ok=True)
        saida = open(log, "w", encoding="utf-8")
    except OSError:
        saida = subprocess.DEVNULL  # type: ignore[assignment]
    cmd = comando_abrir_com(python) if python else comando_abrir(pasta)
    try:
        return subprocess.Popen(cmd, cwd=str(pasta_app()), creationflags=SEM_JANELA,
                                stdin=subprocess.DEVNULL, stdout=saida, stderr=saida, close_fds=True,
                                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})  # sem __pycache__ no app
    finally:
        if saida is not subprocess.DEVNULL:
            saida.close()


_processo_lab: subprocess.Popen | None = None   # o Laboratório aberto por este app (um só por vez)


def trazer_janela_do_processo(pid: int) -> bool:
    """Restaura e põe na frente a janela principal do processo `pid` (Windows). False se não achou."""
    try:
        import ctypes
        from ctypes import wintypes
        u32 = ctypes.windll.user32
        achadas: list[int] = []

        @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def cada(hwnd, _l):
            dono = wintypes.DWORD()
            u32.GetWindowThreadProcessId(hwnd, ctypes.byref(dono))
            if dono.value == pid and u32.IsWindowVisible(hwnd) and u32.GetWindowTextLengthW(hwnd) > 0:
                achadas.append(hwnd)
            return True

        u32.EnumWindows(cada, 0)
        if not achadas:
            return False
        u32.ShowWindow(achadas[0], 9)        # SW_RESTORE
        u32.SetForegroundWindow(achadas[0])
        return True
    except Exception:
        return False


def tem_janela_do_laboratorio() -> bool:
    return (pasta_app() / "lab" / "__main__.py").is_file()


def _gb(n: int) -> str:
    return f"{n / 2**30:.1f}".replace(".", ",") + " GB"


# ---------- interface (tkinter só é importado aqui dentro) ----------
class Dialogo:
    """Janela do Laboratório antes de abrir: verificação, oferta de usar o que já existe, confirmação do preparo,
    progresso e falha. Tudo na thread do tkinter; os trabalhos longos falam por fila."""

    def __init__(self, raiz, ao_fechar: Callable[[], None], pasta: Path | None = None,
                 decidir_fn: Callable[[], Decisao] | None = None, abrir: Callable | None = None) -> None:
        import tkinter as tk
        from tkinter import ttk
        from tema import BORDA, CARTAO, FONTE, FUNDO, GRADE, SUAVE, TEXTO, ZONAS

        self._tk, self._ttk = tk, ttk
        self.cores = dict(BORDA=BORDA, CARTAO=CARTAO, FONTE=FONTE, FUNDO=FUNDO, GRADE=GRADE, SUAVE=SUAVE,
                          TEXTO=TEXTO, ERRO=ZONAS["quente"][1], OK=ZONAS["normal"][1])
        self.raiz, self.ao_fechar = raiz, ao_fechar
        self.pasta = pasta or pasta_ambiente()
        self._abrir = abrir or abrir_com_aviso
        self._decidir = decidir_fn or (lambda: decidir(self.pasta, arquivo_escolha(self.pasta)))
        self.fila: queue.Queue = queue.Queue()
        self.preparo: Preparo | None = None
        self.decisao: Decisao = Decisao("preparar")
        self.tela = ""
        self.top = tk.Toplevel(raiz)
        self.top.title("TempCPU — Laboratório")
        self.top.configure(bg=FUNDO)
        self.top.resizable(False, False)
        self.top.protocol("WM_DELETE_WINDOW", self._fechar)
        self.corpo = tk.Frame(self.top, bg=CARTAO, highlightbackground=BORDA, highlightthickness=1, padx=22, pady=18)
        self.corpo.pack(padx=16, pady=16)
        self.mostrar_verificando()
        threading.Thread(target=self._verificar, daemon=True).start()
        self.top.after(150, self._bombear)

    # --- utilidades
    def existe(self) -> bool:
        try:
            return bool(self.top.winfo_exists())
        except Exception:
            return False

    def trazer(self) -> None:
        self.top.deiconify()
        self.top.lift()
        self.top.focus_force()

    def _limpar_corpo(self) -> None:
        for w in self.corpo.winfo_children():
            w.destroy()

    def _texto(self, texto: str, negrito: bool = False, cor: str | None = None, espaco: int = 8) -> None:
        c = self.cores
        self._tk.Label(self.corpo, text=texto, font=(c["FONTE"], 11 if negrito else 10, "bold" if negrito else "normal"),
                       bg=c["CARTAO"], fg=cor or c["TEXTO"], justify="left", anchor="w", wraplength=460
                       ).pack(fill="x", pady=(0, espaco))

    def _lista(self, titulo: str, linhas: list[tuple[str, str, str]]) -> None:
        """Pequena tabela "nome: situação"; o que falta fica em destaque."""
        c = self.cores
        self._tk.Label(self.corpo, text=titulo, font=(c["FONTE"], 10, "bold"), bg=c["CARTAO"], fg=c["TEXTO"],
                       anchor="w").pack(fill="x", pady=(0, 2))
        for nome, estado, texto in linhas:
            self._tk.Label(self.corpo, text=f"   {nome}: {texto}", font=(c["FONTE"], 10), bg=c["CARTAO"],
                           fg=c["OK"] if estado == "ok" else c["ERRO"], anchor="w", justify="left",
                           wraplength=460).pack(fill="x")
        self._tk.Frame(self.corpo, bg=c["CARTAO"], height=8).pack()

    def _botoes(self, *itens: tuple[str, Callable[[], None], bool]) -> None:
        c = self.cores
        linha = self._tk.Frame(self.corpo, bg=c["CARTAO"])
        linha.pack(fill="x", pady=(10, 0))
        for texto, cmd, principal in itens:
            self._tk.Button(linha, text=texto, command=cmd, relief="flat", bd=0, cursor="hand2",
                            bg=c["OK"] if principal else c["GRADE"], fg="white" if principal else c["TEXTO"],
                            activebackground=c["BORDA"], font=(c["FONTE"], 10, "bold" if principal else "normal"),
                            padx=14, pady=5).pack(side="right", padx=(8, 0))

    # --- telas
    def mostrar_verificando(self) -> None:
        self.tela = "verificando"
        self._limpar_corpo()
        self._texto("Verificando o seu computador…", negrito=True)
        self._texto("Procurando um Python com as bibliotecas do Laboratório. Só olho o que já existe; nada é baixado "
                    "nem instalado.", cor=self.cores["SUAVE"], espaco=0)

    def mostrar_oferta(self) -> None:
        a = self.decisao.achado
        assert a is not None
        self.tela = "oferta"
        self._limpar_corpo()
        self._texto(f"Encontrei o Python {a.aval.python} com as bibliotecas necessárias. Usar sem instalar nada?",
                    negrito=True)
        self._texto(f"{a.caminho}", cor=self.cores["SUAVE"], espaco=4)
        self._lista("O que já existe no seu computador", [(n, e, t) for n, e, t in a.aval.itens])
        if a.aval.divergente:
            self._texto(aviso_divergente(versoes_fixadas()), cor=self.cores["SUAVE"], espaco=4)
        self._texto("Nada será baixado nem instalado. O Laboratório só lê esse Python; você pode esquecer a escolha "
                    "a qualquer momento (botão direito em Laboratório).", cor=self.cores["SUAVE"])
        self._botoes(("Agora não", self._fechar, False),
                     ("Instalar um ambiente separado", self.mostrar_confirmacao, False),
                     ("Usar o que já tem (recomendado)", self._usar_existente, True))

    def mostrar_confirmacao(self) -> None:
        self.tela = "confirmacao"
        self._limpar_corpo()
        self._texto("Preparar o Laboratório", negrito=True)
        parcial = melhor_parcial(self.decisao.achados)
        if parcial:
            self._lista(f"O que já existe no seu computador ({parcial.caminho})",
                        [(n, e, t) for n, e, t in parcial.aval.itens])
        else:
            self._lista("O que já existe no seu computador", [("Python", "ausente", "não encontrado")])
        motivo = motivo_python_nao_suportado()
        if motivo:
            self._texto(motivo, cor=self.cores["ERRO"])
            self._botoes(("Fechar", self._fechar, False))
            return
        self._texto("O Laboratório é um módulo opcional que ensina machine learning (aprendizado de máquina) com o "
                    "histórico do seu computador. Ele roda em um programa separado e o TempCPU continua igual sem ele.")
        try:
            livre = _gb(espaco_livre(self.pasta))
        except OSError:
            livre = "indisponível"
        self._texto(f"O que será instalado: scikit-learn, numpy e scipy (com dependências), em um ambiente separado, "
                    f"ocupando {TAMANHO_TEXTO}. É preciso baixar da internet.\nDestino: {self.pasta}\n"
                    f"Espaço livre no disco: {livre}", espaco=4)
        self._texto("Nada é instalado até você confirmar. Depois você pode removê-lo (botão direito em Laboratório).",
                    cor=self.cores["SUAVE"])
        self._botoes(("Agora não", self._fechar, False), ("Preparar Laboratório", self._iniciar, True))

    def mostrar_progresso(self) -> None:
        self.tela = "progresso"
        self._limpar_corpo()
        self._texto("Preparando o Laboratório…", negrito=True)
        self._etapa = self._tk.Label(self.corpo, text="Começando…", font=(self.cores["FONTE"], 10),
                                     bg=self.cores["CARTAO"], fg=self.cores["TEXTO"], anchor="w", justify="left")
        self._etapa.pack(fill="x", pady=(0, 8))
        self._barra = self._ttk.Progressbar(self.corpo, mode="indeterminate", length=460)
        self._barra.pack(fill="x")
        self._barra.start(18)
        self._texto("Pode levar alguns minutos, conforme a sua internet. Pode continuar usando o TempCPU.",
                    cor=self.cores["SUAVE"], espaco=0)
        self._botoes(("Cancelar", self._cancelar, False))

    def mostrar_resultado(self, estado: str, mensagem: str) -> None:
        self.tela = "resultado"
        self._limpar_corpo()
        if estado == PRONTO:
            self._texto("Laboratório pronto", negrito=True, cor=self.cores["OK"])
            self._texto("Tudo instalado e verificado.")
            self._botoes(("Fechar", self._fechar, False), ("Abrir Laboratório", self._abrir_e_fechar, True))
        elif estado == AUSENTE:
            self._texto("Preparo cancelado", negrito=True)
            self._texto(mensagem)
            self._botoes(("Preparar de novo", self.mostrar_confirmacao, False), ("Fechar", self._fechar, False))
        else:
            self._texto("Não foi possível preparar o Laboratório", negrito=True, cor=self.cores["ERRO"])
            self._texto(mensagem)
            self._botoes(("Fechar", self._fechar, False), ("Tentar de novo", self._iniciar, True))

    # --- ações
    def _verificar(self) -> None:
        try:
            d = self._decidir()
        except Exception:  # a verificação nunca pode travar o Laboratório: cai na confirmação do preparo
            d = Decisao("preparar")
        self.fila.put(("decisao", d))

    def _usar_existente(self) -> None:
        a = self.decisao.achado
        assert a is not None
        gravar_escolha(arquivo_escolha(self.pasta), a.caminho, a.aval.versoes)
        self._abrir(self.raiz, self.pasta, a.caminho)
        self._fechar()

    def _iniciar(self) -> None:
        self.preparo = Preparo(self.pasta, python_base(), arquivo_requisitos(),
                               ao_evento=lambda t, d: self.fila.put((t, d)))
        self.mostrar_progresso()
        self.preparo.iniciar()

    def _cancelar(self) -> None:
        if self.preparo:
            self.preparo.cancelar()
            self._etapa.config(text="Cancelando e limpando…")

    def _abrir_e_fechar(self) -> None:
        self._abrir(self.raiz, self.pasta)
        self._fechar()

    def _fechar(self) -> None:
        if self.preparo and self.preparo.estado == PREPARANDO:  # X durante o preparo = Cancelar
            self._cancelar()
            return
        try:
            self.top.destroy()
        finally:
            self.ao_fechar()

    def _ao_decidir(self, d: Decisao) -> None:
        self.decisao = d
        if d.tipo == "ambiente":
            self._abrir_e_fechar()
        elif d.tipo == "existente":
            self._abrir(self.raiz, self.pasta, d.python)
            self._fechar()
        elif d.tipo == "oferecer":
            self.mostrar_oferta()
        else:
            self.mostrar_confirmacao()

    def _bombear(self) -> None:
        if not self.existe():
            return
        try:
            while True:
                tipo, dado = self.fila.get_nowait()
                if tipo == "decisao":
                    self._ao_decidir(dado)
                elif tipo == "etapa":
                    i, n, texto = dado
                    self._etapa.config(text=f"Etapa {i + 1} de {n}: {texto}…")
                elif tipo == "fim":
                    self.mostrar_resultado(*dado)
        except queue.Empty:
            pass
        if self.existe():
            self.top.after(150, self._bombear)


def abrir_com_aviso(raiz, pasta: Path | None = None, python: Path | None = None) -> bool:
    """Abre o Laboratório; mostra o motivo se não for possível. Verifica se o processo sobreviveu ao início."""
    from tkinter import messagebox
    pasta = pasta or pasta_ambiente()
    if not tem_janela_do_laboratorio():
        messagebox.showinfo("TempCPU — Laboratório", "O ambiente está pronto, mas esta versão do app ainda não "
                            "traz a janela do Laboratório (pasta lab).", parent=raiz)
        return False
    global _processo_lab
    if _processo_lab is not None and _processo_lab.poll() is None:   # já aberto: não abre outro
        if not trazer_janela_do_processo(_processo_lab.pid):
            messagebox.showinfo("TempCPU — Laboratório", "O Laboratório já está aberto.", parent=raiz)
        return True
    try:
        proc = abrir_processo(pasta, python)
    except OSError as e:
        messagebox.showerror("TempCPU — Laboratório", f"Não foi possível abrir o Laboratório: {e.strerror or e}",
                             parent=raiz)
        return False
    _processo_lab = proc

    def conferir() -> None:
        codigo = proc.poll()
        if codigo not in (None, 0):
            try:
                detalhe = arquivo_log(pasta).read_text(encoding="utf-8", errors="replace").strip()[-600:]
            except OSError:
                detalhe = ""
            messagebox.showerror("TempCPU — Laboratório",
                                 "O Laboratório fechou logo ao abrir." + (f"\n\n{detalhe}" if detalhe else ""),
                                 parent=raiz)

    raiz.after(2500, conferir)
    return True


def acionar(raiz, ao_fechar: Callable[[], None], decidir_fn: Callable[[], Decisao] | None = None,
            abrir: Callable | None = None) -> Dialogo | None:
    """Clique em Laboratório. Ambiente próprio pronto: abre direto. Senão, a janela verifica (sem rede) se já há um
    Python que sirva e oferece usá-lo; só se nada servir mostra a confirmação do preparo (download)."""
    pasta = pasta_ambiente()
    if estado_ambiente(pasta) == PRONTO:
        (abrir or abrir_com_aviso)(raiz, pasta)
        return None
    return Dialogo(raiz, ao_fechar, pasta, decidir_fn=decidir_fn, abrir=abrir)


def esquecer_com_aviso(raiz) -> None:
    from tkinter import messagebox
    esquecer_escolha(arquivo_escolha())
    messagebox.showinfo("TempCPU — Laboratório", "Pronto. Na próxima abertura o Laboratório vai verificar de novo. "
                        "O Python que você tinha escolhido não foi alterado.", parent=raiz)


def montar_menu(menu, raiz) -> None:
    """Itens do botão direito em Laboratório."""
    instalado = estado_ambiente(pasta_ambiente()) != AUSENTE
    menu.add_command(label="Remover Laboratório…", state="normal" if instalado else "disabled",
                     command=lambda: remover_com_confirmacao(raiz))
    if arquivo_escolha().exists():
        menu.add_command(label="Esquecer o Python escolhido", command=lambda: esquecer_com_aviso(raiz))


def remover_seguro(pasta: Path) -> str:
    """`remover_pasta` que nunca levanta: devolve "" se deu certo, senão o motivo em português."""
    try:
        return remover_pasta(pasta)
    except Exception as e:
        return f"Não foi possível remover o Laboratório: {getattr(e, 'strerror', None) or e}"


def remover_com_confirmacao(raiz) -> None:
    """Remover Laboratório: confirma, apaga só a pasta do ambiente (nunca o histórico) numa thread."""
    from tkinter import messagebox
    pasta = pasta_ambiente()
    if estado_ambiente(pasta) == AUSENTE:
        messagebox.showinfo("TempCPU — Laboratório", "O Laboratório não está instalado.", parent=raiz)
        return
    if not messagebox.askyesno("TempCPU — Remover Laboratório",
                               f"Apagar o ambiente do Laboratório ({TAMANHO_TEXTO}) em:\n{pasta}\n\n"
                               "Seu histórico de temperaturas não será alterado. Remover?", parent=raiz):
        return
    resultado: list[str] = []
    threading.Thread(target=lambda: resultado.append(remover_seguro(pasta)), daemon=True).start()

    def esperar() -> None:
        if not resultado:
            raiz.after(200, esperar)
        elif resultado[0]:
            messagebox.showerror("TempCPU — Laboratório", resultado[0], parent=raiz)
        else:
            messagebox.showinfo("TempCPU — Laboratório", "Laboratório removido.", parent=raiz)

    esperar()
