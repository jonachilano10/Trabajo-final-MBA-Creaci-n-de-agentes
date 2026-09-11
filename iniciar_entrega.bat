@echo off
cd /d "%~dp0"
set "AGENT_DATA_DIR=%~dp0runtime\entrega_final"
python run_web.py
pause
