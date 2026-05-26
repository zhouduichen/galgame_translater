@echo off
cd /d "D:\ComfyUI"
echo [ComfyUI] Starting ComfyUI with API enabled...
echo [ComfyUI] API available at: http://127.0.0.1:8188
echo.
py -3.11 main.py --listen --enable-cors-header --fp32-vae
pause
