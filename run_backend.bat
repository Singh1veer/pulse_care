@echo off
cd /d "%~dp0backend"
echo Starting CampusCare Backend on http://localhost:8000 ...
python -m uvicorn main:app --reload --port 8000
pause
