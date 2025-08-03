from flask import Flask, render_template, request, flash, jsonify, redirect, url_for, session
import os, sqlite3, fitz, re, json
from models_db import db, Recruiter
from flask_sqlalchemy import SQLAlchemy
from llama_cpp import Llama

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

def extract_text_from_pdf(path):
    doc = fitz.open(path)
    return "\n".join(p.get_text() for p in doc)

def extract_candidate_name(resume_text):
    lines = resume_text.split('\n')[:5]
    for line in lines:
        line = line.strip()
        if line and len(line.split()) <= 4 and not any(char.isdigit() for char in line):
            words = line.split()
            if len(words) >= 2 and all(word.isalpha() for word in words):
                return ' '.join(words[:2])
    return "there"

def generate_response(prompt):
    out = llm(f"[INST] {prompt} [/INST]", max_tokens=400, temperature=0.7, stop=["</s>"])
    return out["choices"][0]["text"].strip()

def clean_response(response):
    lines = response.split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if line and not re.match(r'^\d+\.', line):
            cleaned_lines.append(line)
            break
    result = ' '.join(cleaned_lines).strip()
    if '?' in result:
        parts = result.split('?')
        result = parts[0] + '?'
    return result

# Context prompt
CTX = "AI Interviewer prompt..."
MAX_TURNS = 15
FIRST_QUESTION = "Hello candidate! Introduce yourself."

@app.route('/')
def loading():      
    return render_template('loading.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        recruiter = Recruiter.query.filter_by(email=email, password=password).first()
        if recruiter:
            return redirect(url_for('recruiter_dashboard', recruiter_name=recruiter.name))
        else:
            return "Invalid credentials", 401
    return render_template('login.html')

@app.route('/recruiter_dashboard')
def recruiter_dashboard():
    recruiter_name = request.args.get('recruiter_name', 'Recruiter')
    return render_template('recruiterdboard.html', name=recruiter_name)

@app.route('/texInterview')
def text_interview():
    return render_template('texInterview.html')

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
