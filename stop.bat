@echo off
echo ========================================
echo Stopping Bybit AI Swing Trader Servers
echo ========================================
echo.

echo Checking for running servers...

REM Kill uvicorn processes
taskkill /f /im python.exe /fi "WINDOWTITLE eq Backend Server*" >nul 2>&1
if %errorlevel%==0 (
    echo [OK] Backend server stopped
) else (
    echo [INFO] No backend server found running
)

REM Kill node processes
taskkill /f /im node.exe /fi "WINDOWTITLE eq Frontend Server*" >nul 2>&1
if %errorlevel%==0 (
    echo [OK] Frontend server stopped
) else (
    echo [INFO] No frontend server found running
)

echo.
echo ========================================
echo All servers stopped successfully
echo ========================================
timeout /t 2 > nul