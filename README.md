# Free AI Agent Call Center

A complete step-by-step implementation of an AI Call Center using Asterisk, Python (FastAPI), Whisper (STT), pyttsx3 (TTS), and Ollama (LLM) for processing. It features a React based real-time dashboard.

## Project Structure

```
ai-call-center/
├── asterisk_config/       # Scripts to be used in /etc/asterisk on Ubuntu
│   ├── extensions.conf
│   └── sip.conf
├── backend/               # FastAPI backed and AGI server
│   ├── agi_server.py
│   ├── main.py
│   └── requirements.txt
├── frontend/              # React based web dashboard
├── setup.sh               # Main setup script (Ubuntu-focused)
└── start_callcenter.sh    # Main starting script
```

## Running

This project natively relies on **Linux (Ubuntu)**. If you are on Windows, you will need to utilize **WSL2**, a Virtual Machine, or a remote server. 

### Ubuntu / Linux Instructions

1. Run `chmod +x setup.sh` and execute `./setup.sh` to install everything including dependencies.
2. Ensure you have your `asterisk` configured properly with the `asterisk_config` files.
3. Start the system via `./start_callcenter.sh`.
4. Connect using a softphone and monitor the calls at `http://localhost:8000`.
