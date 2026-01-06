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

# --- ⚠️ CONFIGURATION & SECRETS ---
GROQ_API_KEY = ""
SUPA_URL = ""
SUPA_KEY = ""
LINK_SINGLE = "https://example.com"
LINK_MONTHLY = "https://example.com"
PAYPAL_ME_LINK = "https://paypal.me"
DB_CONNECTED = False
supabase = None

# 1. Load Secrets Safely
try:
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
        pass 

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
/* Tab Styling */
div[data-testid="stTabs"] button {
    font-size: 18px;
    width: 100%;
}
</style>
"""

# --- SESSION STATE ---
if 'user_data' not in st.session_state: st.session_state.user_data = None
if 'generated_resume' not in st.session_state: st.session_state.generated_resume = None
if 'demo_cache' not in st.session_state: st.session_state.demo_cache = {}
if 'selected_plan' not in st.session_state: st.session_state.selected_plan = None

# =========================================================
# 🤖 AI & DOCX HELPER FUNCTIONS
# =========================================================

def generate_ai_content(role, region, style, user_info, job_desc):
    """Generates Resume Content using Groq or Demo Text"""
    if role == "DEMO":
        return "JOHN DOE\n\nPROFESSIONAL SUMMARY\nExperienced professional..."
    
    if not GROQ_API_KEY:
        return "⚠️ Error: Groq API Key is missing. Please add it to secrets.toml."

    try:
        client = Groq(api_key=GROQ_API_KEY)
        prompt = f"""
        Act as a professional Resume Writer for the {region} market.
        Role: {role}. Style: {style}.
        
        Job Description: {job_desc}
        
        User History: {user_info}
        
        Write a complete, optimized resume based on the above.
        """
        
        completion = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2048,
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error generating content: {str(e)}"

def create_styled_docx(text_content):
    doc = Document()
    for line in text_content.split('\n'):
        if line.strip():
            p = doc.add_paragraph(line)
            if line.isupper() and len(line) < 50:
                p.runs[0].bold = True
                p.runs[0].font.size = Pt(12)
            else:
                p.runs[0].font.size = Pt(11)
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

# =========================================================
# 🗄️ DATABASE FUNCTIONS
# =========================================================

def login_user(email):
    """Fetch user from Supabase"""
    if not DB_CONNECTED: 
        if email == "test@test.com": return {"email": email, "plan_type": "TRIAL_MONTHLY", "credits": 10, "expiry_date": (datetime.now() + timedelta(days=5)).isoformat()}
        return None
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
    if not DB_CONNECTED: return True 
    
    expiry = datetime.now() + timedelta(days=days_valid)
    data = {
        "email": email,
        "plan_type": plan_type,
        "credits": credits,
        "expiry_date": expiry.isoformat()
    }
    try:
        supabase.table("users").upsert(data).execute()
        return True
    except Exception as e:
        st.error(f"Registration Error: {e}")
        return False

def update_credits(email, new_credits):
    if DB_CONNECTED:
        supabase.table("users").update({"credits": new_credits}).eq("email", email).execute()

# =========================================================
# 🔒 PAYMENT & AUTH SCREEN (UPDATED WITH TABS)
# =========================================================
def show_payment_screen():
    st.markdown("<h1 style='text-align: center;'>🌍 Global AI Resume Builder</h1>", unsafe_allow_html=True)
    
    if not DB_CONNECTED:
        st.warning("⚠️ Database is Offline (Check Secrets). Using Offline Mode.")

    # --- TABS FOR LOGIN VS REGISTER ---
    tab_login, tab_register = st.tabs(["🔑 LOGIN", "📝 REGISTER (Select Plan)"])

    # -------------------------
    # TAB 1: LOGIN
    # -------------------------
    with tab_login:
        st.subheader("Welcome Back!")
        with st.form("login_form"):
            login_email = st.text_input("Enter your registered email:")
            submit_login = st.form_submit_button("Log In", type="primary", use_container_width=True)
            
            if submit_login:
                if "@" in login_email:
                    user = login_user(login_email)
                    if user:
                        st.session_state.user_data = user
                        st.success("Login Successful!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("❌ Account not found. Please register in the next tab.")
                else:
                    st.error("Please enter a valid email.")

    # -------------------------
    # TAB 2: REGISTER (PRICING)
    # -------------------------
    with tab_register:
        st.subheader("Choose a Plan to Create Account")
        
        c1, c2, c3 = st.columns(3)
        
        # 1. DEMO
        with c1:
            st.info("👶 **Free Demo**\n\nNo Download.\nView Examples Only.")
            if st.button("Try Demo Mode", use_container_width=True):
                st.session_state.user_data = {"email": "guest", "plan_type": "DEMO", "credits": 0}
                st.rerun()
                
        # 2. SINGLE PASS
        with c2:
            st.warning("⚡ **Single Pass**\n\n**KES 50 / $0.50**\n3 Generation Limit.")
            if st.button("Select Single Pass", key="btn_single", use_container_width=True):
                st.session_state.selected_plan = "Single"
                
        # 3. MONTHLY TRIAL
        with c3:
            st.success("🏆 **Monthly Pro**\n\n**3 DAYS FREE TRIAL**\nThen KES 1000/mo.")
            if st.button("Select Free Trial", key="btn_monthly", use_container_width=True):
                st.session_state.selected_plan = "Monthly"

        st.divider()

        # --- DYNAMIC FORMS BASED ON PLAN SELECTION ---
        if st.session_state.selected_plan == "Single":
            st.markdown("### 💳 Finish Registration: Single Pass")
            st.write("1. Pay **KES 50** or **$0.50**.")
            st.markdown(f"[**Pay KES 50 (M-Pesa)**]({LINK_SINGLE}) | [**Pay $0.50 (PayPal)**]({PAYPAL_ME_LINK}/0.50USD)")
            
            st.write("2. Create Account:")
            with st.form("single_reg_form"):
                act_email = st.text_input("Your Email:")
                trans_code = st.text_input("Payment Code (e.g. M-Pesa Code):")
                if st.form_submit_button("Verify & Register"):
                    if len(trans_code) > 5 and "@" in act_email:
                        if register_user(act_email, "SINGLE", 3, 1):
                            st.session_state.user_data = login_user(act_email)
                            st.balloons()
                            st.success("Activated! Redirecting...")
                            time.sleep(2)
                            st.rerun()
                    else:
                        st.error("Invalid Code/Email")

        elif st.session_state.selected_plan == "Monthly":
            st.markdown("### 📝 Finish Registration: 3-Day Free Trial")
            st.info("No payment now. Billing starts after 3 days.")
            
            with st.form("trial_form"):
                email = st.text_input("Email Address", placeholder="name@example.com")
                phone = st.text_input("Phone Number", placeholder="07...")
                pay_method = st.radio("Future Payment Method", ["M-Pesa", "Visa", "PayPal"], horizontal=True)
                
                if st.form_submit_button("✅ Create Account"):
                    if "@" in email and len(phone) > 5:
                        with st.spinner("Creating Account..."):
                            if register_user(email, "TRIAL_MONTHLY", 9999, 3):
                                st.session_state.user_data = login_user(email)
                                st.balloons()
                                st.success(f"✅ Account Created for {email}!")
                                time.sleep(2)
                                st.rerun()
                            else:
                                st.error("Database Error.")
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

    plan = user.get("plan_type")
    credits = user.get("credits", 0)
    is_demo = (plan == "DEMO")
    
    # Expiry Check
    if not is_demo:
        try:
            expiry = dateutil.parser.isoparse(user['expiry_date'])
            if expiry.tzinfo is None: now = datetime.now()
            else: now = datetime.now(expiry.tzinfo)

            if now > expiry:
                st.error("⏳ Plan Expired. Please Renew.")
                if st.button("Back to Login"):
                    st.session_state.user_data = None
                    st.rerun()
                return
            
            if plan == "TRIAL_MONTHLY":
                days = (expiry - now).days
                st.markdown(f"<div class='trial-banner'>💎 <b>TRIAL ACTIVE:</b> {days} days remaining.</div>", unsafe_allow_html=True)
        except: pass

    st.title("🚀 AI Resume Builder")
    
    # --- SIDEBAR ---
    with st.sidebar:
        st.write(f"👤 **{user.get('email')}**")
        if is_demo:
            st.warning("👀 DEMO MODE")
            if st.button("Unlock Full Access"):
                st.session_state.user_data = None
                st.rerun()
        else:
            st.metric("Credits Left", credits)
            if st.button("Logout", type="secondary"):
                st.session_state.user_data = None
                st.rerun()

    # --- 1. SETUP ---
    st.subheader("1. Setup")
    col_cat, col_region, col_style = st.columns(3)
    
    with col_cat:
        cv_category = st.selectbox("Role / Industry", ["Corporate", "NGO / UN", "Tech / IT", "Healthcare", "Engineering", "Sales"])
    with col_region:
        cv_region = st.selectbox("Format Standard", ["🇰🇪 Kenya / UK", "🇺🇸 USA (Resume)", "🇪🇺 Europass", "🇨🇦 Canada"])
    with col_style:
        visual_style = st.selectbox("Visual Style", ["Modern Clean", "Classic Professional", "Executive"])

    # --- 2. INPUTS ---
    if is_demo:
        st.subheader(f"👁️ Preview: {cv_region}")
        cache_key = f"{cv_category}_{cv_region}"
        if cache_key not in st.session_state.demo_cache:
            st.session_state.demo_cache[cache_key] = generate_ai_content("DEMO", cv_region, "DEMO", "DEMO", "DEMO")
        st.markdown(f"<div class='protected-view'><div class='watermark'>DEMO</div>{st.session_state.demo_cache[cache_key]}</div>", unsafe_allow_html=True)
    
    else:
        st.header("2. Your Information")
        c_left, c_right = st.columns(2)
        with c_left: job_desc = st.text_area("Target Job Description:", height=250)
        with c_right: resume_text = st.text_area("Your Info (Experience & Education):", height=250)

        col_btn = st.columns([1, 2, 1])[1]
        with col_btn:
            if st.button("🚀 Generate Optimized CV", type="primary", use_container_width=True):
                fresh_user = login_user(user['email'])
                current_creds = fresh_user['credits'] if fresh_user else credits
                
                if current_creds < 1:
                    st.error("🚫 Limit Reached.")
                elif not resume_text:
                    st.warning("Enter info first.")
                else:
                    with st.spinner("AI Generating..."):
                        res = generate_ai_content(cv_category, cv_region, visual_style, resume_text, job_desc)
                        st.session_state.generated_resume = res
                        if fresh_user:
                            update_credits(user['email'], current_creds - 1)
                            st.session_state.user_data['credits'] = current_creds - 1

        if st.session_state.generated_resume:
            st.divider()
            st.header("3. Download")
            st.text_area("Editor:", st.session_state.generated_resume, height=600)
            if "Error" not in st.session_state.generated_resume:
                st.download_button("📥 Download .docx", create_styled_docx(st.session_state.generated_resume), "CV.docx", type="primary")

# =========================================================
# 🏁 ENTRY POINT
# =========================================================
if __name__ == "__main__":
    if st.session_state.user_data is None:
        show_payment_screen()
    else:
        show_main_app()
