@echo off
chcp 65001 >nul
title SuperCapa v3 - Instalando dependencias...

echo ============================================================
echo   SUPERCAPA v3 - Preparando entorno
echo ============================================================

:: Comprobar Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no encontrado. Instala Python 3.10+ desde:
    echo         https://www.python.org/downloads/windows/
    echo         MARCA la casilla "Add python.exe to PATH"
    pause
    exit /b 1
)

:: Instalar dependencias si faltan
echo Verificando librerias...
pip show pyautogui >nul 2>&1 || pip install pyautogui --quiet
pip show SpeechRecognition >nul 2>&1 || pip install SpeechRecognition --quiet
pip show keyboard >nul 2>&1 || pip install keyboard --quiet
pip show pyaudio >nul 2>&1 || pip install pyaudio --quiet
pip show pyperclip >nul 2>&1 || pip install pyperclip --quiet

echo.
echo Todas las librerias OK.
echo.

title SuperCapa v3 - Control por voz + puntero moto
echo Iniciando SuperCapa v3...
echo.

:: Ejecutar con permisos elevados para atajos globales de teclado
python supercapa.py

if errorlevel 1 (
    echo.
    echo [ERROR] SuperCapa termino con error. Revisa el mensaje arriba.
    pause
)
