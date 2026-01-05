import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta

# --- CONFIGURATION CHECK ---
SUPA_URL = st.secrets.get("supabase", {}).get("url")
SUPA_KEY = st.secrets.get("supabase", {}).get("key")

if not SUPA_URL or not SUPA_KEY:
    st.error("❌ CRITICAL ERROR: Supabase Credentials missing in secrets.toml")
    st.stop()

# --- CONNECT TO DB ---
try:
    supabase: Client = create_client(SUPA_URL, SUPA_KEY)
except Exception as e:
    st.error(f"❌ DATABASE CONNECTION FAILED: {e}")
    st.stop()

# --- FUNCTIONS ---
def login_user(email):
    """Fetch user details from Supabase"""
    try:
        response = supabase.table("users").select("*").eq("email", email).execute()
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        st.error(f"Login Failed: {e}")
        return None

def register_user_in_db(email, plan_type, credits, days_valid):
    """
    UPSERT: Creates new user OR updates existing user.
    """
    expiry = datetime.now() + timedelta(days=days_valid)
    
    data = {
        "email": email,
        "plan_type": plan_type,
        "credits": credits,
        "expiry_date": expiry.isoformat()
    }
    
    try:
        response = supabase.table("users").upsert(data).execute()
        return True
    except Exception as e:
        st.error(f"Registration Error: {e}")
        return False

def deduct_credit(email, current_credits):
    """Updates user credits"""
    try:
        new_credits = max(0, current_credits - 1)
        supabase.table("users").update({"credits": new_credits}).eq("email", email).execute()
        return new_credits
    except Exception as e:
        st.error(f"Credit Deduction Failed: {e}")
        return current_credits