# Milestone 1 – User Authentication System

## 📌 Project Title
User Authentication System using Streamlit and JWT

---

## 📝 Description

In this milestone, we developed a user authentication system using **Streamlit** as the frontend framework and **JWT (JSON Web Token)** for secure session handling.

The application allows users to:

- Create an account with validation
- Login securely
- Access a protected dashboard
- Recover password using Security Question verification

User data is temporarily stored using **Streamlit session state (in-memory storage)** for demonstration purposes.

---

## 🚀 Features Implemented

- ✅ User Signup with input validation
- ✅ Email validation using Regex
- ✅ Password validation (minimum 8 characters, alphanumeric)
- ✅ Security Question selection (Dropdown)
- ✅ Security Answer verification
- ✅ Secure Login using JWT token
- ✅ Protected Dashboard after login
- ✅ Forgot Password functionality
- ✅ Password reset after correct security answer
- ✅ Logout functionality
- ✅ Session management using `st.session_state`

---

## 🛠 Technologies Used

- Python
- Streamlit
- PyJWT
- Regex
- Session State Management

