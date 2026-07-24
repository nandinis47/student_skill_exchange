@echo off
title Student Skills Exchange - Launcher
color 0A

echo ================================================
echo   Student Skills Exchange - Starting...
echo ================================================
echo.

:: Kill any old instances on these ports
echo [1] Clearing old processes...
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":5000"') do (
    taskkill /PID %%a /F >nul 2>&1
)
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":8080"') do (
    taskkill /PID %%a /F >nul 2>&1
)
timeout /t 1 /nobreak >nul

:: Start Flask backend in background
echo [2] Starting Flask backend...
start /B "" python "backend\app.py" > logs\backend.log 2>&1
timeout /t 3 /nobreak >nul

:: Start frontend HTTP server in background  
echo [3] Starting frontend server...
start /B "" python -m http.server 8080 --directory frontend > logs\frontend.log 2>&1
timeout /t 2 /nobreak >nul

:: Open browser
echo [4] Opening browser...
start "" "http://localhost:8080/index.html"

echo.
echo ================================================
echo   App is running!
echo   Open:  http://localhost:8080
echo   Login: aarav@college.edu / pass123
echo ================================================
echo.
echo   Press any key to STOP the servers...
pause >nul

echo Stopping servers...
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":5000"') do taskkill /PID %%a /F >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano 2^>nul ^| findstr ":8080"') do taskkill /PID %%a /F >nul 2>&1
echo Done. Goodbye!
