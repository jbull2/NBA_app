import streamlit as st
import json
import os

from itsdangerous import URLSafeTimedSerializer, BadSignature
from streamlit_cookies_manager import EncryptedCookieManager


# ---------------------------
# Load secrets (Render + local)
# ---------------------------
def load_secrets():
    if "STREAMLIT_SECRETS" in os.environ:
        return json.loads(os.environ["STREAMLIT_SECRETS"])

    try:
        return st.secrets
    except Exception:
        return {}

SECRETS = load_secrets()


# ---------------------------
# Config
# ---------------------------
AUTH_SECRET = SECRETS.get("auth", {}).get("secret_key", "dev-secret-key")
COOKIE_NAME = "nba_app_auth"
COOKIE_MAX_AGE = 60 * 60 * 24 * 7  # 7 days


# ---------------------------
# Cookie + token setup
# ---------------------------
serializer = URLSafeTimedSerializer(AUTH_SECRET)

cookies = EncryptedCookieManager(
    prefix="nba_app_",
    password=AUTH_SECRET
)

# Required by streamlit-cookies-manager
if not cookies.ready():
    st.stop()


# ---------------------------
# Helpers
# ---------------------------
def set_login_cookie(username: str):
    token = serializer.dumps(username)
    cookies[COOKIE_NAME] = token
    cookies.save()


def clear_login_cookie():
    if COOKIE_NAME in cookies:
        del cookies[COOKIE_NAME]
        cookies.save()


def get_logged_in_user():
    token = cookies.get(COOKIE_NAME)
    if not token:
        return None

    try:
        return serializer.loads(token, max_age=COOKIE_MAX_AGE)
    except BadSignature:
        return None


# ---------------------------
# Main auth gate
# ---------------------------
def require_login():
    # Restore session from cookie
    user = get_logged_in_user()
    if user:
        st.session_state.authenticated = True
        st.session_state.user = user
        return True

    st.session_state.authenticated = False

    users = SECRETS.get("auth", {}).get("users", {})

    if not users:
        st.error("Authentication is not configured.")
        return False

    st.title("🔐 Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username in users and password == users[username]:
            st.session_state.authenticated = True
            st.session_state.user = username
            set_login_cookie(username)
            st.rerun()
        else:
            st.error("Invalid username or password")

    return False


# ---------------------------
# Logout helper
# ---------------------------
def logout():
    clear_login_cookie()
    st.session_state.authenticated = False
    st.session_state.user = None
    st.rerun()