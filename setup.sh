#!/bin/bash

echo "Setting up Free AI Call Center..."

# Install system dependencies
sudo apt update
sudo apt install -y python3-pip nodejs npm redis-server postgresql postgresql-contrib
sudo apt install -y asterisk asterisk-dev sox ffmpeg

# Install Ollama (Free LLM)
curl -fsSL https://ollama.ai/install.sh | sh

# Start services
sudo systemctl enable redis-server
sudo systemctl start redis-server
sudo systemctl enable asterisk
sudo systemctl start asterisk

# Install Python dependencies
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Download Ollama model
ollama pull llama2

# Setup frontend
cd ../frontend
npm install
npm run build

echo "Setup complete! Run ./start_callcenter.sh to start the system"
