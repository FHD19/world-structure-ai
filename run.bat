@echo off
chcp 65001 >nul
title 世界结构认知AI

echo ========================================
echo   世界结构认知AI - World Structure AI
echo ========================================
echo.

cd /d "%~dp0"

echo [1/2] 检查并安装依赖...
pip install -r requirements.txt -q
if errorlevel 1 (
    echo 依赖安装失败，请手动执行: pip install -r requirements.txt
    pause
    exit /b 1
)

echo [2/2] 启动服务...
echo.
echo   浏览器将自动打开: http://127.0.0.1:5000
echo   按 Ctrl+C 停止服务
echo ========================================
echo.

start "" http://127.0.0.1:5000

python app.py

pause
