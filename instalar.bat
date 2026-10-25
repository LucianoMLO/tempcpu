@echo off
rem Prepara o TempCPU: cria o ambiente do Python e instala o que ele precisa. Rode uma vez (duplo clique).
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo.
  echo Nao encontrei o Python neste computador.
  echo Instale em https://www.python.org/downloads/ e depois de um duplo clique neste arquivo de novo.
  echo Na instalacao, deixe marcada a opcao "Install launcher for all users" ^(ja vem marcada^).
  echo.
  pause
  exit /b 1
)
echo Preparando o TempCPU. Isso leva 1 a 2 minutos e precisa de internet...
py -3 -m venv .venv
if errorlevel 1 goto erro
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto erro
if not exist ".env" copy ".env.example" ".env" >nul
echo.
echo Pronto! Para abrir o TempCPU, de um duplo clique em iniciar.bat
echo.
pause
exit /b 0
:erro
echo.
echo Algo deu errado na preparacao. Confira a internet e tente de novo.
echo Se continuar, abra um problema em https://github.com/LucianoMLO/tempcpu/issues
echo.
pause
exit /b 1
