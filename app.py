# app.py
import os
import requests
import streamlit as st
import msal
from dotenv import load_dotenv

load_dotenv()

TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")

AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPES = ["User.Read"]

st.set_page_config(page_title="Microsoft Login (Device Code)", layout="centered")
st.title("Microsoft login (Device Code)")

def die_ui(msg: str):
    st.error(msg)
    st.stop()

def graph_get(url: str, token: str):
    r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=30)
    if r.status_code >= 400:
        die_ui(f"{r.status_code} {r.text}")
    return r.json()

def build_app():
    if not TENANT_ID or not CLIENT_ID:
        die_ui("Missing TENANT_ID or CLIENT_ID in environment (.env).")

    return msal.PublicClientApplication(CLIENT_ID, authority=AUTHORITY)

app = build_app()

# Session state init
st.session_state.setdefault("flow", None)
st.session_state.setdefault("token", None)
st.session_state.setdefault("me", None)

# If already logged in, show identity
if st.session_state["me"]:
    me = st.session_state["me"]
    st.success("LOGIN OK")
    st.subheader("I am")
    st.write(f"**Name:** {me.get('displayName')}")
    st.write(f"**Email:** {me.get('userPrincipalName')}")
    st.write(f"**ID:** {me.get('id')}")
    if st.button("Log out (clear session)"):
        st.session_state["flow"] = None
        st.session_state["token"] = None
        st.session_state["me"] = None
        st.rerun()
    st.stop()

col1, col2 = st.columns(2)

with col1:
    if st.button("Start login"):
        flow = app.initiate_device_flow(scopes=SCOPES)
        if "message" not in flow:
            die_ui(f"Device flow init failed: {flow}")
        st.session_state["flow"] = flow
        st.session_state["token"] = None
        st.session_state["me"] = None
        st.rerun()

with col2:
    if st.button("I already signed in (check)"):
        if not st.session_state["flow"]:
            die_ui("No active login flow. Click “Start login” first.")
        result = app.acquire_token_by_device_flow(st.session_state["flow"])
        token = result.get("access_token")
        if not token:
            # Common case: authorization_pending while you haven't finished in browser
            err = result.get("error")
            desc = result.get("error_description", "")
            if err:
                st.warning(f"{err}: {desc}")
            else:
                st.warning(str(result))
            st.stop()

        st.session_state["token"] = token
        st.session_state["me"] = graph_get("https://graph.microsoft.com/v1.0/me", token)
        st.rerun()

flow = st.session_state["flow"]
if not flow:
    st.info("Click **Start login** to begin.")
    st.stop()

# Show instructions and a link that opens in a NEW TAB
st.subheader("Step 1 — Open Microsoft login in a new tab")

login_url = (
    flow.get("verification_uri_complete")
    or flow.get("verification_uri")
    or "https://microsoft.com/devicelogin"
)

# This opens in a new tab in Streamlit
st.link_button("Open Microsoft sign-in (new tab)", login_url)

st.write("Step 2 — Enter this code:")
st.code(flow.get("user_code", ""), language="text")

# Optional: show the full message MSAL provides (helpful for users)
with st.expander("Show full device-flow message"):
    st.write(flow.get("message", ""))

st.subheader("Step 3 — After you finish in the browser")
st.write("Come back here and click **I already signed in (check)**.")

