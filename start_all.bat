@echo off
title 夜樱工坊 - 一键启动
cd /d "%~dp0"

echo ============================================
echo   夜樱工坊 - Galgame 转译器 一键启动
echo ============================================
echo.

:: ─── 检查 Docker ──────────────────────────────────
where docker >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 未找到 Docker，请先安装 Docker Desktop
    echo         https://www.docker.com/products/docker-desktop/
    pause
    exit /b 1
)

:: ─── 停止已有本地服务（防止端口冲突）────────────
echo [准备] 停止本地运行的 API/Worker...
for /f "skip=3 tokens=2" %%a in ('tasklist /fi "imagename eq python.exe" /v 2^>nul ^| findstr /i "uvicorn uvicorn"') do (
    taskkill /f /pid %%a >nul 2>nul
)

:: ─── 启动 ComfyUI（本机运行，需 GPU）─────────────
echo.
echo [1/4] 启动 ComfyUI...
if exist "D:\ComfyUI\main.py" (
    start "ComfyUI" cmd /c "cd /d D:\ComfyUI && py -3.11 main.py --listen --enable-cors-header --fp32-vae"
    echo        ComfyUI 启动中（新窗口），等待初始化...
    timeout /t 15 /nobreak >nul
) else (
    echo        [跳过] D:\ComfyUI 未找到，请确保 ComfyUI 已安装
)

:: ─── 启动 Docker 服务 ─────────────────────────────
echo.
echo [2/4] 构建并启动 Docker 容器（API + Worker + 前端）...
docker compose up -d --build
if %ERRORLEVEL% NEQ 0 (
    echo [错误] Docker 服务启动失败，请检查 Docker 是否运行
    pause
    exit /b 1
)

:: ─── 等待 API 就绪 ───────────────────────────────
echo.
echo [3/4] 等待 API 就绪...
set /a elapsed=0
:wait_api
if %elapsed% gtr 30 (
    echo [超时] API 启动超时，请检查日志
    goto :show_info
)
timeout /t 2 /nobreak >nul
curl -s http://localhost:8001/api/health >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    set /a elapsed+=1
    goto wait_api
)
echo        API 已就绪！

:: ─── 等待 Web 就绪 ───────────────────────────────
echo.
echo [4/4] 等待前端就绪...
set /a elapsed=0
:wait_web
if %elapsed% gtr 60 (
    echo [超时] 前端启动超时，请检查日志
    goto :show_info
)
timeout /t 2 /nobreak >nul
curl -s -o nul -w "%%{http_code}" http://localhost:3001 2>nul | findstr "200 304" >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    set /a elapsed+=1
    goto wait_web
)
echo        前端已就绪！

:show_info
echo.
echo ============================================
echo   所有服务已启动！
echo.
echo   前端:      http://localhost:3001
echo   API:       http://localhost:8001
echo   ComfyUI:   http://localhost:8188
echo.
echo   按任意键停止所有服务...
echo ============================================
pause >nul

:: ─── 停止服务 ────────────────────────────────────
echo.
echo [停止] 关闭 Docker 服务...
docker compose down

echo [停止] 关闭 ComfyUI...
taskkill /f /fi "WINDOWTITLE eq ComfyUI" >nul 2>nul

echo 服务已全部停止。
timeout /t 2 /nobreak >nul
