import streamlit as st
from groq import Groq
from supabase import create_client, Client
from docx import Document
from docx.shared import Pt
import io
import time
from datetime import datetime, timedelta
import dateutil.parser # Helps parse DB timestamps

# --- ⚠️ CONFIGURATION ---
try:
    # API Keys
    GROQ_API_KEY = st.secrets["groq"]["api_key"]
    SUPA_URL = st.secrets["supabase"]["url"]
    SUPA_KEY = st.secrets["supabase"]["key"]
    
    # Links
    LINK_SINGLE = st.secrets["LINK_SINGLE"]
    LINK_MONTHLY = st.secrets["LINK_MONTHLY"]
    PAYPAL_ME_LINK = st.secrets["PAYPAL_ME_LINK"]
    
    # Initialize DB
    supabase: Client = create_client(SUPA_URL, SUPA_KEY)
    DB_CONNECTED = True
except Exception as e:
    st.error(f"Configuration Error: {e}. Check secrets.toml.")
    DB_CONNECTED = False
    GROQ_API_KEY = ""

# --- PAGE CONFIG ---
st.set_page_config(page_title="AI Resume Pro", page_icon="🌍", layout="wide")

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

# --- SESSION STATE INITIALIZATION ---
if 'user_data' not in st.session_state: st.session_state.user_data = None
if 'generated_resume' not in st.session_state: st.session_state.generated_resume = None
if 'demo_cache' not in st.session_state: st.session_state.demo_cache = {}

# =========================================================
# 🗄️ DATABASE FUNCTIONS
# =========================================================

def login_user(email):
    """Fetch user details from Supabase"""
    if not DB_CONNECTED: return None
    try:
        response = supabase.table("users").select("*").eq("email", email).execute()
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        return None

def register_user(email, plan_type, credits, days_valid):
    """Create or Update a user in Supabase"""
    if not DB_CONNECTED: return False
    
    expiry = datetime.now() + timedelta(days=days_valid)
    
    data = {
        "email": email,
        "plan_type": plan_type,
        "credits": credits,
        "expiry_date": expiry.isoformat()
    }
    
    try:
        # Upsert: Updates if exists, Inserts if new
        supabase.table("users").upsert(data).execute()
        return True
    except Exception as e:
        st.error(f"DB Error: {e}")
        return False

def deduct_credit(email, current_credits):
    """Reduce credit count by 1"""
    if not DB_CONNECTED: return
    try:
        new_credits = max(0, current_credits - 1)
        supabase.table("users").update({"credits": new_credits}).eq("email", email).execute()
        # Update local session to match
        st.session_state.user_data['credits'] = new_credits
    except Exception as e:
        st.error(f"Credit Update Failed: {e}")

# =========================================================
# 🔒 ACCESS & PAYMENT LOGIC
# =========================================================

def verify_code_simulated(code):
    """Simulate payment verification"""
    return len(code.strip()) >= 8

def show_auth_screen():
    st.markdown("<h1 style='text-align: center;'>🌍 Global AI Resume Builder</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Log in or choose a plan to start.</p>", unsafe_allow_html=True)

    # --- LOGIN SECTION ---
    with st.expander("🔑 Already have an account? Login here", expanded=True):
        col_em, col_btn = st.columns([3, 1])
        login_email = col_em.text_input("Enter your Email to Login:", key="login_field")
        if col_btn.button("Login / Refresh", use_container_width=True):
            user = login_user(login_email)
            if user:
                st.session_state.user_data = user
                st.success(f"Welcome back! You have {user['credits']} credits left.")
                time.sleep(1)
                st.rerun()
            else:
                st.error("User not found. Please purchase a plan below.")

    st.divider()

    # --- PRICING CARDS ---
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
        with st.popover("Buy Single Pass"):
            st.write("1. Pay **KES 50** via M-Pesa/IntaSend:")
            st.markdown(f"[**Pay Link**]({LINK_SINGLE})")
            st.write("2. Or Pay **$0.50** via PayPal:")
            st.markdown(f"[**PayPal Link**]({PAYPAL_ME_LINK}/0.50USD)")
            
            st.divider()
            email_pay = st.text_input("Your Email:", placeholder="For account creation")
            code_pay = st.text_input("Transaction Code:")
            
            if st.button("Verify & Activate Single Pass"):
                if verify_code_simulated(code_pay) and "@" in email_pay:
                    # Register in DB: Single Plan, 3 Credits, 1 Day access
                    if register_user(email_pay, "SINGLE", 3, 1):
                        st.session_state.user_data = login_user(email_pay)
                        st.balloons()
                        st.success("Activated! Redirecting...")
                        time.sleep(2)
                        st.rerun()
                else:
                    st.error("Invalid Code or Email.")

    # 3. MONTHLY TRIAL
    with c3:
        st.success("🏆 **Monthly Pro**\n\n**3 DAYS FREE TRIAL**\nThen KES 1000/mo.")
        with st.popover("Start Free Trial"):
            st.write("**Register for Trial**")
            t_email = st.text_input("Email Address")
            t_phone = st.text_input("Phone (for future billing)")
            t_method = st.radio("Future Payment:", ["M-Pesa", "Card", "PayPal"])
            
            if st.button("Start 3-Day Free Trial"):
                if "@" in t_email and len(t_phone) > 5:
                    # Register in DB: Monthly Trial, 9999 Credits, 3 Days access
                    if register_user(t_email, "TRIAL_MONTHLY", 9999, 3):
                        st.session_state.user_data = login_user(t_email)
                        st.balloons()
                        st.success("Trial Started! Redirecting...")
                        time.sleep(2)
                        st.rerun()
                else:
                    st.error("Invalid Details.")

# =========================================================
# ⚙️ MAIN APPLICATION
# =========================================================
def show_main_app():
    st.markdown(PROTECTED_CSS, unsafe_allow_html=True)
    
    user = st.session_state.user_data
    is_demo = user.get("plan_type") == "DEMO"
    
    # --- CHECK EXPIRY & CREDITS ---
    if not is_demo:
        # Check Date
        expiry_str = user.get('expiry_date')
        if expiry_str:
            expiry_dt = dateutil.parser.isoparse(expiry_str)
            # Remove timezone info for simple comparison
            if datetime.now(expiry_dt.tzinfo) > expiry_dt:
                st.error("⏳ Your plan has expired. Please renew.")
                if st.button("Logout"):
                    st.session_state.user_data = None
                    st.rerun()
                return

        # Check Credits
        credits_left = user.get('credits', 0)
        
        # Display Banner
        if user.get("plan_type") == "TRIAL_MONTHLY":
            days_left = (expiry_dt - datetime.now(expiry_dt.tzinfo)).days
            st.markdown(f"<div class='trial-banner'>💎 <b>TRIAL ACTIVE:</b> {days_left} days left. <b>Unlimited</b> generations.</div>", unsafe_allow_html=True)
        elif user.get("plan_type") == "SINGLE":
            st.markdown(f"<div class='trial-banner' style='background-color:#fff3cd; color:#856404; border-color:#ffeeba;'>⚡ <b>SINGLE PASS:</b> {credits_left} Generations Remaining.</div>", unsafe_allow_html=True)

    st.title("🚀 AI Resume Builder")
    
    # --- 1. CONFIGURATION ---
    st.subheader("1. Setup")
    col_cat, col_region, col_style = st.columns(3)
    
    with col_cat:
        cv_category = st.selectbox("Role / Industry", [
            "Corporate / Administration", "NGO / United Nations", 
            "Tech / Software / IT", "Medical / Healthcare",
            "Engineering", "Sales / Marketing",
            "Entry-Level / Internship"
        ])
    with col_region:
        cv_region = st.selectbox("Region / Standard", [
            "🇰🇪 Kenya / UK (Standard CV)", "🇺🇸 USA (Resume)",
            "🇪🇺 Europe (Europass)", "🇨🇦 Canada",
            "🇦🇪 Middle East", "🌏 International"
        ])
    with col_style:
        visual_style = st.selectbox("Visual Template", ["Modern Clean", "Classic Professional", "Executive"])

    # --- SIDEBAR INFO ---
    with st.sidebar:
        st.info(f"👤 User: {user.get('email')}")
        if is_demo:
            st.warning("👀 DEMO MODE")
            if st.button("Logout / Purchase"):
                st.session_state.user_data = None
                st.rerun()
        else:
            st.metric("Credits Left", user.get('credits', 0))
            if st.button("Logout"):
                st.session_state.user_data = None
                st.rerun()

    # --- 2. INPUTS (CENTERED) ---
    if is_demo:
        st.subheader(f"👁️ Preview: {cv_category}")
        cache_key = f"{cv_category}_{cv_region}"
        if cache_key not in st.session_state.demo_cache:
            st.session_state.demo_cache[cache_key] = generate_ai_content("DEMO", cv_region, "DEMO", "DEMO", "DEMO")
        st.markdown(f"<div class='protected-view'><div class='watermark'>DEMO</div>{st.session_state.demo_cache[cache_key]}</div>", unsafe_allow_html=True)
    
    else:
        st.header("2. Your Information")
        c_left, c_right = st.columns(2)
        with c_left:
             job_desc = st.text_area("Target Job Description (Optional):", height=250, placeholder="Paste job advert here...")
        with c_right:
             resume_text = st.text_area("Your Info (Work History, Education, Skills):", height=250, placeholder="Name: ...\nExperience: ...")

        # --- GENERATE BUTTON ---
        col_spacer, col_btn, col_spacer2 = st.columns([1, 2, 1])
        with col_btn:
            if st.button("🚀 Generate Optimized CV", type="primary", use_container_width=True):
                # Check DB credits again before generating
                current_user = login_user(user['email'])
                if current_user['credits'] < 1:
                    st.error("🚫 You have 0 credits left. Please top up.")
                elif not resume_text: 
                    st.warning("Please enter your information.")
                else:
                    with st.spinner("Connecting to AI..."):
                        res = generate_ai_content(cv_category, cv_region, visual_style, resume_text, job_desc)
                        st.session_state.generated_resume = res
                        
                        # 🔥 DEDUCT CREDIT IN DB
                        deduct_credit(user['email'], current_user['credits'])
                        st.success("Generated! Credit deducted.")
                        time.sleep(1)
                        st.rerun()

        # --- EDITOR & DOWNLOAD ---
        if st.session_state.generated_resume:
            st.divider()
            st.header("3. Review & Download")
            st.text_area("Editor:", st.session_state.generated_resume, height=600)
            st.download_button(f"📥 Download {cv_region} CV", create_styled_docx(st.session_state.generated_resume), "Professional_CV.docx", type="primary")

# =========================================================
# 🧠 AI & DOC HELPERS
# =========================================================
def generate_ai_content(cat, region, style, res, job):
    if cat == "DEMO": return "This is a demo preview text..."
    
    prompt = f"""
    Act as an expert Resume Writer for a '{cat}' role.
    TARGET REGION: {region}
    STYLE: {style}
    
    RULES:
    - USA: 1 page, no personal details.
    - Kenya/UK: Standard CV format.
    - Europe: Europass structure.
    
    USER INFO: {res}
    JOB DESC: {job}
    
    Return ONLY the resume text.
    """
    
    try:
        client = Groq(api_key=GROQ_API_KEY)
        return client.chat.completions.create(messages=[{"role":"user","content":prompt}],model="llama-3.3-70b-versatile").choices[0].message.content
    except Exception as e: return f"AI Error: {str(e)}"

def create_styled_docx(text):
    doc = Document()
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Calibri'
    font.size = Pt(11)
    for line in text.split('\n'):
        doc.add_paragraph(line)
    buffer = io.BytesIO(); doc.save(buffer); buffer.seek(0)
    return buffer

# --- RUN CHECK ---
if st.session_state.user_data is None:
    show_auth_screen()
else:
    show_main_app()
