@echo off
title RAG Docker Stop
cd /d "%~dp0"

echo Stopping Docker deployment ...
docker compose down
echo Done. Data is kept in backend\data.
pause
