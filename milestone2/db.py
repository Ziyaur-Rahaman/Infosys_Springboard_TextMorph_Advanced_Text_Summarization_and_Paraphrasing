
import sqlite3
import bcrypt
import datetime
import time

DB_NAME = "users.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users
                 (email TEXT PRIMARY KEY, password BLOB, created_at TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS password_history
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  email TEXT,
                  password BLOB,
                  set_at TEXT,
                  FOREIGN KEY(email) REFERENCES users(email))""")
    c.execute("""CREATE TABLE IF NOT EXISTS login_attempts
                 (email TEXT PRIMARY KEY,
                  attempts INTEGER DEFAULT 0,
                  last_attempt REAL)""")
    conn.commit()
    conn.close()

def _get_timestamp():
    return datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

def register_user(email, password):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        now = _get_timestamp()
        c.execute("INSERT INTO users (email, password, created_at) VALUES (?, ?, ?)", (email, hashed, now))
        c.execute("INSERT INTO password_history (email, password, set_at) VALUES (?, ?, ?)", (email, hashed, now))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def authenticate_user(email, password):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE email = ?", (email,))
    data = c.fetchone()
    conn.close()
    if data:
        stored_hash = data[0]
        if bcrypt.checkpw(password.encode("utf-8"), stored_hash):
            _reset_attempts(email)
            return True
    _record_failed_attempt(email)
    return False

def check_is_old_password(email, password):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT password, set_at FROM password_history WHERE email = ? ORDER BY set_at DESC", (email,))
    history = c.fetchall()
    conn.close()
    for stored_hash, set_at in history:
        if bcrypt.checkpw(password.encode("utf-8"), stored_hash):
            return set_at
    return None

def check_password_reused(email, new_password):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT password FROM password_history WHERE email = ?", (email,))
    history = c.fetchall()
    conn.close()
    for (stored_hash,) in history:
        if bcrypt.checkpw(new_password.encode("utf-8"), stored_hash):
            return True
    return False

def check_user_exists(email):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT 1 FROM users WHERE email = ?", (email,))
    data = c.fetchone()
    conn.close()
    return data is not None

def update_password(email, new_password):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(new_password.encode("utf-8"), salt)
    now = _get_timestamp()
    c.execute("UPDATE users SET password = ? WHERE email = ?", (hashed, email))
    c.execute("INSERT INTO password_history (email, password, set_at) VALUES (?, ?, ?)", (email, hashed, now))
    conn.commit()
    conn.close()

MAX_ATTEMPTS = 3
LOCKOUT_SECONDS = 60

def _record_failed_attempt(email):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    now = time.time()
    c.execute("SELECT attempts, last_attempt FROM login_attempts WHERE email = ?", (email,))
    row = c.fetchone()
    if row:
        attempts, last = row
        if now - last > LOCKOUT_SECONDS:
            c.execute("UPDATE login_attempts SET attempts = 1, last_attempt = ? WHERE email = ?", (now, email))
        else:
            c.execute("UPDATE login_attempts SET attempts = ?, last_attempt = ? WHERE email = ?", (attempts + 1, now, email))
    else:
        c.execute("INSERT INTO login_attempts (email, attempts, last_attempt) VALUES (?, 1, ?)", (email, now))
    conn.commit()
    conn.close()

def _reset_attempts(email):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM login_attempts WHERE email = ?", (email,))
    conn.commit()
    conn.close()

def is_rate_limited(email):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT attempts, last_attempt FROM login_attempts WHERE email = ?", (email,))
    row = c.fetchone()
    conn.close()
    if row:
        attempts, last = row
        elapsed = time.time() - last
        if attempts >= MAX_ATTEMPTS and elapsed < LOCKOUT_SECONDS:
            return True, LOCKOUT_SECONDS - elapsed
    return False, 0

def get_all_users():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT email, created_at FROM users ORDER BY created_at DESC")
    users = c.fetchall()
    conn.close()
    return users

def delete_user(email):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM password_history WHERE email = ?", (email,))
    c.execute("DELETE FROM login_attempts WHERE email = ?", (email,))
    c.execute("DELETE FROM users WHERE email = ?", (email,))
    conn.commit()
    conn.close()
