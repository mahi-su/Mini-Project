import io
import os
import re
import secrets
import sqlite3
import textwrap
import uuid
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    abort,
    flash,
    g,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from gtts import gTTS
from werkzeug.security import check_password_hash, generate_password_hash

try:
    from deep_translator import GoogleTranslator
except Exception:  # pragma: no cover - handled at runtime for beginner setup
    GoogleTranslator = None

try:
    import google.generativeai as genai
except Exception:  # pragma: no cover - app still works with fallback generation
    genai = None

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None


BASE_DIR = Path(__file__).resolve().parent
DATABASE_DIR = BASE_DIR / "database"
DATABASE_PATH = DATABASE_DIR / "stories.db"
SCHEMA_PATH = DATABASE_DIR / "schema.sql"
AUDIO_DIR = BASE_DIR / "static" / "audio"

LANGUAGES = {
    "English": {"code": "en", "translator": "en", "label": "English"},
    "Hindi": {"code": "hi", "translator": "hi", "label": "Hindi"},
    "Telugu": {"code": "te", "translator": "te", "label": "Telugu"},
}

EMOTIONS = {
    "Happy": "warm, cheerful, hopeful, and family friendly",
    "Horror": "suspenseful, mysterious, atmospheric, but suitable for students",
    "Adventure": "fast moving, brave, discovery focused, and cinematic",
    "Funny": "light, witty, playful, and clean",
    "Motivational": "inspiring, disciplined, resilient, and positive",
}

VOICE_TLDS = {
    "standard": "com",
    "india": "co.in",
    "australia": "com.au",
    "uk": "co.uk",
}


if load_dotenv:
    load_dotenv(BASE_DIR / ".env")

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "dev-change-this-secret-key"),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("FLASK_ENV") == "production",
    MAX_CONTENT_LENGTH=1024 * 1024,
)


def connect_db():
    DATABASE_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    DATABASE_DIR.mkdir(exist_ok=True)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    with connect_db() as conn:
        schema = SCHEMA_PATH.read_text(encoding="utf-8")
        conn.executescript(schema)


def query_one(query, params=()):
    with connect_db() as conn:
        return conn.execute(query, params).fetchone()


def query_all(query, params=()):
    with connect_db() as conn:
        return conn.execute(query, params).fetchall()


def execute_db(query, params=()):
    with connect_db() as conn:
        cursor = conn.execute(query, params)
        conn.commit()
        return cursor.lastrowid


@app.before_request
def load_user_and_csrf():
    session.setdefault("csrf_token", secrets.token_hex(32))
    g.user = None
    user_id = session.get("user_id")
    if user_id:
        g.user = query_one(
            "SELECT id, username, email FROM users WHERE id = ?",
            (user_id,),
        )


@app.before_request
def csrf_protect():
    if request.method != "POST":
        return
    form_token = request.form.get("csrf_token", "")
    session_token = session.get("csrf_token", "")
    if not form_token or not session_token or not secrets.compare_digest(form_token, session_token):
        abort(400, description="Invalid CSRF token")


@app.context_processor
def inject_template_globals():
    return {
        "csrf_token": session.get("csrf_token", ""),
        "current_user": g.get("user"),
        "languages": LANGUAGES.keys(),
        "emotions": EMOTIONS.keys(),
        "is_admin": is_admin_user(),
    }


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if g.user is None:
            flash("Please login to continue.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped_view


def is_admin_user():
    user = g.get("user")
    if not user:
        return False
    admin_email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    return user["username"].lower() == "admin" or (admin_email and user["email"].lower() == admin_email)


def clean_keywords(raw_keywords):
    keywords = re.sub(r"\s+", " ", raw_keywords or "").strip()
    keywords = re.sub(r"[<>]", "", keywords)
    return keywords[:200]


def validate_story_form(form):
    keywords = clean_keywords(form.get("keywords", ""))
    language = form.get("language", "English")
    emotion = form.get("emotion", "Adventure")
    voice = form.get("voice", "standard")
    slow_audio = form.get("slow_audio") == "on"

    errors = []
    if len(keywords) < 3:
        errors.append("Enter at least one useful keyword.")
    if language not in LANGUAGES:
        errors.append("Choose a supported language.")
    if emotion not in EMOTIONS:
        errors.append("Choose a supported emotion.")
    if voice not in VOICE_TLDS:
        errors.append("Choose a supported voice style.")

    return {
        "keywords": keywords,
        "language": language,
        "emotion": emotion,
        "voice": voice,
        "slow_audio": slow_audio,
        "errors": errors,
    }


def generate_story_with_gemini(keywords, emotion):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or genai is None:
        return None

    model_name = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)

    prompt = f"""
Write an original short story in English for a BTech AIML mini project demo.

Keywords: {keywords}
Emotion: {emotion} ({EMOTIONS[emotion]})

Rules:
- Keep it between 450 and 650 words.
- Make the story meaningful, context-aware, and easy to understand.
- Include a clear beginning, middle, and ending.
- Avoid unsafe content, personal data, copyrighted characters, and explicit violence.
- Do not add markdown headings. Return only the story.
""".strip()

    response = model.generate_content(prompt)
    story = getattr(response, "text", "") or ""
    story = story.strip()
    return story or None


def fallback_story_generator(keywords, emotion):
    keyword_list = [item.strip() for item in re.split(r",|;", keywords) if item.strip()]
    if not keyword_list:
        keyword_list = [keywords]

    subject = ", ".join(keyword_list[:4])
    lead = keyword_list[0].title()
    mood_line = EMOTIONS[emotion]

    openers = {
        "Happy": f"In the bright town of Suryavanam, everyone knew {lead} as a small idea with a big smile.",
        "Horror": f"At midnight, the old science block became strangely silent whenever someone mentioned {lead}.",
        "Adventure": f"When the village map began glowing around the word {lead}, three friends knew the day would not be ordinary.",
        "Funny": f"The trouble began when {lead} was announced as the chief guest for the college talent day.",
        "Motivational": f"{lead} looked ordinary to everyone else, but to Asha it was the first step toward a brave dream.",
    }

    endings = {
        "Happy": "By evening, the whole town celebrated not because everything was perfect, but because everyone had helped make it better.",
        "Horror": "When the first sunlight entered the corridor, the shadow vanished, leaving behind only a warning to respect forgotten stories.",
        "Adventure": "They returned with tired feet, full hearts, and proof that courage grows each time it is used.",
        "Funny": "The principal laughed the loudest and declared that some accidents deserve a certificate of creativity.",
        "Motivational": "From that day, Asha wrote one line above her desk: small steps become strong stories when we do not stop.",
    }

    body = [
        openers[emotion],
        (
            f"The story moved around {subject}, but its real strength came from the choices people made. "
            f"Every scene carried a {mood_line} feeling, so the events stayed connected to the selected emotion."
        ),
        (
            "The main character noticed a problem that others ignored. Instead of waiting for a miracle, "
            "they used observation, teamwork, and a little imagination to understand what was happening."
        ),
        (
            f"As {subject} became more important, the challenge grew larger. A wrong decision could ruin the plan, "
            "but a calm mind helped the group connect clues, learn from mistakes, and move forward."
        ),
        (
            "The final moment tested everything they had learned. They did not win because they were perfect; "
            "they won because they listened carefully, trusted each other, and acted at the right time."
        ),
        endings[emotion],
    ]
    return "\n\n".join(body)


def generate_english_story(keywords, emotion):
    try:
        gemini_story = generate_story_with_gemini(keywords, emotion)
        if gemini_story:
            return gemini_story, "Gemini"
    except Exception as exc:
        app.logger.warning("Gemini generation failed: %s", exc)

    return fallback_story_generator(keywords, emotion), "Fallback"


def translate_story(story, language):
    if language == "English":
        return story, None

    if GoogleTranslator is None:
        return story, "Translation package is not available. Showing English story."

    target = LANGUAGES[language]["translator"]
    try:
        chunks = split_for_translation(story)
        translated = [
            GoogleTranslator(source="auto", target=target).translate(chunk)
            for chunk in chunks
        ]
        return "\n\n".join(translated), None
    except Exception as exc:
        app.logger.warning("Translation failed: %s", exc)
        return story, "Translation failed. Showing English story."


def split_for_translation(text, limit=4200):
    paragraphs = text.split("\n\n")
    chunks = []
    current = ""
    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= limit:
            current = candidate
        else:
            if current:
                chunks.append(current)
            chunks.extend(textwrap.wrap(paragraph, width=limit, break_long_words=False))
            current = ""
    if current:
        chunks.append(current)
    return chunks or [text]


def create_tts_audio(story, language, user_id, voice="standard", slow_audio=False):
    lang_code = LANGUAGES[language]["code"]
    tld = VOICE_TLDS.get(voice, "com")
    filename = f"story_{user_id}_{uuid.uuid4().hex}.mp3"
    output_path = AUDIO_DIR / filename

    try:
        tts = gTTS(text=story, lang=lang_code, tld=tld, slow=slow_audio)
        tts.save(str(output_path))
        return filename, None
    except Exception as exc:
        app.logger.warning("TTS failed: %s", exc)
        return None, "Text-to-speech failed. You can still read and download the story PDF."


def get_story_or_404(story_id):
    story = query_one(
        """
        SELECT stories.*, users.username
        FROM stories
        JOIN users ON users.id = stories.user_id
        WHERE stories.id = ?
        """,
        (story_id,),
    )
    if story is None:
        abort(404)
    if not is_admin_user() and story["user_id"] != session.get("user_id"):
        abort(403)
    return story


def register_pdf_font():
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    configured_font = os.environ.get("PDF_FONT_PATH", "").strip()
    candidates = [
        Path(configured_font) if configured_font else None,
        Path(r"C:\Windows\Fonts\Nirmala.ttf"),
        Path(r"C:\Windows\Fonts\nirmala.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
    ]

    for font_path in candidates:
        if font_path and font_path.exists():
            try:
                pdfmetrics.registerFont(TTFont("AppUnicode", str(font_path)))
                return "AppUnicode"
            except Exception:
                continue
    return "Helvetica"


def wrap_pdf_text(text, font_name, font_size, max_width):
    from reportlab.pdfbase import pdfmetrics

    lines = []
    for paragraph in text.splitlines():
        if not paragraph.strip():
            lines.append("")
            continue

        current = ""
        for word in paragraph.split(" "):
            candidate = f"{current} {word}".strip()
            if pdfmetrics.stringWidth(candidate, font_name, font_size) <= max_width:
                current = candidate
                continue

            if current:
                lines.append(current)
                current = ""

            piece = ""
            for char in word:
                if pdfmetrics.stringWidth(piece + char, font_name, font_size) <= max_width:
                    piece += char
                else:
                    if piece:
                        lines.append(piece)
                    piece = char
            current = piece

        if current:
            lines.append(current)
    return lines


def create_story_pdf(story):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 0.72 * inch
    y = height - margin
    font_name = register_pdf_font()

    pdf.setTitle("Generated Story")
    pdf.setFont(font_name, 18)
    pdf.drawString(margin, y, "Generated Story")
    y -= 26

    pdf.setFont(font_name, 10)
    meta = f"Keywords: {story['keywords']} | Language: {story['language']} | Emotion: {story['emotion']}"
    for line in wrap_pdf_text(meta, font_name, 10, width - 2 * margin):
        pdf.drawString(margin, y, line)
        y -= 14

    y -= 12
    pdf.setFont(font_name, 12)
    for line in wrap_pdf_text(story["generated_story"], font_name, 12, width - 2 * margin):
        if y < margin:
            pdf.showPage()
            pdf.setFont(font_name, 12)
            y = height - margin
        pdf.drawString(margin, y, line)
        y -= 17

    pdf.save()
    buffer.seek(0)
    return buffer


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if g.user:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        errors = []
        if not re.fullmatch(r"[A-Za-z0-9_]{3,30}", username):
            errors.append("Username must be 3-30 characters and use only letters, numbers, or underscores.")
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            errors.append("Enter a valid email address.")
        if len(password) < 8:
            errors.append("Password must be at least 8 characters.")
        if password != confirm_password:
            errors.append("Passwords do not match.")

        if errors:
            for error in errors:
                flash(error, "danger")
            return render_template("register.html")

        try:
            user_id = execute_db(
                "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                (username, email, generate_password_hash(password)),
            )
            session.clear()
            session["user_id"] = user_id
            session["csrf_token"] = secrets.token_hex(32)
            flash("Account created successfully. Welcome!", "success")
            return redirect(url_for("dashboard"))
        except sqlite3.IntegrityError:
            flash("Username or email already exists.", "danger")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = query_one("SELECT * FROM users WHERE email = ?", (email,))

        if user and check_password_hash(user["password"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["csrf_token"] = secrets.token_hex(32)
            flash("Logged in successfully.", "success")
            return redirect(url_for("dashboard"))

        flash("Invalid email or password.", "danger")

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    stories = query_all(
        """
        SELECT id, keywords, language, emotion, created_at
        FROM stories
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT 8
        """,
        (g.user["id"],),
    )
    totals = query_one(
        """
        SELECT COUNT(*) AS count,
               COALESCE(MAX(created_at), '-') AS latest_story
        FROM stories
        WHERE user_id = ?
        """,
        (g.user["id"],),
    )
    return render_template("dashboard.html", stories=stories, totals=totals)


@app.route("/generate", methods=["POST"])
@login_required
def generate():
    form = validate_story_form(request.form)
    if form["errors"]:
        for error in form["errors"]:
            flash(error, "danger")
        return redirect(url_for("dashboard"))

    english_story, source = generate_english_story(form["keywords"], form["emotion"])
    final_story, translation_warning = translate_story(english_story, form["language"])
    audio_file, audio_warning = create_tts_audio(
        final_story,
        form["language"],
        g.user["id"],
        voice=form["voice"],
        slow_audio=form["slow_audio"],
    )

    story_id = execute_db(
        """
        INSERT INTO stories
            (user_id, keywords, language, emotion, generated_story, audio_file, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            g.user["id"],
            form["keywords"],
            form["language"],
            form["emotion"],
            final_story,
            audio_file,
            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )

    flash(f"Story generated using {source}.", "success")
    if translation_warning:
        flash(translation_warning, "warning")
    if audio_warning:
        flash(audio_warning, "warning")

    return redirect(url_for("result", story_id=story_id))


@app.route("/result/<int:story_id>")
@login_required
def result(story_id):
    story = get_story_or_404(story_id)
    return render_template("result.html", story=story)


@app.route("/download/audio/<int:story_id>")
@login_required
def download_audio(story_id):
    story = get_story_or_404(story_id)
    if not story["audio_file"]:
        abort(404)

    audio_path = (AUDIO_DIR / story["audio_file"]).resolve()
    if AUDIO_DIR.resolve() not in audio_path.parents or not audio_path.exists():
        abort(404)

    return send_file(
        audio_path,
        mimetype="audio/mpeg",
        as_attachment=True,
        download_name=f"story_{story_id}.mp3",
    )


@app.route("/download/pdf/<int:story_id>")
@login_required
def download_pdf(story_id):
    story = get_story_or_404(story_id)
    pdf_buffer = create_story_pdf(story)
    return send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"story_{story_id}.pdf",
    )


@app.route("/delete/story/<int:story_id>", methods=["POST"])
@login_required
def delete_story(story_id):
    story = get_story_or_404(story_id)
    if story["audio_file"]:
        audio_path = AUDIO_DIR / story["audio_file"]
        if audio_path.exists():
            audio_path.unlink()
    execute_db("DELETE FROM stories WHERE id = ?", (story_id,))
    flash("Story removed from history.", "info")
    return redirect(url_for("dashboard"))


@app.route("/admin")
@login_required
def admin_dashboard():
    if not is_admin_user():
        abort(403)
    stats = query_one(
        """
        SELECT
            (SELECT COUNT(*) FROM users) AS users_count,
            (SELECT COUNT(*) FROM stories) AS stories_count,
            (SELECT COUNT(*) FROM stories WHERE audio_file IS NOT NULL) AS audio_count
        """
    )
    recent = query_all(
        """
        SELECT stories.id, stories.keywords, stories.language, stories.emotion,
               stories.created_at, users.username
        FROM stories
        JOIN users ON users.id = stories.user_id
        ORDER BY stories.created_at DESC
        LIMIT 12
        """
    )
    return render_template("admin.html", stats=stats, recent=recent)


@app.errorhandler(404)
def not_found(error):
    return render_template("error.html", code=404, message="Page not found."), 404


@app.errorhandler(403)
def forbidden(error):
    return render_template("error.html", code=403, message="You do not have access to this page."), 403


@app.errorhandler(400)
def bad_request(error):
    return render_template("error.html", code=400, message="Bad request. Please try again."), 400


init_db()


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "1") == "1")
