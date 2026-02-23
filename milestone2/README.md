# 🔐 Milestone 2 — Advanced Secure Authentication System and Readability Analyzer



---

## 📝 Description

In Milestone 2, we significantly upgraded the authentication system built in Milestone 1 by replacing in-memory session storage with a **persistent SQLite database**, introducing **industry-standard password hashing** using bcrypt, adding an **email-based OTP verification** system for password recovery, implementing **rate limiting** to prevent brute-force attacks, and integrating a **Text Readability Analyzer** as a core application feature.

The application now includes:
- Persistent user storage using SQLite (3 structured tables)
- Secure password hashing using bcrypt (one-way, salted)
- Email-based OTP for password reset using HMAC-SHA1 (RFC 4226)
- Rate limiting — account lockout after repeated failed login attempts
- Password history tracking — prevents reuse of previously set passwords
- Text Readability Analyzer supporting both plain text and PDF uploads
- Admin panel for user management
- Redesigned UI with a glassmorphism neon cyber theme

---

## 🚀 Features Implemented

| # | Feature | Status |
|---|---------|--------|
| 1 | Persistent SQLite Database (3 tables) | ✅ |
| 2 | bcrypt Password Hashing with Salt | ✅ |
| 3 | Password History — Prevent Reuse | ✅ |
| 4 | Old Password Detection on Login | ✅ |
| 5 | Rate Limiting (3 attempts → 60s lockout) | ✅ |
| 6 | Email Regex Validation | ✅ |
| 7 | Password Strength Meter (Weak / Medium / Strong) | ✅ |
| 8 | OTP Generation using HMAC-SHA1 (RFC 4226) | ✅ |
| 9 | OTP Wrapped in JWT Token (hashed + expiring) | ✅ |
| 10 | OTP Email Delivery via Gmail SMTP | ✅ |
| 11 | Multi-Step Password Recovery Flow | ✅ |
| 12 | JWT Session Management (30 min expiry) | ✅ |
| 13 | Protected Dashboard with Sidebar Navigation | ✅ |
| 14 | Text Readability Analyzer (TXT + PDF upload) | ✅ |
| 15 | Admin Panel (View & Delete Users) | ✅ |
| 16 | Neon Glassmorphism UI Theme | ✅ |
| 17 | Logout Functionality | ✅ |

--

## 🗄️ Database Schema

Three SQLite tables manage all user data:

```sql
-- Stores registered users
CREATE TABLE users (
    email      TEXT PRIMARY KEY,
    password   BLOB,        -- bcrypt hashed
    created_at TEXT
);

-- Tracks all past passwords per user
CREATE TABLE password_history (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    email    TEXT,
    password BLOB,          -- bcrypt hashed
    set_at   TEXT,
    FOREIGN KEY(email) REFERENCES users(email)
);

-- Tracks failed login attempts for rate limiting
CREATE TABLE login_attempts (
    email        TEXT PRIMARY KEY,
    attempts     INTEGER DEFAULT 0,
    last_attempt REAL     -- Unix timestamp
);
```

---

## 🔐 OTP Verification Flow

The forgot password system uses a **4-stage flow**:

```
📧 Enter Email  →  📨 Send OTP  →  ✅ Verify Code  →  🔒 Reset Password
```



## 📖 Readability Analyzer

Supports **plain text input** and **PDF / TXT file upload**.  
Calculates 5 industry-standard academic readability metrics:

| Metric | What it measures |
|--------|-----------------|
| Flesch Reading Ease | 0–100 score — higher means easier to read |
| Flesch-Kincaid Grade | US school grade level equivalent |
| SMOG Index | Years of education needed — common in medical writing |
| Gunning Fog | Based on sentence length and complex words |
| Coleman-Liau | Uses character counts instead of syllables |

Results are displayed as **interactive gauge charts** alongside text statistics (sentence count, word count, syllables, complex words, character count).

---



## 📸 Screenshots

<img width="1470" height="730" alt="Screenshot 2026-02-23 at 6 09 43 PM" src="https://github.com/user-attachments/assets/4db8c1fa-2270-4bc9-82f2-576eccd5ac07" />

<img width="1470" height="730" alt="Screenshot 2026-02-23 at 6 10 30 PM" src="https://github.com/user-attachments/assets/44fea5df-e837-4257-a9fb-7fc7dd03f4f2" />

<img width="1470" height="762" alt="Screenshot 2026-02-23 at 6 10 41 PM" src="https://github.com/user-attachments/assets/21c80312-5ff0-489d-8c7c-fa02879c8ab4" />

<img width="1470" height="762" alt="Screenshot 2026-02-23 at 6 10 48 PM" src="https://github.com/user-attachments/assets/d4a21306-05bd-498b-9bdd-ec012fda4d31" />

<img width="1470" height="762" alt="Screenshot 2026-02-23 at 6 10 57 PM" src="https://github.com/user-attachments/assets/e7b013db-de9a-4ccf-afe0-a1961d42595c" />




