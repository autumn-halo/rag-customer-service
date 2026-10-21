@echo off
title RAG Docker Launcher
cd /d "%~dp0"

echo =============================================
echo   RAG E-commerce QA System - Docker Mode
echo   1) starting container ...
echo   2) browser opens automatically
echo   NOTE: do NOT run start.bat at the same time
echo =============================================
echo.

docker compose up -d

echo Waiting for the app to warm up ...
timeout /t 10 /nobreak >nul
start "" http://localhost:8000
