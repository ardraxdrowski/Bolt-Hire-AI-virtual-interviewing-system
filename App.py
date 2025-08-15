from flask import Flask, render_template, request, flash, jsonify, redirect, url_for, session
import os, sqlite3, fitz, re, json
from models_db import db, Recruiter
from flask_sqlalchemy import SQLAlchemy
from llama_cpp import Llama
import whisper
from TTS.api import TTS
from pydub import AudioSegment
from pydub.utils import which

app = Flask(__name__)            
app.secret_key = os.getenv('KEY', 'change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///recruiters.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)  

with app.app_context():
    db.create_all() 
os.makedirs("uploads", exist_ok=True)
os.makedirs("static", exist_ok=True)

MODEL_PATH = os.getenv('MODEL_PATH', 'D:/Models/mistral-7b-instruct-v0.1.Q4_K_M.gguf')
llm = Llama(model_path=MODEL_PATH, n_ctx=2048, n_threads=6, n_batch=256)
whisper_model = whisper.load_model("base")
tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC")
AudioSegment.converter = which("ffmpeg")

# basic parser and LLM functions...
# (Omitted here for brevity in building intermediate app, but has whisper/tts routes)

@app.route('/speak', methods=['POST'])
def speak():
    txt = request.json.get('text', '')
    out = os.path.join("static", "output.wav")
    tts.tts_to_file(text=txt, file_path=out)
    return jsonify({"status": "ok"})

@app.route('/transcribe', methods=['POST'])
def transcribe():
    f = request.files.get('audio')
    in_path = os.path.join("uploads", "in.webm")
    wav = os.path.join("uploads", "in.wav")
    f.save(in_path)
    AudioSegment.from_file(in_path).export(wav, format="wav")
    txt = whisper_model.transcribe(wav)["text"]
    return jsonify({"response": "transcribed text", "transcript": txt})

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
