@echo off
cd /d "%~dp0src"
python server.py --data data/project-conversations.json
pause
