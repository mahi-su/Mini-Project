# Multilingual Story Generation & Speech System

A complete Flask mini project for AI-powered multilingual story generation and speech synthesis. Users can register, login, generate emotion-based stories from keywords, translate stories into English, Hindi, or Telugu, convert the result into MP3 audio, and download the story as a PDF.

## Features

- Secure registration, login, logout, and session management
- Password hashing with Werkzeug
- SQLite database with users and stories tables
- Gemini API story generation with a rule-based fallback generator
- Translation using `deep-translator`
- Text-to-speech using `gTTS`
- Browser audio player and MP3 download
- PDF download using ReportLab
- Story history per user
- Regenerate, copy, and delete story actions
- Responsive Bootstrap 5 UI
- Dark mode with local browser preference
- Optional admin monitor

## Tech Stack

- Frontend: HTML5, CSS3, Bootstrap 5, JavaScript
- Backend: Python, Flask
- Database: SQLite
- AI/NLP: Gemini API
- Translation: deep-translator
- Text-to-Speech: gTTS
- PDF: ReportLab

## Project Structure

```text
project/
├── app.py
├── requirements.txt
├── README.md
├── .env.example
├── database/
│   └── schema.sql
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── result.html
│   ├── admin.html
│   └── error.html
├── static/
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── app.js
│   ├── audio/
│   └── images/
│       └── story_banner.png
└── models/
    └── README.md
```

## Database Design

### Users Table

| Column | Type | Notes |
|---|---|---|
| id | INTEGER | Primary key |
| username | TEXT | Unique username |
| email | TEXT | Unique email |
| password | TEXT | Hashed password |

### Stories Table

| Column | Type | Notes |
|---|---|---|
| id | INTEGER | Primary key |
| user_id | INTEGER | Foreign key to users |
| keywords | TEXT | User entered keywords |
| language | TEXT | English, Hindi, or Telugu |
| emotion | TEXT | Happy, Horror, Adventure, Funny, Motivational |
| generated_story | TEXT | Final generated story |
| audio_file | TEXT | MP3 filename |
| created_at | TEXT | Timestamp |

The database is created automatically from `database/schema.sql` when `app.py` starts.

## Setup Instructions

### Quick Start On Windows

Double-click:

```text
run.bat
```

The batch file will create a virtual environment, install dependencies, create `.env` if needed, open the browser, and start the Flask server.

### 1. Open the project folder

```powershell
cd "C:\Users\modug\OneDrive\Documents\New project\project"
```

### 2. Create a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

### 4. Create environment file

```powershell
copy .env.example .env
```

Open `.env` and set values:

```env
SECRET_KEY=replace-with-a-long-random-secret
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-1.5-flash
ADMIN_EMAIL=admin@example.com
FLASK_DEBUG=1
```

`GEMINI_API_KEY` is optional for demos. If it is empty, the app uses the built-in fallback story generator.

### 5. Run the Flask app

```powershell
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

## Gemini API Integration

The app reads the API key from `.env`:

```python
api_key = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=api_key)
model = genai.GenerativeModel(os.environ.get("GEMINI_MODEL", "gemini-1.5-flash"))
response = model.generate_content(prompt)
```

If Gemini fails or the key is missing, the fallback generator keeps the project usable for demonstrations.

## Functional Workflow

```text
Register/Login
    ↓
Enter Keywords
    ↓
Select Language, Emotion, and Voice
    ↓
Generate English Story with Gemini or Fallback
    ↓
Translate to Hindi or Telugu if selected
    ↓
Convert Story to Speech with gTTS
    ↓
Display Story, Audio Player, PDF Download, MP3 Download
```

## Admin Dashboard

Admin access is available at:

```text
/admin
```

A user is treated as admin if:

- Their username is `admin`, or
- Their email matches `ADMIN_EMAIL` in `.env`

## Important Notes

- Translation and gTTS require internet access because they use online services.
- Generated MP3 files are stored in `static/audio/`.
- The SQLite database file is stored at `database/stories.db`.
- For Hindi or Telugu PDF rendering on another machine, set `PDF_FONT_PATH` in `.env` if the default system fonts do not render properly.
- Do not commit real API keys or production secrets.

## Viva Explanation Points

- Flask routes handle authentication, dashboard flow, story generation, downloads, and admin monitoring.
- SQLite stores users and generated stories with a foreign key relationship.
- Passwords are never stored directly; only hashed values are saved.
- Gemini acts as the transformer-based NLP model for context-aware story generation.
- `deep-translator` provides multilingual output for Hindi and Telugu.
- `gTTS` converts the generated story into downloadable speech.
- The UI is responsive, beginner-friendly, and includes dark mode and history for a polished project demo.
