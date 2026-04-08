@echo off
echo ========================================
echo Killing processes on ports 3000-3004
echo ========================================
echo.

echo Checking for processes using ports 3000-3004...

REM Try to kill processes on each port
for /L %%p in (3000,1,3004) do (
    echo Checking port %%p...
    REM Use PowerShell to find and kill process
    powershell -Command "try { $process = Get-NetTCPConnection -LocalPort %%p -ErrorAction Stop | Select-Object -ExpandProperty OwningProcess; if ($process) { Stop-Process -Id $process -Force; Write-Host 'Killed process on port %%p' } else { Write-Host 'No process found on port %%p' } } catch { Write-Host 'No process on port %%p' }" 2>nul
)

echo.
echo Checking Node.js processes...
taskkill /f /im node.exe >nul 2>&1
if %errorlevel%==0 (
    echo [OK] Killed Node.js processes
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