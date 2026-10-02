@echo off
title LYAXIS labs - Compilador VEX.exe
echo ==============================================================================
echo LYAXIS labs(TM) // Compilador Automatizado de VEX
echo ==============================================================================
echo.
echo [1/3] Verificando dependencias de Python y PyInstaller...
python -m pip install --upgrade pyinstaller

echo.
echo [2/3] Empaquetando VEX en ejecutable autonomo (VEX.exe)...
pyinstaller --noconsole --onefile --name "VEX" --add-data "config;config" main.py

echo.
echo ==============================================================================
if %ERRORLEVEL% EQU 0 (
    echo [EXITO] Compilacion completada con exito.
    echo El ejecutable final se encuentra en la carpeta: dist\VEX.exe
) else (
    echo [ERROR] Ocurrio un fallo durante la creacion del ejecutable VEX.exe.
    echo Verifica que todas las dependencias esten instaladas: pip install -r requirements.txt
)
echo ==============================================================================
echo.
pause
