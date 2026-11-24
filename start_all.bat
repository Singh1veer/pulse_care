@echo off
echo ===================================================
echo Starting CampusCare Full-Stack System
echo ===================================================

echo [1/2] Launching Backend Server on port 8000...
start "CampusCare Backend" cmd /k "cd /d %~dp0backend && python -m uvicorn main:app --reload --port 8000"

timeout /t 2 /nobreak > nul

echo [2/2] Launching Frontend Dev Server on port 5173...
start "CampusCare Frontend" cmd /k "cd /d %~dp0Code\frontend && npm.cmd run dev"

echo.
echo ===================================================
echo Both services are now running!
echo Frontend: http://localhost:5173
echo Backend:  http://localhost:8000
echo ===================================================
timeout /t 5
