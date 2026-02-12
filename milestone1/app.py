
import streamlit as st
import jwt
import datetime
import time
import re

# --- Configuration ---
SECRET_KEY = "super_secret_key_for_demo"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# --- JWT Utils ---
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except:
        return None

# --- Validation ---
def is_valid_email(email):
    pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
    return bool(re.match(pattern, email))

def is_valid_password(password):
    if len(password) < 8:
        return False
    if not password.isalnum():
        return False
    return True

# --- Session Initialization ---
if "jwt_token" not in st.session_state:
    st.session_state.jwt_token = None

if "page" not in st.session_state:
    st.session_state.page = "login"

if "users" not in st.session_state:
    # Structure:
    # {
    #   email: {
    #       username,
    #       password,
    #       security_question,
    #       security_answer
    #   }
    # }
    st.session_state.users = {}

# --- Security Questions ---
SECURITY_QUESTIONS = [
    "What is your pet name?",
    "What is your mother’s maiden name?",
    "What is your favorite teacher?"
]

# ============================
# LOGIN PAGE
# ============================
def login_page():
    st.title("Login")

    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")

        if submit:
            user = st.session_state.users.get(email)

            if user and user["password"] == password:
                token = create_access_token({"sub": email, "username": user["username"]})
                st.session_state.jwt_token = token
                st.success("Login successful!")
                time.sleep(0.5)
                st.rerun()
            else:
                st.error("Invalid email or password")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Create Account"):
            st.session_state.page = "signup"
            st.rerun()

    with col2:
        if st.button("Forgot Password"):
            st.session_state.page = "forgot_password"
            st.rerun()

# ============================
# SIGNUP PAGE
# ============================
def signup_page():
    st.title("Create Account")

    with st.form("signup_form"):
        username = st.text_input("Username")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")

        security_question = st.selectbox("Security Question", SECURITY_QUESTIONS)
        security_answer = st.text_input("Security Answer")

        submit = st.form_submit_button("Sign Up")

        if submit:
            errors = []

            if not username:
                errors.append("Username required")

            if not is_valid_email(email):
                errors.append("Invalid email")

            if email in st.session_state.users:
                errors.append("Email already exists")

            if not is_valid_password(password):
                errors.append("Password must be 8+ alphanumeric chars")

            if password != confirm_password:
                errors.append("Passwords do not match")

            if not security_answer:
                errors.append("Security answer required")

            if errors:
                for e in errors:
                    st.error(e)
            else:
                st.session_state.users[email] = {
                    "username": username,
                    "password": password,
                    "security_question": security_question,
                    "security_answer": security_answer.lower()
                }

                st.success("Account created successfully!")
                st.session_state.page = "login"
                st.rerun()

    if st.button("Back to Login"):
        st.session_state.page = "login"
        st.rerun()

# ============================
# FORGOT PASSWORD FLOW
# ============================
def forgot_password_page():
    st.title("Forgot Password")

    email = st.text_input("Enter your registered Email")

    if st.button("Verify Email"):
        user = st.session_state.users.get(email)

        if user:
            st.session_state.reset_email = email
            st.success("Email found!")
        else:
            st.error("Email not registered")

    if "reset_email" in st.session_state:
        user = st.session_state.users.get(st.session_state.reset_email)

        st.write("Security Question:")
        st.info(user["security_question"])

        answer = st.text_input("Enter Security Answer")

        if st.button("Verify Answer"):
            if answer.lower() == user["security_answer"]:
                st.session_state.allow_password_reset = True
                st.success("Answer verified! Set new password.")
            else:
                st.error("Incorrect security answer")

    if st.session_state.get("allow_password_reset"):
        new_password = st.text_input("New Password", type="password")

        if st.button("Update Password"):
            if is_valid_password(new_password):
                st.session_state.users[st.session_state.reset_email]["password"] = new_password
                st.success("Password updated successfully!")
                del st.session_state["reset_email"]
                del st.session_state["allow_password_reset"]
                st.session_state.page = "login"
                time.sleep(1)
                st.rerun()
            else:
                st.error("Password must be 8+ alphanumeric characters")

    if st.button("Back to Login"):
        st.session_state.page = "login"
        st.rerun()

# ============================
# DASHBOARD
# ============================
def dashboard_page():
    payload = verify_token(st.session_state.jwt_token)

    if not payload:
        st.session_state.jwt_token = None
        st.session_state.page = "login"
        st.rerun()

    st.sidebar.title("Menu")
    if st.sidebar.button("Logout"):
        st.session_state.jwt_token = None
        st.session_state.page = "login"
        st.rerun()

    st.title(f"Welcome {payload['username']} 👋")
    st.write("This is your dashboard.")

# ============================
# MAIN ROUTER
# ============================
if st.session_state.jwt_token:
    dashboard_page()
else:
    if st.session_state.page == "signup":
        signup_page()
    elif st.session_state.page == "forgot_password":
        forgot_password_page()
    else:
        login_page()
