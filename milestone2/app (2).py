
import streamlit as st
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import secrets
import bcrypt
import jwt
import datetime
import time
import os
import re
import hmac
import hashlib
import struct
import db
from streamlit_option_menu import option_menu
import plotly.graph_objects as go
import PyPDF2

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────
EMAIL_PASSWORD   = os.getenv("EMAIL_PASSWORD")
SECRET_KEY       = os.getenv("JWT_SECRET", "super-secret-key-change-this")
EMAIL_ADDRESS    = "newm92869@gmail.com"
OTP_EXPIRY_MIN   = 10

st.set_page_config(
    page_title="Infosys LLM — Secure Portal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────
# GLOBAL CSS  (Glassmorphism / Cyber theme)
# ─────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&family=JetBrains+Mono:wght@300;400;600&display=swap');

:root {
  --bg:      #060b18;
  --surface: rgba(255,255,255,0.04);
  --border:  rgba(0,230,180,0.18);
  --accent:  #00e6b4;
  --accent2: #6e7bff;
  --danger:  #ff4f6d;
  --warn:    #ffb347;
  --text:    #e4f0f6;
  --muted:   #6b82a0;
  --radius:  14px;
}

html, body, [class*="css"] {
  font-family: 'JetBrains Mono', monospace !important;
  background-color: var(--bg) !important;
  color: var(--text) !important;
}

/* Animated mesh background */
.stApp::before {
  content: '';
  position: fixed;
  inset: 0;
  background:
    radial-gradient(ellipse 80% 60% at 20% 10%, rgba(0,230,180,0.07) 0%, transparent 60%),
    radial-gradient(ellipse 60% 80% at 80% 90%, rgba(110,123,255,0.07) 0%, transparent 60%),
    radial-gradient(ellipse 40% 40% at 50% 50%, rgba(0,0,0,0) 0%, rgba(6,11,24,1) 100%);
  pointer-events: none;
  z-index: 0;
}

/* Scrollbar */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--accent); border-radius: 4px; }

/* Card container */
.glass-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 2rem;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  box-shadow: 0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.05);
}

/* Headers */
h1 { font-family: 'Syne', sans-serif !important; font-size: 2.4rem !important;
     font-weight: 800 !important; color: var(--accent) !important;
     letter-spacing: -0.5px; text-shadow: 0 0 30px rgba(0,230,180,0.35); }
h2 { font-family: 'Syne', sans-serif !important; font-weight: 700 !important;
     color: var(--text) !important; font-size: 1.4rem !important; }
h3 { font-family: 'Syne', sans-serif !important; font-weight: 700 !important;
     color: var(--accent2) !important; font-size: 1.1rem !important; }

/* Inputs */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
  background: rgba(255,255,255,0.04) !important;
  border: 1px solid var(--border) !important;
  border-radius: 8px !important;
  color: var(--text) !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 0.9rem !important;
  padding: 0.6rem 0.9rem !important;
  transition: border-color 0.25s, box-shadow 0.25s;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 3px rgba(0,230,180,0.12) !important;
}

/* Select */
.stSelectbox > div > div {
  background: rgba(255,255,255,0.04) !important;
  border: 1px solid var(--border) !important;
  border-radius: 8px !important;
  color: var(--text) !important;
}

/* Buttons */
.stButton > button {
  background: linear-gradient(135deg, rgba(0,230,180,0.12), rgba(110,123,255,0.12)) !important;
  border: 1px solid var(--accent) !important;
  border-radius: 8px !important;
  color: var(--accent) !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-weight: 600 !important;
  font-size: 0.88rem !important;
  letter-spacing: 0.5px !important;
  padding: 0.55rem 1.2rem !important;
  transition: all 0.25s ease !important;
  width: 100% !important;
}
.stButton > button:hover {
  background: linear-gradient(135deg, rgba(0,230,180,0.28), rgba(110,123,255,0.28)) !important;
  box-shadow: 0 0 20px rgba(0,230,180,0.25) !important;
  transform: translateY(-1px) !important;
}
.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, var(--accent), var(--accent2)) !important;
  color: #060b18 !important;
  border: none !important;
  font-weight: 700 !important;
}
.stButton > button[kind="primary"]:hover {
  box-shadow: 0 0 25px rgba(0,230,180,0.45) !important;
}

/* Form */
.stForm { background: transparent !important; border: none !important; }
[data-testid="stForm"] {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important;
  padding: 1.5rem !important;
}

/* Alerts */
.stSuccess, .stError, .stWarning, .stInfo {
  border-radius: 8px !important;
  border-left-width: 3px !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 0.88rem !important;
}

/* Sidebar */
section[data-testid="stSidebar"] > div {
  background: linear-gradient(180deg, #090f1f 0%, #060b18 100%) !important;
  border-right: 1px solid var(--border) !important;
}

/* Metrics */
[data-testid="stMetricValue"] {
  color: var(--accent) !important;
  font-family: 'Syne', sans-serif !important;
  font-size: 1.8rem !important;
}
[data-testid="stMetricLabel"] {
  color: var(--muted) !important;
  font-size: 0.75rem !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] { gap: 6px; border-bottom: 1px solid var(--border) !important; }
.stTabs [data-baseweb="tab"] {
  background: transparent !important;
  color: var(--muted) !important;
  border-radius: 6px 6px 0 0 !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 0.85rem !important;
}
.stTabs [aria-selected="true"] {
  background: rgba(0,230,180,0.1) !important;
  color: var(--accent) !important;
  border-bottom: 2px solid var(--accent) !important;
}

/* Chat */
[data-testid="stChatMessage"] {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important;
  margin-bottom: 0.8rem !important;
}
[data-testid="stChatInputContainer"] {
  border-top: 1px solid var(--border) !important;
  background: rgba(255,255,255,0.02) !important;
}
[data-testid="stChatInput"] textarea {
  background: transparent !important;
  color: var(--text) !important;
  font-family: 'JetBrains Mono', monospace !important;
}

/* File uploader */
[data-testid="stFileUploader"] {
  background: var(--surface) !important;
  border: 1px dashed var(--border) !important;
  border-radius: var(--radius) !important;
}

/* Expander */
.streamlit-expanderHeader {
  background: var(--surface) !important;
  color: var(--accent2) !important;
  border-radius: 6px !important;
}

/* Password strength pills */
.pill-weak   { display:inline-block; padding:3px 12px; border-radius:99px; background:rgba(255,79,109,0.15); color:#ff4f6d; font-weight:700; font-size:0.8rem; border:1px solid rgba(255,79,109,0.4); }
.pill-medium { display:inline-block; padding:3px 12px; border-radius:99px; background:rgba(255,179,71,0.15); color:#ffb347; font-weight:700; font-size:0.8rem; border:1px solid rgba(255,179,71,0.4); }
.pill-strong { display:inline-block; padding:3px 12px; border-radius:99px; background:rgba(0,230,180,0.15); color:#00e6b4; font-weight:700; font-size:0.8rem; border:1px solid rgba(0,230,180,0.4); }

/* Progress bar */
.stProgress > div > div > div { background: linear-gradient(90deg, var(--accent), var(--accent2)) !important; border-radius: 99px !important; }
.stProgress > div > div { background: rgba(255,255,255,0.06) !important; border-radius: 99px !important; }

/* Divider */
hr { border-color: var(--border) !important; margin: 1.5rem 0 !important; }

/* DataFrames / tables */
[data-testid="stDataFrame"] { border: 1px solid var(--border) !important; border-radius: var(--radius) !important; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# DB INIT
# ─────────────────────────────────────────
if "db_initialized" not in st.session_state:
    db.init_db()
    st.session_state["db_initialized"] = True

# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────
def get_relative_time(date_str):
    if not date_str: return "some time ago"
    try:
        past = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        diff = datetime.datetime.utcnow() - past
        d, s = diff.days, diff.seconds
        if d > 365:  return f"{d // 365}y ago"
        if d > 30:   return f"{d // 30}mo ago"
        if d > 0:    return f"{d}d ago"
        if s > 3600: return f"{s // 3600}h ago"
        if s > 60:   return f"{s // 60}m ago"
        return "just now"
    except: return date_str

def is_valid_email(email):
    return re.match(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$", email) is not None

def check_password_strength(password):
    if not password: return "Weak", 0, ["Enter a password"]
    has_upper   = bool(re.search(r"[A-Z]", password))
    has_lower   = bool(re.search(r"[a-z]", password))
    has_digit   = bool(re.search(r"\d", password))
    has_special = bool(re.search(r"[!@#$%^&*()\-_=+\[\]{};:'\",.<>?/\\|`~]", password))
    has_space   = bool(re.search(r"\s", password))
    issues = []
    score  = 0
    if has_space: return "Weak", 5, ["No spaces allowed"]
    if len(password) >= 8: score += 30
    else: issues.append("Min 8 characters")
    if has_upper and has_lower: score += 20
    else: issues.append("Mix upper & lower case")
    if has_digit: score += 20
    else: issues.append("Include a number")
    if has_special: score += 30
    else: issues.append("Add a special character (!@#…)")
    if score >= 80:   return "Strong", score, []
    if score >= 50:   return "Medium", score, issues
    return "Weak", score, issues

def render_password_strength(password):
    if not password: return
    level, score, issues = check_password_strength(password)
    pill_class = {"Weak":"pill-weak","Medium":"pill-medium","Strong":"pill-strong"}[level]
    st.markdown(f'<span class="{pill_class}">⬤ {level}</span>', unsafe_allow_html=True)
    st.progress(score / 100)
    if issues:
        st.caption("  ·  ".join(issues))

# ─────────────────────────────────────────
# SECURITY — OTP
# ─────────────────────────────────────────
def generate_otp():
    secret  = secrets.token_bytes(20)
    counter = int(time.time())
    msg     = struct.pack(">Q", counter)
    h       = hmac.new(secret, msg, hashlib.sha1).digest()
    offset  = h[19] & 0xf
    code    = ((h[offset] & 0x7f) << 24 | (h[offset+1] & 0xff) << 16 |
               (h[offset+2] & 0xff) << 8  |  h[offset+3] & 0xff)
    return f"{code % 1000000:06d}"

def create_otp_token(otp, email):
    otp_hash = bcrypt.hashpw(otp.encode(), bcrypt.gensalt()).decode()
    payload  = {
        "otp_hash": otp_hash, "sub": email, "type": "password_reset",
        "iat": datetime.datetime.utcnow(),
        "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=OTP_EXPIRY_MIN),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def verify_otp_token(token, input_otp, email):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        if payload.get("type") != "password_reset": return False, "Invalid token type"
        if payload.get("sub") != email:             return False, "Token mismatch"
        if bcrypt.checkpw(input_otp.encode(), payload["otp_hash"].encode()):
            return True, "Valid"
        return False, "Wrong OTP"
    except jwt.ExpiredSignatureError: return False, "⏰ OTP Expired"
    except jwt.InvalidTokenError:     return False, "Invalid Token"

# ─────────────────────────────────────────
# EMAIL
# ─────────────────────────────────────────
def send_email(to_email, otp, app_pass=None):
    msg            = MIMEMultipart()
    msg["From"]    = f"TextMorph <{EMAIL_ADDRESS}>"
    msg["To"]      = to_email
    msg["Subject"] = "🔐 Your Password Reset Code"
    body = f"""
    <html><body style="margin:0;padding:0;background:#060b18;font-family:'Courier New',monospace;">
    <div style="max-width:480px;margin:40px auto;background:rgba(255,255,255,0.04);
                border:1px solid rgba(0,230,180,0.2);border-radius:16px;padding:40px;text-align:center;">
      <div style="font-size:28px;font-weight:800;color:#00e6b4;letter-spacing:-1px;margin-bottom:8px;">
        ⚡ TextMorph
      </div>
      <p style="color:#6b82a0;font-size:13px;margin-bottom:32px;">Password Reset Request for {to_email}</p>
      <div style="background:#060b18;border:1px solid rgba(0,230,180,0.3);border-radius:12px;
                  padding:24px;letter-spacing:12px;font-size:36px;font-weight:700;color:#00e6b4;
                  box-shadow:0 0 30px rgba(0,230,180,0.1);margin-bottom:24px;">
        {otp}
      </div>
      <p style="color:#6b82a0;font-size:12px;">Valid for <strong style="color:#e4f0f6;">{OTP_EXPIRY_MIN} minutes</strong>. Do not share this code.</p>
      <hr style="border-color:rgba(0,230,180,0.1);margin:24px 0;">
      <p style="color:#3a4a5c;font-size:11px;">© 2026 TextMorph Secure Auth</p>
    </div></body></html>"""
    msg.attach(MIMEText(body, "html"))
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        pw = app_pass or EMAIL_PASSWORD
        if not pw: return False, "No App Password found."
        server.login(EMAIL_ADDRESS, pw)
        server.sendmail(EMAIL_ADDRESS, to_email, msg.as_string())
        server.quit()
        return True, "Sent!"
    except Exception as e:
        return False, str(e)

# ─────────────────────────────────────────
# VISUALIZATION
# ─────────────────────────────────────────
def create_gauge(value, title, min_val=0, max_val=100, color="#00e6b4"):
    fig = go.Figure(go.Indicator(
        mode  = "gauge+number",
        value = value,
        title = {"text": title, "font": {"color": color, "size": 13, "family": "Syne"}},
        number= {"font": {"color": color, "size": 22, "family": "JetBrains Mono"}},
        gauge = {
            "axis":   {"range": [min_val, max_val], "tickwidth": 1, "tickcolor": "rgba(255,255,255,0.15)"},
            "bar":    {"color": color, "thickness": 0.5},
            "bgcolor":"#0d1627",
            "borderwidth": 1,
            "bordercolor": "rgba(255,255,255,0.07)",
            "steps": [{"range":[min_val, max_val], "color":"rgba(255,255,255,0.03)"}],
            "threshold": {"line":{"color":color,"width":2},"thickness":0.8,"value":value},
        }
    ))
    fig.update_layout(
        paper_bgcolor="#060b18",
        font={"color":"#e4f0f6","family":"JetBrains Mono"},
        height=220,
        margin=dict(l=15,r=15,t=50,b=10)
    )
    return fig

# ─────────────────────────────────────────
# SESSION DEFAULTS
# ─────────────────────────────────────────
for k, v in [("user", None), ("page", "login")]:
    if k not in st.session_state: st.session_state[k] = v

def switch_page(p): st.session_state["page"] = p; st.rerun()
def logout(): st.session_state["user"] = None; st.session_state["page"] = "login"; st.rerun()

# ─────────────────────────────────────────
# ========= PAGES =========
# ─────────────────────────────────────────

# ── LOGIN ──────────────────────────────────
def login_page():
    col_l, col_m, col_r = st.columns([1.2, 1.8, 1.2])
    with col_m:
        st.markdown('<div style="height:60px"></div>', unsafe_allow_html=True)
        st.markdown("## ⚡ TextMorph")
        st.markdown('<p style="color:#6b82a0;margin-bottom:2rem;">Secure Authentication Portal</p>', unsafe_allow_html=True)

        with st.form("login_form"):
            email    = st.text_input("Email Address", placeholder="you@company.com")
            password = st.text_input("Password", type="password", placeholder="••••••••••")
            submit   = st.form_submit_button("Sign In →", type="primary")

            if submit:
                is_locked, wait_time = db.is_rate_limited(email)
                if is_locked:
                    st.error(f"⛔ Locked — too many attempts. Retry in **{int(wait_time)}s**.")
                elif not email or not password:
                    st.error("All fields are required.")
                elif db.authenticate_user(email, password):
                    st.session_state["user"] = email
                    st.balloons()
                    st.success(f"Welcome back, {email.split('@')[0]}!")
                    time.sleep(0.8)
                    st.rerun()
                else:
                    st.error("Invalid credentials.")
                    old_dt = db.check_is_old_password(email, password)
                    if old_dt:
                        st.warning(f"⚠️ That was a previous password ({get_relative_time(old_dt)}). Use your latest one.")

        st.markdown('<div style="height:8px"></div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        if c1.button("Create Account"): switch_page("register")
        if c2.button("Forgot Password?"): switch_page("forgot")

# ── REGISTER ──────────────────────────────
def register_page():
    col_l, col_m, col_r = st.columns([1.2, 1.8, 1.2])
    with col_m:
        st.markdown('<div style="height:60px"></div>', unsafe_allow_html=True)
        st.markdown("## ⚡ Create Account")
        st.markdown('<p style="color:#6b82a0;margin-bottom:1.5rem;">Join TextMorph Secure Portal</p>', unsafe_allow_html=True)

        email    = st.text_input("Email Address", placeholder="you@company.com")
        password = st.text_input("Password", type="password", placeholder="Min 8 chars")
        render_password_strength(password)

        if st.button("Register →", type="primary"):
            if not email or not password:
                st.error("All fields are required.")
            elif not is_valid_email(email):
                st.error("Invalid email format.")
            else:
                lvl, _, fb = check_password_strength(password)
                if lvl == "Weak":
                    st.error(f"Password too weak: {', '.join(fb)}")
                elif db.register_user(email, password):
                    st.success("✅ Account created! Redirecting…")
                    time.sleep(1.5); switch_page("login")
                else:
                    st.error("Email already registered.")

        st.markdown("---")
        if st.button("← Back to Login"): switch_page("login")

# ── FORGOT PASSWORD ────────────────────────
def forgot_page():
    col_l, col_m, col_r = st.columns([1.2, 1.8, 1.2])
    with col_m:
        st.markdown('<div style="height:60px"></div>', unsafe_allow_html=True)
        st.markdown("## 🔑 Password Recovery")

        if "stage" not in st.session_state: st.session_state["stage"] = "email"

        # Step indicators
        stages  = ["email", "otp", "verify", "reset"]
        labels  = ["📧 Email", "📨 Send OTP", "✅ Verify", "🔒 Reset"]
        cur_idx = stages.index(st.session_state["stage"])
        cols_s  = st.columns(len(stages))
        for i, (s_col, lbl) in enumerate(zip(cols_s, labels)):
            clr = "#00e6b4" if i <= cur_idx else "#3a4a5c"
            s_col.markdown(f'<div style="text-align:center;color:{clr};font-size:0.75rem;font-weight:600;">{lbl}</div>', unsafe_allow_html=True)
        st.markdown("---")

        # ── Stage: email
        if st.session_state["stage"] == "email":
            email = st.text_input("Registered Email", placeholder="you@company.com")
            if st.button("Verify Email →", type="primary"):
                if not email: st.error("Email is required.")
                elif not is_valid_email(email): st.error("Invalid format.")
                elif db.check_user_exists(email):
                    st.session_state["reset_email"] = email
                    st.session_state["stage"] = "otp"
                    st.rerun()
                else: st.error("Email not found.")

        # ── Stage: otp (send)
        elif st.session_state["stage"] == "otp":
            st.info(f"Sending to: **{st.session_state['reset_email']}**")
            app_pass = EMAIL_PASSWORD
            if not app_pass:
                st.warning("⚠️ EMAIL_PASSWORD not in env. Enter manually.")
                app_pass = st.text_input("Google App Password", type="password")

            if st.button("Send OTP →", type="primary"):
                if app_pass:
                    otp = generate_otp()
                    with st.spinner("Dispatching secure code…"):
                        ok, msg = send_email(st.session_state["reset_email"], otp, app_pass)
                    if ok:
                        st.session_state["token"] = create_otp_token(otp, st.session_state["reset_email"])
                        st.session_state["stage"] = "verify"
                        st.success("OTP sent! Check your inbox.")
                        time.sleep(1); st.rerun()
                    else: st.error(f"Email error: {msg}")
                else: st.error("App Password required.")

        # ── Stage: verify OTP
        elif st.session_state["stage"] == "verify":
            st.info("Enter the 6-digit code from your email.")
            otp_input = st.text_input("Verification Code", max_chars=6, placeholder="000000")
            c1, c2 = st.columns(2)
            if c1.button("Verify →", type="primary"):
                if not otp_input: st.error("Code is required.")
                else:
                    ok, msg = verify_otp_token(st.session_state["token"], otp_input, st.session_state["reset_email"])
                    if ok:
                        st.session_state["stage"] = "reset"
                        st.success("Verified! Set new password.")
                        time.sleep(0.8); st.rerun()
                    else: st.error(msg)
            if c2.button("Resend Code"):
                st.session_state["stage"] = "otp"; st.rerun()

        # ── Stage: reset password
        elif st.session_state["stage"] == "reset":
            p1 = st.text_input("New Password", type="password")
            render_password_strength(p1)
            p2 = st.text_input("Confirm Password", type="password")
            if st.button("Update Password →", type="primary"):
                if not p1 or not p2:  st.error("Both fields required.")
                elif p1 != p2:        st.error("Passwords don't match.")
                elif db.check_password_reused(st.session_state["reset_email"], p1):
                    st.error("⚠️ Cannot reuse a previous password.")
                else:
                    lvl, _, _ = check_password_strength(p1)
                    if lvl == "Weak": st.error("Password too weak.")
                    else:
                        db.update_password(st.session_state["reset_email"], p1)
                        st.balloons(); st.success("Password updated! Redirecting…")
                        for k in ["stage","reset_email","token"]:
                            if k in st.session_state: del st.session_state[k]
                        time.sleep(1.5); switch_page("login")

        st.markdown("---")
        if st.button("← Cancel"): switch_page("login")

# ── CHAT ──────────────────────────────────
def chat_page():
    if not st.session_state["user"]: switch_page("login"); return
    st.markdown("## 🤖 Infosys LLM Chat")
    st.caption("Secure AI assistant — your messages are session-only and never stored.")

    if "messages" not in st.session_state: st.session_state.messages = []

    # Chat history display
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Empty state
    if not st.session_state.messages:
        st.markdown("""
        <div style="text-align:center;padding:60px 20px;color:#3a4a5c;">
          <div style="font-size:48px;margin-bottom:16px;">💬</div>
          <div style="font-size:1.1rem;color:#6b82a0;font-weight:600;">Start a conversation</div>
          <div style="font-size:0.85rem;margin-top:8px;">Ask me anything — I'm here to help.</div>
        </div>""", unsafe_allow_html=True)

    if prompt := st.chat_input("Message Infosys LLM…"):
        st.session_state.messages.append({"role":"user","content":prompt})
        with st.chat_message("user"):  st.markdown(prompt)
        with st.chat_message("assistant"):
            # Simulated streamed response
            response = f"**[Simulated Response]**\n\nYou asked: *{prompt}*\n\nThis is a secure mock reply. Integrate your LLM backend here."
            st.markdown(response)
        st.session_state.messages.append({"role":"assistant","content":response})

    # Conversation controls
    if st.session_state.messages:
        if st.button("🗑️ Clear History"):
            st.session_state.messages = []; st.rerun()

# ── READABILITY ────────────────────────────
def readability_page():
    if not st.session_state["user"]: switch_page("login"); return
    import readability as rl

    st.markdown("## 📖 Text Readability Analyzer")
    st.caption("Analyze the reading level and complexity of any text or document.")

    tab1, tab2 = st.tabs(["✍️ Paste Text", "📂 Upload File"])
    text_input = ""

    with tab1:
        raw = st.text_area("Paste your text here:", height=220,
                           placeholder="Enter at least 50 characters…")
        if raw: text_input = raw

    with tab2:
        f = st.file_uploader("Drop a TXT or PDF file", type=["txt","pdf"])
        if f:
            try:
                if f.type == "application/pdf":
                    reader = PyPDF2.PdfReader(f)
                    text_input = "\n".join(p.extract_text() or "" for p in reader.pages)
                    st.info(f"✅ {len(reader.pages)} page(s) loaded from PDF.")
                else:
                    text_input = f.read().decode("utf-8")
                    st.info(f"✅ TXT loaded: {f.name}")
            except Exception as e:
                st.error(f"Read error: {e}")

    if st.button("Analyze →", type="primary"):
        if len(text_input.strip()) < 50:
            st.error("Text too short (minimum 50 characters).")
        else:
            with st.spinner("Running readability analysis…"):
                analyzer = rl.ReadabilityAnalyzer(text_input)
                score    = analyzer.get_all_metrics()

            st.markdown("---")
            st.markdown("### 📊 Results")

            avg = (score["Flesch-Kincaid Grade"] + score["Gunning Fog"] +
                   score["SMOG Index"] + score["Coleman-Liau"]) / 4

            if avg <= 6:    level, clr = "Beginner",      "#28a745"
            elif avg <= 10: level, clr = "Intermediate",  "#00e6b4"
            elif avg <= 14: level, clr = "Advanced",      "#ffb347"
            else:           level, clr = "Expert",        "#ff4f6d"

            st.markdown(f"""
            <div style="background:rgba(255,255,255,0.03);border:1px solid {clr}40;
                        border-left:4px solid {clr};border-radius:12px;
                        padding:24px;text-align:center;margin-bottom:24px;">
              <div style="font-size:1.6rem;font-weight:800;font-family:Syne,sans-serif;color:{clr};">{level}</div>
              <div style="color:#6b82a0;font-size:0.85rem;margin-top:4px;">Approx. Grade Level: <strong style="color:#e4f0f6;">{avg:.1f}</strong></div>
            </div>""", unsafe_allow_html=True)

            # Gauges
            c1, c2, c3 = st.columns(3)
            c1.plotly_chart(create_gauge(score["Flesch Reading Ease"], "Flesch Ease",  0,  100, "#00e6b4"), use_container_width=True)
            c2.plotly_chart(create_gauge(score["Flesch-Kincaid Grade"],"FK Grade",     0,   20, "#6e7bff"), use_container_width=True)
            c3.plotly_chart(create_gauge(score["SMOG Index"],          "SMOG Index",   0,   20, "#ffb347"), use_container_width=True)

            c4, c5 = st.columns(2)
            c4.plotly_chart(create_gauge(score["Gunning Fog"],   "Gunning Fog",   0, 20, "#00ccff"), use_container_width=True)
            c5.plotly_chart(create_gauge(score["Coleman-Liau"],  "Coleman-Liau",  0, 20, "#ff9900"), use_container_width=True)

            # Stats
            st.markdown("### 📝 Text Statistics")
            m1,m2,m3,m4,m5 = st.columns(5)
            m1.metric("Sentences",     analyzer.num_sentences)
            m2.metric("Words",         analyzer.num_words)
            m3.metric("Syllables",     analyzer.num_syllables)
            m4.metric("Complex Words", analyzer.complex_words)
            m5.metric("Characters",    analyzer.char_count)

            # Metric detail expanders
            st.markdown("---")
            st.markdown("### ℹ️ Metric Guide")
            with st.expander("Flesch Reading Ease"):
                st.write("Score 0–100. **Higher = easier**. 60–70 is comfortable for most readers. Academic writing typically scores 0–30.")
            with st.expander("Flesch-Kincaid Grade"):
                st.write("US school grade level. **Grade 8** means an 8th-grader can understand it. Aim for 8–10 for general audiences.")
            with st.expander("SMOG Index"):
                st.write("Simple Measure of Gobbledygook. Widely used for **medical/health** writing. Estimates the years of education needed.")
            with st.expander("Gunning Fog"):
                st.write("Based on sentence length and 'complex' words (3+ syllables). **Score 12** = high school level.")
            with st.expander("Coleman-Liau"):
                st.write("Uses **character counts** instead of syllables — more stable across OCR or extracted PDF text.")

# ── ADMIN ──────────────────────────────────
def admin_page():
    if st.session_state["user"] != "admin@llm.com":
        st.error("⛔ Access Denied")
        return

    st.markdown("## 🛡️ Admin Panel")
    users = db.get_all_users()

    col1, col2 = st.columns(2)
    col1.metric("Total Users", len(users))
    col2.metric("Admin Email", "admin@llm.com")

    st.markdown("---")

    if not users:
        st.info("No users registered yet.")
        return

    st.markdown("### 👤 User Management")
    header = st.columns([3, 2, 1])
    header[0].markdown("**Email**")
    header[1].markdown("**Joined**")
    header[2].markdown("**Action**")
    st.markdown('<hr style="margin:4px 0;">', unsafe_allow_html=True)

    for u_email, u_created in users:
        r1, r2, r3 = st.columns([3, 2, 1])
        r1.write(u_email)
        r2.write(get_relative_time(u_created))
        if u_email != "admin@llm.com":
            if r3.button("Delete", key=u_email, type="primary"):
                db.delete_user(u_email)
                st.warning(f"Removed {u_email}")
                time.sleep(0.4); st.rerun()
        else:
            r3.markdown('<span style="color:#3a4a5c;font-size:0.8rem;">protected</span>', unsafe_allow_html=True)

# ─────────────────────────────────────────
# ROUTING
# ─────────────────────────────────────────
if st.session_state["user"]:
    with st.sidebar:
        st.markdown("""
        <div style="padding:1rem 0 1.5rem;">
          <div style="font-size:1.4rem;font-weight:800;color:#00e6b4;font-family:Syne,sans-serif;letter-spacing:-0.5px;">⚡ TextMorph</div>
          <div style="color:#3a4a5c;font-size:0.75rem;margin-top:2px;">Secure AI Portal</div>
        </div>""", unsafe_allow_html=True)

        user_short = st.session_state["user"].split("@")[0]
        st.markdown(f"""
        <div style="background:rgba(0,230,180,0.06);border:1px solid rgba(0,230,180,0.15);
                    border-radius:10px;padding:12px 14px;margin-bottom:1.5rem;">
          <div style="color:#00e6b4;font-size:0.8rem;font-weight:600;">👤 Signed in as</div>
          <div style="color:#e4f0f6;font-size:0.9rem;margin-top:4px;word-break:break-all;">{st.session_state["user"]}</div>
        </div>""", unsafe_allow_html=True)

        opts  = ["Chat", "Readability"]
        icons = ["chat-dots", "book"]
        if st.session_state["user"] == "admin@llm.com":
            opts.append("Admin"); icons.append("shield-lock")

        selected = option_menu(
            "Navigation", opts, icons=icons,
            menu_icon="grid", default_index=0,
            styles={
                "container":        {"background-color":"transparent","padding":"0"},
                "menu-title":       {"color":"#3a4a5c","font-size":"0.7rem","letter-spacing":"1px"},
                "icon":             {"color":"#6b82a0","font-size":"14px"},
                "nav-link":         {"color":"#6b82a0","font-family":"JetBrains Mono","font-size":"0.88rem",
                                     "border-radius":"8px","margin":"2px 0"},
                "nav-link-selected":{"background-color":"rgba(0,230,180,0.12)","color":"#00e6b4",
                                     "font-weight":"600","border":"1px solid rgba(0,230,180,0.25)"},
            }
        )

        st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)
        if st.button("🔓 Log Out"): logout()

    if selected == "Chat":        chat_page()
    elif selected == "Readability": readability_page()
    elif selected == "Admin":       admin_page()

else:
    page = st.session_state["page"]
    if page == "login":    login_page()
    elif page == "register": register_page()
    elif page == "forgot":   forgot_page()
