"""Gera o TempCPU.exe (PyInstaller, pasta única) e o .zip de distribuição.

Uso (no ambiente do app, com `pip install -r requirements-build.txt`):
    .venv\\Scripts\\python tools\\gerar_executavel.py              # versão normal (pede administrador ao abrir)
    .venv\\Scripts\\python tools\\gerar_executavel.py --teste       # sem pedir administrador, só para testar a build

Saída: dist/TempCPU/ (pasta pronta) e dist/TempCPU-<versão>-win64.zip com o SHA-256.
O Laboratório não é empacotado com o scikit-learn: o executável leva só os arquivos dele (lab/) e o app cria o
ambiente com o Python 3.14 do computador, como no código-fonte.
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

NOME = "TempCPU"
SAIDA = RAIZ / "dist"
TRABALHO = RAIZ / "build"
STAGE = TRABALHO / "stage"
# Módulos que o Laboratório (outro processo, Python do usuário) importa do app: viajam como arquivos, não dentro do .exe.
ARQUIVOS_DO_LAB = ["tema.py", "linha_do_tempo.py", "historico.py", "motivos.py", "lab-requirements.txt"]
EXCLUIR = ["numpy", "scipy", "sklearn", "matplotlib", "pandas", "IPython", "pytest", "unittest", "pydoc", "test"]


def versao() -> str:
    from lab import VERSAO
    return VERSAO


def gerar_icone(destino: Path) -> None:
    from bandeja import desenhar_icone
    destino.parent.mkdir(parents=True, exist_ok=True)
    img = desenhar_icone("°C", "#3d9a6c", "forte")
    img.save(destino, format="ICO", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64)])


def preparar_stage() -> None:
    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True)
    shutil.copytree(RAIZ / "lab", STAGE / "lab", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for nome in ARQUIVOS_DO_LAB:
        shutil.copy2(RAIZ / nome, STAGE / nome)


def construir(teste: bool) -> Path:
    icone = TRABALHO / "tempcpu.ico"
    gerar_icone(icone)
    preparar_stage()
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed", "--name", NOME,
           "--icon", str(icone), "--distpath", str(SAIDA), "--workpath", str(TRABALHO / "pyi"), "--specpath", str(TRABALHO),
           "--paths", str(RAIZ),
           "--hidden-import", "pystray._win32", "--hidden-import", "win32timezone", "--collect-submodules", "win32com",
           "--collect-submodules", "wmi"]
    if not teste:
        cmd += ["--uac-admin"]
    for m in EXCLUIR:
        cmd += ["--exclude-module", m]
    for item in sorted(STAGE.iterdir()):
        cmd += ["--add-data", f"{item};{item.name}" if item.is_dir() else f"{item};."]
    cmd.append(str(RAIZ / "app.py"))
    print(" ".join(cmd[:8]), "...", flush=True)
    subprocess.run(cmd, check=True, cwd=RAIZ)
    pasta = SAIDA / NOME
    for extra in ("LICENSE", "NOTICE.md", "CHANGELOG.md"):
        shutil.copy2(RAIZ / extra, pasta / extra)
    shutil.copy2(RAIZ / ".env.example", pasta / ".env.example")
    (pasta / "LEIA-ME.txt").write_text(
        "TempCPU\n\n"
        "1. Abra TempCPU.exe. O Windows vai perguntar se permite alterações: clique em Sim (é preciso para ler a temperatura).\n"
        "2. A temperatura aparece na janela, na barra de tarefas e perto do relógio.\n"
        "3. Para mudar limites, copie .env.example para .env (nesta pasta) e edite.\n"
        "4. O Laboratório (opcional) precisa do Python 3.14 de 64 bits instalado: python.org/downloads.\n\n"
        "Aviso: este programa ainda não é assinado digitalmente, então o Windows pode mostrar o aviso\n"
        "\"O Windows protegeu o seu computador\". Clique em Mais informações e depois em Executar assim mesmo.\n"
        "Código-fonte e documentação: https://github.com/LucianoMLO/tempcpu\n", encoding="utf-8")
    return pasta


def compactar(pasta: Path) -> Path:
    zip_path = SAIDA / f"{NOME}-{versao()}-win64.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for f in sorted(pasta.rglob("*")):
            if f.is_file():
                z.write(f, Path(NOME) / f.relative_to(pasta))
    h = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    (SAIDA / f"{zip_path.name}.sha256").write_text(f"{h}  {zip_path.name}\n", encoding="utf-8")
    return zip_path


def tamanho_mb(caminho: Path) -> float:
    if caminho.is_file():
        return caminho.stat().st_size / 2**20
    return sum(f.stat().st_size for f in caminho.rglob("*") if f.is_file()) / 2**20


if __name__ == "__main__":
    teste = "--teste" in sys.argv
    pasta = construir(teste)
    print(f"pasta: {pasta}  ({tamanho_mb(pasta):.1f} MB)")
    if not teste:
        z = compactar(pasta)
        print(f"zip:   {z}  ({tamanho_mb(z):.1f} MB)\nsha256: {(SAIDA / (z.name + '.sha256')).read_text().strip()}")
