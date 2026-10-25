@echo off
rem Abre o TempCPU como administrador (necessario para a zona termica ACPI).
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
  echo Ambiente nao encontrado. Rode antes:  py -m venv .venv  e  .venv\Scripts\pip install -r requirements.txt
  pause
  exit /b 1
)
powershell -NoProfile -Command "Start-Process -FilePath '%~dp0.venv\Scripts\pythonw.exe' -ArgumentList '\"%~dp0app.py\" --janela' -WorkingDirectory '%~dp0' -Verb RunAs"
