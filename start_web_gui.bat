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
python -m uvicorn web_gui.backend.app:app --host 0.0.0.0 --port 8000 --reload

pause