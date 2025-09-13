@echo off
echo ============================================================
echo    AI INTERVIEWER SYSTEM - CLIENT DEMO LAUNCHER
echo ============================================================
echo.
echo Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo Launching AI Interviewer Interactive Demo...
echo.
cd backend
python main.py

echo.
echo Demo completed. Press any key to exit...
pause > nul