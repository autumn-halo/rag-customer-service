@echo off
title RAG QA System Launcher
cd /d "%~dp0"

echo =============================================
echo   RAG E-commerce QA System Launcher
echo   1) backend  -> http://localhost:8000
echo   2) frontend -> http://localhost:5173
echo   Browser opens automatically in 5 seconds.
echo   Keep the two new windows open while using.
echo =============================================
echo.

rem ---- friendly check: warn if ports are already busy ----
netstat -ano | findstr "LISTENING" | findstr ":8000" >nul 2>&1
if %errorlevel%==0 echo [WARN] Port 8000 is busy. Backend may already be running.
netstat -ano | findstr "LISTENING" | findstr ":5173" >nul 2>&1
if %errorlevel%==0 echo [WARN] Port 5173 is busy. Frontend may already be running.
echo.

start "RAG Backend"  /D "backend"  cmd /k ".venv\Scripts\python.exe -m uvicorn app.main:app --port 8000 --reload"
start "RAG Frontend" /D "frontend" cmd /k "npm run dev"

timeout /t 5 /nobreak >nul
start "" http://localhost:5173
