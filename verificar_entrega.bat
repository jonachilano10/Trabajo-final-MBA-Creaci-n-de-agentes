@echo off
cd /d "%~dp0"
python scripts\verificar_entrega.py
echo.
if errorlevel 1 (
  echo RESULTADO: la verificacion encontro errores.
) else (
  echo RESULTADO: entrega verificada correctamente.
)
pause
