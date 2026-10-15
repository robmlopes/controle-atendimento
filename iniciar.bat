@echo off
rem Inicia o controle-atendimento (roda dentro do WSL). Clique duas vezes neste arquivo.
setlocal
cd /d "%~dp0"
title Controle de Atendimento

where wsl >nul 2>nul
if errorlevel 1 (
  echo WSL nao encontrado. Instale o WSL para usar este atalho.
  pause
  exit /b 1
)

rem Libera a porta 8000 se houver processo preso antes de subir
wsl sh -c "command -v fuser >/dev/null 2>&1 && fuser -k -n tcp 8000 >/dev/null 2>&1 || true"

wsl --cd "%~dp0." sh scripts/iniciar.sh
echo.
echo Servidor encerrado.
pause
