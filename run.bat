@echo off
cd /d "%~dp0src"
if not exist .venv\Scripts\python.exe python -m venv .venv
if not exist .venv\Scripts\python.exe goto fail
.venv\Scripts\python.exe -c "import numpy,onnxruntime,tokenizers" >nul 2>&1
if errorlevel 1 .venv\Scripts\python.exe -m pip install -r requirements-models.txt
if errorlevel 1 goto fail
.venv\Scripts\python.exe download_models.py
if errorlevel 1 goto fail
echo Open http://127.0.0.1:8765 after startup.
.venv\Scripts\python.exe server.py --data data/project-conversations.json --vector-model models/embedding --qa-model models/qa
pause
exit /b
:fail
echo Setup failed. Install Python 3.12 and retry, or use run-basic.bat.
pause
