@echo off
echo ========================================
echo Starting Foundit - AI File Search
echo ========================================
echo.

echo Starting Python Backend...
start "Foundit Backend" cmd /k "cd backend && python app.py"

echo.
echo Waiting for backend to start...
timeout /t 5 /nobreak >nul

echo.
echo Starting Electron Frontend...
cd frontend
start "Foundit Frontend" cmd /k "npm start"

echo.
echo ========================================
echo Foundit is starting!
echo ========================================
echo.
echo Backend: http://127.0.0.1:8000
echo Frontend: Will open automatically
echo.
echo Press any key to close this window...
pause >nul
