@echo off
REM Crear el entorno virtual
python -m venv venv

REM Activar el entorno virtual
call venv\Scripts\activate

REM Actualizar pip a la última versión
python.exe -m pip install --upgrade pip

REM Instalar las dependencias desde requirements.txt
pip install -r requirements.txt

REM Mensaje final
echo Entorno creado y dependencias instaladas.
pause

