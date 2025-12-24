import streamlit as st
import json
import os

def load_secrets():
    if "STREAMLIT_SECRETS" in os.environ:
        return json.loads(os.environ["STREAMLIT_SECRETS"])

    try:
        return st.secrets
    except Exception:
        return {}

SECRETS = load_secrets()

def require_login():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    users = SECRETS.get("auth", {}).get("users", {})

    if not users:
        st.error("Authentication is not configured.")
        return False

    if st.session_state.authenticated:
        return True

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