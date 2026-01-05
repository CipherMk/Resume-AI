import streamlit as st
from groq import Groq
from supabase import create_client, Client # Added Supabase import
from docx import Document
from docx.shared import Pt
import io
import time
from datetime import datetime, timedelta
import dateutil.parser

# --- PAGE CONFIG ---
st.set_page_config(page_title="AI Resume Pro", page_icon="🌍", layout="wide")

# --- ⚠️ ROBUST CONFIGURATION (DATABASE CONNECT) ---
GROQ_API_KEY = ""
SUPA_URL = ""
SUPA_KEY = ""
LINK_SINGLE = "https://example.com"
LINK_MONTHLY = "https://example.com"
PAYPAL_ME_LINK = "https://paypal.me"
DB_CONNECTED = False
supabase = None

try:
    # 1. Load Secrets Safely
    if "LINK_SINGLE" in st.secrets: LINK_SINGLE = st.secrets["LINK_SINGLE"]
    if "LINK_MONTHLY" in st.secrets: LINK_MONTHLY = st.secrets["LINK_MONTHLY"]
    if "PAYPAL_ME_LINK" in st.secrets: PAYPAL_ME_LINK = st.secrets["PAYPAL_ME_LINK"]
    
    if "groq" in st.secrets:
        GROQ_API_KEY = st.secrets["groq"]["api_key"]
    elif "GROQ_API_KEY" in st.secrets:
        GROQ_API_KEY = st.secrets["GROQ_API_KEY"]

    if "supabase" in st.secrets:
        SUPA_URL = st.secrets["supabase"]["url"].strip()
        SUPA_KEY = st.secrets["supabase"]["key"].strip()
        
        # 🔧 Auto-Fix URL (Adds https:// if missing)
        if not SUPA_URL.startswith("http"):
            SUPA_URL = f"https://{SUPA_URL}"

    # 2. Connect to Database
    if SUPA_URL and SUPA_KEY:
        try:
            supabase: Client = create_client(SUPA_URL, SUPA_KEY)
            DB_CONNECTED = True
        except Exception as e:
            st.warning(f"⚠️ DB Connection Error: {e}")
    else:
        st.warning("⚠️ Database secrets missing. Running offline.")

except Exception as e:
    st.error(f"⚠️ Config Error: {e}")

# --- CSS ---
PROTECTED_CSS = """
<style>
h1 { text-align: center; }
.protected-view {
    background-color: #f8f9fa; padding: 30px; border-radius: 10px;
    border: 1px solid #ddd; height: 600px; overflow-y: auto;
    font-family: "Times New Roman"; position: relative;
}
.watermark {
    position: absolute; top: 50%; left: 50%;
    transform: translate(-50%, -50%) rotate(-30deg);
    font-size: 80px; color: rgba(0,0,0,0.05); font-weight: 900;
}
.trial-banner {
    background-color: #d4edda; color: #155724; padding: 10px;
    border-radius: 5px; text-align: center; margin-bottom: 20px; border: 1px solid #c3e6cb;
}
</style>
"""

# --- SESSION STATE ---
if 'user_data' not in st.session_state: st.session_state.user_data = None
if 'generated_resume' not in st.session_state: st.session_state.generated_resume = None
if 'demo_cache' not in st.session_state: st.session_state.demo_cache = {}
if 'selected_plan' not in st.session_state: st.session_state.selected_plan = None

# =========================================================
# 🗄️ DATABASE FUNCTIONS (NEW)
# =========================================================

def login_user(email):
    """Fetch user from Supabase"""
    if not DB_CONNECTED: return None
    try:
        response = supabase.table("users").select("*").eq("email", email).execute()
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        print(e)
        return None

def register_user(email, plan_type, credits, days_valid):
    """Register or Update user in Supabase"""
    if not DB_CONNECTED: return False
    
    expiry = datetime.now() + timedelta(days=days_valid)
    
    data = {
        "email": email,
        "plan_type": plan_type,
        "credits": credits,
        "expiry_date": expiry.isoformat()
    }
    
    try:
        # Upsert: Creates new or updates existing
        supabase.table("users").upsert(data).execute()
        return True
    except Exception as e:
        st.error(f"Registration Error: {e}")
        return False

def update_credits(email, new_credits):
    if DB_CONNECTED:
        supabase.table("users").update({"credits": new_credits}).eq("email", email).execute()

# =========================================================
# 🔒 PAYMENT & AUTH SCREEN
# =========================================================
def show_payment_screen():
    st.markdown("<h1 style='text-align: center;'>🌍 Global AI Resume Builder</h1>", unsafe_allow_html=True)
    
    if not DB_CONNECTED:
        st.error("⚠️ Database is Offline. Check Secrets.")

    # --- 1. LOGIN SECTION (NEW) ---
    with st.expander("🔑 Already have an account? Login here", expanded=False):
        l_col1, l_col2 = st.columns([3,1])
        login_email = l_col1.text_input("Enter Email to Login:")
        if l_col2.button("Login", use_container_width=True):
            user = login_user(login_email)
            if user:
                st.session_state.user_data = user
                st.success("Welcome back!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("User not found.")

    st.divider()
    st.markdown("<p style='text-align: center;'>Select a plan to start.</p>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    
    # 1. DEMO
    with c1:
        st.info("👶 **Free Demo**\n\nNo Download.\nView Examples Only.")
        if st.button("Enter Demo Mode", use_container_width=True):
            st.session_state.user_data = {"email": "guest", "plan_type": "DEMO", "credits": 0}
            st.rerun()
            
    # 2. SINGLE PASS
    with c2:
        st.warning("⚡ **Single CV Pass**\n\n**KES 50 / $0.50**\n3 Generation Limit.")
        if st.button("Select Single Pass", key="btn_single", use_container_width=True):
            st.session_state.selected_plan = "Single"
            
    # 3. MONTHLY TRIAL
    with c3:
        st.success("🏆 **Monthly Pro**\n\n**3 DAYS FREE TRIAL**\nThen KES 1000/mo.")
        if st.button("Start Free Trial", key="btn_monthly", use_container_width=True):
            st.session_state.selected_plan = "Monthly"

    st.divider()

    # --- PLAN LOGIC ---
    if st.session_state.selected_plan == "Single":
        st.subheader("💳 One-Time Payment: Single Pass")
        st.write("1. Pay **KES 50** or **$0.50** via links below.")
        st.markdown(f"[**Pay KES 50 (M-Pesa)**]({LINK_SINGLE}) | [**Pay $0.50 (PayPal)**]({PAYPAL_ME_LINK}/0.50USD)")
        
        st.write("2. Activate Account:")
        c_email, c_code = st.columns(2)
        act_email = c_email.text_input("Your Email:")
        trans_code = c_code.text_input("Transaction Code:")
        
        if st.button("Verify & Activate", type="primary"):
            if len(trans_code) > 5 and "@" in act_email:
                # REGISTER USER IN DB
                if register_user(act_email, "SINGLE", 3, 1):
                    st.session_state.user_data = login_user(act_email)
                    st.balloons()
                    st.success("Activated! Redirecting...")
                    time.sleep(2)
                    st.rerun()
            else:
                st.error("Invalid Code/Email")

    elif st.session_state.selected_plan == "Monthly":
        st.subheader("📝 Start Your 3-Day Free Trial")
        st.info("Billing of **KES 1000** starts automatically after 3 days.")
        
        with st.form("trial_form"):
            col_email, col_phone = st.columns(2)
            email = col_email.text_input("Email Address", placeholder="name@example.com")
            phone = col_phone.text_input("Phone Number", placeholder="07...")
            pay_method = st.radio("Select Future Payment Method", ["M-Pesa (Auto-Debit)", "Visa / MasterCard", "PayPal"], horizontal=True)
            
            st.markdown("---")
            # --- 🔥 THIS IS THE UPDATE YOU ASKED FOR 🔥 ---
            if st.form_submit_button("✅ Confirm & Start Free Trial", type="primary"):
                if "@" in email and len(phone) > 5:
                    with st.spinner("Registering Account..."):
                        # REGISTER USER IN DB
                        success = register_user(email, "TRIAL_MONTHLY", 9999, 3)
                        
                        if success:
                            st.session_state.user_data = login_user(email)
                            st.balloons()
                            st.success(f"✅ Trial Activated for {email}!")
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error("Database Error. Check connection.")
                else:
                    st.error("Invalid details.")

# =========================================================
# ⚙️ MAIN APP LOGIC
# =========================================================
def show_main_app():
    st.markdown(PROTECTED_CSS, unsafe_allow_html=True)
    
    user = st.session_state.user_data
    if not user: 
        st.rerun()
        return

    # Check Plan Status
    plan = user.get("plan_type")
    credits = user.get("credits", 0)
    
    # Expiry Check
    if plan != "DEMO":
        try:
            expiry = dateutil.parser.isoparse(user['expiry_date'])
            now = datetime.now(expiry.tzinfo)
            if now > expiry:
                st.error("⏳ Plan Expired. Please Renew.")
                if st.button("Back to Payment"):
                    st.session_state.user_data = None
                    st.rerun()
                return
            
            # Show Banner
            if plan == "TRIAL_MONTHLY":
                days = (expiry - now).days
                st.markdown(f"<div class='trial-banner'>💎 <b>TRIAL ACTIVE:</b> {days} days remaining. Unlimited Generations.</div>", unsafe_allow_html=True)
        except: pass

    is_demo = (plan == "DEMO")
    
    st.title("🚀 AI Resume Builder")
    
    # --- 1. SETUP ---
    st.subheader("1. Setup")
    col_cat, col_region, col_style = st.columns(3)
    
    with col_cat:
        cv_category = st.selectbox("Role / Industry", ["Corporate", "NGO / UN", "Tech / IT", "Healthcare", "Engineering", "Sales", "Entry-Level"])
    with col_region:
        cv_region = st.selectbox("Format Standard", ["🇰🇪 Kenya / UK", "🇺🇸 USA (Resume)", "🇪🇺 Europass", "🇨🇦 Canada", "🇦🇪 Middle East"])
    with col_style:
        visual_style = st.selectbox("Visual Style", ["Modern Clean", "Classic Professional", "Executive"])

    # --- SIDEBAR ---
    with st.sidebar:
        st.info(f"User: {user.get('email')}")
        if is_demo:
            st.warning("👀 DEMO MODE")
            if st.button("Unlock Full Access"):
                st.session_state.user_data = None
                st.rerun()
        else:
            st.metric("Credits Left", credits)
            if st.button("Logout"):
