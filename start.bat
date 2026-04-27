@echo off
setlocal

if not exist ".venv\Scripts\python.exe" (
    echo Virtualenv non trovato. Creazione in corso...
    python -m venv .venv
    if errorlevel 1 exit /b %errorlevel%
)

".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 exit /b %errorlevel%

".venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000
