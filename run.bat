@echo off
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"

echo ================================
echo    TikTok Auto Bot
echo ================================
echo.

REM Kiem tra Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not installed!
    echo Please install Python 3.11+ from python.org
    pause
    exit /b 1
)

REM Cai thu vien
echo [INFO] Installing dependencies...
pip install -r "%~dp0requirements.txt" -q

REM Chay bot
echo [INFO] Starting bot...
python -X utf8 "%~dp0main.py"

pause
