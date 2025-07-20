from flask import Flask, render_template, request, flash, jsonify, redirect, url_for, session
import os, sqlite3, fitz
from models_db import db, Recruiter
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)            
app.secret_key = os.getenv('KEY', 'change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///recruiters.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)  

with app.app_context():
    db.create_all() 
os.makedirs("uploads", exist_ok=True)
os.makedirs("static", exist_ok=True)

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

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
