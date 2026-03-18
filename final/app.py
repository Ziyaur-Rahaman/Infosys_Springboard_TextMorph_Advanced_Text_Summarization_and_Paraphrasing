import os
import re
import time
import hmac
import base64
import random
import sqlite3
import bcrypt
import jwt
import torch
import nltk
import textstat
import hashlib
import secrets
import datetime
import struct
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import matplotlib.pyplot as plt

from io import BytesIO
from collections import Counter
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

from wordcloud import WordCloud
from streamlit_option_menu import option_menu
import PyPDF2
# sent_tokenize is imported inside _safe_sent_tokenize() to gracefully handle missing NLTK data

# -------------------------------
# STREAMLIT PAGE CONFIG
# -------------------------------
st.set_page_config(
    page_title="TextMorph",
    page_icon="🎓",
    layout="centered"
)

# -------------------------------
# ENV / APP CONFIG
# -------------------------------
ALGORITHM = "HS256"
DB_NAME = os.getenv("DB_PATH", "users.db")
EMAIL_ADDRESS = "Infosysteam91@gmail.com"
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
SECRET_KEY = os.getenv("JWT_SECRET", "super-secret-key-change-this")
OTP_EXPIRY_MINUTES = 10

SUPPORTED_LANGUAGES = [
    "English", "Hindi", "Tamil", "Kannada", "Telugu", "Marathi",
    "Bengali", "Gujarati", "Malayalam", "Urdu", "Punjabi"
]

# -------------------------------
# NLTK — SSL-first downloader
# -------------------------------
import ssl

# Patch SSL globally BEFORE any NLTK download so corporate/macOS certs never block us
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except Exception:
    pass

def _nltk_download_safe(resource):
    """Silently download an NLTK resource; swallow all errors."""
    try:
        nltk.download(resource, quiet=True)
    except Exception:
        pass

def _ensure_nltk_data():
    """Check each required resource and download only if missing."""
    resources = {
        "tokenizers/punkt":     "punkt",
        "tokenizers/punkt_tab": "punkt_tab",
        "corpora/cmudict":      "cmudict",   # required by textstat syllable/difficult-words
    }
    for find_path, package in resources.items():
        try:
            nltk.data.find(find_path)
        except LookupError:
            _nltk_download_safe(package)

_ensure_nltk_data()

# Safe sentence tokenizer — falls back to regex if NLTK data is still unavailable
def _safe_sent_tokenize(text):
    try:
        from nltk.tokenize import sent_tokenize as _nltk_sent
        return _nltk_sent(text)
    except Exception:
        return re.split(r'(?<=[.!?])\s+', text.strip())

# -------------------------------
# TRANSFORMERS
# -------------------------------
TRANSFORMERS_AVAILABLE = False
BNB_AVAILABLE = False

try:
    from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
    TRANSFORMERS_AVAILABLE = True
    try:
        from transformers import BitsAndBytesConfig
        BNB_AVAILABLE = True
    except ImportError:
        BNB_AVAILABLE = False
except ImportError:
    TRANSFORMERS_AVAILABLE = False

LANG_CODES = {
    "English": "eng_Latn",
    "Hindi": "hin_Deva",
    "Tamil": "tam_Taml",
    "Kannada": "kan_Knda",
    "Telugu": "tel_Telu",
    "Marathi": "mar_Deva",
    "Bengali": "ben_Beng",
    "Gujarati": "guj_Gujr",
    "Malayalam": "mal_Mlym",
    "Urdu": "urd_Arab",
    "Punjabi": "pan_Guru",
}

# -------------------------------
# STYLES
# -------------------------------
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg, #041C32, #06283D);
    color: white;
}
.neon-card {
    background: rgba(255,255,255,0.05);
    backdrop-filter: blur(15px);
    padding: 40px;
    border-radius: 20px;
    border: 1px solid rgba(0,245,255,0.5);
    box-shadow: 0 0 25px rgba(0,245,255,0.4);
    animation: fadeIn 0.8s ease-in-out;
}
h1, h2, h3 {
    color: #00F5FF;
    text-align: center;
}
.stTextInput>div>div>input {
    background: transparent;
    border: none;
    border-bottom: 2px solid #00F5FF;
    color: white;
    font-size: 16px;
}
.stSelectbox>div>div {
    background: rgba(255,255,255,0.05);
    border: 1px solid #00F5FF;
    border-radius: 10px;
    color: white;
}
.stButton>button {
    width: 100%;
    border-radius: 30px;
    padding: 12px;
    font-weight: bold;
    border: none;
    background: linear-gradient(90deg, #00F5FF, #00C9A7);
    color: black;
    transition: 0.3s ease;
    box-shadow: 0 0 15px rgba(0,245,255,0.6);
    white-space: nowrap !important;
}
.stButton>button:hover {
    transform: scale(1.05);
    box-shadow: 0 0 25px rgba(0,245,255,1);
}
[data-testid="stSidebar"] {
    background: #031926;
}
@keyframes fadeIn {
    from {opacity: 0; transform: translateY(20px);}
    to {opacity: 1; transform: translateY(0);}
}
</style>
""", unsafe_allow_html=True)

# -------------------------------
# DATABASE LAYER
# -------------------------------
max_login_attempts = 3
lockout_time = 300

def _get_conn():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def _get_timestamp():
    return datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

def init_db():
    conn = _get_conn()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS user_activity (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT,
        action TEXT,
        language TEXT,
        created_at TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS locked_accounts (
        email TEXT PRIMARY KEY,
        locked_at TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS deleted_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT,
        username TEXT,
        deleted_at TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS user_roles(
        email TEXT PRIMARY KEY,
        role TEXT DEFAULT 'user'
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS user_profiles(
        email TEXT PRIMARY KEY,
        avatar BLOB
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        email TEXT PRIMARY KEY,
        username TEXT,
        password BLOB,
        security_question TEXT,
        security_answer BLOB,
        created_at TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS password_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT,
        password BLOB,
        set_at TEXT,
        FOREIGN KEY(email) REFERENCES users(email)
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS login_attempts (
        email TEXT PRIMARY KEY,
        attempts INTEGER,
        last_attempt REAL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT,
        original_text TEXT,
        generated_text TEXT,
        task_type TEXT,
        rating INTEGER,
        comments TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS activity_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT,
        activity_type TEXT,
        details TEXT,
        output_text TEXT,
        model_used TEXT,
        created_at TEXT
    )
    """)

    conn.commit()
    conn.close()
    init_admin()

def check_user_exists(email):
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT 1 FROM users WHERE email = ?", (email,))
    row = c.fetchone()
    conn.close()
    return row is not None

def init_admin():
    if not check_user_exists("admin@textmorph.com"):
        register_user("Admin", "admin@textmorph.com", "Admin@123Secure!", "Admin default question", "admin")

def register_user(username, email, password, question, answer):
    conn = _get_conn()
    c = conn.cursor()
    try:
        hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        hashed_answer = bcrypt.hashpw(answer.encode(), bcrypt.gensalt())
        now = _get_timestamp()

        c.execute("""
        INSERT INTO users (email, username, password, security_question, security_answer, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (email, username, hashed_password, question, hashed_answer, now))

        c.execute(
            "INSERT OR IGNORE INTO user_roles (email, role) VALUES (?, 'user')",
            (email,)
        )

        c.execute("""
        INSERT INTO password_history (email, password, set_at)
        VALUES (?, ?, ?)
        """, (email, hashed_password, now))

        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_username(email):
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT username FROM users WHERE email=?", (email,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def get_security_question(email):
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT security_question FROM users WHERE email = ?", (email,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def verify_security_answer(email, answer):
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT security_answer FROM users WHERE email = ?", (email,))
    row = c.fetchone()
    conn.close()
    if row:
        return bcrypt.checkpw(answer.encode("utf-8"), row[0])
    return False

def get_login_attempts(email):
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT attempts, last_attempt FROM login_attempts WHERE email = ?", (email,))
    row = c.fetchone()
    conn.close()
    return row if row else (0, 0)

def increment_login_attempts(email):
    conn = _get_conn()
    c = conn.cursor()
    attempts, _ = get_login_attempts(email)
    now = time.time()
    c.execute("""
    INSERT OR REPLACE INTO login_attempts (email, attempts, last_attempt)
    VALUES (?, ?, ?)
    """, (email, attempts + 1, now))
    conn.commit()
    conn.close()

def reset_login_attempts(email):
    conn = _get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM login_attempts WHERE email = ?", (email,))
    conn.commit()
    conn.close()

def is_rate_limited(email):
    attempts, last_attempt = get_login_attempts(email)
    if attempts >= max_login_attempts:
        remaining = lockout_time - (time.time() - last_attempt)
        if remaining > 0:
            return True, remaining
        reset_login_attempts(email)
    return False, 0

def lock_account(email):
    conn = _get_conn()
    c = conn.cursor()
    c.execute("""
    INSERT OR REPLACE INTO locked_accounts(email, locked_at)
    VALUES (?, ?)
    """, (email, _get_timestamp()))
    conn.commit()
    conn.close()

def unlock_account(email):
    conn = _get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM locked_accounts WHERE email=?", (email,))
    c.execute("DELETE FROM login_attempts WHERE email=?", (email,))
    conn.commit()
    conn.close()

def get_locked_accounts():
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT email, locked_at FROM locked_accounts")
    rows = c.fetchall()
    conn.close()
    return rows

def authenticate_user(email, password):
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT email FROM locked_accounts WHERE email=?", (email,))
    locked = c.fetchone()
    conn.close()

    if locked:
        return "locked"

    limited, _ = is_rate_limited(email)
    if limited:
        lock_account(email)
        return "locked"

    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE email=?", (email,))
    row = c.fetchone()
    conn.close()

    if row and bcrypt.checkpw(password.encode("utf-8"), row[0]):
        reset_login_attempts(email)
        return True

    increment_login_attempts(email)
    attempts, _ = get_login_attempts(email)
    if attempts >= max_login_attempts:
        lock_account(email)
    return False

def check_is_old_password(email, password):
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT password, set_at FROM password_history WHERE email = ? ORDER BY set_at DESC", (email,))
    rows = c.fetchall()
    conn.close()
    for stored_hash, set_at in rows:
        if bcrypt.checkpw(password.encode("utf-8"), stored_hash):
            return set_at
    return None

def check_password_reused(email, new_password):
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT password FROM password_history WHERE email = ?", (email,))
    rows = c.fetchall()
    conn.close()
    for (stored_hash,) in rows:
        if bcrypt.checkpw(new_password.encode("utf-8"), stored_hash):
            return True
    return False

def update_password(email, new_password):
    conn = _get_conn()
    c = conn.cursor()
    hashed = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt())
    now = _get_timestamp()

    c.execute("UPDATE users SET password = ? WHERE email = ?", (hashed, email))
    c.execute("INSERT INTO password_history (email, password, set_at) VALUES (?, ?, ?)", (email, hashed, now))
    conn.commit()
    conn.close()

def save_feedback(email, original_text, generated_text, task_type, rating, comments):
    conn = _get_conn()
    c = conn.cursor()
    now = _get_timestamp()
    c.execute("""
    INSERT INTO feedback (email, original_text, generated_text, task_type, rating, comments, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (email, original_text, generated_text, task_type, rating, comments, now))
    conn.commit()
    conn.close()

def get_all_feedback():
    conn = _get_conn()
    c = conn.cursor()
    c.execute("""
        SELECT id, email, task_type, rating, comments, created_at
        FROM feedback ORDER BY created_at DESC
    """)
    rows = c.fetchall()
    conn.close()
    return rows

def log_activity(email, activity_type, details, output_text, model_used):
    conn = _get_conn()
    c = conn.cursor()
    now = _get_timestamp()
    c.execute("""
    INSERT INTO activity_history (email, activity_type, details, output_text, model_used, created_at)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (email, activity_type, details, output_text, model_used, now))
    conn.commit()
    conn.close()

def get_user_activity(email):
    conn = _get_conn()
    c = conn.cursor()
    c.execute("""
    SELECT activity_type, details, output_text, model_used, created_at
    FROM activity_history
    WHERE email = ? AND activity_type != 'Login'
    ORDER BY created_at DESC
    """, (email,))
    rows = c.fetchall()
    conn.close()
    return rows

def get_profile_image(email):
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT avatar FROM user_profiles WHERE email=?", (email,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def delete_profile_image(email):
    conn = _get_conn()
    c = conn.cursor()
    c.execute("UPDATE user_profiles SET avatar = NULL WHERE email = ?", (email,))
    conn.commit()
    conn.close()

# -------------------------------
# READABILITY
# -------------------------------

def _syllable_fallback(text: str) -> int:
    """Vowel-group syllable estimator — used when cmudict is unavailable."""
    return sum(
        max(1, len(re.findall(r'[aeiouAEIOU]+', w)))
        for w in text.split()
    )

def _difficult_words_fallback(text: str) -> int:
    """Count words with 3+ syllables via fallback estimator."""
    count = 0
    for w in re.findall(r'\b[a-zA-Z]+\b', text):
        if max(1, len(re.findall(r'[aeiouAEIOU]+', w))) >= 3:
            count += 1
    return count

class ReadabilityAnalyzer:
    def __init__(self, text):
        self.text = text
        self.num_sentences = textstat.sentence_count(text)
        self.num_words = textstat.lexicon_count(text, removepunct=True)
        self.char_count = textstat.char_count(text)

        # difficult_words internally calls syllable_count → needs cmudict
        try:
            self.complex_words = textstat.difficult_words(text)
        except (LookupError, Exception):
            self.complex_words = _difficult_words_fallback(text)

        # syllable_count needs cmudict
        try:
            self.num_syllables = textstat.syllable_count(text)
        except (LookupError, Exception):
            self.num_syllables = _syllable_fallback(text)

    def get_all_metrics(self):
        def _safe(fn, fallback=0.0):
            try:
                return fn(self.text)
            except (LookupError, Exception):
                return fallback

        return {
            "Flesch Reading Ease":  _safe(textstat.flesch_reading_ease,  50.0),
            "Flesch-Kincaid Grade": _safe(textstat.flesch_kincaid_grade,   8.0),
            "SMOG Index":           _safe(textstat.smog_index,             8.0),
            "Gunning Fog":          _safe(textstat.gunning_fog,            8.0),
            "Coleman-Liau":         _safe(textstat.coleman_liau_index,     8.0),
        }

# -------------------------------
# MODEL REGISTRY — lazy loader map
# -------------------------------
MODEL_REGISTRY = {
    ("summarization", "bart"): "sshleifer/distilbart-cnn-12-6",
    ("summarization", "pegasus"): "google/pegasus-cnn_dailymail",
    ("summarization", "flan-t5"): "google/flan-t5-small",
    ("paraphrase", "flan_t5"): "google/flan-t5-small",
    ("paraphrase", "bart"): "eugenesiow/bart-paraphrase",
}

@st.cache_resource(show_spinner=False)
def load_model(model_type: str, task: str):
    """
    Lazily load and cache a single model by task + model_type.
    model_type examples: "BART", "FLAN-T5", "Pegasus"
    task examples: "summarization", "paraphrase"
    Returns {"tokenizer": ..., "model": ...} or None on failure.
    """
    if not TRANSFORMERS_AVAILABLE:
        return None

    # Normalise: "FLAN-T5" → "flan-t5", "flan_t5" stays "flan_t5"
    normalised = model_type.lower()
    registry_key = (task, normalised)

    if registry_key not in MODEL_REGISTRY:
        return None

    model_id = MODEL_REGISTRY[registry_key]
    try:
        tokenizer = AutoTokenizer.from_pretrained(model_id)
        model = AutoModelForSeq2SeqLM.from_pretrained(model_id)
        return {"tokenizer": tokenizer, "model": model}
    except Exception:
        return None

# -------------------------------
# TRANSLATION MODEL (kept as-is)
# -------------------------------
@st.cache_resource(show_spinner=False)
def load_translation_model():
    if not TRANSFORMERS_AVAILABLE:
        return None, None
    try:
        model_id = "facebook/nllb-200-distilled-600M"
        tokenizer = AutoTokenizer.from_pretrained(model_id)
        model = AutoModelForSeq2SeqLM.from_pretrained(model_id)
        return tokenizer, model
    except Exception:
        return None, None

def translate_text(text, source_lang="English", target_lang="English"):
    if source_lang == target_lang:
        return text

    tok, model = load_translation_model()
    if tok is None or model is None:
        return text

    src_code = LANG_CODES.get(source_lang, "eng_Latn")
    tgt_code = LANG_CODES.get(target_lang, "eng_Latn")

    try:
        sentences = _safe_sent_tokenize(text)
        chunks, curr_chunk, curr_len = [], [], 0
        for s in sentences:
            s_len = len(s.split())
            if curr_len + s_len > 200 and curr_chunk:
                chunks.append(" ".join(curr_chunk))
                curr_chunk = [s]
                curr_len = s_len
            else:
                curr_chunk.append(s)
                curr_len += s_len
        if curr_chunk:
            chunks.append(" ".join(curr_chunk))

        translated_parts = []
        for chunk in chunks:
            tok.src_lang = src_code
            inputs = tok(chunk, return_tensors="pt", max_length=512, truncation=True)
            tgt_token_id = tok.convert_tokens_to_ids(tgt_code)
            with torch.no_grad():
                outputs = model.generate(**inputs, forced_bos_token_id=tgt_token_id, max_length=384)
            translated_parts.append(tok.decode(outputs[0], skip_special_tokens=True))
        return " ".join(translated_parts)
    except Exception:
        return text

# -------------------------------
# NLP / SUMMARIZATION LAYER
# -------------------------------
def _detect_hallucination(original_text, generated_text):
    gen_words = generated_text.split()
    orig_words = set(original_text.lower().split())

    if len(gen_words) < 3:
        return True

    word_counts = Counter(w.lower().strip(".,!?();:'\"") for w in gen_words)
    most_common_count = word_counts.most_common(1)[0][1] if word_counts else 0
    if most_common_count > len(gen_words) * 0.5 and len(gen_words) > 20:
        return True

    gen_clean = [w.lower().strip(".,!?();:'\"") for w in gen_words]
    novel_words = [w for w in gen_clean if w not in orig_words and len(w) > 3]
    if len(novel_words) > len(gen_words) * 0.85 and len(gen_words) > 30:
        return True

    return False

def simple_text_summarization(text, summary_length):
    try:
        sentences = _safe_sent_tokenize(text)
        if len(sentences) <= 2:
            return text[:100] + "..." if len(text) > 100 else text

        if summary_length == "Short":
            return " ".join(sentences[:max(1, len(sentences) // 4)])
        elif summary_length == "Medium":
            return " ".join(sentences[:max(2, len(sentences) // 2)])
        else:
            return " ".join(sentences[:max(3, int(len(sentences) * 0.75))])
    except Exception:
        return text[:150] + "..." if len(text) > 150 else text

def local_summarize(text, summary_length, model_type, models_dict, target_lang="English"):
    model_key = model_type.lower()
    if model_key not in models_dict or models_dict[model_key] is None:
        result = simple_text_summarization(text, summary_length)
        if target_lang != "English":
            result = translate_text(result, "English", target_lang)
        return result

    model_info = models_dict[model_key]
    tokenizer = model_info["tokenizer"]
    model = model_info["model"]

    input_length = len(tokenizer.encode(text))
    safe_max = max(60, int(input_length * 0.95))
    length_config = {
        "Short": {"max_length": min(60, max(20, input_length // 4)), "min_length": min(10, max(5, input_length // 6))},
        "Medium": {"max_length": min(150, max(40, input_length // 2)), "min_length": min(25, max(12, input_length // 4))},
        "Long": {"max_length": min(safe_max, max(80, int(input_length * 0.9))), "min_length": min(50, max(25, input_length // 2))},
    }
    config = length_config.get(summary_length, length_config["Medium"])
    config["min_length"] = min(config["min_length"], config["max_length"] - 5)
    config["min_length"] = max(config["min_length"], 5)

    prompt = text
    if model_key == "flan-t5":
        if summary_length == "Short":
            prompt = f"Write a brief 2-3 sentence summary of the following text: {text}"
        elif summary_length == "Medium":
            prompt = f"Write a detailed summary of the following text, covering the main points: {text}"
        else:
            prompt = f"Write a comprehensive and thorough summary of the following text, covering all key points and important details: {text}"

    try:
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=1024, padding=True)
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=config["max_length"],
                min_new_tokens=config["min_length"],
                num_beams=2,
                no_repeat_ngram_size=3,
                repetition_penalty=1.5,
                early_stopping=True,
            )
        summary = tokenizer.decode(outputs[0], skip_special_tokens=True)

        if _detect_hallucination(text, summary) or not summary.strip():
            summary = simple_text_summarization(text, summary_length)

        if target_lang != "English":
            summary = translate_text(summary, "English", target_lang)

        return summary
    except Exception:
        result = simple_text_summarization(text, summary_length)
        if target_lang != "English":
            result = translate_text(result, "English", target_lang)
        return result

# -------------------------------
# NLP / PARAPHRASING LAYER
# -------------------------------
def apply_fallback_paraphrasing(text, complexity):
    words = text.split()
    if len(words) <= 3:
        return text

    substitutions = {
        "Simple": {
            "utilize": "use", "facilitate": "help", "fundamental": "basic",
            "however": "but", "moreover": "also", "subsequently": "then",
            "important": "key",
        },
        "Neutral": {
            "use": "utilize", "help": "assist", "basic": "fundamental",
            "but": "however", "also": "furthermore", "important": "significant",
        },
        "Advanced": {
            "use": "leverage", "help": "facilitate", "basic": "foundational",
            "but": "nevertheless", "also": "moreover", "important": "paramount",
        },
    }

    sub_dict = substitutions.get(complexity, substitutions["Neutral"])
    output = []
    for word in words:
        clean_word = word.strip(".,!?();:'\"").lower()
        if clean_word in sub_dict:
            new_word = sub_dict[clean_word]
            if word[0].isupper():
                new_word = new_word.capitalize()
            output.append(new_word)
        else:
            output.append(word)
    return " ".join(output)

def paraphrase_with_model(text, complexity, style, model_type, models_dict, target_lang="English"):
    model_key = model_type.lower().replace("-", "_")
    try:
        model_info = models_dict.get(model_key)
        if model_info is None:
            result = apply_fallback_paraphrasing(text, complexity)
            if target_lang != "English":
                result = translate_text(result, "English", target_lang)
            return result

        tokenizer = model_info["tokenizer"]
        model = model_info["model"]

        sentences = _safe_sent_tokenize(text)
        chunks, curr, curr_len = [], [], 0
        for s in sentences:
            slen = len(s.split())
            if curr_len + slen > 80 and curr:
                chunks.append(" ".join(curr))
                curr = [s]
                curr_len = slen
            else:
                curr.append(s)
                curr_len += slen
        if curr:
            chunks.append(" ".join(curr))

        outputs_all = []
        for chunk in chunks:
            if model_key == "flan_t5":
                prompt = f"paraphrase the following text using different words and sentence structure: {chunk} </s>"
            else:
                prompt = f"paraphrase: {chunk}"

            inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512, padding="max_length")
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=150,
                    min_new_tokens=20,
                    num_beams=1,
                    no_repeat_ngram_size=3,
                    repetition_penalty=1.8,
                )
            paraphrased = tokenizer.decode(outputs[0], skip_special_tokens=True)
            outputs_all.append(paraphrased if paraphrased.strip() else chunk)

        final_paraphrase = " ".join(outputs_all)
        if not final_paraphrase.strip():
            final_paraphrase = apply_fallback_paraphrasing(text, complexity)

        if target_lang != "English":
            final_paraphrase = translate_text(final_paraphrase, "English", target_lang)

        return final_paraphrase
    except Exception:
        result = apply_fallback_paraphrasing(text, complexity)
        if target_lang != "English":
            result = translate_text(result, "English", target_lang)
        return result

# -------------------------------
# HELPERS
# -------------------------------
def create_token(data):
    data["exp"] = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

def valid_email(email):
    return re.match(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$", email)

def valid_password(password):
    return re.match(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$", password)

def password_strength(password):
    score = 0
    if len(password) >= 8: score += 1
    if re.search(r"[A-Z]", password): score += 1
    if re.search(r"[a-z]", password): score += 1
    if re.search(r"\d", password): score += 1
    if re.search(r"[@$!%*?&]", password): score += 1
    return score

def get_relative_time(date_str):
    if not date_str:
        return "some time ago"
    try:
        past = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        diff = datetime.datetime.utcnow() - past
        days = diff.days
        if days > 365: return f"{days // 365} years ago"
        if days > 30: return f"{days // 30} months ago"
        if days > 0: return f"{days} days ago"
        return "recently"
    except Exception:
        return date_str

def generate_otp():
    secret = secrets.token_bytes(20)
    counter = int(time.time())
    msg = struct.pack(">Q", counter)
    hmac_hash = hmac.new(secret, msg, hashlib.sha1).digest()
    offset = hmac_hash[19] & 0xF
    code = (
        ((hmac_hash[offset] & 0x7F) << 24) |
        ((hmac_hash[offset + 1] & 0xFF) << 16) |
        ((hmac_hash[offset + 2] & 0xFF) << 8) |
        (hmac_hash[offset + 3] & 0xFF)
    )
    return f"{code % 1000000:06d}"

def create_otp_token(otp, email):
    otp_hash = bcrypt.hashpw(otp.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    payload = {
        "otp_hash": otp_hash,
        "sub": email,
        "type": "password_reset",
        "iat": datetime.datetime.utcnow(),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=OTP_EXPIRY_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def verify_otp_token(token, input_otp, email):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        if payload.get("sub") != email:
            return False, "Token mismatch"
        if bcrypt.checkpw(input_otp.encode("utf-8"), payload["otp_hash"].encode("utf-8")):
            return True, "Valid"
        return False, "Invalid OTP"
    except Exception as e:
        return False, str(e)

def send_email(to_email, otp, app_pass):
    if not app_pass and not EMAIL_PASSWORD:
        return False, "EMAIL_PASSWORD is not set"

    msg = MIMEMultipart()
    msg["From"] = f"Infosys Springboard <{EMAIL_ADDRESS}>"
    msg["To"] = to_email
    msg["Subject"] = "🔐 TextMorph - Password Reset OTP"

    body = f"""
    <html>
    <body style="font-family: Arial; background:#0e1117; color:white; padding:20px;">
        <div style="max-width:500px; margin:auto; background:#1f2937; padding:30px; border-radius:12px; border:1px solid #00F5FF;">
            <h2>TextMorph Security</h2>
            <p>Use this OTP for account: {to_email}</p>
            <div style="font-size:32px; font-weight:bold; letter-spacing:6px; padding:20px; background:#00F5FF; color:black; border-radius:8px;">
                {otp}
            </div>
            <p>Valid for {OTP_EXPIRY_MINUTES} minutes</p>
        </div>
    </body>
    </html>
    """
    msg.attach(MIMEText(body, "html"))

    try:
        s = smtplib.SMTP("smtp.gmail.com", 587)
        s.starttls()
        s.login(EMAIL_ADDRESS, app_pass if app_pass else EMAIL_PASSWORD)
        s.sendmail(EMAIL_ADDRESS, to_email, msg.as_string())
        s.quit()
        return True, "Sent"
    except Exception as e:
        return False, str(e)

def extract_text(file):
    try:
        if file.type == "application/pdf":
            reader = PyPDF2.PdfReader(file)
            return "".join([(page.extract_text() or "") + "\n" for page in reader.pages])
        return file.read().decode("utf-8")
    except Exception as e:
        st.error(f"Error reading file: {e}")
        return ""

def create_gauge(value, title, min_val, max_val, color):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={"text": title},
        gauge={
            "axis": {"range": [min_val, max_val]},
            "bar": {"color": color},
            "steps": [
                {"range": [min_val, (min_val + max_val) / 3], "color": "#1f2937"},
                {"range": [(min_val + max_val) / 3, (min_val + max_val) * 2 / 3], "color": "#374151"},
                {"range": [(min_val + max_val) * 2 / 3, max_val], "color": "#4b5563"},
            ],
        }
    ))
    fig.update_layout(height=250, margin=dict(l=10, r=10, t=40, b=10))
    return fig

def is_admin(email):
    if email == "admin@textmorph.com":
        return True
    conn = _get_conn()
    role = conn.execute("SELECT role FROM user_roles WHERE email=?", (email,)).fetchone()
    conn.close()
    return bool(role and role[0].lower() == "admin")

def render_feedback_ui(email, original_text, generated_text, task_type):
    with st.expander("📝 Provide Feedback"):
        col1, col2 = st.columns([1, 4])
        with col1:
            rating = st.radio("Rating", [1, 2, 3, 4, 5], horizontal=True, key=f"r_{task_type}_{hash(str(original_text)[:20])}")
        with col2:
            comments = st.text_input("Comments (optional)", key=f"c_{task_type}_{hash(str(original_text)[:20])}")

        if st.button("Submit Feedback", key=f"fbs_{task_type}_{hash(str(original_text)[:20])}"):
            save_feedback(email, original_text, generated_text, task_type, rating, comments)
            st.success("Thank you for your feedback!")

def _clear_stale_results(new_menu):
    if st.session_state.get("current_menu") != new_menu:
        for key in ["last_summary", "last_summary_text", "summarization_history", "last_para", "last_para_text", "paraphrasing_history"]:
            if key in st.session_state:
                del st.session_state[key]
        st.session_state["current_menu"] = new_menu

# -------------------------------
# PAGES
# -------------------------------
def signup():
    st.markdown('<div class="neon-card">TextMorph Advanced Summarization & Paraphrasing</div>', unsafe_allow_html=True)
    st.title("Create Account")

    questions = [
        "What is your pet name?",
        "What is your mother's maiden name?",
        "What is your favorite teacher?",
        "What was your first school name?",
        "What is your favorite food?"
    ]

    with st.form("signup_form"):
        username = st.text_input("Username")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        confirm = st.text_input("Confirm Password", type="password")
        question = st.selectbox("Security Question", questions)
        answer = st.text_input("Security Answer")
        submit = st.form_submit_button("Signup")

        if password:
            st.text(f"Password strength: {password_strength(password)}/5")

        if submit:
            username = username.strip()
            email = email.strip()
            password = password.strip()
            confirm = confirm.strip()
            answer = answer.strip()

            if not username:
                st.error("Username cannot be empty")
            elif not email:
                st.error("Email cannot be empty")
            elif not password:
                st.error("Password cannot be empty")
            elif not confirm:
                st.error("Confirm password cannot be empty")
            elif not answer:
                st.error("Security answer cannot be empty")
            elif not valid_email(email):
                st.error("Invalid email format")
            elif not valid_password(password):
                st.error("Password must be strong")
            elif password != confirm:
                st.error("Passwords do not match")
            elif check_user_exists(email):
                st.error("Email already registered")
            elif register_user(username, email, password, question, answer):
                st.success("Account created successfully 🎉")
                st.session_state.page = "login"
                st.rerun()
            else:
                st.error("User already exists")

    if st.button("Go to Login"):
        st.session_state.page = "login"
        st.rerun()

def login():
    st.markdown('<div class="neon-card">TextMorph Advanced Summarization & Paraphrasing</div>', unsafe_allow_html=True)
    st.title("Login")

    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")

        if submit:
            auth = authenticate_user(email, password)

            if auth == "locked":
                st.error("Account locked. Try again later.")
            elif auth:
                username = get_username(email)
                st.session_state["user"] = email
                st.session_state["token"] = create_token({"email": email, "username": username})
                st.success("Login Successful! 🎉")
                time.sleep(1)
                st.session_state.page = "admin_dashboard" if is_admin(email) else "dashboard"
                st.rerun()
            else:
                st.error("Invalid credentials.")
                old_dt = check_is_old_password(email, password)
                if old_dt:
                    st.warning(f"Note: You used an old password from {get_relative_time(old_dt)}.")

    col1, _, col2 = st.columns([1, 2, 1])
    with col1:
        if st.button("Forgot Password", use_container_width=True):
            st.session_state.page = "forgot"
            st.rerun()
    with col2:
        if st.button("Create Account", use_container_width=True):
            st.session_state.page = "signup"
            st.rerun()

def forgot_password():
    if "stage" not in st.session_state:
        st.session_state.stage = "email"
    if "reset_email" not in st.session_state:
        st.session_state.reset_email = ""
    if "otp_token" not in st.session_state:
        st.session_state.otp_token = None
    if "otp_sent_time" not in st.session_state:
        st.session_state.otp_sent_time = None

    st.title("🔒 Forgot Password")

    if st.session_state.stage == "email":
        email = st.text_input("Enter your registered Email")
        if st.button("Verify Email"):
            if check_user_exists(email):
                st.session_state.reset_email = email
                st.session_state.email_verified = True
                st.success("Email Verified ✅")
            else:
                st.error("Email not found")

        if st.session_state.get("email_verified"):
            col1, _, col2 = st.columns([1.3, 1, 1.3])
            with col1:
                if st.button("Reset via OTP", use_container_width=True):
                    st.session_state.stage = "otp"
                    st.rerun()
            with col2:
                if st.button("Reset via Security Question", use_container_width=True):
                    st.session_state.stage = "security"
                    st.rerun()

    elif st.session_state.stage == "otp":
        st.subheader("OTP Verification")
        st.info(f"OTP will be sent to {st.session_state.reset_email}")

        OTP_VALID_SECONDS = 600

        if not st.session_state.otp_sent_time:
            if st.button("Send OTP"):
                otp = generate_otp()
                ok, msg = send_email(st.session_state.reset_email, otp, EMAIL_PASSWORD)
                if ok:
                    st.session_state.otp_token = create_otp_token(otp, st.session_state.reset_email)
                    st.session_state.otp_sent_time = time.time()
                    st.success("OTP sent successfully 📧")
                else:
                    st.error(f"Failed to send OTP: {msg}")

        if st.session_state.otp_sent_time:
            elapsed = time.time() - st.session_state.otp_sent_time
            remaining = int(OTP_VALID_SECONDS - elapsed)

            if remaining <= 0:
                st.error("OTP expired. Please resend.")
                st.session_state.otp_sent_time = None
                st.session_state.otp_token = None
            else:
                st.info(f"OTP expires in {remaining} seconds")
                otp_input = st.text_input("Enter OTP")
                col1, _, col2 = st.columns([1, 2, 1])

                if col1.button("Verify OTP", use_container_width=True):
                    if not otp_input.strip():
                        st.error("Please enter OTP")
                    else:
                        ok, _ = verify_otp_token(st.session_state.otp_token, otp_input.strip(), st.session_state.reset_email)
                        if ok:
                            st.success("OTP Verified ✅")
                            st.session_state.stage = "reset"
                            st.session_state.otp_sent_time = None
                            st.rerun()
                        else:
                            st.error("Invalid OTP")

                if col2.button("Resend OTP", use_container_width=True):
                    st.session_state.otp_sent_time = None
                    st.session_state.otp_token = None
                    st.rerun()

    elif st.session_state.stage == "security":
        question = get_security_question(st.session_state.reset_email)
        st.write(f"Security Question: {question}")
        answer = st.text_input("Enter Answer")

        if st.button("Verify Answer"):
            if verify_security_answer(st.session_state.reset_email, answer):
                st.session_state.stage = "reset"
                st.success("Answer Verified ✅")
                st.rerun()
            else:
                st.error("Incorrect Answer")

    elif st.session_state.stage == "reset":
        new_pass = st.text_input("New Password", type="password")
        confirm_pass = st.text_input("Confirm Password", type="password")

        if st.button("Update Password"):
            if not valid_password(new_pass):
                st.error("Weak password")
            elif new_pass != confirm_pass:
                st.error("Passwords do not match")
            elif check_password_reused(st.session_state.reset_email, new_pass):
                st.error("You cannot reuse old password")
            else:
                update_password(st.session_state.reset_email, new_pass)
                st.success("Password Updated Successfully 🎉")

    if st.button("Back to Login"):
        st.session_state.stage = "email"
        st.session_state.page = "login"
        st.rerun()

def readability_page():
    if not st.session_state["user"]:
        st.session_state.page = "login"
        st.rerun()

    st.title("📖 Text Readability Analyzer")
    tab1, tab2 = st.tabs(["✍️ Input Text", "📂 Upload File (TXT/PDF)"])
    text_input = ""

    with tab1:
        raw_text = st.text_area("Enter text to analyze (min 50 chars):", height=200)
        if raw_text:
            text_input = raw_text

    with tab2:
        uploaded_file = st.file_uploader("Upload a file", type=["txt", "pdf"])
        if uploaded_file:
            text_input = extract_text(uploaded_file)
            if text_input:
                st.info("✅ File loaded")

    if st.button("Analyze Readability", type="primary"):
        if len(text_input) < 50:
            st.error("Text is too short.")
        else:
            analyzer = ReadabilityAnalyzer(text_input)
            score = analyzer.get_all_metrics()
            avg_grade = (
                score["Flesch-Kincaid Grade"] +
                score["Gunning Fog"] +
                score["SMOG Index"] +
                score["Coleman-Liau"]
            ) / 4

            if avg_grade <= 6:
                level, color = "Beginner (Elementary)", "#28a745"
            elif avg_grade <= 10:
                level, color = "Intermediate (Middle School)", "#17a2b8"
            elif avg_grade <= 14:
                level, color = "Advanced (High School/College)", "#ffc107"
            else:
                level, color = "Expert (Professional/Academic)", "#dc3545"

            st.markdown(f"""
            <div style="background-color:#1f2937; padding:20px; border-radius:10px; border-left:5px solid {color}; text-align:center;">
                <h2 style="margin:0; color:{color} !important;">Overall Level: {level}</h2>
                <p style="margin:5px 0 0 0; color:#9ca3af;">Approximate Grade Level: {int(avg_grade)}</p>
            </div>
            """, unsafe_allow_html=True)

            c1, c2, c3 = st.columns(3)
            with c1:
                st.plotly_chart(create_gauge(score["Flesch Reading Ease"], "Flesch Reading Ease", 0, 100, "#00ffcc"), use_container_width=True)
            with c2:
                st.plotly_chart(create_gauge(score["Flesch-Kincaid Grade"], "Flesch-Kincaid Grade", 0, 20, "#ff00ff"), use_container_width=True)
            with c3:
                st.plotly_chart(create_gauge(score["SMOG Index"], "SMOG Index", 0, 20, "#ffff00"), use_container_width=True)

            c4, c5 = st.columns(2)
            with c4:
                st.plotly_chart(create_gauge(score["Gunning Fog"], "Gunning Fog", 0, 20, "#00ccff"), use_container_width=True)
            with c5:
                st.plotly_chart(create_gauge(score["Coleman-Liau"], "Coleman-Liau", 0, 20, "#ff9900"), use_container_width=True)

def summarizer_page():
    st.title("📝 Multi-level Summarization")

    if "summarization_history" not in st.session_state:
        st.session_state.summarization_history = []

    col1, col2 = st.columns([2, 1])

    with col1:
        text_input = st.text_area("Enter text to summarize (min 50 chars):", height=200, key="summarization_text")
        uploaded_file = st.file_uploader("Or upload a file", type=["txt", "pdf"], key="sum_upload")
        if uploaded_file:
            text_input = extract_text(uploaded_file)
            st.info(f"✅ File loaded ({len(text_input.split())} words)")

    with col2:
        summary_length = st.selectbox("Summary Length", ["Short", "Medium", "Long"])
        model_type = st.selectbox("Model", ["FLAN-T5", "BART", "Pegasus"])
        target_lang = st.selectbox("🌐 Output Language", SUPPORTED_LANGUAGES)

        if st.button("Generate Summary", type="primary", use_container_width=True):
            if len(text_input) < 50:
                st.error("Text is too short.")
            else:
                with st.spinner(f"Loading {model_type} model…"):
                    model_data = load_model(model_type, "summarization")
                model_key = model_type.lower()
                models_dict = {model_key: model_data}
                summary = local_summarize(text_input, summary_length, model_type, models_dict, target_lang=target_lang)
                st.session_state.last_summary = summary
                st.session_state.last_summary_text = text_input
                st.session_state.last_summary_lang = target_lang
                log_activity(st.session_state["user"], "Summarization", f"Length: {summary_length}, Lang: {target_lang}", summary, model_type)

    if "last_summary" in st.session_state:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("📄 Original Text")
            st.info(st.session_state.last_summary_text)
        with c2:
            st.subheader("📝 Generated Summary")
            st.success(st.session_state.last_summary)

        render_feedback_ui(st.session_state["user"], st.session_state.last_summary_text, st.session_state.last_summary, "Summarization")

def paraphraser_page():
    st.title("🔄 Advanced Paraphrasing Engine")

    col1, col2 = st.columns([2, 1])

    with col1:
        text_input = st.text_area("Enter text to paraphrase (min 50 chars):", height=200, key="para_text")
        uploaded_file = st.file_uploader("Or upload a file", type=["txt", "pdf"], key="para_upload")
        if uploaded_file:
            text_input = extract_text(uploaded_file)
            st.info(f"✅ File loaded ({len(text_input.split())} words)")

    with col2:
        complexity = st.selectbox("Complexity Level", ["Simple", "Neutral", "Advanced"])
        style = st.selectbox("Paraphrasing Style", ["Simplification", "Formalization", "Creative"])
        model_type = st.selectbox("Model", ["FLAN-T5", "BART"])
        target_lang = st.selectbox("🌐 Output Language", SUPPORTED_LANGUAGES, key="para_lang")

        if st.button("Generate Paraphrase", type="primary", use_container_width=True):
            if len(text_input) < 50:
                st.error("Text is too short.")
            else:
                with st.spinner(f"Loading {model_type} model…"):
                    model_data = load_model(model_type, "paraphrase")
                # paraphrase_with_model uses key like "flan_t5", not "flan-t5"
                model_key = model_type.lower().replace("-", "_")
                models_dict = {model_key: model_data}
                paraphrased = paraphrase_with_model(text_input, complexity, style, model_type, models_dict, target_lang=target_lang)
                st.session_state.last_para = paraphrased
                st.session_state.last_para_text = text_input
                st.session_state.last_para_lang = target_lang
                log_activity(st.session_state["user"], "Paraphrasing", f"Complexity: {complexity}, Style: {style}", paraphrased, model_type)

    if "last_para" in st.session_state:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("📄 Original Text")
            st.info(st.session_state.last_para_text)
        with c2:
            st.subheader("🔄 Paraphrased Text")
            st.success(st.session_state.last_para)

        render_feedback_ui(st.session_state["user"], st.session_state.last_para_text, st.session_state.last_para, "Paraphrasing")

def history_page():
    st.title("📜 Activity History Dashboard")
    activities = get_user_activity(st.session_state["user"])
    if not activities:
        st.info("No activity history yet.")
        return

    df = pd.DataFrame(activities, columns=["Activity Type", "Details", "Output", "Model Used", "Timestamp"])
    st.dataframe(df, use_container_width=True)

def augmentation_page():
    st.title("🗃️ Dataset Augmentation & Custom Model Tuning")
    st.info("🚀 Demo version")

    aug_input = st.text_area(
        "Original Text (Paste multiple paragraphs here):",
        height=200,
        value="The quick brown fox jumps over the lazy dog.\n\nArtificial Intelligence is rapidly evolving in the modern era."
    )

    col1, col2 = st.columns(2)
    with col1:
        aug_type = st.selectbox("Transformation Type", ["Paraphrasing", "Summarization"])
    with col2:
        aug_setting = st.selectbox("Setting", ["Short", "Medium", "Long"] if aug_type == "Summarization" else ["Advanced", "Simple", "Neutral"])

    if st.button("Generate Dataset 🚀", use_container_width=True):
        paragraphs = [p.strip() for p in aug_input.split("\n\n") if len(p.strip()) > 10]
        if not paragraphs:
            st.error("Please enter at least one valid paragraph.")
        else:
            # Load the model once before the loop (cached after first call)
            if aug_type == "Summarization":
                with st.spinner("Loading BART model…"):
                    _aug_model_data = load_model("BART", "summarization")
                _aug_models_dict = {"bart": _aug_model_data}
            else:
                with st.spinner("Loading FLAN-T5 model…"):
                    _aug_model_data = load_model("FLAN-T5", "paraphrase")
                _aug_models_dict = {"flan_t5": _aug_model_data}

            results = []
            for idx, para in enumerate(paragraphs):
                if aug_type == "Summarization":
                    res = local_summarize(para, aug_setting, "BART", _aug_models_dict)
                else:
                    res = paraphrase_with_model(para, aug_setting, "Creative", "FLAN-T5", _aug_models_dict)

                results.append({
                    "#": idx + 1,
                    "Original Text": para,
                    "Target Text": res
                })

            df = pd.DataFrame(results)
            st.dataframe(df, use_container_width=True)
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Download Dataset (CSV)", csv, "augmented_dataset.csv", "text/csv")

def user_profile(email):
    st.title("👤 User Profile")
    conn = _get_conn()

    st.subheader("📧 Change Email")
    new_email = st.text_input("Enter New Email")
    if st.button("Update Email"):
        if not new_email:
            st.error("Email cannot be empty")
        elif new_email == email:
            st.error("New email cannot be same as current")
        elif not valid_email(new_email):
            st.error("Invalid email format")
        else:
            existing = conn.execute("SELECT email FROM users WHERE email=?", (new_email,)).fetchone()
            if existing:
                st.error("Email already exists")
            else:
                try:
                    conn.execute("UPDATE users SET email=? WHERE email=?", (new_email, email))
                    conn.execute("UPDATE user_roles SET email=? WHERE email=?", (new_email, email))
                    conn.execute("UPDATE activity_history SET email=? WHERE email=?", (new_email, email))
                    conn.execute("UPDATE feedback SET email=? WHERE email=?", (new_email, email))
                    conn.execute("UPDATE user_profiles SET email=? WHERE email=?", (new_email, email))
                    conn.commit()
                    st.session_state.user = new_email
                    st.success("Email updated successfully")
                    st.rerun()
                except Exception:
                    conn.rollback()
                    st.error("Error updating email")

    st.markdown("---")
    st.subheader("🔑 Change Password")
    new_password = st.text_input("New Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")
    if st.button("Update Password"):
        if not new_password or not confirm_password:
            st.error("Both password fields are required")
        elif not valid_password(new_password):
            st.error("Password must contain uppercase, lowercase, number and special character")
        elif new_password != confirm_password:
            st.error("Passwords do not match")
        else:
            hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt())
            conn.execute("UPDATE users SET password=? WHERE email=?", (hashed, email))
            conn.commit()
            st.success("Password updated successfully")

    st.markdown("---")
    st.subheader("🖼 Upload Avatar")
    avatar = st.file_uploader("Upload Profile Picture", type=["png", "jpg", "jpeg"])
    if avatar:
        img = avatar.read()
        conn.execute("REPLACE INTO user_profiles(email,avatar) VALUES (?,?)", (email, img))
        conn.commit()
        st.success("Avatar Updated")
        st.rerun()

    data = conn.execute("SELECT avatar FROM user_profiles WHERE email=?", (email,)).fetchone()
    if data and data[0]:
        st.image(data[0], width=150)

    if st.button("Delete Profile Picture"):
        delete_profile_image(email)
        st.success("Profile picture deleted!")
        st.rerun()

    conn.close()

def admin_dashboard():
    st.title("🛠 Admin Dashboard")
    conn = _get_conn()
    users = pd.read_sql_query("""
    SELECT u.email
    FROM users u
    LEFT JOIN user_roles r ON u.email = r.email
    WHERE COALESCE(r.role,'user') != 'admin'
    """, conn)
    activity = pd.read_sql_query("SELECT * FROM activity_history", conn)
    feedback = pd.read_sql_query("SELECT * FROM feedback", conn)
    conn.close()

    col1, col2, col3 = st.columns(3)
    col1.metric("👥 Total Users", len(users))
    col2.metric("📊 Total Activities", len(activity))
    col3.metric("💬 Feedback Received", len(feedback))

def user_management():
    st.subheader("👥 User Management")
    conn = _get_conn()
    users = pd.read_sql_query("""
    SELECT u.email
    FROM users u
    LEFT JOIN user_roles r ON u.email = r.email
    WHERE COALESCE(r.role,'user') != 'admin'
    AND u.email != 'admin@textmorph.com'
    """, conn)

    if users.empty:
        st.info("No users available.")
        conn.close()
        return

    selected_user = st.selectbox("Select User", users["email"])
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Promote to Admin", use_container_width=True):
            conn.execute("INSERT OR REPLACE INTO user_roles(email, role) VALUES (?, 'admin')", (selected_user,))
            conn.commit()
            st.success("User promoted to Admin")
            st.rerun()

    with col2:
        if st.button("Delete User", use_container_width=True):
            conn.execute("DELETE FROM users WHERE email=?", (selected_user,))
            conn.commit()
            st.error("User Deleted")
            st.rerun()

    conn.close()

def locked_accounts_section():
    st.subheader("🔒 Locked Accounts")
    locked_users = get_locked_accounts()

    if not locked_users:
        st.success("No locked accounts.")
    else:
        df = pd.DataFrame(locked_users, columns=["Email", "Locked At"])
        st.dataframe(df, use_container_width=True)
        for email, _ in locked_users:
            col1, col2 = st.columns([3, 1])
            col1.write(email)
            if col2.button("Unlock", key=f"unlock_{email}"):
                unlock_account(email)
                st.success(f"{email} unlocked")
                st.rerun()

def feedback_section():
    st.subheader("💬 User Feedback")
    conn = _get_conn()
    feedback = pd.read_sql_query("""
    SELECT email, task_type, rating, comments, created_at
    FROM feedback ORDER BY created_at DESC
    """, conn)
    conn.close()

    if feedback.empty:
        st.info("No feedback available yet.")
        return

    text = " ".join(feedback["comments"].dropna())
    if text.strip():
        wordcloud = WordCloud(width=800, height=400, background_color="black").generate(text)
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.imshow(wordcloud, interpolation="bilinear")
        ax.axis("off")
        st.pyplot(fig)

    st.dataframe(feedback, use_container_width=True)

def analytics_dashboard():
    st.title("📊 System Analytics")
    conn = _get_conn()
    activity = pd.read_sql_query("""
    SELECT email, activity_type, model_used, created_at
    FROM activity_history
    """, conn)
    conn.close()

    if activity.empty:
        st.info("No activity data available yet.")
        return

    feature_counts = activity["activity_type"].value_counts()
    st.plotly_chart(go.Figure(data=[go.Bar(x=feature_counts.index, y=feature_counts.values)]), use_container_width=True)

# -------------------------------
# APP INIT
# -------------------------------
if "db_initialized" not in st.session_state:
    init_db()
    st.session_state["db_initialized"] = True

# NOTE: No eager model loading here — models are lazy-loaded on first button click
# and cached by @st.cache_resource for all subsequent calls.

if "page" not in st.session_state:
    st.session_state.page = "login"

if "token" not in st.session_state:
    st.session_state.token = None

if "user" not in st.session_state:
    st.session_state.user = None

# -------------------------------
# ROUTING
# -------------------------------
if st.session_state.user:
    with st.sidebar:
        email = st.session_state["user"]
        username = get_username(email)
        avatar = get_profile_image(email)
        is_admin_user = is_admin(email)

        if avatar:
            img_base64 = base64.b64encode(avatar).decode()
            st.markdown(
                f'<img src="data:image/png;base64,{img_base64}" style="width:120px;height:120px;border-radius:50%;object-fit:cover;border:3px solid #00f5ff;">',
                unsafe_allow_html=True
            )
        else:
            st.image("https://cdn-icons-png.flaticon.com/512/149/149071.png", width=80)

        st.markdown(f"### 👤 {username}")

        if not is_admin_user:
            opts = ["Readability", "Summarize", "Paraphrase", "Augmentation", "History", "Profile"]
            icons = ["book", "file-text", "arrow-repeat", "sliders", "clock-history", "person"]
        else:
            opts = ["Admin Dashboard", "User Management", "Activity Tracking", "Analytics", "Feedback", "Locked Accounts"]
            icons = ["speedometer", "people", "activity", "bar-chart", "chat-left-text", "lock"]

        selected = option_menu(
            "TextMorph",
            opts,
            icons=icons,
            menu_icon="cast",
            default_index=0,
            styles={
                "container": {"background-color": "#0e1a24", "padding": "10px"},
                "icon": {"color": "#00F5FF", "font-size": "18px"},
                "nav-link": {"color": "#cfd8dc", "font-size": "16px", "text-align": "left", "margin": "5px", "--hover-color": "#123344"},
                "nav-link-selected": {"background-color": "#123344", "color": "#00F5FF", "border-radius": "10px", "box-shadow": "0 0 10px #00F5FF"},
            }
        )

        if st.button("🔓 Log Out"):
            st.session_state.clear()
            st.session_state.page = "login"
            st.rerun()

    _clear_stale_results(selected)

    if selected == "Profile":
        user_profile(email)
    elif selected == "Summarize":
        summarizer_page()
    elif selected == "Paraphrase":
        paraphraser_page()
    elif selected == "Readability":
        readability_page()
    elif selected == "Augmentation":
        augmentation_page()
    elif selected == "History":
        history_page()
    elif selected == "Admin Dashboard":
        admin_dashboard()
    elif selected == "User Management":
        user_management()
    elif selected == "Activity Tracking":
        history_page()
    elif selected == "Feedback":
        feedback_section()
    elif selected == "Locked Accounts":
        locked_accounts_section()
    elif selected == "Analytics":
        analytics_dashboard()
else:
    if st.session_state.page == "login":
        login()
    elif st.session_state.page == "signup":
        signup()
    elif st.session_state.page == "forgot":
        forgot_password()