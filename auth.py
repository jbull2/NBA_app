import os
import streamlit as st


def get_users():
    """
    Load users from Streamlit secrets (local / Streamlit Cloud)
    or from environment variables (Render).
    """

    # 1️⃣ Streamlit secrets (local dev or Streamlit Cloud)
    if "auth" in st.secrets and "users" in st.secrets["auth"]:
        return dict(st.secrets["auth"]["users"])

    # 2️⃣ Environment variable fallback (Render)
    # Format: AUTH_USERS="user1:pass1,user2:pass2"
    env_users = os.getenv("AUTH_USERS")
    if env_users:
        return dict(pair.split(":") for pair in env_users.split(","))

    # 3️⃣ No auth configured
    return {}


def require_login():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    users = get_users()

    if not users:
        st.error("Authentication is not configured.")
        st.stop()

    st.title("🔐 Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username in users and password == users[username]:
            st.session_state.authenticated = True
            st.session_state.user = username
            st.rerun()
        else:
            st.error("Invalid username or password")

    return False