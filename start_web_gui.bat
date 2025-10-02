@echo off
echo ============================================
echo     AgenticSys Web GUI Control Center
echo ============================================
echo.

REM Navigate to project directory
cd /d "%~dp0"

REM Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
) else if exist ".venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
)

echo.
echo Starting Web GUI server...
echo ============================================
echo.
echo The control center will be available at:
echo   http://localhost:8000
echo.
echo Open your browser to access the interface
echo Press Ctrl+C to stop the server
echo ============================================
echo.

REM Start the FastAPI server
REM Running without reload to prevent issues with file watching on Windows
REM WebSocket timeout increased to 60s to match client ping interval (30s)
REM This prevents server from closing "idle" connections during long agent runs
python -m uvicorn web_gui.backend.app:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 60 --ws-ping-interval 20 --ws-ping-timeout 60

pause