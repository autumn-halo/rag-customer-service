@echo off
chcp 65001 >nul
title RAG 前端页面
cd /d "%~dp0frontend"
echo ============================================
echo   正在启动前端页面...
echo   浏览器访问: http://localhost:5173
echo   关闭本窗口即可停止
echo ============================================
call npm run dev
pause
