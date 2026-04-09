@echo off
echo Installing backend dependencies...
cd backend
call venv\Scripts\activate.bat
pip install -r requirements.txt
cd ..
echo Installing frontend dependencies...
cd frontend
npm install
cd ..
echo Installation complete!
pause