#!/bin/bash
cd backend
source venv/bin/activate

# Start backend services
python agi_server.py &
python main.py &

echo "AI Call Center started!"
echo "Dashboard: http://localhost:8000"
echo "AGI Server: localhost:4573"
