@echo off
echo ========================================
echo Bybit AI Swing Trader - Status Check
echo ========================================
echo.

echo Checking Backend Server (Port 8000)...
curl -s http://localhost:8000 >nul 2>&1
if %errorlevel%==0 (
    echo [OK] Backend server is running
    curl -s http://localhost:8000 | findstr "Bybit AI Swing Trader" >nul
    if %errorlevel%==0 (
        echo [OK] Backend API responding correctly
    ) else (
        echo [WARNING] Backend responding but may have issues
    )
) else (
    echo [ERROR] Backend server not responding
)

echo.
echo Checking Frontend Server (Port 3000)...
curl -s http://localhost:3000 >nul 2>&1
if %errorlevel%==0 (
    echo [OK] Frontend server is running
    curl -s http://localhost:3000 | findstr "BYBIT AI SCANNER" >nul
    if %errorlevel%==0 (
        echo [OK] Frontend UI loaded correctly
    ) else (
        echo [WARNING] Frontend responding but may have issues
    )
) else (
    echo [ERROR] Frontend server not responding
)

echo.
echo Checking running processes...
tasklist /fi "WINDOWTITLE eq Backend Server*" /nh 2>nul | findstr "cmd.exe" >nul
if %errorlevel%==0 (
    echo [OK] Backend server process found
) else (
    echo [INFO] Backend server process not found
)

tasklist /fi "WINDOWTITLE eq Frontend Server*" /nh 2>nul | findstr "cmd.exe" >nul
if %errorlevel%==0 (
    echo [OK] Frontend server process found
) else (
    echo [INFO] Frontend server process not found
)

echo.
echo ========================================
echo Status check complete
echo ========================================
echo.
echo URLs to check manually:
echo Backend API: http://localhost:8000
echo Frontend UI: http://localhost:3000
echo API Docs: http://localhost:8000/docs
echo.
pause