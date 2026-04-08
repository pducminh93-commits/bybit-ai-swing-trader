# Bybit AI Swing Trader - Quick Start

## 🚀 Quick Start with Scripts

### Prerequisites
- **Python 3.12+**: Download from https://python.org
- **Node.js LTS**: Download from https://nodejs.org (see below)
- **Git**: Download from https://git-scm.com (optional)

### Installing Node.js
If you get "Node.js not found" error:

1. Run: `install_nodejs.bat`
2. Follow the instructions to download Node.js LTS
3. Install the .msi file
4. Restart Command Prompt
5. Verify: `node --version` and `npm --version`

See `NODEJS_INSTALL_GUIDE.md` for detailed instructions.

## Starting the Application

### Windows (Recommended)
#### Method 1: One-Click Start
```bash
# Double-click start.bat or run in command prompt
start.bat
```

### Linux/Mac
#### Method 1: Shell Script
```bash
# Make executable and run
chmod +x start.sh
./start.sh
```

#### Method 2: Manual Start
```bash
# Terminal 1 - Backend
cd backend
source venv/Scripts/activate  # or venv/bin/activate on Mac/Linux
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 - Frontend
cd frontend
npm run dev
```

### Stopping the Application

#### Windows
```bash
stop.bat
```

#### Linux/Mac
```bash
# Press Ctrl+C in each terminal
# Or kill processes manually
pkill -f uvicorn
pkill -f "npm run dev"
```

## Access URLs
- **Frontend (UI)**: http://localhost:3000
- **Backend (API)**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs (Swagger UI)

## Development Mode

For development with hot reload:
1. Run start script
2. Edit code in your IDE
3. Changes will auto-reload:
   - Backend: FastAPI auto-reloads on Python file changes
   - Frontend: Vite auto-reloads on React/TypeScript changes

## Troubleshooting

### Backend Won't Start
```bash
# Check if port 8000 is free
netstat -ano | findstr :8000  # Windows
netstat -tulpn | grep :8000   # Linux/Mac

# Kill process using port 8000
# Windows: taskkill /PID <PID> /F
# Linux/Mac: kill <PID>
```

### Frontend Won't Start
```bash
# Check Node.js version
node --version

# Clear node_modules and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### Both Servers Won't Start
```bash
# Check if files exist
ls start.*

# Run with verbose output
# Check console output for specific errors
```

## System Requirements

- **OS**: Windows 10+, Linux, macOS
- **RAM**: Minimum 4GB
- **Disk Space**: 2GB free
- **Network**: Internet connection for initial setup

## Support

If you encounter issues:
1. Check the console output in server terminals
2. Verify all dependencies are installed
3. Check firewall/antivirus blocking ports
4. Try incognito/private browsing mode