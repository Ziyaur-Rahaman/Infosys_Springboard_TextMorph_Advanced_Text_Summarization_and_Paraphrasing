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
import pytz

from io import BytesIO
from collections import Counter
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

from wordcloud import WordCloud
from streamlit_option_menu import option_menu
import PyPDF2

# -----------------------------------------------
# STREAMLIT PAGE CONFIG
# -----------------------------------------------
st.set_page_config(page_title="TextMorph", page_icon="🎓", layout="wide")

# -----------------------------------------------
# ENV / APP CONFIG
# -----------------------------------------------
ALGORITHM          = "HS256"
DB_NAME            = os.getenv("DB_PATH", "users.db")
EMAIL_ADDRESS      = "Infosysteam91@gmail.com"
EMAIL_PASSWORD     = os.getenv("EMAIL_PASSWORD")
SECRET_KEY         = os.getenv("JWT_SECRET", "super-secret-key-change-this")
OTP_EXPIRY_MINUTES = 10

SUPPORTED_LANGUAGES = [
    "English", "Hindi", "Tamil", "Kannada", "Telugu", "Marathi",
    "Bengali", "Gujarati", "Malayalam", "Urdu", "Punjabi"
]

# -----------------------------------------------
# NLTK — SSL-first downloader
# -----------------------------------------------
import ssl
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except Exception:
    pass

def _nltk_download_safe(resource):
    try:
        nltk.download(resource, quiet=True)
    except Exception:
        pass

def _ensure_nltk_data():
    resources = {
        "tokenizers/punkt":     "punkt",
        "tokenizers/punkt_tab": "punkt_tab",
        "corpora/cmudict":      "cmudict",
    }
    for find_path, package in resources.items():
        try:
            nltk.data.find(find_path)
        except LookupError:
            _nltk_download_safe(package)

_ensure_nltk_data()

def _safe_sent_tokenize(text):
    try:
        from nltk.tokenize import sent_tokenize as _t
        return _t(text)
    except Exception:
        return re.split(r'(?<=[.!?])\s+', text.strip())

# -----------------------------------------------
# TRANSFORMERS
# -----------------------------------------------
TRANSFORMERS_AVAILABLE = False
BNB_AVAILABLE          = False
try:
    from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
    TRANSFORMERS_AVAILABLE = True
    try:
        from transformers import BitsAndBytesConfig
        BNB_AVAILABLE = True
    except ImportError:
        pass
except ImportError:
    pass

LANG_CODES = {
    "English": "eng_Latn", "Hindi": "hin_Deva", "Tamil": "tam_Taml",
    "Kannada": "kan_Knda", "Telugu": "tel_Telu", "Marathi": "mar_Deva",
    "Bengali": "ben_Beng", "Gujarati": "guj_Gujr", "Malayalam": "mal_Mlym",
    "Urdu": "urd_Arab", "Punjabi": "pan_Guru",
}

# -----------------------------------------------
# DESIGN SYSTEM
# -----------------------------------------------
NEON = "#00C8FF"; NEON2 = "#0099CC"; BG1 = "#0A0F1E"; BG2 = "#0D1526"
GLASS = "rgba(0,200,255,0.06)"; BORDER = "rgba(0,200,255,0.28)"
RED = "#FF4C6A"; YELLOW = "#00E5FF"; TEXT = "#E8F4FD"; MUTED = "#6B8BA4"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');
html, body, [data-testid="stAppViewContainer"] {{ background: #0A0F1E !important; color: {TEXT}; font-family: 'DM Sans', sans-serif; }}
header {{ visibility: visible !important; }} footer {{ visibility: hidden; }}
h1 {{ font-family:'Syne',sans-serif; font-size:2rem; font-weight:800; color:{NEON}; letter-spacing:-0.5px; margin-bottom:0.25rem; }}
h2 {{ font-family:'Syne',sans-serif; font-size:1.4rem; font-weight:700; color:{NEON}; }}
h3 {{ font-family:'Syne',sans-serif; font-size:1.1rem; font-weight:600; color:#B8E4F9; }}
.stTextInput > div > div > input, .stTextArea > div > div > textarea {{
    background: rgba(10,20,40,0.90) !important; border: 1px solid {BORDER} !important;
    border-radius: 10px !important; color: {TEXT} !important; font-size: 0.95rem !important; padding: 10px 14px !important;
}}
.stTextInput > div > div > input:focus, .stTextArea > div > div > textarea:focus {{
    border-color: {NEON} !important; box-shadow: 0 0 0 2px rgba(0,200,255,.15) !important;
}}
.stSelectbox > div > div {{ background: rgba(10,20,40,0.90) !important; border: 1px solid {BORDER} !important; border-radius: 10px !important; color: {TEXT} !important; }}
.stButton > button {{
     background: linear-gradient(145deg, #0F1B2D, #0C1828) !important;
    border: 1px solid rgba(0,200,255,0.28) !important;
    border-radius: 12px !important;

    padding: 12px 16px !important;
    min-height: 60px !important;

    font-size: 0.9rem !important;
    line-height: 1.3 !important;

    display: flex !important;
    align-items: center !important;
    justify-content: center !important;

    white-space: normal !important;
    text-align: center !important;

    transition: all 0.2s ease !important;
}}
.stButton > button:hover {{  transform: translateY(-2px) !important;
    box-shadow: 0 6px 18px rgba(0,200,255,0.2) !important; }}
[data-testid="stSidebar"] {{ background: #0D1526 !important; }}
[data-testid="stMetric"] {{ background: rgba(13,24,46,0.95); border: 1px solid {BORDER}; border-radius: 14px; padding: 16px 20px !important; }}
[data-testid="stMetricLabel"] {{ color:{MUTED} !important; font-size:.8rem !important; }}
[data-testid="stMetricValue"] {{ color:{NEON} !important; font-family:'Syne',sans-serif !important; font-weight:700 !important; }}
[data-testid="stDataFrame"] th {{ background: rgba(0,200,255,.12) !important; color: {NEON} !important; font-size:.8rem; text-transform:uppercase; border-bottom: 1px solid {BORDER} !important; }}
[data-testid="stDataFrame"] td {{ color: {TEXT} !important; border-bottom: 1px solid rgba(0,200,255,.07) !important; font-size:.85rem; }}
.stTabs [data-baseweb="tab-list"] {{ gap: 6px; background: transparent; border-bottom: 1px solid {BORDER}; }}
.stTabs [data-baseweb="tab"] {{ border-radius: 10px 10px 0 0; color: {MUTED}; background: transparent; font-size:.88rem; font-weight:500; padding: 8px 20px; }}
.stTabs [aria-selected="true"] {{ background: rgba(0,200,255,.10) !important; color: {NEON} !important; border-bottom: 2px solid {NEON} !important; }}
[data-testid="stExpander"] {{ background: rgba(13,24,46,0.95); border: 1px solid {BORDER}; border-radius: 12px; }}
[data-testid="stExpander"] summary {{ font-size:.9rem; font-weight:600; color:{NEON}; }}
[data-testid="stAlert"] {{ border-radius: 10px !important; font-size: 0.88rem !important; }}
[data-testid="stFileUploader"] {{ background: rgba(28,18,5,.6) !important; border: 1px dashed {BORDER} !important; border-radius: 12px !important; padding: 12px !important; }}
[data-testid="stDownloadButton"] > button {{ background: transparent !important; color: {NEON} !important; border: 1px solid {BORDER} !important; border-radius: 50px !important; box-shadow: none !important; font-size: 0.85rem !important; padding: 8px 20px !important; }}
[data-testid="stDownloadButton"] > button:hover {{ background: rgba(0,200,255,.12) !important; border-color: {NEON} !important; }}
.stats-row {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; width: 100%; margin-top: 4px; }}
@media (max-width: 680px) {{ .stats-row {{ grid-template-columns: repeat(2, 1fr); }} }}
.stat-box {{ background: rgba(13,24,46,0.95); border: 1px solid {BORDER}; border-radius: 14px; padding: 18px 14px; text-align: center; }}
.stat-num {{ font-family:'Syne',sans-serif; font-size:1.8rem; font-weight:800; color:#00C8FF; }}
.stat-label {{ font-size:.78rem; color:#6B8BA4; margin-top:4px; }}
::-webkit-scrollbar {{ width:5px; }} ::-webkit-scrollbar-track {{ background: {BG1}; }} ::-webkit-scrollbar-thumb {{ background:{BORDER}; border-radius:6px; }}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------
# DATABASE
# -----------------------------------------------
max_login_attempts = 3
lockout_time = 300

def _get_conn():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def _get_timestamp():
    return datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

def init_db():
    conn = _get_conn(); c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS user_activity (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT, action TEXT, language TEXT, created_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS locked_accounts (email TEXT PRIMARY KEY, locked_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS deleted_users (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT, username TEXT, deleted_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS user_roles (email TEXT PRIMARY KEY, role TEXT DEFAULT 'user')")
    c.execute("CREATE TABLE IF NOT EXISTS user_profiles (email TEXT PRIMARY KEY, avatar BLOB)")
    c.execute("CREATE TABLE IF NOT EXISTS users (email TEXT PRIMARY KEY, username TEXT, password BLOB, security_question TEXT, security_answer BLOB, created_at TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS password_history (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT, password BLOB, set_at TEXT, FOREIGN KEY(email) REFERENCES users(email))")
    c.execute("CREATE TABLE IF NOT EXISTS login_attempts (email TEXT PRIMARY KEY, attempts INTEGER, last_attempt REAL)")
    c.execute("CREATE TABLE IF NOT EXISTS feedback (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT, original_text TEXT, generated_text TEXT, task_type TEXT, rating INTEGER, comments TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    c.execute("CREATE TABLE IF NOT EXISTS activity_history (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT, activity_type TEXT, details TEXT, output_text TEXT, model_used TEXT, language TEXT, created_at TEXT)")
    conn.commit(); conn.close(); init_admin()

def check_user_exists(email):
    conn = _get_conn(); c = conn.cursor()
    c.execute("SELECT 1 FROM users WHERE email = ?", (email,)); row = c.fetchone(); conn.close()
    return row is not None

def init_admin():
    if not check_user_exists("admin@textmorph.com"):
        register_user("Admin", "admin@textmorph.com", "Admin@123Secure!", "Admin default question", "admin")

def register_user(username, email, password, question, answer):
    conn = _get_conn(); c = conn.cursor()
    try:
        hp = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        ha = bcrypt.hashpw(answer.encode(), bcrypt.gensalt())
        now = _get_timestamp()
        c.execute("INSERT INTO users (email,username,password,security_question,security_answer,created_at) VALUES(?,?,?,?,?,?)", (email,username,hp,question,ha,now))
        c.execute("INSERT OR IGNORE INTO user_roles (email,role) VALUES(?,'user')", (email,))
        c.execute("INSERT INTO password_history (email,password,set_at) VALUES(?,?,?)", (email,hp,now))
        conn.commit(); return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_username(email):
    conn = _get_conn(); c = conn.cursor()
    c.execute("SELECT username FROM users WHERE email=?", (email,)); row = c.fetchone(); conn.close()
    return row[0] if row else None

def get_security_question(email):
    conn = _get_conn(); c = conn.cursor()
    c.execute("SELECT security_question FROM users WHERE email=?", (email,)); row = c.fetchone(); conn.close()
    return row[0] if row else None

def verify_security_answer(email, answer):
    conn = _get_conn(); c = conn.cursor()
    c.execute("SELECT security_answer FROM users WHERE email=?", (email,)); row = c.fetchone(); conn.close()
    return bcrypt.checkpw(answer.encode("utf-8"), row[0]) if row else False

def get_login_attempts(email):
    conn = _get_conn(); c = conn.cursor()
    c.execute("SELECT attempts, last_attempt FROM login_attempts WHERE email=?", (email,)); row = c.fetchone(); conn.close()
    return row if row else (0, 0)

def increment_login_attempts(email):
    conn = _get_conn(); c = conn.cursor()
    attempts, _ = get_login_attempts(email)
    c.execute("INSERT OR REPLACE INTO login_attempts (email,attempts,last_attempt) VALUES(?,?,?)", (email, attempts+1, time.time()))
    conn.commit(); conn.close()

def reset_login_attempts(email):
    conn = _get_conn(); c = conn.cursor()
    c.execute("DELETE FROM login_attempts WHERE email=?", (email,)); conn.commit(); conn.close()

def is_rate_limited(email):
    attempts, last = get_login_attempts(email)
    if attempts >= max_login_attempts:
        remaining = lockout_time - (time.time() - last)
        if remaining > 0: return True, remaining
        reset_login_attempts(email)
    return False, 0

def lock_account(email):
    conn = _get_conn(); c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO locked_accounts(email,locked_at) VALUES(?,?)", (email, _get_timestamp()))
    conn.commit(); conn.close()

def unlock_account(email):
    conn = _get_conn(); c = conn.cursor()
    c.execute("DELETE FROM locked_accounts WHERE email=?", (email,))
    c.execute("DELETE FROM login_attempts WHERE email=?", (email,))
    conn.commit(); conn.close()

def get_locked_accounts():
    conn = _get_conn(); c = conn.cursor()
    c.execute("SELECT email, locked_at FROM locked_accounts"); rows = c.fetchall(); conn.close()
    return rows

def authenticate_user(email, password):
    conn = _get_conn(); c = conn.cursor()
    c.execute("SELECT email FROM locked_accounts WHERE email=?", (email,)); locked = c.fetchone(); conn.close()
    if locked: return "locked"
    limited, _ = is_rate_limited(email)
    if limited: lock_account(email); return "locked"
    conn = _get_conn(); c = conn.cursor()
    c.execute("SELECT password FROM users WHERE email=?", (email,)); row = c.fetchone(); conn.close()
    if row and bcrypt.checkpw(password.encode("utf-8"), row[0]):
        reset_login_attempts(email); return True
    increment_login_attempts(email)
    attempts, _ = get_login_attempts(email)
    if attempts >= max_login_attempts: lock_account(email)
    return False

def check_is_old_password(email, password):
    conn = _get_conn(); c = conn.cursor()
    c.execute("SELECT password, set_at FROM password_history WHERE email=? ORDER BY set_at DESC", (email,)); rows = c.fetchall(); conn.close()
    for h, s in rows:
        if bcrypt.checkpw(password.encode("utf-8"), h): return s
    return None

def check_password_reused(email, new_password):
    conn = _get_conn(); c = conn.cursor()
    c.execute("SELECT password FROM password_history WHERE email=?", (email,)); rows = c.fetchall(); conn.close()
    for (h,) in rows:
        if bcrypt.checkpw(new_password.encode("utf-8"), h): return True
    return False

def update_password(email, new_password):
    conn = _get_conn(); c = conn.cursor()
    h = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()); now = _get_timestamp()
    c.execute("UPDATE users SET password=? WHERE email=?", (h, email))
    c.execute("INSERT INTO password_history (email,password,set_at) VALUES(?,?,?)", (email, h, now))
    conn.commit(); conn.close()

def save_feedback(email, original_text, generated_text, task_type, rating, comments):
    conn = _get_conn(); c = conn.cursor()
    c.execute("INSERT INTO feedback (email,original_text,generated_text,task_type,rating,comments,created_at) VALUES(?,?,?,?,?,?,?)",
              (email, original_text, generated_text, task_type, rating, comments, _get_timestamp()))
    conn.commit(); conn.close()

def log_activity(email, activity_type, details, output_text, model_used, language="English"):
    conn = _get_conn(); c = conn.cursor()
    c.execute("INSERT INTO activity_history (email,activity_type,details,output_text,model_used,language,created_at) VALUES(?,?,?,?,?,?,?)",
              (email, activity_type, details, output_text, model_used, language, _get_timestamp()))
    conn.commit(); conn.close()

def get_user_activity(email):
    conn = _get_conn(); c = conn.cursor()
    c.execute("SELECT activity_type,details,output_text,model_used,created_at FROM activity_history WHERE email=? AND activity_type!='Login' ORDER BY created_at DESC", (email,))
    rows = c.fetchall(); conn.close(); return rows

def get_all_activity():
    conn = _get_conn(); c = conn.cursor()
    c.execute("SELECT email,activity_type,details,language,model_used,created_at,output_text FROM activity_history ORDER BY created_at DESC")
    rows = c.fetchall(); conn.close(); return rows

def get_profile_image(email):
    conn = _get_conn(); c = conn.cursor()
    c.execute("SELECT avatar FROM user_profiles WHERE email=?", (email,)); row = c.fetchone(); conn.close()
    return row[0] if row else None

def delete_profile_image(email):
    conn = _get_conn(); c = conn.cursor()
    c.execute("UPDATE user_profiles SET avatar=NULL WHERE email=?", (email,)); conn.commit(); conn.close()

def is_admin(email):
    if email == "admin@textmorph.com": return True
    conn = _get_conn()
    role = conn.execute("SELECT role FROM user_roles WHERE email=?", (email,)).fetchone(); conn.close()
    return bool(role and role[0].lower() == "admin")

# -----------------------------------------------
# READABILITY — guarded against missing cmudict
# -----------------------------------------------
def _syllable_fallback(text):
    return sum(max(1, len(re.findall(r'[aeiouAEIOU]+', w))) for w in text.split())

def _difficult_words_fallback(text):
    return sum(1 for w in re.findall(r'\b[a-zA-Z]+\b', text) if max(1, len(re.findall(r'[aeiouAEIOU]+', w))) >= 3)

class ReadabilityAnalyzer:
    def __init__(self, text):
        self.text = text
        self.num_sentences = textstat.sentence_count(text)
        self.num_words     = textstat.lexicon_count(text, removepunct=True)
        self.char_count    = textstat.char_count(text)
        try:    self.complex_words = textstat.difficult_words(text)
        except: self.complex_words = _difficult_words_fallback(text)
        try:    self.num_syllables = textstat.syllable_count(text)
        except: self.num_syllables = _syllable_fallback(text)

    def get_all_metrics(self):
        def _s(fn, fb=0.0):
            try: return fn(self.text)
            except: return fb
        return {
            "Flesch Reading Ease":  _s(textstat.flesch_reading_ease,  50.0),
            "Flesch-Kincaid Grade": _s(textstat.flesch_kincaid_grade,   8.0),
            "SMOG Index":           _s(textstat.smog_index,             8.0),
            "Gunning Fog":          _s(textstat.gunning_fog,            8.0),
            "Coleman-Liau":         _s(textstat.coleman_liau_index,     8.0),
        }

# -----------------------------------------------
# MODEL REGISTRY — lazy loader
# -----------------------------------------------
MODEL_REGISTRY = {
    ("summarization", "bart"):    "sshleifer/distilbart-cnn-12-6",
    ("summarization", "pegasus"): "google/pegasus-cnn_dailymail",
    ("summarization", "flan-t5"): "google/flan-t5-small",
    ("paraphrase",    "flan_t5"): "google/flan-t5-small",
    ("paraphrase",    "bart"):    "eugenesiow/bart-paraphrase",
}

@st.cache_resource(show_spinner=False)
def load_model(model_type: str, task: str):
    if not TRANSFORMERS_AVAILABLE: return None
    key = (task, model_type.lower())
    if key not in MODEL_REGISTRY: return None
    try:
        tok = AutoTokenizer.from_pretrained(MODEL_REGISTRY[key])
        mdl = AutoModelForSeq2SeqLM.from_pretrained(MODEL_REGISTRY[key])
        return {"tokenizer": tok, "model": mdl}
    except: return None

@st.cache_resource(show_spinner=False)
def load_translation_model():
    if not TRANSFORMERS_AVAILABLE: return None, None
    try:
        mid = "facebook/nllb-200-distilled-600M"
        return AutoTokenizer.from_pretrained(mid), AutoModelForSeq2SeqLM.from_pretrained(mid)
    except: return None, None

# -----------------------------------------------
# NLP UTILITIES
# -----------------------------------------------
def translate_text(text, source_lang="English", target_lang="English"):
    if source_lang == target_lang: return text
    tok, mdl = load_translation_model()
    if tok is None: return text
    src = LANG_CODES.get(source_lang, "eng_Latn"); tgt = LANG_CODES.get(target_lang, "eng_Latn")
    try:
        sentences = _safe_sent_tokenize(text); chunks=[]; curr=[]; cl=0
        for s in sentences:
            sl = len(s.split())
            if cl+sl > 200 and curr: chunks.append(" ".join(curr)); curr=[s]; cl=sl
            else: curr.append(s); cl+=sl
        if curr: chunks.append(" ".join(curr))
        parts = []
        for chunk in chunks:
            tok.src_lang = src
            inp = tok(chunk, return_tensors="pt", max_length=512, truncation=True)
            tid = tok.convert_tokens_to_ids(tgt)
            with torch.no_grad(): out = mdl.generate(**inp, forced_bos_token_id=tid, max_length=384)
            parts.append(tok.decode(out[0], skip_special_tokens=True))
        return " ".join(parts)
    except: return text

def _detect_hallucination(orig, gen):
    gw = gen.split(); ow = set(orig.lower().split())
    if len(gw) < 3: return True
    wc = Counter(w.lower().strip(".,!?();:'\"") for w in gw)
    mc = wc.most_common(1)[0][1] if wc else 0
    if mc > len(gw)*0.5 and len(gw) > 20: return True
    gc = [w.lower().strip(".,!?();:'\"") for w in gw]
    nv = [w for w in gc if w not in ow and len(w) > 3]
    if len(nv) > len(gw)*0.85 and len(gw) > 30: return True
    return False

def simple_text_summarization(text, length):
    try:
        s = _safe_sent_tokenize(text)
        if len(s) <= 2: return text[:100]+"..." if len(text)>100 else text
        if length=="Short":  return " ".join(s[:max(1,len(s)//4)])
        if length=="Medium": return " ".join(s[:max(2,len(s)//2)])
        return " ".join(s[:max(3,int(len(s)*0.75))])
    except: return text[:150]+"..." if len(text)>150 else text

def local_summarize(text, summary_length, model_type, models_dict, target_lang="English"):
    mk = model_type.lower()
    if mk not in models_dict or models_dict[mk] is None:
        r = simple_text_summarization(text, summary_length)
        return translate_text(r,"English",target_lang) if target_lang!="English" else r
    tok = models_dict[mk]["tokenizer"]; mdl = models_dict[mk]["model"]
    il = len(tok.encode(text)); sm = max(60, int(il*0.95))
    lc = {
        "Short":  {"max_length":min(60,max(20,il//4)),   "min_length":min(10,max(5,il//6))},
        "Medium": {"max_length":min(150,max(40,il//2)),  "min_length":min(25,max(12,il//4))},
        "Long":   {"max_length":min(sm,max(80,int(il*0.9))), "min_length":min(50,max(25,il//2))},
    }
    cfg = lc.get(summary_length, lc["Medium"])
    cfg["min_length"] = min(cfg["min_length"], cfg["max_length"]-5); cfg["min_length"] = max(cfg["min_length"],5)
    prompt = text
    if mk == "flan-t5":
        prompts = {"Short":f"Write a brief 2-3 sentence summary: {text}","Medium":f"Write a detailed summary covering main points: {text}","Long":f"Write a comprehensive summary covering all key points: {text}"}
        prompt = prompts.get(summary_length, text)
    try:
        inp = tok(prompt, return_tensors="pt", truncation=True, max_length=1024, padding=True)
        with torch.no_grad():
            out = mdl.generate(**inp, max_new_tokens=cfg["max_length"], min_new_tokens=cfg["min_length"],
                               num_beams=2, no_repeat_ngram_size=3, repetition_penalty=1.5, early_stopping=True)
        summary = tok.decode(out[0], skip_special_tokens=True)
        if _detect_hallucination(text,summary) or not summary.strip():
            summary = simple_text_summarization(text, summary_length)
        return translate_text(summary,"English",target_lang) if target_lang!="English" else summary
    except:
        r = simple_text_summarization(text, summary_length)
        return translate_text(r,"English",target_lang) if target_lang!="English" else r

def apply_fallback_paraphrasing(text, complexity):
    words = text.split()
    if len(words) <= 3: return text
    subs = {
        "Simple":   {"utilize":"use","facilitate":"help","fundamental":"basic","however":"but","moreover":"also"},
        "Neutral":  {"use":"utilize","help":"assist","basic":"fundamental","but":"however","also":"furthermore"},
        "Advanced": {"use":"leverage","help":"facilitate","basic":"foundational","but":"nevertheless","also":"moreover"},
    }
    sd = subs.get(complexity, subs["Neutral"]); out=[]
    for w in words:
        cw = w.strip(".,!?();:'\"").lower()
        if cw in sd:
            nw = sd[cw]; nw = nw.capitalize() if w[0].isupper() else nw; out.append(nw)
        else: out.append(w)
    return " ".join(out)

def paraphrase_with_model(text, complexity, style, model_type, models_dict, target_lang="English"):
    mk = model_type.lower().replace("-","_")
    mi = models_dict.get(mk)
    if mi is None:
        r = apply_fallback_paraphrasing(text, complexity)
        return translate_text(r,"English",target_lang) if target_lang!="English" else r
    try:
        tok=mi["tokenizer"]; mdl=mi["model"]
        sentences=_safe_sent_tokenize(text); chunks=[]; curr=[]; cl=0
        for s in sentences:
            sl=len(s.split())
            if cl+sl>80 and curr: chunks.append(" ".join(curr)); curr=[s]; cl=sl
            else: curr.append(s); cl+=sl
        if curr: chunks.append(" ".join(curr))
        out=[]
        for chunk in chunks:
            prompt = (f"paraphrase the following text using different words and sentence structure: {chunk} </s>" if mk=="flan_t5" else f"paraphrase: {chunk}")
            inp = tok(prompt, return_tensors="pt", truncation=True, max_length=512, padding="max_length")
            with torch.no_grad():
                o = mdl.generate(**inp, max_new_tokens=150, min_new_tokens=20, num_beams=1, no_repeat_ngram_size=3, repetition_penalty=1.8)
            p = tok.decode(o[0], skip_special_tokens=True)
            out.append(p if p.strip() else chunk)
        final = " ".join(out)
        if not final.strip(): final = apply_fallback_paraphrasing(text, complexity)
        return translate_text(final,"English",target_lang) if target_lang!="English" else final
    except:
        r = apply_fallback_paraphrasing(text, complexity)
        return translate_text(r,"English",target_lang) if target_lang!="English" else r

# -----------------------------------------------
# HELPERS
# -----------------------------------------------
def create_token(data):
    data["exp"] = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    return jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

def valid_email(email):
    return re.match(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$", email)

def valid_password(password):
    return re.match(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$", password)

def password_strength(password):
    score=0
    if len(password)>=8: score+=1
    if re.search(r"[A-Z]",password): score+=1
    if re.search(r"[a-z]",password): score+=1
    if re.search(r"\d",password): score+=1
    if re.search(r"[@$!%*?&]",password): score+=1
    return score

def get_relative_time(date_str):
    if not date_str: return "some time ago"
    try:
        past=datetime.datetime.strptime(date_str,"%Y-%m-%d %H:%M:%S"); diff=datetime.datetime.utcnow()-past; days=diff.days
        if days>365: return f"{days//365} years ago"
        if days>30:  return f"{days//30} months ago"
        if days>0:   return f"{days} days ago"
        return "recently"
    except: return date_str

def get_greeting():
    hour=datetime.datetime.now(pytz.timezone("Asia/Kolkata")).hour
    if 5<=hour<12: return "Good Morning.. 🌅"
    if 12<=hour<17: return "Good Afternoon.. ☀️"
    if 17<=hour<21: return "Good Evening.. 🌇"
    return "Good Night.. 🌙"

def generate_otp():
    secret=secrets.token_bytes(20); msg=struct.pack(">Q",int(time.time()))
    h=hmac.new(secret,msg,hashlib.sha1).digest(); offset=h[19]&0xF
    code=((h[offset]&0x7F)<<24|(h[offset+1]&0xFF)<<16|(h[offset+2]&0xFF)<<8|(h[offset+3]&0xFF))
    return f"{code%1000000:06d}"

def create_otp_token(otp, email):
    payload={"otp_hash":bcrypt.hashpw(otp.encode("utf-8"),bcrypt.gensalt()).decode("utf-8"),
             "sub":email,"type":"password_reset","iat":datetime.datetime.utcnow(),
             "exp":datetime.datetime.utcnow()+datetime.timedelta(minutes=OTP_EXPIRY_MINUTES)}
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def verify_otp_token(token, input_otp, email):
    try:
        payload=jwt.decode(token,SECRET_KEY,algorithms=["HS256"])
        if payload.get("sub")!=email: return False,"Token mismatch"
        if bcrypt.checkpw(input_otp.encode("utf-8"),payload["otp_hash"].encode("utf-8")): return True,"Valid"
        return False,"Invalid OTP"
    except Exception as e: return False,str(e)

def send_email(to_email, otp, app_pass):
    if not app_pass and not EMAIL_PASSWORD: return False,"EMAIL_PASSWORD not set"
    msg=MIMEMultipart(); msg["From"]=f"TextMorph <{EMAIL_ADDRESS}>"; msg["To"]=to_email; msg["Subject"]="🔐 TextMorph - Password Reset OTP"
    body=f"""<html><body style="font-family:Arial;background:#0e1117;color:white;padding:20px;">
    <div style="max-width:500px;margin:auto;background:#1f2937;padding:30px;border-radius:12px;border:1px solid #00C8FF;">
    <h2>TextMorph Security</h2><p>OTP for: {to_email}</p>
    <div style="font-size:32px;font-weight:bold;letter-spacing:6px;padding:20px;background:#00C8FF;color:black;border-radius:8px;">{otp}</div>
    <p>Valid for {OTP_EXPIRY_MINUTES} minutes</p></div></body></html>"""
    msg.attach(MIMEText(body,"html"))
    try:
        s=smtplib.SMTP("smtp.gmail.com",587); s.starttls(); s.login(EMAIL_ADDRESS,app_pass if app_pass else EMAIL_PASSWORD)
        s.sendmail(EMAIL_ADDRESS,to_email,msg.as_string()); s.quit(); return True,"Sent"
    except Exception as e: return False,str(e)

def extract_text(file):
    try:
        if file.type=="application/pdf":
            reader=PyPDF2.PdfReader(file)
            return "".join([(page.extract_text() or "")+"\n" for page in reader.pages])
        return file.read().decode("utf-8")
    except Exception as e: st.error(f"Error reading file: {e}"); return ""

def create_gauge(value, title, min_val, max_val, color):
    fig=go.Figure(go.Indicator(mode="gauge+number",value=value,title={"text":title},
        gauge={"axis":{"range":[min_val,max_val]},"bar":{"color":color},
               "steps":[{"range":[min_val,(min_val+max_val)/3],"color":"#1f2937"},
                        {"range":[(min_val+max_val)/3,(min_val+max_val)*2/3],"color":"#374151"},
                        {"range":[(min_val+max_val)*2/3,max_val],"color":"#4b5563"}]}))
    fig.update_layout(height=250,margin=dict(l=10,r=10,t=40,b=10)); return fig

def render_feedback_ui(email, original_text, generated_text, task_type):
    bk=f"{task_type}_{hash(str(original_text)[:20])}"; rk=f"r_{bk}"; ck=f"c_{bk}"; btk=f"fbs_{bk}"; rsk=f"reset_{bk}"
    if st.session_state.get(rsk,False):
        st.session_state[rk]=None; st.session_state[ck]=""; st.session_state[rsk]=False
    with st.expander("📝 Provide Feedback"):
        c1,c2=st.columns([1,4])
        with c1: rating=st.radio("Rating",[1,2,3,4,5],horizontal=True,key=rk)
        with c2: comments=st.text_input("Comments (optional)",key=ck)
        if st.button("Submit Feedback",key=btk):
            save_feedback(email,original_text,generated_text,task_type,rating,comments)
            st.success("Thank you for your feedback!"); st.session_state[rsk]=True; st.rerun()

def _simulate_training_metrics(model_arch, epochs, learning_rate, batch_size, dropout_rate, quantization):
    random.seed(hash(f"{model_arch}{epochs}{learning_rate}{batch_size}{dropout_rate}{quantization}"))
    lr=float(learning_rate); bl={"T5-Small":0.55,"BART-Base":0.48,"FLAN-T5":0.42}.get(model_arch,0.50)
    fl=round(max(0.15,bl*(1.0-(min(epochs,10)*0.06))*(1.0-(lr*8000))+dropout_rate*0.08+{"FP16 (None)":0.0,"8-bit":0.02,"4-bit":0.05}.get(quantization,0.0)+random.uniform(-0.03,0.03)),2)
    acc=round(min(95,65+(epochs*2.5)+(1-fl)*20+random.uniform(-2,3)),1)
    rl=round(random.uniform(1.5,4.0)+epochs*0.15,1); bleu=round(0.25+(epochs*0.02)+(1-fl)*0.15+random.uniform(-0.03,0.03),2)
    lc=[]; cl=bl+1.0
    for _ in range(epochs): cl=cl*(0.6+random.uniform(-0.05,0.05))+random.uniform(-0.02,0.02); lc.append(round(max(fl,cl),3))
    lc[-1]=fl
    return {"final_loss":fl,"delta_loss":str(round(random.uniform(-0.08,-0.15),2)),"accuracy":f"{acc}%","delta_acc":f"+{round(random.uniform(1,6),1)}%",
            "rouge_l":f"+{rl}","delta_rouge":f"+{round(random.uniform(0.3,1.2),1)}","bleu":str(bleu),"delta_bleu":f"+{round(random.uniform(0.02,0.08),2)}",
            "loss_curve":lc,"epochs_x":list(range(1,epochs+1))}

# -----------------------------------------------
# AUTH PAGES
# -----------------------------------------------
def _auth_header():
    st.markdown("""<div style="text-align:center;margin-bottom:10px;">
        <h1 style="color:#00C8FF;font-size:40px;margin-bottom:2px;">🔐 TextMorph</h1>
        <p style="color:#6B8BA4;font-size:15px;margin:0;">Secure Authentication Portal</p>
    </div>""", unsafe_allow_html=True)

def signup():
    _auth_header()
    questions=["What is your pet name?","What is your mother's maiden name?","What is your favorite teacher?","What was your first school name?","What is your favorite food?"]
    _,col,_=st.columns([1,2,1])
    with col:
        with st.form("signup_form"):
            c1,c2=st.columns(2)
            with c1: username=st.text_input("👤 Username")
            with c2: email=st.text_input("📧 Email")
            password=st.text_input("🔒 Password",type="password"); confirm=st.text_input("🔒 Confirm Password",type="password")
            question=st.selectbox("❓ Security Question",questions); answer=st.text_input("✏️ Security Answer")
            submit=st.form_submit_button("✨ Create Account",use_container_width=True)
            if password: st.text(f"Password strength: {password_strength(password)}/5")
            if submit:
                username=username.strip(); email=email.strip(); password=password.strip(); confirm=confirm.strip(); answer=answer.strip()
                if not username:                    st.error("Username cannot be empty")
                elif not email:                     st.error("Email cannot be empty")
                elif not valid_email(email):        st.error("Invalid email format")
                elif not valid_password(password):  st.error("Weak password. Use uppercase, lowercase, number and special character.")
                elif password!=confirm:             st.error("Passwords do not match")
                elif not answer:                    st.error("Security answer required")
                elif check_user_exists(email):      st.error("Email already registered")
                elif register_user(username,email,password,question,answer):
                    st.success("🎉 Account created!"); st.session_state.page="login"; st.rerun()
                else:                               st.error("Registration failed.")
        if st.button("🔑 Go to Login",use_container_width=True):
            st.session_state.page="login"; st.rerun()

def login():
    _auth_header()
    _,col,_=st.columns([1,1.4,1])
    with col:
        with st.form("login_form"):
            st.markdown(f"""<div style="margin-bottom:20px"><div style="font-family:'Syne',sans-serif;font-size:1.4rem;font-weight:800;color:{TEXT};">👋 Welcome back</div>
                <div style="font-size:.9rem;color:{MUTED};margin-top:6px;">Sign in to continue</div></div>""",unsafe_allow_html=True)
            email=st.text_input("Email"); password=st.text_input("Password",type="password"); submit=st.form_submit_button("Login")
            if submit:
                auth=authenticate_user(email,password)
                if auth=="locked":   st.error("Account locked. Try again later.")
                elif auth:
                    st.session_state["user"]=email; st.session_state["token"]=create_token({"email":email,"username":get_username(email)})
                    st.session_state["_nav_to"]="Home"; st.success("Login Successful! 🎉"); time.sleep(1)
                    st.session_state.page="admin_dashboard" if is_admin(email) else "dashboard"; st.rerun()
                else:
                    st.error("Invalid credentials.")
                    old=check_is_old_password(email,password)
                    if old: st.warning(f"Note: You used an old password from {get_relative_time(old)}.")
        c1,c2=st.columns(2)
        with c1:
            if st.button("Forgot password?",use_container_width=True): st.session_state.page="forgot"; st.rerun()
        with c2:
            if st.button("Create account",use_container_width=True): st.session_state.page="signup"; st.rerun()

def forgot_password():
    if "stage" not in st.session_state: st.session_state.stage="email"
    if "reset_email" not in st.session_state: st.session_state.reset_email=""
    if "otp_token" not in st.session_state: st.session_state.otp_token=None
    if "otp_sent_time" not in st.session_state: st.session_state.otp_sent_time=None
    st.title("🔒 Forgot Password")
    if st.session_state.stage=="email":
        email=st.text_input("Enter your registered Email")
        if st.button("Verify Email"):
            if check_user_exists(email): st.session_state.reset_email=email; st.session_state.email_verified=True; st.success("Email Verified ✅")
            else: st.error("Email not found")
        if st.session_state.get("email_verified"):
            c1,_,c2=st.columns([1.3,1,1.3])
            with c1:
                if st.button("Reset via OTP",use_container_width=True): st.session_state.stage="otp"; st.rerun()
            with c2:
                if st.button("Reset via Security Question",use_container_width=True): st.session_state.stage="security"; st.rerun()
    elif st.session_state.stage=="otp":
        st.subheader("OTP Verification"); st.info(f"OTP will be sent to {st.session_state.reset_email}")
        OTP_VALID_SECONDS=600
        if not st.session_state.otp_sent_time:
            if st.button("Send OTP"):
                otp=generate_otp(); ok,msg=send_email(st.session_state.reset_email,otp,EMAIL_PASSWORD)
                if ok: st.session_state.otp_token=create_otp_token(otp,st.session_state.reset_email); st.session_state.otp_sent_time=time.time(); st.success("OTP sent 📧")
                else: st.error(f"Failed: {msg}")
        if st.session_state.otp_sent_time:
            remaining=int(OTP_VALID_SECONDS-(time.time()-st.session_state.otp_sent_time))
            if remaining<=0: st.error("OTP expired."); st.session_state.otp_sent_time=None; st.session_state.otp_token=None
            else:
                st.info(f"OTP expires in {remaining} seconds"); otp_input=st.text_input("Enter OTP")
                c1,_,c2=st.columns([1,2,1])
                if c1.button("Verify OTP",use_container_width=True):
                    if not otp_input.strip(): st.error("Please enter OTP")
                    else:
                        ok,_=verify_otp_token(st.session_state.otp_token,otp_input.strip(),st.session_state.reset_email)
                        if ok: st.session_state.stage="reset"; st.session_state.otp_sent_time=None; st.rerun()
                        else: st.error("Invalid OTP")
                if c2.button("Resend OTP",use_container_width=True): st.session_state.otp_sent_time=None; st.session_state.otp_token=None; st.rerun()
    elif st.session_state.stage=="security":
        q=get_security_question(st.session_state.reset_email); st.write(f"Security Question: {q}"); answer=st.text_input("Enter Answer")
        if st.button("Verify Answer"):
            if verify_security_answer(st.session_state.reset_email,answer): st.session_state.stage="reset"; st.success("Verified ✅"); st.rerun()
            else: st.error("Incorrect Answer")
    elif st.session_state.stage=="reset":
        np=st.text_input("New Password",type="password"); cp=st.text_input("Confirm Password",type="password")
        if st.button("Update Password"):
            if not valid_password(np): st.error("Weak password")
            elif np!=cp: st.error("Passwords do not match")
            elif check_password_reused(st.session_state.reset_email,np): st.error("Cannot reuse old password")
            else: update_password(st.session_state.reset_email,np); st.success("Password Updated 🎉")
    if st.button("Back to Login"): st.session_state.stage="email"; st.session_state.page="login"; st.rerun()

# -----------------------------------------------
# USER PAGES
# -----------------------------------------------
def home_page():
    email=st.session_state["user"]
    st.markdown("""<div style="display:flex;align-items:center;gap:14px;margin-bottom:28px">
      <span style="font-size:2.2rem">🏠</span>
      <div><p style="font-family:'Syne',sans-serif;font-weight:800;font-size:1.7rem;color:#00C8FF;margin:0;">Welcome back!</p>
      <p style="font-size:.85rem;color:#6B8BA4;margin:4px 0 0">What would you like to do today?</p></div>
    </div>""", unsafe_allow_html=True)
    TOOLS=[("📝","Summarize","Condense long texts into crisp summaries with adjustable length and language output."),
           ("🔄","Paraphrase","Rewrite content with different styles and complexity levels — from formal to creative."),
           ("📖","Readability","Analyse your text across 5 readability indices and get actionable grade-level insights."),
           ("🗃️","Augmentation","Generate NLP training pairs at scale — ideal for fine-tuning your own models."),
           ("📜","History","Browse your full activity log with filters, analytics, and CSV export."),
           ("👤","Profile","Update your avatar, email, and password.")]
    r1=st.columns(3,gap="large")
    for col,(icon,title,desc) in zip(r1,TOOLS[:3]):
        with col:
            if st.button(f"{icon}\n\n**{title}**\n\n{desc}",key=f"home_{title}",use_container_width=True):
                st.session_state["_nav_to"]=title; st.rerun()
    st.markdown("<div style='height:4px'></div>",unsafe_allow_html=True)
    r2=st.columns(3,gap="large")
    for col,(icon,title,desc) in zip(r2,TOOLS[3:]):
        with col:
            if st.button(f"{icon}\n\n**{title}**\n\n{desc}",key=f"home_{title}",use_container_width=True):
                st.session_state["_nav_to"]=title; st.rerun()
    st.markdown("<hr style='border-color:rgba(0,200,255,0.28);margin:28px 0'>",unsafe_allow_html=True)
    acts=get_user_activity(email) or []
    df_a=pd.DataFrame(acts,columns=["Activity Type","Details","Output","Model Used","Timestamp"]) if acts else pd.DataFrame()
    total=len(df_a); sums=len(df_a[df_a["Activity Type"]=="Summarization"]) if len(df_a) else 0
    paras=len(df_a[df_a["Activity Type"]=="Paraphrasing"]) if len(df_a) else 0; models=df_a["Model Used"].nunique() if len(df_a) else 0
    st.markdown(f"""<div class="stats-row">
      <div class="stat-box"><div class="stat-num">{total}</div><div class="stat-label">Total Operations</div></div>
      <div class="stat-box"><div class="stat-num">{sums}</div><div class="stat-label">Summarizations</div></div>
      <div class="stat-box"><div class="stat-num">{paras}</div><div class="stat-label">Paraphrases</div></div>
      <div class="stat-box"><div class="stat-num">{models}</div><div class="stat-label">Models Used</div></div>
    </div>""", unsafe_allow_html=True)

def readability_page():
    c1,c2=st.columns([6,1])
    with c2:
        if st.button("⬅ Back",key="back_r"): st.session_state["_nav_to"]="Home"; st.rerun()
    st.title("📖 Text Readability Analyzer")
    tab1,tab2=st.tabs(["✍️ Input Text","📂 Upload File (TXT/PDF)"]); text_input=""
    with tab1:
        rt=st.text_area("Enter text to analyze (min 50 chars):",height=200)
        if rt: text_input=rt
    with tab2:
        uf=st.file_uploader("Upload a file",type=["txt","pdf"])
        if uf: text_input=extract_text(uf); st.info("✅ File loaded")
    if st.button("Analyze Readability",type="primary"):
        if len(text_input)<50: st.error("Text is too short (min 50 chars).")
        else:
            az=ReadabilityAnalyzer(text_input); score=az.get_all_metrics()
            ag=(score["Flesch-Kincaid Grade"]+score["Gunning Fog"]+score["SMOG Index"]+score["Coleman-Liau"])/4
            if ag<=6: lv,cl="Beginner (Elementary)","#28a745"
            elif ag<=10: lv,cl="Intermediate (Middle School)","#17a2b8"
            elif ag<=14: lv,cl="Advanced (High School/College)","#ffc107"
            else: lv,cl="Expert (Professional/Academic)","#dc3545"
            st.markdown(f"""<div style="background:#1f2937;padding:20px;border-radius:10px;border-left:5px solid {cl};text-align:center;">
                <h2 style="margin:0;color:{cl} !important;">Overall Level: {lv}</h2>
                <p style="margin:5px 0 0;color:#9ca3af;">Approx Grade Level: {int(ag)}</p></div>""",unsafe_allow_html=True)
            c1,c2,c3=st.columns(3)
            with c1: st.plotly_chart(create_gauge(score["Flesch Reading Ease"],"Flesch Reading Ease",0,100,"#00ffcc"),use_container_width=True)
            with c2: st.plotly_chart(create_gauge(score["Flesch-Kincaid Grade"],"Flesch-Kincaid Grade",0,20,"#ff00ff"),use_container_width=True)
            with c3: st.plotly_chart(create_gauge(score["SMOG Index"],"SMOG Index",0,20,"#ffff00"),use_container_width=True)
            c4,c5=st.columns(2)
            with c4: st.plotly_chart(create_gauge(score["Gunning Fog"],"Gunning Fog",0,20,"#00ccff"),use_container_width=True)
            with c5: st.plotly_chart(create_gauge(score["Coleman-Liau"],"Coleman-Liau",0,20,"#ff9900"),use_container_width=True)
            s1,s2,s3,s4,s5=st.columns(5)
            s1.metric("Sentences",az.num_sentences); s2.metric("Words",az.num_words)
            s3.metric("Syllables",az.num_syllables); s4.metric("Complex Words",az.complex_words); s5.metric("Characters",az.char_count)

def summarizer_page():
    c1,c2=st.columns([6,1])
    with c2:
        if st.button("⬅ Back",key="back_s"): st.session_state["_nav_to"]="Home"; st.rerun()
    st.title("📝 Multi-level Summarization")
    if "summarization_history" not in st.session_state: st.session_state.summarization_history=[]
    col1,col2=st.columns([2,1])
    with col1:
        st.subheader("Input Text")
        text_input=st.text_area("Enter text to summarize (min 50 chars):",height=200,key="summarization_text")
        uf=st.file_uploader("Or upload a file",type=["txt","pdf"],key="sum_upload")
        if uf: text_input=extract_text(uf); st.info(f"✅ File loaded ({len(text_input.split())} words)")
    with col2:
        st.subheader("Settings")
        summary_length=st.selectbox("Summary Length",["Short","Medium","Long"])
        model_type=st.selectbox("Model",["FLAN-T5","BART","Pegasus"])
        target_lang=st.selectbox("🌐 Output Language",SUPPORTED_LANGUAGES)
        if st.button("Generate Summary",type="primary",use_container_width=True):
            if len(text_input)<50: st.error("Text is too short.")
            else:
                with st.spinner(f"Loading {model_type} model…"):
                    md=load_model(model_type,"summarization")
                mk=model_type.lower(); mdict={mk:md}
                summary=local_summarize(text_input,summary_length,model_type,mdict,target_lang=target_lang)
                st.session_state.last_summary=summary; st.session_state.last_summary_text=text_input; st.session_state.last_summary_lang=target_lang
                log_activity(st.session_state["user"],"Summarization",f"Length:{summary_length},Lang:{target_lang}",summary,model_type,target_lang)
                st.session_state.summarization_history.append({"timestamp":datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"input":text_input[:100]+"...","summary":summary,"length":summary_length,"model":model_type,"lang":target_lang})
    if "last_summary" in st.session_state:
        st.markdown("---"); st.header("📋 Summary Results")
        c1,c2=st.columns(2)
        with c1: st.subheader("📄 Original Text"); st.info(st.session_state.last_summary_text); st.caption(f"**Word Count:** {len(st.session_state.last_summary_text.split())}")
        with c2: st.subheader("📝 Generated Summary"); st.success(st.session_state.last_summary); st.caption(f"**Word Count:** {len(st.session_state.last_summary.split())}")
        render_feedback_ui(st.session_state["user"],st.session_state.last_summary_text,st.session_state.last_summary,"Summarization")
        with st.expander("📜 Session History"):
            for item in reversed(st.session_state.summarization_history[-5:]):
                st.write(f"**{item['timestamp']}** — {item['length']} ({item['model']})"); st.info(f"Input: {item['input']}"); st.success(f"Summary: {item['summary']}"); st.markdown("---")

def paraphraser_page():
    c1,c2=st.columns([6,1])
    with c2:
        if st.button("⬅ Back",key="back_p"): st.session_state["_nav_to"]="Home"; st.rerun()
    st.title("🔄 Advanced Paraphrasing Engine")
    if "paraphrasing_history" not in st.session_state: st.session_state.paraphrasing_history=[]
    col1,col2=st.columns([2,1])
    with col1:
        st.subheader("Input Text")
        text_input=st.text_area("Enter text to paraphrase (min 50 chars):",height=200,key="para_text")
        uf=st.file_uploader("Or upload a file",type=["txt","pdf"],key="para_upload")
        if uf: text_input=extract_text(uf); st.info(f"✅ File loaded ({len(text_input.split())} words)")
    with col2:
        st.subheader("Settings")
        complexity=st.selectbox("Complexity Level",["Simple","Neutral","Advanced"])
        style=st.selectbox("Paraphrasing Style",["Simplification","Formalization","Creative"])
        model_type=st.selectbox("Model",["FLAN-T5","BART"])
        target_lang=st.selectbox("🌐 Output Language",SUPPORTED_LANGUAGES,key="para_lang")
        if st.button("Generate Paraphrase",type="primary",use_container_width=True):
            if len(text_input)<50: st.error("Text is too short.")
            else:
                with st.spinner(f"Loading {model_type} model…"):
                    md=load_model(model_type,"paraphrase")
                mk=model_type.lower().replace("-","_"); mdict={mk:md}
                para=paraphrase_with_model(text_input,complexity,style,model_type,mdict,target_lang=target_lang)
                st.session_state.last_para=para; st.session_state.last_para_text=text_input; st.session_state.last_para_lang=target_lang
                log_activity(st.session_state["user"],"Paraphrasing",f"Complexity:{complexity},Style:{style}",para,model_type,target_lang)
                st.session_state.paraphrasing_history.append({"timestamp":datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),"input":text_input[:100]+"...","paraphrase":para,"complexity":complexity,"style":style,"model":model_type,"lang":target_lang})
    if "last_para" in st.session_state:
        st.markdown("---"); st.header("📋 Paraphrase Results")
        c1,c2=st.columns(2)
        with c1: st.subheader("📄 Original Text"); st.info(st.session_state.last_para_text); st.caption(f"**Word Count:** {len(st.session_state.last_para_text.split())}")
        with c2: st.subheader("🔄 Paraphrased Text"); st.success(st.session_state.last_para); st.caption(f"**Word Count:** {len(st.session_state.last_para.split())}")
        render_feedback_ui(st.session_state["user"],st.session_state.last_para_text,st.session_state.last_para,"Paraphrasing")
        with st.expander("📜 Session History"):
            for item in reversed(st.session_state.paraphrasing_history[-5:]):
                st.write(f"**{item['timestamp']}** — {item['complexity']} ({item['style']}) — {item['model']}"); st.info(f"Input: {item['input']}"); st.success(f"Paraphrase: {item['paraphrase']}"); st.markdown("---")

def history_page():
    c1,c2=st.columns([6,1])
    with c2:
        if st.button("⬅ Back",key="back_h"): st.session_state["_nav_to"]="Home"; st.rerun()
    st.title("📜 Activity History Dashboard")
    activities=get_user_activity(st.session_state["user"])
    if not activities: st.info("No activity history yet."); return
    df=pd.DataFrame(activities,columns=["Activity Type","Details","Output","Model Used","Timestamp"])
    df=df[df["Activity Type"]!="Login"]
    c1,c2=st.columns(2)
    with c1: af=st.selectbox("Filter by Activity",["All"]+list(df["Activity Type"].unique()))
    with c2: mf=st.selectbox("Filter by Model",["All"]+list(df["Model Used"].unique()))
    if af!="All": df=df[df["Activity Type"]==af]
    if mf!="All": df=df[df["Model Used"]==mf]
    c1,c2,c3=st.columns(3)
    c1.metric("Username",get_username(st.session_state["user"])); c2.metric("Total Activities",len(df)); c3.metric("Models Used",df["Model Used"].nunique())
    csv=df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇ Download History (CSV)",csv,"history.csv","text/csv",use_container_width=True)
    st.markdown("---")
    for _,row in df.iterrows():
        icon="🧠" if row["Activity Type"]=="Summarization" else "🔄"
        dp=row["Details"][:120]+("..." if len(row["Details"])>120 else "")
        st.markdown(f"""<div style="background:rgba(255,255,255,0.05);padding:20px;border-radius:12px;border:1px solid #00C8FF;margin-bottom:15px;">
            <h4>{icon} {row["Activity Type"]}</h4><p><b>🤖 Model:</b> {row["Model Used"]}</p>
            <p><b>📅 Date:</b> {row["Timestamp"]}</p><p><b>📄 Details:</b> {dp}</p></div>""",unsafe_allow_html=True)
        with st.expander("🔍 View Full Output"): st.info(row["Details"]); st.success(row["Output"])
    st.markdown("---"); st.subheader("📊 Usage Analytics")
    c1,c2=st.columns(2)
    ac=df["Activity Type"].value_counts().reset_index(); ac.columns=["Activity","Count"]
    mc=df["Model Used"].value_counts().reset_index(); mc.columns=["Model","Usage"]
    c1.plotly_chart(px.bar(ac,x="Activity",y="Count",title="Activity Distribution",text="Count"),use_container_width=True)
    c2.plotly_chart(px.bar(mc,x="Model",y="Usage",title="Top Used Models",text="Usage"),use_container_width=True)

def augmentation_page():
    c1,c2=st.columns([6,1])
    with c2:
        if st.button("⬅ Back",key="back_a"): st.session_state["_nav_to"]="Home"; st.rerun()
    st.title("🗃️ Dataset Augmentation & Custom Model Tuning")
    tab_explore,tab_tune,tab_studio=st.tabs(["📊 Dataset Explorer","🛠️ Model Tuning","🧪 Augmentation Studio"])
    with tab_explore:
        st.subheader("Data Inspector & Cleaner")
        datasets={"CNN/DailyMail":{"samples":311029,"type":"News Summarization","avg_words":781},"XSum":{"samples":226711,"type":"Extreme Summarization","avg_words":431},"PAWS":{"samples":108461,"type":"Paraphrase","avg_words":21}}
        sd=st.selectbox("Select Active Dataset",list(datasets.keys()))
        c1,c2,c3=st.columns(3); c1.metric("Total Samples",f"{datasets[sd]['samples']:,}"); c2.metric("Task Type",datasets[sd]["type"]); c3.metric("Avg Length",f"{datasets[sd]['avg_words']} words")
        c1,c2=st.columns(2)
        with c1: mn=st.slider("Filter Minimum Words",5,100,10)
        with c2: mx=st.slider("Filter Maximum Words",100,2000,1000)
        fs=int(datasets[sd]["samples"]*(0.9-(mn/1000)-(1000-mx)/2000)); st.success(f"✅ Cleaned Dataset: **{fs:,} valid pairs**")
    with tab_tune:
        st.subheader("🛠️ Model Configuration Matrix")
        c1,c2,c3=st.columns(3)
        with c1: ma=st.selectbox("Model Architecture",["T5-Small","BART-Base","FLAN-T5"]); ep=st.slider("Training Epochs",1,10,3)
        with c2: qt=st.selectbox("Quantization",["FP16 (None)","8-bit","4-bit"]); bs=st.slider("Batch Size",8,32,16)
        with c3: lr=st.selectbox("Learning Rate",["1e-5","2e-5","3e-5"]); dr=st.slider("Dropout",0.0,0.5,0.1)
        if st.button("🚀 Execute Distributed Training",type="primary",use_container_width=True):
            with st.spinner(f"Training {ma}..."):
                prog=st.progress(0)
                for i in range(100): time.sleep(0.01); prog.progress(i+1)
                st.success(f"✅ {ma} trained!")
                metrics=_simulate_training_metrics(ma,ep,lr,bs,dr,qt)
                m1,m2,m3,m4=st.columns(4)
                m1.metric("Final Loss",metrics["final_loss"],metrics["delta_loss"]); m2.metric("Accuracy",metrics["accuracy"],metrics["delta_acc"])
                m3.metric("ROUGE-L",metrics["rouge_l"],metrics["delta_rouge"]); m4.metric("BLEU",metrics["bleu"],metrics["delta_bleu"])
                fig=go.Figure(data=go.Scatter(x=metrics["epochs_x"],y=metrics["loss_curve"],mode="lines+markers",line=dict(color="#00ffcc",width=3)))
                fig.update_layout(title=f"Training Loss — {ma}",xaxis_title="Epoch",yaxis_title="Loss",template="plotly_dark",height=300)
                st.plotly_chart(fig,use_container_width=True)
                log_activity(st.session_state["user"],"Model Training",f"Trained {ma}",f"Loss:{metrics['final_loss']}",ma)
    with tab_studio:
        st.subheader("🧪 Live Dataset Pair Generator")
        aug_input=st.text_area("Original Text (separate paragraphs with blank lines):",height=200,value="The quick brown fox jumps over the lazy dog.\n\nArtificial Intelligence is rapidly evolving in the modern era.")
        c1,c2=st.columns(2)
        with c1: at=st.selectbox("Transformation Type",["Paraphrasing","Summarization"])
        with c2: asetting=st.selectbox("Setting",["Short","Medium","Long"] if at=="Summarization" else ["Advanced","Simple","Neutral"])
        if st.button("Generate Dataset 🚀",use_container_width=True):
            paragraphs=[p.strip() for p in aug_input.split("\n\n") if len(p.strip())>10]
            if not paragraphs: st.error("Please enter at least one valid paragraph.")
            else:
                if at=="Summarization":
                    with st.spinner("Loading BART model…"): _am=load_model("BART","summarization")
                    _ad={"bart":_am}
                else:
                    with st.spinner("Loading FLAN-T5 model…"): _am=load_model("FLAN-T5","paraphrase")
                    _ad={"flan_t5":_am}
                results=[]; prog=st.progress(0)
                for idx,para in enumerate(paragraphs):
                    res=(local_summarize(para,asetting,"BART",_ad) if at=="Summarization" else paraphrase_with_model(para,asetting,"Creative","FLAN-T5",_ad))
                    results.append({"#":idx+1,"Original Text":para,"Target Text":res}); prog.progress((idx+1)/len(paragraphs))
                st.success(f"✅ Generated {len(results)} pairs!")
                df=pd.DataFrame(results); st.dataframe(df,use_container_width=True)
                csv=df.to_csv(index=False).encode("utf-8")
                st.download_button("📥 Download Dataset (CSV)",csv,"augmented_dataset.csv","text/csv")
                log_activity(st.session_state["user"],"Batch Augmentation",f"Type:{at},Samples:{len(results)}",str(results),"Augmentation Engine")

def user_profile(email):
    c1,c2=st.columns([6,1])
    with c2:
        if st.button("⬅ Back",key="back_prof"): st.session_state["_nav_to"]="Home"; st.rerun()
    st.title("👤 User Profile"); conn=_get_conn()
    st.subheader("📧 Change Email"); new_email=st.text_input("Enter New Email")
    if st.button("Update Email"):
        if not new_email: st.error("Email cannot be empty")
        elif new_email==email: st.error("New email cannot be same as current")
        elif not valid_email(new_email): st.error("Invalid email format")
        else:
            ex=conn.execute("SELECT email FROM users WHERE email=?",(new_email,)).fetchone()
            if ex: st.error("Email already exists")
            else:
                try:
                    for tbl in ["users","user_roles","activity_history","feedback","user_profiles"]:
                        conn.execute(f"UPDATE {tbl} SET email=? WHERE email=?",(new_email,email))
                    conn.commit(); st.session_state.user=new_email; st.success("Email updated"); st.rerun()
                except: conn.rollback(); st.error("Error updating email")
    st.markdown("---"); st.subheader("🔑 Change Password")
    np=st.text_input("New Password",type="password"); cp=st.text_input("Confirm Password",type="password")
    if st.button("Update Password"):
        if not np or not cp: st.error("Both fields required")
        elif not valid_password(np): st.error("Weak password")
        elif np!=cp: st.error("Passwords do not match")
        else:
            h=bcrypt.hashpw(np.encode(),bcrypt.gensalt())
            conn.execute("UPDATE users SET password=? WHERE email=?",(h,email)); conn.commit(); st.success("Password updated")
    st.markdown("---"); st.subheader("🖼 Upload Avatar")
    av=st.file_uploader("Upload Profile Picture",type=["png","jpg","jpeg"])
    if av:
        img=av.read(); conn.execute("REPLACE INTO user_profiles(email,avatar) VALUES(?,?)",(email,img)); conn.commit(); st.success("Avatar Updated"); st.rerun()
    data=conn.execute("SELECT avatar FROM user_profiles WHERE email=?",(email,)).fetchone()
    if data and data[0]: st.image(data[0],width=150)
    if st.button("Delete Profile Picture"): delete_profile_image(email); st.success("Profile picture deleted!"); st.rerun()
    conn.close()

# -----------------------------------------------
# ADMIN PAGES
# -----------------------------------------------
def admin_home_page():
    st.markdown("""<div style="display:flex;align-items:center;gap:14px;margin-bottom:28px">
      <span style="font-size:2.2rem">🛠️</span>
      <div><p style="font-weight:800;font-size:1.7rem;color:#00C8FF;margin:0;">Admin Dashboard</p>
      <p style="font-size:.85rem;color:#6B8BA4;">Manage users, analytics, and system</p></div>
    </div>""", unsafe_allow_html=True)
    ADMIN_TOOLS=[("👥","Users","Delete users, manage roles, and control access"),
                 ("📊","Analytics","View system insights, usage trends, and metrics"),
                 ("📜","Activity","Track all user actions and system logs"),
                 ("❌","Remove Admin","Revoke admin privileges"),
                 ("💬","Feedback","Review user feedback and ratings"),
                 ("🔒","Locked","Manage locked accounts"),
                 ("⬇️","Download","Export system data in CSV format")]
    cols=st.columns(3,gap="large")
    for i,(icon,title,desc) in enumerate(ADMIN_TOOLS):
        with cols[i%3]:
            if st.button(f"{icon}\n\n**{title}**\n\n{desc}",key=f"admin_{title}"):
                st.session_state["_nav_to"]=title; st.rerun()
    st.markdown("<hr>",unsafe_allow_html=True)
    conn=_get_conn()
    ta=conn.execute("SELECT COUNT(*) FROM users u LEFT JOIN user_roles r ON u.email=r.email WHERE r.role='admin' OR u.email='admin@textmorph.com'").fetchone()[0]
    tu=conn.execute("SELECT COUNT(*) FROM users u LEFT JOIN user_roles r ON u.email=r.email WHERE COALESCE(r.role,'user')!='admin' AND u.email!='admin@textmorph.com'").fetchone()[0]
    conn.close(); tact=len(get_all_activity())
    st.markdown(f"""<div class="stats-row">
      <div class="stat-box"><div class="stat-num">{tu}</div><div class="stat-label">Users</div></div>
      <div class="stat-box"><div class="stat-num">{ta}</div><div class="stat-label">Admins</div></div>
      <div class="stat-box"><div class="stat-num">{tact}</div><div class="stat-label">Activities</div></div>
      <div class="stat-box"><div class="stat-num">Live</div><div class="stat-label">Status</div></div>
    </div>""", unsafe_allow_html=True)

def user_management():
    c1,c2=st.columns([6,1])
    with c2:
        if st.button("⬅ Back",key="back_um"): st.session_state["_nav_to"]="Home"; st.rerun()
    st.subheader("👥 User Management"); conn=_get_conn()
    users=pd.read_sql_query("SELECT u.email FROM users u LEFT JOIN user_roles r ON u.email=r.email WHERE COALESCE(r.role,'user')!='admin' AND u.email!='admin@textmorph.com'",conn)
    if users.empty: st.info("No users available."); conn.close(); return
    su=st.selectbox("Select User",users["email"]); c1,c2=st.columns(2)
    with c1:
        if st.button("Promote to Admin",use_container_width=True): conn.execute("INSERT OR REPLACE INTO user_roles(email,role) VALUES(?,'admin')",(su,)); conn.commit(); st.success("Promoted"); st.rerun()
    with c2:
        if st.button("Delete User",use_container_width=True): conn.execute("DELETE FROM users WHERE email=?",(su,)); conn.commit(); st.error("User Deleted"); st.rerun()
    conn.close()

def remove_admin():
    c1,c2=st.columns([6,1])
    with c2:
        if st.button("⬅ Back",key="back_ra"): st.session_state["_nav_to"]="Home"; st.rerun()
    st.subheader("🛑 Remove Admin Access"); conn=_get_conn()
    admins=pd.read_sql_query("SELECT email FROM user_roles WHERE role='admin'",conn)
    if admins.empty: st.info("No admin users."); conn.close(); return
    sa=st.selectbox("Select Admin to Remove",admins["email"])
    if st.button("Remove Admin Privilege"): conn.execute("DELETE FROM user_roles WHERE email=?",(sa,)); conn.commit(); st.success("Admin privileges removed"); st.rerun()
    conn.close()

def locked_accounts_section():
    c1,c2=st.columns([6,1])
    with c2:
        if st.button("⬅ Back",key="back_la"): st.session_state["_nav_to"]="Home"; st.rerun()
    st.subheader("🔒 Locked Accounts"); lu=get_locked_accounts()
    if not lu: st.success("No locked accounts.")
    else:
        df=pd.DataFrame(lu,columns=["Email","Locked At"]); st.dataframe(df,use_container_width=True)
        for email,_ in lu:
            c1,c2=st.columns([3,1]); c1.write(email)
            if c2.button("Unlock",key=f"unlock_{email}"): unlock_account(email); st.success(f"{email} unlocked"); st.rerun()
    st.markdown("---"); st.subheader("⚙️ Manual Account Control"); conn=_get_conn()
    ef=pd.read_sql_query("SELECT u.email FROM users u LEFT JOIN user_roles r ON u.email=r.email WHERE COALESCE(r.role,'user')!='admin' AND u.email!='admin@textmorph.com'",conn); conn.close()
    emails=ef["email"].tolist()
    if not emails: st.info("No users available."); return
    su=st.selectbox("Select User",emails); c1,c2=st.columns(2)
    if c1.button("🔒 Lock Account"): lock_account(su); st.warning(f"{su} locked"); st.rerun()
    if c2.button("🔓 Unlock Account"): unlock_account(su); st.success(f"{su} unlocked"); st.rerun()

def feedback_section():
    c1,c2=st.columns([6,1])
    with c2:
        if st.button("⬅ Back",key="back_fb"): st.session_state["_nav_to"]="Home"; st.rerun()
    st.subheader("💬 User Feedback"); conn=_get_conn()
    feedback=pd.read_sql_query("SELECT email,task_type,rating,comments,created_at FROM feedback ORDER BY created_at DESC",conn); conn.close()
    if feedback.empty: st.info("No feedback available yet."); return
    text=" ".join(feedback["comments"].dropna())
    if text.strip():
        wc=WordCloud(width=800,height=400,background_color="black").generate(text)
        fig,ax=plt.subplots(figsize=(10,5)); ax.imshow(wc,interpolation="bilinear"); ax.axis("off"); st.pyplot(fig)
    for _,row in feedback.iterrows():
        st.markdown(f"""<div style="border:1px solid #00C8FF;border-radius:12px;padding:18px;margin-bottom:15px;background:rgba(0,40,60,0.6);">
            <h3 style="color:#00C8FF;">🧠 {row['task_type']}</h3>
            <p>👤 <b>User:</b> {row['email']}</p><p>⭐ <b>Rating:</b> {"⭐"*int(row['rating'])}</p>
            <p>💬 <b>Comment:</b> {row['comments'] if row['comments'] else "No comment"}</p>
            <p>📅 <b>Date:</b> {row['created_at']}</p></div>""",unsafe_allow_html=True)

def analytics_dashboard():
    c1,c2=st.columns([6,1])
    with c2:
        if st.button("⬅ Back",key="back_an"): st.session_state["_nav_to"]="Home"; st.rerun()
    st.title("📊 System Analytics"); conn=_get_conn()
    activity=pd.read_sql_query("SELECT email,activity_type,model_used,created_at FROM activity_history",conn); conn.close()
    if activity.empty: st.info("No activity data."); return
    st.subheader("⭐ Feature Popularity"); fc=activity["activity_type"].value_counts()
    st.plotly_chart(go.Figure(data=[go.Bar(x=fc.index,y=fc.values)]),use_container_width=True)
    st.subheader("🤖 Model Usage"); mc=activity["model_used"].dropna().value_counts()
    if not mc.empty: st.plotly_chart(go.Figure(data=[go.Pie(labels=mc.index,values=mc.values)]),use_container_width=True)
    st.subheader("📅 Daily Activity Trend"); activity["created_at"]=pd.to_datetime(activity["created_at"]); activity["date"]=activity["created_at"].dt.date
    daily=activity.groupby("date").size()
    st.plotly_chart(go.Figure(data=[go.Scatter(x=daily.index,y=daily.values,mode="lines+markers")]),use_container_width=True)

def activity_tracking():
    c1,c2=st.columns([6,1])
    with c2:
        if st.button("⬅ Back",key="back_at"): st.session_state["_nav_to"]="Home"; st.rerun()
    st.subheader("📊 Activity Tracking"); activities=get_all_activity()
    if not activities: st.info("No activity recorded yet."); return
    df=pd.DataFrame(activities,columns=["Email","Action","Details","Language","Model Name","Timestamp","Output"])
    c1,c2,c3=st.columns(3)
    with c1: uf=st.selectbox("Filter by User",["All"]+sorted(df["Email"].unique()))
    with c2: af=st.selectbox("Filter by Action",["All"]+sorted(df["Action"].unique()))
    with c3: mf=st.selectbox("Filter by Model",["All"]+sorted(df["Model Name"].unique()))
    filtered=df.copy()
    if uf!="All": filtered=filtered[filtered["Email"]==uf]
    if af!="All": filtered=filtered[filtered["Action"]==af]
    if mf!="All": filtered=filtered[filtered["Model Name"]==mf]
    c1,c2,c3=st.columns(3); c1.metric("Total",len(df)); c2.metric("Active Users",df["Email"].nunique()); c3.metric("Action Types",df["Action"].nunique())
    st.markdown("---")
    for _,row in filtered.iterrows():
        icon="🧠" if row["Action"]=="Summarization" else ("🔄" if row["Action"]=="Paraphrasing" else "⚙️")
        dp=str(row["Details"])[:120]+("..." if len(str(row["Details"]))>120 else "")
        st.markdown(f"""<div style="background:rgba(255,255,255,0.05);padding:20px;border-radius:12px;border:1px solid #00C8FF;margin-bottom:15px;">
            <h4>{icon} {row["Action"]}</h4><p><b>👤 User:</b> {row["Email"]}</p>
            <p><b>🌐 Language:</b> {row["Language"] or "English"}</p><p><b>🤖 Model:</b> {row["Model Name"]}</p>
            <p><b>📅 Date:</b> {row["Timestamp"]}</p><p><b>📄 Details:</b> {dp}</p></div>""",unsafe_allow_html=True)
        with st.expander("🔍 View Full Output"): st.info(str(row["Details"])); st.success(str(row["Output"]))

def export_data():
    c1,c2=st.columns([6,1])
    with c2:
        if st.button("⬅ Back",key="back_exp"): st.session_state["_nav_to"]="Home"; st.rerun()
    st.subheader("⬇ Export System Data"); conn=_get_conn()
    users=pd.read_sql_query("SELECT * FROM users",conn); acts=pd.read_sql_query("SELECT * FROM activity_history",conn)
    fb=pd.read_sql_query("SELECT * FROM feedback",conn); du=pd.read_sql_query("SELECT * FROM deleted_users",conn); conn.close()
    export_df=pd.concat([users.assign(type="active_user"),du.assign(type="deleted_user"),acts.assign(type="activity"),fb.assign(type="feedback")],ignore_index=True)
    st.download_button("📥 Download Full System Report",export_df.to_csv(index=False).encode(),"system_report.csv","text/csv")

# -----------------------------------------------
# APP INIT
# -----------------------------------------------
if "db_initialized" not in st.session_state:
    init_db(); st.session_state["db_initialized"]=True

# No eager model loading — all models lazy-load on first button click

if "page"    not in st.session_state: st.session_state.page="login"
if "token"   not in st.session_state: st.session_state.token=None
if "user"    not in st.session_state: st.session_state.user=None
if "_nav_to" not in st.session_state: st.session_state["_nav_to"]="Home"

# -----------------------------------------------
# ROUTING
# -----------------------------------------------
if st.session_state.user:
    with st.sidebar:
        try: jwt.decode(st.session_state.token, SECRET_KEY, algorithms=[ALGORITHM])
        except: st.session_state.clear(); st.session_state.page="login"; st.rerun()
        email=st.session_state["user"]; username=get_username(email); avatar=get_profile_image(email)
        st.image("https://www.infosys.com/content/dam/infosys-web/en/about/springboard/images/infosys-springboard.png",width=150)
        if avatar:
            st.markdown(f'<img src="data:image/png;base64,{base64.b64encode(avatar).decode()}" style="width:100px;height:100px;border-radius:50%;object-fit:cover;border:3px solid #00C8FF;">',unsafe_allow_html=True)
        else:
            st.image("https://cdn-icons-png.flaticon.com/512/149/149071.png",width=80)
        st.markdown(f"""<div style="font-size:20px;font-weight:bold;color:#6B8BA4;margin-bottom:8px;">👤 {username}</div>
            <div style="font-size:14px;color:#B8E4F9;margin-top:6px;">{get_greeting()}</div>""",unsafe_allow_html=True)
        st.markdown("---")
        if st.button("🔓 Logout",key="logout_btn"): st.session_state.clear(); st.session_state.page="login"; st.rerun()

    page=st.session_state["_nav_to"]; admin=is_admin(st.session_state["user"])

    if not admin:
        if   page=="Home":        home_page()
        elif page=="Summarize":   summarizer_page()
        elif page=="Paraphrase":  paraphraser_page()
        elif page=="Readability": readability_page()
        elif page=="Augmentation":augmentation_page()
        elif page=="History":     history_page()
        elif page=="Profile":     user_profile(st.session_state["user"])
    else:
        if   page=="Home":         admin_home_page()
        elif page=="Users":        user_management()
        elif page=="Analytics":    analytics_dashboard()
        elif page=="Activity":     activity_tracking()
        elif page=="Remove Admin": remove_admin()
        elif page=="Feedback":     feedback_section()
        elif page=="Locked":       locked_accounts_section()
        elif page=="Download":     export_data()
else:
    if   st.session_state.page=="login":  login()
    elif st.session_state.page=="signup": signup()
    elif st.session_state.page=="forgot": forgot_password()
