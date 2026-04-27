@echo off
setlocal

set "PYTHON_CMD="

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 --version >nul 2>nul
    if %errorlevel%==0 set "PYTHON_CMD=py -3"
)

if not defined PYTHON_CMD (
    where python >nul 2>nul
    if %errorlevel%==0 (
        python --version >nul 2>nul
        if %errorlevel%==0 set "PYTHON_CMD=python"
    )
)

if not defined PYTHON_CMD (
    echo Python non trovato.
    echo Installa Python 3.11 o superiore con:
    echo winget install -e --id Python.Python.3.12
    echo.
    echo Poi chiudi e riapri il terminale e rilancia:
    echo .\start.bat
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Virtualenv non trovato. Creazione in corso...
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 exit /b %errorlevel%
)

".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 exit /b %errorlevel%

".venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000
