@echo off
chcp 65001 >nul
title RAG 后端服务
cd /d "%~dp0backend"
echo ============================================
echo   正在启动后端服务...
echo   接口文档: http://localhost:8000/docs
echo   关闭本窗口即可停止服务
echo ============================================
".venv\Scripts\python.exe" -m uvicorn app.main:app --port 8000 --reload
pause
