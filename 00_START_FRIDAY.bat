@echo off
setlocal
cd /d "%~dp0"

:: Start Ollama background service if not already running
where ollama >nul 2>&1
if %errorlevel% equ 0 (
    start "" /B ollama serve >nul 2>&1
) else (
    if exist "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" (
        start "" /B "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" serve >nul 2>&1
    )
)

:: Launch Friday Assistant
if exist ".\.venv\Scripts\pythonw.exe" (
    start "" ".\.venv\Scripts\pythonw.exe" "main.py"
    exit /b 0
)

if exist ".\.venv\Scripts\python.exe" (
    start "" ".\.venv\Scripts\python.exe" "main.py"
    exit /b 0
)

python main.py
