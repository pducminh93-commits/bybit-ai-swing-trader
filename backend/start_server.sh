#!/bin/bash

# Start Bybit AI Swing Trader Backend
echo "Starting Bybit AI Swing Trader Backend..."

# Check if Python is available
if ! command -v python &> /dev/null; then
    echo "Python is not installed. Please install Python 3.8+ to continue."
    exit 1
fi

# Check if we're in the correct directory
if [ ! -f "main.py" ]; then
    echo "main.py not found. Please run this script from the backend directory."
    exit 1
fi

# Install dependencies if requirements.txt exists
if [ -f "requirements.txt" ]; then
    echo "Installing Python dependencies..."
    pip install -r requirements.txt
fi

# Initialize database if needed
echo "Initializing database..."
python init_db.py

# Start the server
echo "Starting server on http://localhost:8000"
echo "Press Ctrl+C to stop the server"
uvicorn main:app --reload --host 0.0.0.0 --port 8000