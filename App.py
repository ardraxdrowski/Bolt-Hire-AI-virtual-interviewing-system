from flask import Flask, render_template, render_template_string, request, flash, jsonify, redirect, url_for, session
import os, sqlite3, whisper, fitz, re, json
from pydub import AudioSegment
from pydub.utils import which
from llama_cpp import Llama
from langdetect import detect
from TTS.api import TTS
from datetime import datetime
from models_db import db, Recruiter
from flask_sqlalchemy import SQLAlchemy
import smtplib
from datetime import datetime
import uuid
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv
load_dotenv()



#Initial setup 

app = Flask(__name__)            
app.secret_key = os.getenv('KEY', 'change-in-production')
#database config
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///recruiters.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)  

with app.app_context():
    db.create_all() 
os.makedirs("uploads", exist_ok=True)
os.makedirs("static", exist_ok=True)

EMAIL_CONFIG = {
    'sendgrid_api_key': 'SendGrid-API-key', 
    'from_email': 'mailid@whatever.com',
    'from_name': 'makeshiftname'
}
#validation code block to check if required env variables have been set
if not EMAIL_CONFIG['sendgrid_api_key']:
    print("WARNING: SENDGRID_API_KEY not set in environment variables!")
    print("Email functionality will not work until you set up your .env file")

def create_simple_email(to_email, subject, body):
    """Create a simple email message without MIME"""
    message = f"""From: {EMAIL_CONFIG['sender_name']} <{EMAIL_CONFIG['email']}>
To: {to_email}
Subject: {subject}

{body}"""
    return message


def send_interview_invitation(candidate_email, candidate_name, recruiter_name, job_role):
    """Send interview invitation email using SendGrid API"""
    try:
        print("DEBUG - EMAIL_CONFIG:", EMAIL_CONFIG)
        print("DEBUG - API Key exists?", 'sendgrid_api_key' in EMAIL_CONFIG)
        print("DEBUG - API Key value:", EMAIL_CONFIG.get('sendgrid_api_key', 'NOT FOUND'))
        if not EMAIL_CONFIG.get('sendgrid_api_key'):
            return False, "SendGrid API key is missing"
        
        # Generate unique interview link
        interview_token = str(uuid.uuid4())
        interview_link = f"http://localhost:5000/interview/{interview_token}"
        
        # Store the interview session in database
        with sqlite3.connect(DB) as conn:
            conn.execute('''
                INSERT INTO interview_sessions (session_id, candidate_name, candidate_email, job_role, status)
                VALUES (?, ?, ?, ?, 'invitation')
            ''', (interview_token, candidate_name, candidate_email, job_role))
        
        # Create email content
        subject = f"Interview Invitation - {job_role} Position"
        
        body = f"""Dear {candidate_name},

We are pleased to invite you for an AI-powered interview for the {job_role} position.

INTERVIEW DETAILS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Position: {job_role}
- Interview Type: AI Virtual Interview  
- Duration: Approximately 20-30 minutes
- Recruiter: {recruiter_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

INSTRUCTIONS:
1. Click on the interview link below to start
2. Ensure you have a stable internet connection
3. Find a quiet environment for the interview
4. You can choose between voice or text mode during the interview

🎤 INTERVIEW LINK:
{interview_link}

⚠️ IMPORTANT NOTE: This link is valid for 7 days from the date of this email.

If you have any technical issues or questions, please contact us immediately.

Best regards,
{recruiter_name}
AI Interview System

---
This is an automated message from the AI Interview System.
"""
        
        # Create and send message via SendGrid
        message = Mail(
            from_email=(EMAIL_CONFIG['from_email'], EMAIL_CONFIG['from_name']),
            to_emails=candidate_email,
            subject=subject,
            plain_text_content=body
        )
        
        sg = SendGridAPIClient(EMAIL_CONFIG['sendgrid_api_key'])
        response = sg.send(message)
        
        print(f"Email sent successfully to {candidate_email}")
        return True, "Interview invitation sent successfully"
        
    except Exception as e:
      import traceback
      error_details = traceback.format_exc()
      print(f"FULL ERROR DETAILS:")
      print(error_details)
      return False, f"Failed to send email: {str(e)}"

#Test email function
@app.route('/test_email_simple')
def test_email_simple():
    """Test route to check if simple email is working"""
    try:
        #Test email credentials
        server = smtplib.SMTP_SSL(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'], timeout=10)
        server.login(EMAIL_CONFIG['email'], EMAIL_CONFIG['password'])
        server.quit()
        
        return jsonify({
            'success': True,
            'message': 'Email configuration is working! ✅'
        })
    except smtplib.SMTPAuthenticationError:
        return jsonify({
            'success': False,
            'message': 'Authentication failed. Check your email and app password.'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Email configuration error: {str(e)}'
        })

#Global DB path- performance DB
DB = 'performance.db'

MODEL_PATH = os.getenv('MODEL_PATH', 'D:/Models/mistral-7b-instruct-v0.1.Q4_K_M.gguf')

#models
llm            = Llama(model_path= 'MODEL_PATH', n_ctx=2048, n_threads=6, n_batch=256)
whisper_model  = whisper.load_model("base")
tts            = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC")
AudioSegment.converter = which("ffmpeg")

#Persistence 

def init_performance_db():
    with sqlite3.connect('performance.db') as con:
        print("Connected to DB:", 'performance.db')
        con.execute('''
            CREATE TABLE IF NOT EXISTS performancefeedback (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              rating INTEGER NOT NULL,
              feedback TEXT
            )''')
        con.execute('''
            CREATE TABLE IF NOT EXISTS performance (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              candidate_id TEXT,
              candidate_name TEXT, 
              question TEXT,
              answer TEXT,
              tech_score REAL,
              comm_score REAL,
              crit_score REAL,
              team_score REAL,
              leadership_score REAL,
              overall_score REAL,
              percentile REAL,
              ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
        con.execute('''
            CREATE TABLE IF NOT EXISTS interview_sessions (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              session_id TEXT UNIQUE,
              candidate_id TEXT,
              candidate_name TEXT,
              candidate_email TEXT,
              job_role TEXT,
              start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
              end_time TIMESTAMP,
              final_scores TEXT,
              status TEXT DEFAULT 'active'
            )''')
#init_performance_db()
import sqlite3
#user experience feedback storing
def init_feedback_db():
    conn = sqlite3.connect('feedback.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            interface_rating INTEGER,
            relevance_rating INTEGER,
            flow_rating INTEGER,
            comfort_rating INTEGER,
            mode TEXT,
            issues TEXT,
            issue_details TEXT,
            suggestions TEXT
        )
    ''')
    conn.commit()
    conn.close()


#init_db()


#Candidate and JD context fetching
def extract_text_from_pdf(path):
    doc = fitz.open(path)
    return "\n".join(p.get_text() for p in doc)

def extract_candidate_name(resume_text):
    """Extract candidate name from resume text"""
    lines = resume_text.split('\n')[:5]  #checking first 5 lines
    for line in lines:
        line = line.strip()
        if line and len(line.split()) <= 4 and not any(char.isdigit() for char in line):
            #Simple heuristic: likely a name if it's short, has no numbers
            words = line.split()
            if len(words) >= 2 and all(word.isalpha() for word in words):
                return ' '.join(words[:2])  #Return first two words as name
    return "there"  #Default fallback

def generate_response(prompt):
    out = llm(f"[INST] {prompt} [/INST]", max_tokens=400, temperature=0.7, stop=["</s>"])
    return out["choices"][0]["text"].strip()

def clean_response(response):
    """Clean the response to ensure only one question is returned"""
    #Removig numbered lists or multiple questions
    lines = response.split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if line and not re.match(r'^\d+\.', line):  #Removing numbered items
            cleaned_lines.append(line)
            break  #considering only the first meaningful line
    
    result = ' '.join(cleaned_lines).strip()
    #Removing any trailing question marks beyond the first question
    if '?' in result:
        parts = result.split('?')
        result = parts[0] + '?'
    
    return result

def evaluate_answer(question, answer, jd_context, resume_context):
    """Evaluate candidate's answer across multiple dimensions"""
    evaluation_prompt = f"""
    You are an expert interviewer evaluating a candidate's response. Rate the answer on a scale of 1-10 for each dimension:

    Job Context: {jd_context}
    Resume Context: {resume_context}
    Question: {question}
    Answer: {answer}

    Evaluate and provide scores (1-10) for:
    1. Technical Skills (domain knowledge, technical accuracy)
    2. Communication Skills (clarity, articulation, structure)
    3. Critical Thinking (problem-solving, analytical approach)
    4. Teamwork & Collaboration (team experience, interpersonal skills)
    5. Leadership Potential (initiative, decision-making, influence)

    Format your response exactly as:
    Technical: X
    Communication: Y
    Critical: Z
    Teamwork: W
    Leadership: V
    """
    
    try:
        evaluation = generate_response(evaluation_prompt)
        scores = {}
        
        #Parsing scores from the response
        for line in evaluation.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                try:
                    score = float(re.findall(r'\d+(?:\.\d+)?', value)[0])
                    if 'technical' in key:
                        scores['tech'] = min(10, max(1, score))
                    elif 'communication' in key:
                        scores['comm'] = min(10, max(1, score))
                    elif 'critical' in key:
                        scores['crit'] = min(10, max(1, score))
                    elif 'teamwork' in key:
                        scores['team'] = min(10, max(1, score))
                    elif 'leadership' in key:
                        scores['leadership'] = min(10, max(1, score))
                except:
                    continue
        
        #Filling in any missing scores with default values
        for key in ['tech', 'comm', 'crit', 'team', 'leadership']:
            if key not in scores:
                scores[key] = 5.0
                
        return scores
    except:
        #Returning default scores if evaluation fails
        return {'tech': 5.0, 'comm': 5.0, 'crit': 5.0, 'team': 5.0, 'leadership': 5.0}
def get_last_valid_qa():
    """Fetch the most recent question-answer pair where the answer was not empty"""
    with sqlite3.connect(DB) as conn:
        cursor = conn.execute('''
            SELECT question, answer FROM performance
            WHERE candidate_name = ?
              AND DATE(ts) = DATE('now')
              AND TRIM(answer) != ''
            ORDER BY id DESC LIMIT 1
        ''', (candidate_name,))
        
        row = cursor.fetchone()
        if row:
            return row[0], row[1]
        else:
            return None, None

def calculate_percentile(scores):
    """Calculate percentile based on overall performance"""
    overall = sum(scores.values()) / len(scores)
    #Simple percentile calculation-
    percentile = min(99, max(1, (overall - 1) * 11.11))  #1-10 scale to percentile
    return round(percentile, 1)

#Loading and processing resume and JD
resume_text = extract_text_from_pdf("Resume.pdf")
jd_text     = open("JD.txt","r",encoding="utf-8").read()
jd_sum      = generate_response("Summarise this job description in 3 lines, focusing on key requirements:\n"+jd_text)
res_sum     = generate_response("Summarise this resume in 3 lines, focusing on key qualifications:\n"+resume_text)
candidate_name = extract_candidate_name(resume_text)

CTX = (
    "You are an AI interviewer conducting a professional, conversational interview.\n\n"
    f"Job Requirements:\n{jd_sum}\n\n"
    f"Candidate Background:\n{res_sum}\n\n"
    "ROLE: Your role is to assess the compatibility of the candidate for the specified job decscription. So, Make questions relevant to the role and candidate's background. "
    "INTERVIEW GUIDELINES:\n"
    "• Ask ONE question at a time, maximum 15 questions total\n"
    "• Make each question contextual to their previous response\n"
    "• While building on their responses by referencing what they've shared, do not get fixated on just their response and instead, keep a balance between being contextual to the conversation, yet properly assessing the candidate for the Job Description given.\n"
    "• Keep the conversation natural and flowing like human dialogue\n"
    "• If the candidate replies in a non-English language, politely ask them to continue in English.\n"
    "• If the candidate responds nervously (e.g., says \"Im nervous, \"feeling anxious\"), reassure them politely and encourage them to continue.\n"
    "• If the candidate responds off-topic, gently guide them back to the question.\n"
    "• If the candidate does not answer or says-I don't know, acknowledge politely and move to the next question.\n"
    "• Always respond naturally, as a human interviewer would.\n"
    "• While Technical Skills (domain knowledge) should be the main focus, also include questions such that you can assess the candidate holistically and not just technically. Ask stuff to assess thier skills across: Communication Skills (clarity, articulation, structure), Critical Thinking (problem-solving, analytical approach), Teamwork & Collaboration (team experience, interpersonal skills) and Leadership Potential (initiative, decision-making, influence), based on what is required for the role and the JD.\n\n"
    
    "ASSESSMENT AREAS:\n"
    "• Role-specific technical/functional skills\n"
    "• Problem-solving and out-of-the-box thinking (with real examples)\n"
    "• Communication and critical thinking\n"
    "• Teamwork and other relevant soft skills for this role\n\n"
    
    "CONVERSATION FLOW:\n"
    "• While building on their responses by referencing what they've shared, do not get fixated on just their response and instead, keep a balance between being contextual to the conversation, yet properly assessing the candidate for the Job Description given.\n"
    "• Explore interesting resume elements not yet discussed\n"
    "• If they seem unsure, confused, ignorant or say'I don't know' or similar, gently guide them\n"
    "• Make them feel heard and valued\n\n"
    
    "End the interview politely after 15 questions or when assessment is complete. "
    "If they ask you anything before wrapping up(ask this as second last question), acknowledge their query and answer it briefly and conclude with a proper thanking messsage(last dialogue)"
) 

MAX_TURNS    = 15
FIRST_QUESTION = f"Hello {candidate_name}! I hope you're doing well today. I'm excited to learn more about you and discuss this opportunity. To start, could you please introduce yourself and tell me what drew you to apply for this position?"

#core logic
def initialise_session():
    """Initialise or ensure session has required variables"""
    if 'session_id' not in session:
        session['session_id'] = f"interview_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        #log:session start
        with sqlite3.connect(DB) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO interview_sessions (session_id, candidate_name, job_role, start_time)
                VALUES (?, ?, ?, ?)
            ''', (session['session_id'], candidate_name, "Software Developer", datetime.now()))
    
    if 'turn_count' not in session:
        session['turn_count'] = 0
    if 'last_question' not in session:
        session['last_question'] = FIRST_QUESTION
    #if 'skipped' not in session:
    #     session['skipped'] = []
    if 'turn_complete' not in session:
        session['turn_complete'] = True
    if 'mode' not in session:
        session['mode'] = 'voice'
    if 'interview_started' not in session:
        session['interview_started'] = False

 
def finalise_interview():
    """Calculate final scores and update interview session"""
    with sqlite3.connect(DB) as conn:
        #fetching all performance data for this session
        cursor = conn.execute('''
            SELECT AVG(tech_score), AVG(comm_score), AVG(crit_score), 
                   AVG(team_score), AVG(leadership_score), AVG(overall_score), AVG(percentile)
            FROM performance 
            WHERE candidate_name = ? AND DATE(ts) = DATE('now')
        ''', (candidate_name,))
        
        result = cursor.fetchone()
        if result and result[0]:
            final_scores = {
                'technical': round(result[0], 2),
                'communication': round(result[1], 2),
                'critical_thinking': round(result[2], 2),
                'teamwork': round(result[3], 2),
                'leadership': round(result[4], 2),
                'overall': round(result[5], 2),
                'percentile': round(result[6], 1)
            }
            
            #Update- session record
            conn.execute('''
                UPDATE interview_sessions 
                SET end_time = ?, final_scores = ?, status = 'completed'
                WHERE session_id = ?
            ''', (datetime.now(), json.dumps(final_scores), session.get('session_id')))

# #Routes  
@app.route('/start_interview', methods=['GET', 'POST'])
def start_interview():
    
    if 'interview_token' in session:
        token = session['interview_token']
        session['session_id'] = token
         
        global candidate_name
        if 'candidate_name_from_email' in session:
            candidate_name = session['candidate_name_from_email']
    else:
        session.clear()
        initialise_session()
    
    #Don't reset if interview has already started (for mode switches)
    if not session.get('interview_started', False):
        session['turn_count'] = 0
        session['last_question'] = FIRST_QUESTION
        session['turn_complete'] = True
        session['interview_started'] = True
    
    return jsonify({"response": session['last_question']})
 

@app.route('/test_send_email')
def test_send_email():
    """Quick test route to send yourself an email"""
    success, message = send_interview_invitation(
        candidate_email="your-email@gmail.com",  # Replace with your email
        candidate_name="Test Candidate", 
        recruiter_name="Test Recruiter",
        job_role="Test Position"
    )
    
    if success:
        return f"<h1>✅ Test Email Sent!</h1><p>{message}</p><p>Check your inbox!</p>"
    else:
        return f"<h1>❌ Email Failed</h1><p>{message}</p>"
    
@app.route('/ask', methods=['POST'])
def ask():
    initialise_session()

    def strip_intro(text):
        text = text.strip()
        lowered = text.lower()
        bad_starts = [
            "sure", "hi", "hello", "welcome", "thanks for",
            "let's start", "to begin", "let's get started",
            "i'm excited", "i'm looking forward",
            "today we'll", "thanks again", "shall we begin"
        ]
        for phrase in bad_starts:
            if lowered.startswith(phrase):
                lines = text.split('\n')
                lines = [line for line in lines if phrase not in line.lower()]
                text = '\n'.join(lines).strip()
                break
        return text

    usr = request.json.get('message') or request.json.get('user_input') or ''
    if not usr.strip():
        return jsonify({"response": "I didn't catch that. Could you please try again?"})

    raw_response = handle_interview_logic(usr)
    cleaned_response = strip_intro(raw_response)

    return jsonify({"response": cleaned_response})

 
#TTS,STT 
@app.route('/speak', methods=['POST'])
def speak():
    txt = request.json.get('text', '')
    if not txt:
        return jsonify({"status": "error", "message": "No text provided"}), 400
    
    out = os.path.join("static", "output.wav")
    try:
        tts.tts_to_file(text=txt, file_path=out)
        session['turn_complete'] = False
        return jsonify({"status": "ok"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/transcribe', methods=['POST'])
def transcribe():
    f = request.files.get('audio')
    if not f: 
        return jsonify({"response": "No audio received"}), 400
    
    try:
        in_path = os.path.join("uploads", "in.webm")
        wav = os.path.join("uploads", "in.wav")
        f.save(in_path)
        AudioSegment.from_file(in_path).export(wav, format="wav")
        txt = whisper_model.transcribe(wav)["text"]
        
        session['turn_complete'] = True
        response = handle_interview_logic(txt)
        
        return jsonify({"response": response, "transcript": txt})
    except Exception as e:
        return jsonify({"response": f"Sorry, I couldn't process your audio. Could you try again? Error: {str(e)}"}), 500

# @app.route('/end_interview', methods=['POST'])
# def end_interview():
#     session['interview_ended'] = True 
#     return jsonify({'status': 'success'})

@app.route('/candidate_feedback')
def candidate_feedback():
    #Rendering candidate feedback form option and thank-you page
    return render_template('tocanfeedback.html')
@app.route('/submit_feedback', methods=['GET', 'POST'])
def submit_feedback():
    if request.method == 'POST':
        #Extracting form data
        interface = request.form.get('interface')
        relevance = request.form.get('relevance')
        flow = request.form.get('flow')
        comfort = request.form.get('comfort')
        mode = request.form.get('mode')
        issues = request.form.get('issues')
        issue_details = request.form.get('issue_details')
        suggestions = request.form.get('suggestions')

        #Storing into database
        conn = sqlite3.connect('feedback.db')
        c = conn.cursor()
        c.execute('''
            INSERT INTO feedback(
                interface_rating, relevance_rating, flow_rating, comfort_rating,
                mode, issues, issue_details, suggestions
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            interface, relevance, flow, comfort,
            mode, issues, issue_details, suggestions
        ))
        conn.commit()
        conn.close()

        return '', 200  #JS alert will handle success message

    #Rendering feedback form 
    return render_template('canfeedback.html')

@app.route('/candidate_performance/<candidate_id>')
def candidate_performance(candidate_id):
    with sqlite3.connect(DB) as conn:
        conn.row_factory = sqlite3.Row

        #Fetch individual performance records
        performance_data = conn.execute('''
            SELECT question, answer, tech_score, comm_score, crit_score, team_score, leadership_score, overall_score, percentile, ts
            FROM performance
            WHERE candidate_id = ? OR candidate_name =?
            ORDER BY ts ASC
        ''', (candidate_id, candidate_id)).fetchall()

        #Fetch session summary (optional)
        session_summary = conn.execute('''
            SELECT final_scores, start_time, end_time
            FROM interview_sessions
            WHERE (candidate_id = ? OR candidate_name = ?) AND DATE(start_time) = DATE('now')
            ORDER BY start_time DESC LIMIT 1
        ''', (candidate_id, candidate_id)).fetchone()

    return render_template('performance_fb.html',
                           candidate_id=candidate_id,
                           performance_data=performance_data,
                           session_summary=session_summary)

@app.route('/view_feedback')
def view_feedback():
    conn = sqlite3.connect('feedback.db')
    conn.row_factory = sqlite3.Row
    feedbacks = conn.execute('SELECT * FROM feedback ORDER BY timestamp DESC').fetchall()
    conn.close()
    return render_template('viewuserfb.html', feedbacks=feedbacks)

@app.route('/send_interview_invite', methods=['POST'])
def send_interview_invite():
    data = request.json
    candidate_email = data.get('candidate_email')
    candidate_name = data.get('candidate_name')
    recruiter_name = data.get('recruiter_name', 'HR Team')
    job_role = data.get('job_role', 'Software Developer')
    
    if not candidate_email or not candidate_name:
        return jsonify({
            'success': False,
            'message': 'Candidate email and name are required'
        }), 400
    
    success, message = send_interview_invitation(candidate_email, candidate_name, recruiter_name, job_role)
    
    if success:
        return jsonify({
            'success': True,
            'message': f'Interview invitation sent to {candidate_name} at {candidate_email}'
        })
    else:
        return jsonify({
            'success': False,
            'message': message
        }), 500

@app.route('/interview/<token>')
def interview_from_token(token):
    """Start interview from email token"""
    with sqlite3.connect(DB) as conn:
        cursor = conn.execute('''
            SELECT candidate_name, candidate_email, job_role, status
            FROM interview_sessions
            WHERE session_id = ?
        ''', (token,))
        session_data = cursor.fetchone()
    
    if not session_data:
        return f"""
        <html>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <h2>❌ Invalid Interview Link</h2>
            <p>This interview link is invalid or has expired.</p>
            <p>Please contact your recruiter for a new invitation.</p>
        </body>
        </html>
        """, 404
    
    candidate_name_from_token, candidate_email, job_role, status = session_data
    
    if status == 'completed':
        return f"""
        <html>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <h2>✅ Interview Already Completed</h2>
            <p>Hi {candidate_name_from_token}, you have already completed this interview.</p>
            <p>Thank you for your participation!</p>
        </body>
        </html>
        """
    
    #Set session data for the interview
    session['interview_token'] = token
    session['candidate_name_from_email'] = candidate_name_from_token
    session['candidate_email'] = candidate_email
    session['job_role'] = job_role
    
    #Update session status to active
    with sqlite3.connect(DB) as conn:
        conn.execute('''
            UPDATE interview_sessions 
            SET status = 'active', start_time = CURRENT_TIMESTAMP
            WHERE session_id = ?
        ''', (token,))
    
    #Redirect to interview start page
    return f"""
    <html>
    <head>
        <title>Start Interview</title>
        <style>
            body {{ font-family: Arial; max-width: 600px; margin: 50px auto; padding: 20px; }}
            .container {{ text-align: center; background: #f8f9fa; padding: 30px; border-radius: 10px; }}
            .btn {{ padding: 15px 30px; margin: 10px; border: none; border-radius: 5px; font-size: 16px; cursor: pointer; text-decoration: none; display: inline-block; }}
            .voice-btn {{ background: #007bff; color: white; }}
            .text-btn {{ background: #28a745; color: white; }}
            .btn:hover {{ opacity: 0.8; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Welcome to Your AI Interview</h1>
            <h2>Hello {candidate_name_from_token}!</h2>
            <p><strong>Position:</strong> {job_role}</p>
            <hr>
            <h3>Choose Your Interview Mode:</h3>
            <a href="/vInterview" class="btn voice-btn">🎤 Voice Interview</a>
            <a href="/texInterview" class="btn text-btn">💬 Text Interview</a>
            <hr>
            <p><small>Duration: 20-30 minutes | You can switch modes during the interview</small></p>
        </div>
    </body>
    </html>
    """
#Performance Analytics Routes  
@app.route('/performance_summary')
def performance_summary():
    """Get performance summary for the current candidate"""
    candidate_id = request.args.get('candidate', candidate_name)
    with sqlite3.connect(DB) as conn:
        cursor = conn.execute('''
            SELECT AVG(tech_score) as avg_tech, AVG(comm_score) as avg_comm, 
                   AVG(crit_score) as avg_crit, AVG(team_score) as avg_team,
                   AVG(leadership_score) as avg_leadership, AVG(overall_score) as avg_overall,
                   AVG(percentile) as avg_percentile, COUNT(*) as total_questions
            FROM performance 
            WHERE (candidate_id = ? OR candidate_name =?) AND DATE(ts) = DATE('now')
        ''', (candidate_id, candidate_id))
        
        result = cursor.fetchone()
        
        if result and result[0]:
            return jsonify({
                "candidate_id": candidate_id,
                "scores": {
                    "technical": round(result[0], 2),
                    "communication": round(result[1], 2),
                    "critical_thinking": round(result[2], 2),
                    "teamwork": round(result[3], 2),
                    "leadership": round(result[4], 2),
                    "overall": round(result[5], 2)
                },
                "percentile": round(result[6], 1),
                "questions_answered": result[7]
            })
        else:
            return jsonify({"message": "No performance data available"}), 404

#Pages  
@app.route('/')
def loading():      
    return render_template('loading.html')

@app.route('/GuidelinesToU')
def guidelines():
    return render_template('GuidelinesToU.html')


@app.route('/vInterview')
def voice_interview():
    initialise_session()
    session['mode'] = 'voice'
    
    return render_template('vInterview.html', 
                         last_question=session.get('last_question', FIRST_QUESTION),
                         is_first_question=(session.get('turn_count', 0) == 0),
                         candidate_name=candidate_name)

@app.route('/texInterview')
def text_interview():
    initialise_session()
    session['mode'] = 'text'
    
    return render_template('texInterview.html', 
                         last_question=session.get('last_question', FIRST_QUESTION),
                         is_first_question=(session.get('turn_count', 0) == 0),
                         candidate_name=candidate_name)


def handle_interview_logic(user_input):
    initialise_session()
    
    user_input = user_input.strip()
    if not user_input:
        return "I didn't quite catch that. Could you please repeat your response?"
    
    if len(user_input.split()) > 2:
      try:
            if not any(lang.lang == "en"):
                #Instead of hardcoding, let LLaMA craft the reply
                prompt = f"""{CTX}

The candidate responded in a non-English language: "{user_input}".
Politely ask them to continue in English so you can understand their answers better."""
                return clean_response(generate_response(prompt))
      except:
            pass
         

    vague = ["i don't know", "not sure", "idk", "rephrase", "confused", "unclear"]
    turns = session.get('turn_count', 0)
    last_q = session.get('last_question', FIRST_QUESTION)

    if any(user_input.lower().strip() == v for v in vague):

        prompt = f"{CTX}\n\nThe candidate seemed confused by this question: \"{last_q}\"\nMake the candidate feel comfortable and rephrase it more simply and clearly, asking the same thing in different words."
        new_q = clean_response(generate_response(prompt))
        session['last_question'] = new_q
        return f"No problem! Let me rephrase that. {new_q}"

    #Check if interview is complete (final turn reached)
    if turns >= MAX_TURNS:
        finalise_interview()
        #Closing message that acknowledges candidate queries + thanks them
        prompt = f"""{CTX}
The candidate was asked: "{last_q}"
They answered: "{user_input}"
Please craft a warm and professional closing message that:
1. Briefly responds to the candidate's question (if applicable),
2. Wraps up the interview gracefully with a thank-you.
"""
        closing_response = clean_response(generate_response(prompt))
        #Mark interview ended in session so frontend can redirect
        session['interview_ended'] = True
        return closing_response

    #Evaluate the current answer
    scores = evaluate_answer(last_q, user_input, jd_sum, res_sum)
    overall_score = sum(scores.values()) / len(scores)
    percentile = calculate_percentile(scores)

    with sqlite3.connect(DB) as conn:
        conn.execute('''
            INSERT INTO performance (candidate_id, candidate_name, question, answer, tech_score, comm_score, 
                                   crit_score, team_score, leadership_score, overall_score, percentile)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ? )
        ''', (candidate_name, candidate_name, last_q, user_input, scores['tech'], scores['comm'], 
              scores['crit'], scores['team'], scores['leadership'], overall_score, percentile))

    #Generate next question
    if turns == MAX_TURNS - 1:
        prompt = f"{CTX}\n\nThis is the final question. Candidate just answered: \"{user_input}\"\nAsk ONE closing question to wrap up the interview professionally."
    else:
        prompt = f"{CTX}\n\nCandidate just answered: \"{user_input}\"\nBased on their response and the conversation flow, ask ONE relevant follow-up question."

    next_q = clean_response(generate_response(prompt))

    session['turn_count'] = turns + 1
    session['last_question'] = next_q
    session['turn_complete'] = False
    session['interview_started'] = True

    return next_q
 

@app.route('/next_question', methods=['GET', 'POST'])
def next_question():
    initialise_session()

    def strip_intro(text):
        text = text.strip()
        lowered = text.lower()
        bad_starts = [
            "sure", "hi", "hello", "welcome", "thanks for",
            "let's start", "to begin", "let's get started",
            "i'm excited", "i'm looking forward",
            "today we'll", "thanks again", "shall we begin"
        ]
        for phrase in bad_starts:
            if lowered.startswith(phrase):
                lines = text.split('\n')
                lines = [line for line in lines if phrase not in line.lower()]
                text = '\n'.join(lines).strip()
                break
        return text

    turns = session.get('turn_count', 0)
    if turns >= MAX_TURNS:
        finalise_interview()
        return jsonify({
            "response": "Thank you! The interview has been completed.",
            "completed": True,
            "redirect_url": "/candidate_feedback"
        })

    prompt = f"{CTX}\n\nContinue the interview with ONE relevant question. Current turn: {turns + 1}/{MAX_TURNS}"
    q_raw = generate_response(prompt)
    q = strip_intro(clean_response(q_raw))
    session['last_question'] = q
    session['turn_count'] = turns + 1
    session['turn_complete'] = False
    return jsonify({"response": q, "completed": False})


 

@app.route('/switch_mode', methods=['POST'])
def switch_mode():
    initialise_session()

    force = request.json.get('force', False)
    current_mode = session.get('mode', 'voice')
    new_mode = 'text' if current_mode == 'voice' else 'voice'

    complete_turn = session.get('turn_complete', True)  #rue = ready for next Q
    last_question = session.get('last_question', None)
    turns = session.get('turn_count', 0)

    popup_message = (
        "Confirm Interview Mode Switch. You are about to change the interview mode. "
        "Please click the switch button again to confirm and proceed. "
        "Don't worry-we'll just continue from where we left off."
    )

    #First click always returns popup ===
    if not force:
        return jsonify({
            "allowed": False,
            "message": popup_message
        })

    #Second click: switch mode depending on scenario ===

    #Interview already complete
    if turns >= MAX_TURNS:
        session['mode'] = new_mode
        return jsonify({
            "allowed": True,
            "new_mode": new_mode,
            "message": popup_message,
            "question": "Thank you! The interview has been completed.",
            "completed": True,
            "redirect_url": "/candidate_feedback"
        })

    #Case 1: Mid-turn (question asked, no answer yet)
    if not complete_turn:
        session['mode'] = new_mode
        session['turn_complete'] = False
        return jsonify({
            "allowed": True,
            "new_mode": new_mode,
            "message": popup_message,
            "question": f"Here's where we left off: {last_question}",
            "completed": False
        })
    #Case 2: Between turns
    if complete_turn and turns > 0:
        session['mode'] = new_mode

    if turns >= MAX_TURNS:
        #Interview done, redirect to feedback
        return jsonify({
            "allowed": True,
            "new_mode": new_mode,
            "message": popup_message,
            "question": "Thank you! The interview has been completed.",
            "completed": True,
            "redirect_url": "/candidate_feedback"
        })

    prompt = f"{CTX}\n\nContinue the interview with ONE relevant question. Current turn: {turns + 1}/{MAX_TURNS}"
    next_q = clean_response(generate_response(prompt))
    session['last_question'] = next_q
    session['turn_count'] = turns + 1
    session['turn_complete'] = False
    return jsonify({
        "allowed": True,
        "new_mode": new_mode,
        "message": popup_message,
        "question": next_q,
        "completed": False
    })

 
    #Case 3: Before first question
    if turns == 0:
        session['mode'] = new_mode
        session['last_question'] = FIRST_QUESTION
        session['turn_count'] = 1
        session['turn_complete'] = False
        return jsonify({
            "allowed": True,
            "new_mode": new_mode,
            "message": popup_message,
            "question": FIRST_QUESTION,
            "completed": False
        })



@app.route('/end_interview', methods=['POST'])
def end_interview():
    session['interview_ended'] = True
     
    session.clear()
    return jsonify({'status': 'success', 'redirect_url': '/candidate_feedback'})

@app.route('/rloading')
def rloading():      
    return render_template('rloading.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    print("Request method:", request.method)
    print("Form data:", request.form)
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        print("Email:", email)
        print("Password:", password)
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

@app.route('/test')
def test():
    return "<h1>Test Route Works!</h1>"

def fix_database_schema():
    """Fix the database schema by adding missing candidate_id column"""
    try:
        with sqlite3.connect(DB) as conn:
            #Add candidate_id column to performance table if it doesn't exist
            try:
                conn.execute('ALTER TABLE performance ADD COLUMN candidate_id TEXT')
                print("Added candidate_id column to performance table")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    print("candidate_id column already exists in performance table")
                else:
                    print(f"Error adding column to performance table: {e}")
            
            #Add candidate_id column to interview_sessions table if it doesn't exist
            try:
                conn.execute('ALTER TABLE interview_sessions ADD COLUMN candidate_id TEXT')
                print("Added candidate_id column to interview_sessions table")
            except sqlite3.OperationalError as e:
                if "duplicate column name" in str(e):
                    print("candidate_id column already exists in interview_sessions table")
                else:
                    print(f"Error adding column to interview_sessions table: {e}")
            
            #Update existing records to populate candidate_id with candidate_name values
            conn.execute('UPDATE performance SET candidate_id = candidate_name WHERE candidate_id IS NULL')
            conn.execute('UPDATE interview_sessions SET candidate_id = candidate_name WHERE candidate_id IS NULL')
            
            conn.commit()
            print("Database schema fixed successfully!")
            
    except Exception as e:
        print(f"Error fixing database schema: {e}")

if __name__ == '__main__':
    init_performance_db()
    fix_database_schema()
    app.run(debug=True, use_reloader=False)

