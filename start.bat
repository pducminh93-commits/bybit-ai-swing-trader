@echo off
echo ========================================
echo Starting Bybit AI Swing Trader
echo ========================================
echo.

echo [0/3] Checking prerequisites...
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found!
    echo Please run install_nodejs.bat first
    pause
    exit /b 1
)
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found!
    echo Please install Python 3.12+ from https://python.org
    pause
    exit /b 1
)

REM Check if frontend dependencies are installed
cd frontend
if not exist node_modules (
    echo [ERROR] Frontend dependencies not installed!
    echo Please run: setup_frontend.bat
    cd ..
    pause
    exit /b 1
)
cd ..

echo [OK] Prerequisites check passed

echo.
echo [1/3] Starting Backend Server...
cd backend
if not exist venv (
    echo [ERROR] Backend virtual environment not found!
    echo Run setup_backend.bat first
    cd ..
    pause
    exit /b 1
)
call venv\Scripts\activate.bat
start "Backend Server" cmd /c "uvicorn main:app --reload --host 0.0.0.0 --port 8000"
cd ..
echo Backend started on http://localhost:8000
echo.

timeout /t 5 /nobreak > nul

echo [2/3] Starting Frontend Server...
cd frontend
start "Frontend Server" cmd /c "npm run dev"
cd ..
echo Frontend started on http://localhost:3000
echo.

timeout /t 3 /nobreak > nul

echo [3/3] Opening browser...
start http://localhost:3000

echo.
echo ========================================
echo All servers started successfully!
echo ========================================
echo.
echo URLs:
echo Frontend: http://localhost:3000
echo Backend:  http://localhost:8000
echo API Docs: http://localhost:8000/docs
echo.
echo Press any key to close this launcher...
pause > nul