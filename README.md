# Bolt-Hire AI - Virtual Interview System

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0.0-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)
![AI](https://img.shields.io/badge/AI-Powered-red.svg)

*An intelligent AI-powered interview platform that conducts automated interviews using voice or text, evaluates responses, and provides comprehensive performance analytics.*

</div>

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [API Endpoints](#api-endpoints)
- [Evaluation Criteria](#evaluation-criteria)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

Bolt-Hire AI is a cutting-edge virtual interview platform that leverages advanced AI models to conduct realistic, conversational interviews. The system provides:

- **Natural Language Processing** using Llama LLM for contextual conversations
- **Speech Recognition** via OpenAI Whisper
- **Text-to-Speech** with Coqui TTS
- **Multi-dimensional Evaluation** across 5 key competency areas
- **Recruiter Dashboard** for managing candidates and viewing analytics

---

## Features

### Interview Modes
- **Voice Interview** - Natural conversation with real-time speech recognition and TTS
- **Text Interview** - Traditional chat-based interview interface
- **Mode Switching** - Seamlessly switch between voice and text during interviews

### AI-Powered
- Contextual question generation based on resume and job description
- Natural conversation flow with follow-up questions
- Handles edge cases (nervousness, confusion, off-topic responses)
- Supports up to 15 questions per interview

### Performance Analytics
Candidates are evaluated across 5 dimensions:
- **Technical Skills** - Domain knowledge and technical accuracy
- **Communication** - Clarity, articulation, and structure
- **Critical Thinking** - Problem-solving and analytical approach
- **Teamwork** - Collaboration and interpersonal skills
- **Leadership** - Initiative, decision-making, and influence

### Recruiter Dashboard
- View all candidates with filtering options
- Send email invitations with unique interview links
- Track interview status (Pending/Shortlisted/Rejected)
- Access detailed performance reports and feedback

### Email System
- Automated interview invitations via SendGrid
- Unique, secure interview links with 7-day validity
- Professional email templates

---

## Tech Stack

### Backend
```
Python 3.10+
Flask 3.0.0
SQLite
```

### AI/ML Models
```
Llama 7B (via llama-cpp-python)
OpenAI Whisper (Speech-to-Text)
Coqui TTS (Text-to-Speech)
```

### Frontend
```
HTML5
CSS3
JavaScript (Vanilla)
```

### APIs & Services
```
SendGrid API (Email)
FFmpeg (Audio processing)
```

---

## Installation

### Prerequisites

Ensure you have the following installed:

- **Python 3.10+**
- **FFmpeg** - [Download here](https://ffmpeg.org/download.html)
- **Llama Model** - Download a GGUF format model (e.g., Mistral 7B Instruct)
- **SendGrid Account** - [Sign up here](https://sendgrid.com/)

### Step 1: Clone the Repository
```bash
git clone https://github.com/yourusername/bolt-hire-ai.git
cd bolt-hire-ai
```

### Step 2: Create Virtual Environment
```bash
#Windows
python -m venv venv
venv\Scripts\activate

#Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies
```bash
pip install -r Requirements.txt
```

### Step 4: Download Llama Model

Download a Llama model in GGUF format (recommended: Mistral 7B Instruct Q4_K_M) and place it in a `Models/` directory.

### Step 5: Set Up Environment Variables

Create a `.env` file in the project root:
```bash
#Copy the example file
cp .env.example .env
```

Add your credentials:
```env
#SendGrid Email Configuration
SENDGRID_API_KEY=your-sendgrid-api-key-here
FROM_EMAIL=your-verified-email@yourdomain.com
FROM_NAME=Your Company Name

#Flask Secret Key
SECRET_KEY=your-secret-key-here

#Model Path
MODEL_PATH=path/to/your/model.gguf
```

### Step 6: Initialise Database
```bash
python App.py
```

The database will be created automatically on first run.

### Step 7: Add Sample Data

Create sample files for testing:
- **Resume.pdf** - A sample candidate resume
- **JD.txt** - A job description text file

Place these in the project root directory.

---

## Configuration

### SendGrid Setup

1. Create a free SendGrid account at https://sendgrid.com
2. Verify your sender email address
3. Create an API Key:
   - Go to Settings → API Keys
   - Click "Create API Key"
   - Give it "Full Access" permissions
   - Copy the key and add to `.env`

### Model Configuration

Adjust model settings in `App.py` if needed:
```python
llm = Llama(
    model_path=MODEL_PATH,
    n_ctx=2048,        # Context window
    n_threads=6,       # CPU threads
    n_batch=256        # Batch size
)
```

### Interview Configuration

Modify interview settings in `App.py`:
```python
MAX_TURNS = 15  # Number of questions per interview
```

---

## Usage

### Starting the Application
```bash
python App.py
```

The application will start on `http://localhost:5000`

### For Recruiters

1. **Access Dashboard**: `http://localhost:5000/recruiter_dashboard`
2. **Send Interview Invitation**: Click "Initiate Interview" for pending candidates
3. **View Performance**: Click "View Feedback" for completed interviews

### For Candidates

1. **Receive Email**: Open invitation email and click the interview link
2. **Choose Mode**: Select Voice or Text interview mode dynamically( switchable in between too)
3. **Complete Interview**: Answer 15 questions naturally

---

## Project Structure
```
bolt-hire-ai/
│
├── App.py                      # Main Flask application
├── models_db.py                # Database models
├── Requirements.txt            # Python dependencies
├── .env                        # Environment variables (not in git)
├── .env.example                # Environment template
├── .gitignore                  # Git ignore rules
├── README.md                   # Documentation
│
├── Templates/                  # HTML templates
│   ├── loading.html
│   ├── GuidelinesToU.html
│   ├── vInterview.html
│   ├── texInterview.html
│   ├── recruiterdboard.html
│   ├── canfeedback.html
│   └── performance_fb.html
│
├── static/                     # Static files
└── uploads/                    # Temporary audio uploads
```

---

## API Endpoints

### Public Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Landing page |
| `GET` | `/GuidelinesToU` | Interview guidelines |
| `GET` | `/interview/<token>` | Start interview from email link |

### Interview Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/vInterview` | Voice interview interface |
| `GET` | `/texInterview` | Text interview interface |
| `POST` | `/start_interview` | Initialise interview session |
| `POST` | `/ask` | Submit text answer |
| `POST` | `/transcribe` | Submit voice answer |
| `POST` | `/speak` | Generate TTS audio |

### Recruiter Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/recruiter_dashboard` | View dashboard |
| `POST` | `/send_interview_invite` | Send email invitation |
| `GET` | `/candidate_performance/<id>` | View candidate report |

---

## Evaluation Criteria

Each candidate is scored on a **1-10 scale** across five dimensions:

### 1. Technical Skills
- Domain knowledge and expertise
- Technical accuracy in responses
- Understanding of job-specific concepts

### 2. Communication Skills
- Clarity and articulation
- Structured responses
- Ability to explain complex concepts

### 3. Critical Thinking
- Problem-solving approach
- Analytical reasoning
- Creative solutions

### 4. Teamwork & Collaboration
- Team experience
- Interpersonal skills
- Collaborative mindset

### 5. Leadership Potential
- Initiative and proactivity
- Decision-making abilities
- Influence and impact

---

## Troubleshooting

### Email Not Sending

Verify:
- SendGrid API key is correct
- Sender email is verified in SendGrid
- `.env` file has correct credentials

### Model Loading Issues

Solutions:
- Use a smaller quantized model (Q4_K_M or Q4_0)
- Increase `n_threads` in model config
- Reduce `n_ctx` to 1024 if memory limited

### Audio Issues

Solutions:
1. Ensure FFmpeg is installed and in PATH
2. Check microphone permissions in browser
3. Use Chrome or Edge for best compatibility

---

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m "Add amazing feature"`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

---

## License

This project is licensed under the **MIT License**.

---

## Acknowledgments

- **Meta AI** - Llama language model
- **OpenAI** - Whisper speech recognition
- **Coqui AI** - TTS models
- **SendGrid** - Email delivery platform
- **Flask** - Web framework

---

<div align="center">

**Made with ❤️**

⭐ Star this repo if you find it useful!

</div>
