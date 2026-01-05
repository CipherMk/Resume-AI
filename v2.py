import streamlit as st
from groq import Groq
from supabase import create_client, Client
from docx import Document
from docx.shared import Pt
import io
import time
from datetime import datetime, timedelta
import dateutil.parser 

# --- PAGE CONFIG ---
st.set_page_config(page_title="AI Resume Pro", page_icon="🌍", layout="wide")

# --- ⚠️ ROBUST CONFIGURATION ---
GROQ_API_KEY = ""
SUPA_URL = ""
SUPA_KEY = ""
LINK_SINGLE = "https://example.com/pay"
LINK_MONTHLY = "https://example.com/subscribe"
PAYPAL_ME_LINK = "https://paypal.me/yourname"
DB_CONNECTED = False
supabase = None

try:
    # 1. Load Secrets safely
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
        # Auto-fix URL
        if not SUPA_URL.startswith("http"):
            SUPA_URL = f"https://{SUPA_URL}"
        
    # 2. Connect to DB
    if SUPA_URL and SUPA_KEY:
        supabase: Client = create_client(SUPA_URL, SUPA_KEY)
        DB_CONNECTED = True
    else:
        st.warning("⚠️ Database secrets missing. App running in offline mode.")

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
    background-color: #d4edda; color: #155724; padding: 15px;
    border-radius: 5px; text-align: center; margin-bottom: 20px; 
    border: 1px solid #c3e6cb; font-size: 1.1rem;
}
</style>
"""

# --- SESSION STATE ---
if 'user_data' not in st.session_state: st.session_state.user_data = None
if 'generated_resume' not in st.session_state: st.session_state.generated_resume = None
if 'demo_cache' not in st.session_state: st.session_state.demo_cache = {}

# =========================================================
# 🗄️ DATABASE FUNCTIONS
# =========================================================

def login_user(email):
    """Fetch user details from Supabase"""
    if not DB_CONNECTED: 
        if email == "test@test.com": return {"email": "test", "credits": 3, "plan_type": "SINGLE"}
        return None
    try:
        response = supabase.table("users").select("*").eq("email", email).execute()
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        st.error(f"DB Connection Error: {e}")
        return None

def register_user(email, plan_type, credits, days_valid):
    """
    UPSERT: Creates new user OR updates existing user.
    This handles registration automatically.
    """
    if not DB_CONNECTED: return False
    
    expiry = datetime.now() + timedelta(days=days_valid)
    
    data = {
        "email": email,
        "plan_type": plan_type,
        "credits": credits,
        "expiry_date": expiry.isoformat()
    }
    
    try:
        # .upsert() ensures we register new users OR update existing ones
        supabase.table("users").upsert(data).execute()
        return True
    except Exception as e:
        st.error(f"DB Registration Error: {e}")
        return False

def deduct_credit(email, current_credits):
    if not DB_CONNECTED: return
    try:
        new_credits = max(0, current_credits - 1)
        supabase.table("users").update({"credits": new_credits}).eq("email", email).execute()
        st.session_state.user_data['credits'] = new_credits
    except Exception as e:
        st.error(f"Credit Update Failed: {e}")

# =========================================================
# 🔒 AUTH SCREEN (LOGIN & REGISTER)
# =========================================================
def verify_code_simulated(code):
    return len(code.strip()) >= 8

def show_auth_screen():
    st.markdown("<h1 style='text-align: center;'>🌍 Global AI Resume Builder</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Enter your email to Login or Register automatically.</p>", unsafe_allow_html=True)
    
    if not DB_CONNECTED:
        st.warning("⚠️ Database not connected. Features will be limited.")

    # --- 1. MAIN LOGIN / AUTO-REGISTER ---
    with st.container():
        col_spacer, col_main, col_spacer2 = st.columns([1, 2, 1])
        with col_main:
            with st.form("auth_form"):
                st.subheader("🔑 Access Portal")
                login_email = st.text_input("Email Address:", placeholder="name@example.com").strip().lower()
                submitted = st.form_submit_button("🚀 Enter App", type="primary", use_container_width=True)
                
                if submitted:
                    if "@" not in login_email:
                        st.error("Please enter a valid email.")
                    else:
                        user = login_user(login_email)
                        
                        # IF NEW USER -> AUTO REGISTER AS FREE TIER
                        if not user:
                            register_user(login_email, "FREE_TIER", 0, 365)
                            user = login_user(login_email)
                            st.toast(f"🆕 Account created for {login_email}!")

                        if user:
                            st.session_state.user_data = user
                            st.success(f"✅ Welcome! Credits: {user.get('credits', 0)}")
                            time.sleep(1)
                            st.rerun()

    st.divider()
    st.markdown("<h3 style='text-align: center;'>💎 Purchase Credits</h3>", unsafe_allow_html=True)

    # --- 2. PRICING PLANS ---
    c1, c2, c3 = st.columns(3)
    
    # DEMO
    with c1:
        st.info("👶 **Free Demo**\n\nNo Download.\nView Examples Only.")
        if st.button("Enter Demo Mode", use_container_width=True):
            st.session_state.user_data = {"email": "guest", "plan_type": "DEMO", "credits": 0}
            st.rerun()
            
    # SINGLE PASS
    with c2:
        st.warning("⚡ **Single CV Pass**\n\n**KES 50 / $0.50**\n3 Generation Limit.")
        with st.popover("Buy Single Pass"):
            st.write("1. Pay **KES 50** via M-Pesa/IntaSend:")
            st.markdown(f"[**Pay Link**]({LINK_SINGLE})")
            st.write("2. Pay **$0.50** via PayPal:")
            st.markdown(f"[**PayPal Link**]({PAYPAL_ME_LINK}/0.50USD)")
            
            st.divider()
            email_pay = st.text_input("Your Email:", value=login_email if 'login_email' in locals() else "")
            code_pay = st.text_input("Transaction Code:")
            
            if st.button("Verify & Activate"):
                if verify_code_simulated(code_pay) and "@" in email_pay:
                    # Register/Update user to SINGLE plan
                    if register_user(email_pay, "SINGLE", 3, 1):
                        st.session_state.user_data = login_user(email_pay)
                        st.balloons()
                        st.success("✅ Account Registered & Pass Activated!")
                        time.sleep(2)
                        st.rerun()
                else:
                    st.error("Invalid Code/Email.")

    # MONTHLY TRIAL (UPDATED LOGIC)
    with c3:
        st.success("🏆 **Monthly Pro**\n\n**3 DAYS FREE TRIAL**\nThen KES 1000/mo.")
        with st.popover("Start Free Trial"):
            st.write("**Register & Start Trial**")
            t_email = st.text_input("Email Address", value=login_email if 'login_email' in locals() else "")
            t_phone = st.text_input("Phone (for future billing)")
            t_method = st.radio("Future Payment:", ["M-Pesa", "Card", "PayPal"])
            
            if st.button("Start 3-Day Free Trial"):
                if "@" in t_email and len(t_phone) > 5:
                    # ✅ THIS LINE REGISTERS THE USER AUTOMATICALLY
                    success = register_user(t_email, "TRIAL_MONTHLY", 9999, 3)
                    
                    if success:
                        # ✅ LOG THEM IN IMMEDIATELY
                        st.session_state.user_data = login_user(t_email)
                        st.balloons()
                        st.success("✅ Account Created & Trial Started! Redirecting...")
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error("Registration Failed. Check connection.")
                else:
                    st.error("Invalid Email or Phone.")

# =========================================================
# ⚙️ MAIN APP LOGIC
# =========================================================
def show_main_app():
    st.markdown(PROTECTED_CSS, unsafe_allow_html=True)
    
    user = st.session_state.user_data
    if not user:
        st.session_state.user_data = None
        st.rerun()
        return

    is_demo = user.get("plan_type") == "DEMO"
    
    # Check Expiry
    if not is_demo and user.get('expiry_date'):
        try:
            expiry_dt = dateutil.parser.isoparse(user['expiry_date'])
            now = datetime.now(expiry_dt.tzinfo)
            if now > expiry_dt:
                st.error("⏳ Your plan has expired. Please renew.")
                if st.button("Logout"):
                    st.session_state.user_data = None
                    st.rerun()
                return
            
            # Show Banners
            if user.get("plan_type") == "TRIAL_MONTHLY":
                days_left = (expiry_dt - now).days
                st.markdown(f"<div class='trial-banner'>💎 <b>TRIAL ACTIVE:</b> {days_left} days left. Unlimited generations.</div>", unsafe_allow_html=True)
            elif user.get("plan_type") == "SINGLE":
                st.markdown(f"<div class='trial-banner' style='background-color:#fff3cd; color:#856404; border-color:#ffeeba;'>⚡ <b>SINGLE PASS:</b> {user.get('credits',0)} Left.</div>", unsafe_allow_html=True)
        except: pass

    st.title("🚀 AI Resume Builder")
    
    # 1. SETUP
    st.subheader("1. Setup")
    col_cat, col_region, col_style = st.columns(3)
    with col_cat:
        cv_category = st.selectbox("Industry", ["Corporate", "NGO/Development", "Tech/IT", "Healthcare", "Engineering", "Sales", "Entry-Level"])
    with col_region:
        cv_region = st.selectbox("Standard", ["🇰🇪 Kenya/UK", "🇺🇸 USA (Resume)", "🇪🇺 Europass", "🇨🇦 Canada", "🇦🇪 Gulf/Middle East", "🌏 International"])
    with col_style:
        visual_style = st.selectbox("Template", ["Modern Clean", "Classic Professional", "Executive"])

    # SIDEBAR
    with st.sidebar:
        st.info(f"👤 {user.get('email')}")
        if not is_demo: st.metric("Credits", user.get('credits', 0))
        if st.button("Logout"):
            st.session_state.user_data = None
            st.rerun()

    # 2. INPUTS & GENERATE
    if is_demo:
        st.subheader(f"👁️ Preview: {cv_category}")
        cache_key = f"{cv_category}_{cv_region}"
        if cache_key not in st.session_state.demo_cache:
            st.session_state.demo_cache[cache_key] = generate_ai_content("DEMO", cv_region, "DEMO", "DEMO", "DEMO")
        st.markdown(f"<div class='protected-view'><div class='watermark'>DEMO</div>{st.session_state.demo_cache[cache_key]}</div>", unsafe_allow_html=True)
    else:
        st.header("2. Your Information")
        c_left, c_right = st.columns(2)
        with c_left: job_desc = st.text_area("Job Description:", height=250)
        with c_right: resume_text = st.text_area("Your Details:", height=250)

        col_sp, col_btn, col_sp2 = st.columns([1, 2, 1])
        with col_btn:
            if st.button("🚀 Generate Optimized CV", type="primary", use_container_width=True):
                # Verify credits one last time
                fresh_user = login_user(user['email'])
                creds = fresh_user['credits'] if fresh_user else user.get('credits', 0)
                
                if creds < 1:
                    st.error("🚫 0 Credits remaining. Please top up.")
                elif not resume_text:
                    st.warning("Enter details first.")
                else:
                    with st.spinner("AI Working..."):
                        res = generate_ai_content(cv_category, cv_region, visual_style, resume_text, job_desc)
                        st.session_state.generated_resume = res
                        if fresh_user: deduct_credit(user['email'], creds)
                        st.rerun()

        if st.session_state.generated_resume:
            st.divider()
            st.header("3. Download")
            st.text_area("Editor:", st.session_state.generated_resume, height=500)
            st.download_button("📥 Download .docx", create_styled_docx(st.session_state.generated_resume), "CV.docx", type="primary")

# =========================================================
# 🧠 AI HELPERS
# =========================================================
def generate_ai_content(cat, region, style, res, job):
    if cat == "DEMO": return "Demo Content..."
    if not GROQ_API_KEY: return "Error: API Key missing."
    prompt = f"Write a {region} style resume for {cat}. Style: {style}. \nUser Info: {res}\nJob: {job}"
    try:
        client = Groq(api_key=GROQ_API_KEY)
        return client.chat.completions.create(messages=[{"role":"user","content":prompt}],model="llama-3.3-70b-versatile").choices[0].message.content
    except Exception as e: return f"AI Error: {e}"

def create_styled_docx(text):
    doc = Document()
    style = doc.styles['Normal']; font = style.font; font.name = 'Calibri'; font.size = Pt(11)
    for line in text.split('\n'): doc.add_paragraph(line)
    buffer = io.BytesIO(); doc.save(buffer); buffer.seek(0)
    return buffer

if st.session_state.user_data is None:
    show_auth_screen()
else:
    show_main_app()
