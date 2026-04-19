import asyncio
import json
import logging
import os
import tempfile
import wave
from datetime import datetime
from typing import Optional

import numpy as np
import speech_recognition as sr
import pyttsx3
import whisper
import torch
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydub import AudioSegment
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import redis
import requests

# Initialize FastAPI
app = FastAPI(title="Free AI Call Center")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database setup
DATABASE_URL = "sqlite:///./call_center.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class CallLog(Base):
    __tablename__ = "call_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    caller_id = Column(String, index=True)
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)
    transcript = Column(Text)
    ai_responses = Column(Text)
    status = Column(String, default="active")

Base.metadata.create_all(bind=engine)

# Redis for real-time data
redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

# Initialize Whisper for STT (free, offline)
print("Loading Whisper model...")
whisper_model = whisper.load_model("base")

# Initialize TTS
tts_engine = pyttsx3.init()
tts_engine.setProperty('rate', 150)
tts_engine.setProperty('volume', 0.9)

# Ollama client for free LLM
class OllamaClient:
    def __init__(self, base_url="http://localhost:11434"):
        self.base_url = base_url
    
    def generate(self, prompt, model="llama2"):
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=30
            )
            if response.status_code == 200:
                return response.json()["response"]
            return "I'm sorry, I'm having trouble processing your request."
        except Exception as e:
            logging.error(f"Ollama error: {e}")
            return "I'm sorry, I'm having trouble processing your request."

ollama_client = OllamaClient()

class AIAgent:
    def __init__(self):
        self.conversation_history = {}
        self.system_prompt = """You are a helpful customer service AI agent. 
        Keep responses concise, friendly, and professional. 
        If you cannot help with something, offer to transfer to a human agent.
        Always ask how you can help at the beginning."""
    
    def process_audio(self, audio_data):
        """Convert audio to text using Whisper"""
        try:
            # Save audio to temporary file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_file.write(audio_data)
                tmp_file_path = tmp_file.name
            
            # Transcribe with Whisper
            result = whisper_model.transcribe(tmp_file_path)
            os.unlink(tmp_file_path)  # Clean up
            
            return result["text"].strip()
        except Exception as e:
            logging.error(f"Speech recognition error: {e}")
            return ""
    
    def generate_response(self, text, caller_id):
        """Generate AI response using Ollama"""
        if caller_id not in self.conversation_history:
            self.conversation_history[caller_id] = []
        
        # Add user message to history
        self.conversation_history[caller_id].append(f"Customer: {text}")
        
        # Create context-aware prompt
        history = "\n".join(self.conversation_history[caller_id][-5:])  # Last 5 exchanges
        prompt = f"{self.system_prompt}\n\nConversation history:\n{history}\n\nCustomer: {text}\nAgent:"
        
        response = ollama_client.generate(prompt)
        
        # Add AI response to history
        self.conversation_history[caller_id].append(f"Agent: {response}")
        
        return response
    
    def text_to_speech(self, text):
        """Convert text to speech using pyttsx3"""
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tts_engine.save_to_file(text, tmp_file.name)
                tts_engine.runAndWait()
                
                # Read the generated audio file
                with open(tmp_file.name, 'rb') as audio_file:
                    audio_data = audio_file.read()
                
                os.unlink(tmp_file.name)  # Clean up
                return audio_data
        except Exception as e:
            logging.error(f"TTS error: {e}")
            return b""

ai_agent = AIAgent()

# AGI Server for Asterisk
from asterisk.agi import AGI

class CallHandler:
    def __init__(self):
        self.active_calls = {}
    
    async def handle_call(self, agi: AGI):
        caller_id = agi.env['agi_callerid']
        
        # Log call start
        db = SessionLocal()
        call_log = CallLog(caller_id=caller_id)
        db.add(call_log)
        db.commit()
        call_id = call_log.id
        db.close()
        
        # Store call info in Redis
        redis_client.hset(f"call:{call_id}", mapping={
            "caller_id": caller_id,
            "status": "active",
            "start_time": datetime.utcnow().isoformat()
        })
        
        try:
            # Welcome message
            welcome_msg = "Hello! Thank you for calling. How can I help you today?"
            welcome_audio = ai_agent.text_to_speech(welcome_msg)
            
            # Play welcome message
            agi.stream_file("welcome")  # You'll need to convert audio to Asterisk format
            
            conversation_log = [f"Agent: {welcome_msg}"]
            
            while True:
                # Record user input
                agi.record_file("temp_recording", "wav", "#", 10000, 0, True, 3)
                
                # Process recorded audio
                with open("/tmp/asterisk-recording.wav", "rb") as f:
                    audio_data = f.read()
                
                user_text = ai_agent.process_audio(audio_data)
                if not user_text:
                    continue
                
                conversation_log.append(f"Customer: {user_text}")
                
                # Check for goodbye/hangup keywords
                if any(word in user_text.lower() for word in ["goodbye", "bye", "thank you", "thanks", "that's all"]):
                    goodbye_msg = "Thank you for calling! Have a great day!"
                    goodbye_audio = ai_agent.text_to_speech(goodbye_msg)
                    conversation_log.append(f"Agent: {goodbye_msg}")
                    # Play goodbye and hang up
                    break
                
                # Generate AI response
                response = ai_agent.generate_response(user_text, caller_id)
                conversation_log.append(f"Agent: {response}")
                
                # Convert response to audio and play
                response_audio = ai_agent.text_to_speech(response)
                # Convert and play through Asterisk
                
                # Update call log
                redis_client.hset(f"call:{call_id}", "last_exchange", json.dumps({
                    "customer": user_text,
                    "agent": response,
                    "timestamp": datetime.utcnow().isoformat()
                }))
        
        except Exception as e:
            logging.error(f"Call handling error: {e}")
        
        finally:
            # Log call end
            db = SessionLocal()
            call_log = db.query(CallLog).filter(CallLog.id == call_id).first()
            if call_log:
                call_log.end_time = datetime.utcnow()
                call_log.transcript = "\n".join(conversation_log)
                db.commit()
            db.close()
            
            redis_client.hset(f"call:{call_id}", "status", "completed")

# API Routes
@app.get("/api/calls")
async def get_calls():
    db = SessionLocal()
    calls = db.query(CallLog).order_by(CallLog.start_time.desc()).limit(50).all()
    db.close()
    
    return [
        {
            "id": call.id,
            "caller_id": call.caller_id,
            "start_time": call.start_time.isoformat() if call.start_time else None,
            "end_time": call.end_time.isoformat() if call.end_time else None,
            "status": call.status
        }
        for call in calls
    ]

@app.get("/api/calls/{call_id}")
async def get_call_details(call_id: int):
    db = SessionLocal()
    call = db.query(CallLog).filter(CallLog.id == call_id).first()
    db.close()
    
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    return {
        "id": call.id,
        "caller_id": call.caller_id,
        "start_time": call.start_time.isoformat() if call.start_time else None,
        "end_time": call.end_time.isoformat() if call.end_time else None,
        "transcript": call.transcript,
        "ai_responses": call.ai_responses,
        "status": call.status
    }

@app.websocket("/ws/dashboard")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Send real-time call updates
            active_calls = []
            for key in redis_client.scan_iter(match="call:*"):
                call_data = redis_client.hgetall(key)
                if call_data.get("status") == "active":
                    active_calls.append(call_data)
            
            await websocket.send_json({"active_calls": active_calls})
            await asyncio.sleep(2)
    except Exception as e:
        logging.error(f"WebSocket error: {e}")

# Serve frontend
app.mount("/", StaticFiles(directory="../frontend/dist", html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
