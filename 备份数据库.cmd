@echo off
set "EKKO_PY=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if not exist "%EKKO_PY%" set "EKKO_PY=python"
"%EKKO_PY%" "%~dp0server\backup.py"
pause
