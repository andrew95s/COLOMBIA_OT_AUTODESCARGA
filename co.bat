@echo off
REM Activar el entorno virtual
call venv\Scripts\activate

REM Ejecutar el script Python
python Scripts\Script_OT.py

REM Mensaje final
echo Ejecución completada.
pause
