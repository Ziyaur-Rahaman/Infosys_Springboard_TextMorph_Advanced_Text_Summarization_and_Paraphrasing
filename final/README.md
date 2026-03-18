# 🎓 TextMorph — Advanced Text Summarization & Paraphrasing

> An AI-powered NLP web application built with Streamlit, HuggingFace Transformers, and Docker.  
> Developed as part of the **Infosys Springboard** program.

---

## 📌 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Run Locally](#run-locally)
  - [Run with Docker](#run-with-docker)
- [Environment Variables](#environment-variables)
- [Models Used](#models-used)
- [Screenshots](#screenshots)
- [Security Features](#security-features)
- [Key Design Decisions](#key-design-decisions)

---

## 📖 Overview

**TextMorph** is a full-stack NLP application that allows users to:
- Summarize long documents into short, medium, or long summaries
- Paraphrase text with different complexity levels and styles
- Analyze text readability with multiple scoring metrics
- Translate output into 11 Indian languages
- Augment datasets for ML training purposes

The app features a complete user authentication system, admin dashboard, activity history, and feedback collection — all running inside a single Streamlit application.

---

## ✨ Features

### 🧠 AI / NLP
| Feature | Description |
|---|---|
| **Multi-level Summarization** | Short, Medium, Long summaries using BART, Pegasus, or FLAN-T5 |
| **Advanced Paraphrasing** | Simple, Neutral, Advanced complexity with Simplification / Formalization / Creative styles |
| **Text Readability Analyzer** | Flesch, Kincaid, SMOG, Gunning Fog, Coleman-Liau scores with visual gauges |
| **Multi-language Translation** | Output in 11 Indian languages using Facebook NLLB-200 |
| **Dataset Augmentation** | Generate paraphrase/summarization datasets and export as CSV |

### 🔐 Authentication & Security
| Feature | Description |
|---|---|
| **User Registration** | Username, email, password, security question |
| **Secure Login** | bcrypt password hashing, JWT session tokens |
| **Password Strength Meter** | Real-time strength scoring |
| **Rate Limiting** | Auto-locks account after 3 failed login attempts |
| **OTP Password Reset** | Time-limited OTP sent via Gmail SMTP |
| **Security Question Reset** | Alternative password recovery method |
| **Password History** | Prevents reuse of old passwords |

### 👤 User Features
| Feature | Description |
|---|---|
| **User Profile** | Change email, password, upload avatar |
| **Activity History** | Full log of all summarization and paraphrasing actions |
| **Feedback System** | Rate outputs 1–5 stars with comments |

### 🛠 Admin Features
| Feature | Description |
|---|---|
| **Admin Dashboard** | Total users, activities, feedback metrics |
| **User Management** | Promote to admin, delete users |
| **Locked Accounts** | View and unlock rate-limited accounts |
| **Feedback Analytics** | Word cloud + feedback table |
| **System Analytics** | Activity bar charts by feature usage |

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | Streamlit, Plotly, Matplotlib |
| **AI Models** | HuggingFace Transformers (BART, Pegasus, FLAN-T5, NLLB-200) |
| **NLP Utilities** | NLTK, textstat |
| **Authentication** | bcrypt, PyJWT, HMAC OTP |
| **Database** | SQLite (via Python sqlite3) |
| **Email** | Gmail SMTP |
| **Containerization** | Docker, Docker Compose |
| **Language** | Python 3.10 |

---

## 📁 Project Structure

```
final/
├── .streamlit/
│   └── config.toml          # Streamlit theme and server config
├── data/                    # SQLite database (persisted via Docker volume)
├── .dockerignore            # Files excluded from Docker image
├── .env.example             # Environment variable template
├── app.py                   # Main application (single-file Streamlit app)
├── docker-compose.yml       # Docker Compose configuration
├── Dockerfile               # Docker image definition
├── README.md                # This file
└── requirements.txt         # Python dependencies
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+ **or** Docker Desktop installed

---

### Run Locally

**Step 1 — Clone the repository**
```bash
git clone https://github.com/Ziyaur-Rahaman/Infosys_Springboard_TextMorph_Advanced_Text_Summarization_and_Paraphrasing.git
cd Infosys_Springboard_TextMorph_Advanced_Text_Summarization_and_Paraphrasing/final
```

**Step 2 — Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows
```

**Step 3 — Install dependencies**
```bash
pip install -r requirements.txt
```

**Step 4 — Download NLTK data**
```bash
python -c "
import ssl
ssl._create_default_https_context = ssl._create_unverified_context
import nltk
nltk.download('punkt')
nltk.download('punkt_tab')
nltk.download('cmudict')
"
```

**Step 5 — Set environment variables**
```bash
cp .env.example .env
# Edit .env with your real values
```

**Step 6 — Run the app**
```bash
streamlit run app.py
```

Open **http://localhost:8501**

---

### Run with Docker

**Step 1 — Clone the repository**
```bash
git clone https://github.com/Ziyaur-Rahaman/Infosys_Springboard_TextMorph_Advanced_Text_Summarization_and_Paraphrasing.git
cd Infosys_Springboard_TextMorph_Advanced_Text_Summarization_and_Paraphrasing/final
```

**Step 2 — Set environment variables**
```bash
cp .env.example .env
# Edit .env with your real values
```

**Step 3 — Create data folder**
```bash
mkdir -p data
```

**Step 4 — Build and run**
```bash
docker compose up --build -d
```

Open **http://localhost:8501** ✅

---

### Docker Commands Reference

| Action | Command |
|---|---|
| Start | `docker compose up -d` |
| Stop | `docker compose down` |
| Restart (after code change) | `docker compose restart` |
| Rebuild (after requirements change) | `docker compose up --build -d` |
| View logs | `docker compose logs -f` |
| Check status | `docker compose ps` |

---

## 🔑 Environment Variables

Copy `.env.example` to `.env` and fill in your values:

| Variable | Description | Required |
|---|---|---|
| `JWT_SECRET` | Secret key for JWT session tokens. Use a long random string. | ✅ Yes |
| `EMAIL_PASSWORD` | Gmail App Password for OTP emails (not your regular password) | ✅ For OTP reset |
| `DB_PATH` | Path to SQLite database file (default: `users.db`) | Docker only |

**How to get a Gmail App Password:**
1. Go to [myaccount.google.com](https://myaccount.google.com)
2. Security → 2-Step Verification → Enable
3. Search **App Passwords**
4. Create one for **Mail**
5. Paste the 16-character password into `.env`

---

## 🤖 Models Used

| Model | Task | Source |
|---|---|---|
| `sshleifer/distilbart-cnn-12-6` | Summarization | HuggingFace |
| `google/pegasus-cnn_dailymail` | Summarization | HuggingFace |
| `google/flan-t5-small` | Summarization + Paraphrasing | HuggingFace |
| `eugenesiow/bart-paraphrase` | Paraphrasing | HuggingFace |
| `facebook/nllb-200-distilled-600M` | Translation (11 languages) | HuggingFace |

### Lazy Loading
All models use **lazy loading** — they are downloaded and loaded into memory **only when the user clicks a button**, not at startup. This reduces startup time from 3–5 minutes to under 2 seconds.

After the first use, models are cached in memory via `@st.cache_resource` so subsequent requests are instant.

---

## 🌐 Supported Languages

English, Hindi, Tamil, Kannada, Telugu, Marathi, Bengali, Gujarati, Malayalam, Urdu, Punjabi

---

## 🔒 Security Features

- Passwords hashed with **bcrypt**
- Sessions managed with **JWT tokens** (1 hour expiry)
- Account **lockout after 3 failed logins**
- OTP reset with **HMAC-based generation** (10 minute expiry)
- **Password history** prevents reuse of old passwords
- **SSL-safe NLTK downloads** with certificate bypass for restricted environments

---

## ⚙️ Key Design Decisions

### 1. Lazy Loading
Models are not loaded at startup. Each model loads only when first requested and is cached for the session lifetime. This makes the app Docker-friendly and fast to start.

### 2. Single-file Architecture
The entire application lives in `app.py` — database layer, authentication, AI models, UI pages — making it easy to deploy and maintain for a project of this scale.

### 3. SQLite with Docker Volume
SQLite is used for simplicity. In Docker, the database file is stored in a mounted volume (`./data`) so user data persists across container rebuilds and restarts.

### 4. Fallback System for NLTK
If NLTK data cannot be downloaded (SSL/network issues), the app falls back to regex-based sentence splitting and vowel-counting syllable estimation, so it never crashes.

