"""
🔐 Authentication & User Login Page
"""
import streamlit as st
import json
import urllib.request
import urllib.error
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

st.set_page_config(
    page_title="User Login",
    page_icon="🔐",
    layout="centered",
    initial_sidebar_state="expanded",
)

FIREBASE_API_KEY = "AIzaSyDTBL6quWZuxDVj2k4QPBCKYvRSWN9GNIs"

def firebase_auth_api(action: str, payload: dict):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:{action}?key={FIREBASE_API_KEY}"
    data = json.dumps({**payload, "returnSecureToken": True}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8")), None
    except urllib.error.HTTPError as e:
        err_data = json.loads(e.read().decode("utf-8"))
        msg = err_data.get("error", {}).get("message", "Authentication failed")
        if "INVALID_LOGIN_CREDENTIALS" in msg or "INVALID_PASSWORD" in msg or "wrong-password" in msg:
            msg = "Incorrect email or password."
        elif "EMAIL_NOT_FOUND" in msg or "USER_NOT_FOUND" in msg:
            msg = "No account found with this email."
        elif "EMAIL_EXISTS" in msg:
            msg = "An account with this email already exists."
        return None, msg
    except Exception as e:
        return None, str(e)

# Custom Styling
st.markdown("""
<style>
    .auth-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 16px;
        padding: 2rem;
        box-shadow: 0 10px 25px rgba(0,0,0,0.3);
        margin-bottom: 2rem;
    }
    .profile-card {
        background: #0f172a;
        border: 1px solid #059669;
        border-radius: 14px;
        padding: 1.5rem;
        text-align: center;
        color: white;
    }
    .avatar-icon {
        font-size: 3rem;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

st.title("🔐 User Authentication")
st.markdown("Access your BioPolymer AI Screening account, manage sessions, and save recommendation projects.")

user = st.session_state.get("firebase_user")

if user:
    st.markdown('<div class="profile-card">', unsafe_allow_html=True)
    st.markdown('<div class="avatar-icon">👤</div>', unsafe_allow_html=True)
    st.subheader(f"Welcome back, {user.get('displayName') or 'Researcher'}!")
    st.markdown(f"**Email:** `{user.get('email')}`")
    st.markdown(f"**User ID:** `{user.get('uid')}`")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 Go to Recommendations", use_container_width=True, type="primary"):
            st.switch_page("pages/1_Recommend.py")
    with col2:
        if st.button("🚪 Sign Out", use_container_width=True):
            st.session_state.pop("firebase_user", None)
            st.session_state.pop("id_token", None)
            st.success("Successfully signed out.")
            st.rerun()

else:
    tab1, tab2 = st.tabs(["🔑 Sign In", "📝 Create Account"])

    with tab1:
        st.subheader("Sign In to Your Account")
        login_email = st.text_input("Email Address", key="login_email", placeholder="researcher@biopolymer.ai")
        login_pass = st.text_input("Password", type="password", key="login_pass", placeholder="••••••••")

        if st.button("Sign In", type="primary", use_container_width=True):
            if not login_email or not login_pass:
                st.error("Please enter both email and password.")
            else:
                with st.spinner("Authenticating..."):
                    res, err = firebase_auth_api("signInWithPassword", {"email": login_email, "password": login_pass})
                    if err:
                        st.error(f"❌ {err}")
                    else:
                        st.session_state["firebase_user"] = {
                            "email": res.get("email"),
                            "displayName": res.get("displayName") or login_email.split("@")[0].title(),
                            "uid": res.get("localId")
                        }
                        st.session_state["id_token"] = res.get("idToken")
                        st.success("✅ Signed in successfully! Redirecting...")
                        st.rerun()

    with tab2:
        st.subheader("Register New Researcher Account")
        reg_name = st.text_input("Full Name", key="reg_name", placeholder="Dr. Alex Morgan")
        reg_email = st.text_input("Email Address", key="reg_email", placeholder="researcher@biopolymer.ai")
        reg_pass = st.text_input("Password (min 6 chars)", type="password", key="reg_pass", placeholder="••••••••")

        if st.button("Create Account", type="primary", use_container_width=True):
            if not reg_email or not reg_pass:
                st.error("Please provide email and password.")
            elif len(reg_pass) < 6:
                st.error("Password must be at least 6 characters long.")
            else:
                with st.spinner("Creating Firebase account..."):
                    res, err = firebase_auth_api("signUp", {"email": reg_email, "password": reg_pass})
                    if err:
                        st.error(f"❌ {err}")
                    else:
                        if reg_name:
                            firebase_auth_api("update", {"idToken": res["idToken"], "displayName": reg_name})
                        st.session_state["firebase_user"] = {
                            "email": res.get("email"),
                            "displayName": reg_name or reg_email.split("@")[0].title(),
                            "uid": res.get("localId")
                        }
                        st.session_state["id_token"] = res.get("idToken")
                        st.success("✅ Account created successfully! You are now logged in.")
                        st.rerun()

st.divider()
st.caption("🔒 Secured via Google Firebase Authentication & TLS 1.3 Encryption")
