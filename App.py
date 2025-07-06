from flask import Flask, render_template, request, flash, jsonify, redirect, url_for, session
import os, sqlite3
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
