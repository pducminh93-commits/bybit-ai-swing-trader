@echo off
echo ========================================
echo Killing processes on port 3000 for frontend
echo ========================================
echo.

echo Checking for processes using port 3000...

REM Kill process on port 3000
powershell -Command "try { $process = Get-NetTCPConnection -LocalPort 3000 -ErrorAction Stop | Select-Object -ExpandProperty OwningProcess; if ($process) { Stop-Process -Id $process -Force; Write-Host 'Killed process on port 3000' } else { Write-Host 'No process found on port 3000' } } catch { Write-Host 'No process on port 3000' }" 2>nul

echo.
echo Checking Node.js processes...
taskkill /f /im node.exe >nul 2>&1
if %errorlevel%==0 (
    echo [OK] Killed Node.js processes
) else (
    echo [INFO] No Node.js processes found
)

echo.
echo Checking Python processes (for backend)...
taskkill /f /im python.exe >nul 2>&1
if %errorlevel%==0 (
    echo [OK] Killed Python processes
) else (
    echo [INFO] No Python processes found
)

echo.
echo Port 3000 should now be free for frontend.
pause
) else (
    echo [INFO] No Node.js processes found
)

echo.
echo Checking Python processes...
taskkill /f /im python.exe >nul 2>&1
if %errorlevel%==0 (
    echo [OK] Killed Python processes
) else (
    echo [INFO] No Python processes found
)

echo.
timeout /t 2 /nobreak > nul

echo Checking remaining processes...
for /L %%p in (3000,1,3004) do (
    netstat -ano | findstr :%%p >nul 2>&1
    if %errorlevel%==0 (
        echo [WARNING] Port %%p still in use
    ) else (
        echo [OK] Port %%p is free
    )
)

echo.
echo ========================================
echo Port cleanup completed
echo ========================================
pause