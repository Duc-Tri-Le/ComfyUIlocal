@echo off
cd /d "%~dp0ComfyUI"
python main.py --windows-standalone-build --cpu --enable-manager
pause
