import streamlit as st
from groq import Groq
from docx import Document
from docx.shared import Pt
import io
import time
from datetime import datetime, timedelta

# --- ⚠️ CONFIGURATION ---
try:
    API_KEY = st.secrets["GROQ_API_KEY"]
    LINK_SINGLE = st.secrets["LINK_SINGLE"]
    LINK_MONTHLY = st.secrets["LINK_MONTHLY"]
    PAYPAL_ME_LINK = st.secrets["PAYPAL_ME_LINK"]
except:
    API_KEY = "PASTE_KEY_HERE_IF_LOCAL"
    LINK_SINGLE = "https://example.com"
    LINK_MONTHLY = "https://example.com"
    PAYPAL_ME_LINK = "https://paypal.me"

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
    background-color: #d4edda; color: #155724; padding: 10px;
    border-radius: 5px; text-align: center; margin-bottom: 20px; border: 1px solid #c3e6cb;
}
/* Center the inputs */
.stTextArea label {
    font-weight: bold;
    font-size: 1.1rem;
}
</style>
"""

# --- SESSION STATE ---
if 'access_level' not in st.session_state: st.session_state.access_level = "LOCKED"
if 'expiry_time' not in st.session_state: st.session_state.expiry_time = None
if 'generated_resume' not in st.session_state: st.session_state.generated_resume = None
if 'demo_cache' not in st.session_state: st.session_state.demo_cache = {}
if 'generation_count' not in st.session_state: st.session_state.generation_count = 0
if 'selected_plan' not in st.session_state: st.session_state.selected_plan = None
if 'user_email' not in st.session_state: st.session_state.user_email = None

# =========================================================
# 🕒 ACCESS CHECKER
# =========================================================
def check_access():
    if st.session_state.access_level == "LOCKED": return
    if st.session_state.expiry_time and datetime.now() > st.session_state.expiry_time:
        st.session_state.access_level = "LOCKED"
        st.session_state.expiry_time = None
        st.warning("⏳ Session or Trial expired. Please renew/pay.")
        st.rerun()
check_access()

# =========================================================
# 💰 LOGIC HELPERS
# =========================================================
def verify_transaction(code):
    return len(code.strip()) >= 8

def start_free_trial(email, payment_method):
    st.session_state.user_email = email
    st.session_state.access_level = "TRIAL_MONTHLY"
    st.session_state.expiry_time = datetime.now() + timedelta(days=3)
    st.balloons()
    st.success(f"✅ Trial Activated for {email}. You have 3 Days Free!")
    time.sleep(2)
    st.rerun()

# =========================================================
# 🔒 PAYMENT SCREEN
# =========================================================
def show_payment_screen():
    st.markdown("<h1 style='text-align: center;'>🌍 Global AI Resume Builder</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Select a plan to generate international standard CVs.</p>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.info("👶 **Free Demo**\n\nNo Download.\nView Examples Only.")
        if st.button("Enter Demo Mode", use_container_width=True):
            st.session_state.access_level = "DEMO"
            st.session_state.expiry_time = datetime.now() + timedelta(minutes=10)
            st.rerun()
    with c2:
        st.warning("⚡ **Single CV Pass**\n\n**KES 50 / $0.50**\n3 Generation Limit.")
        if st.button("Select Single Pass", key="btn_single", use_container_width=True):
            st.session_state.selected_plan = "Single"
    with c3:
        st.success("🏆 **Monthly Pro**\n\n**3 DAYS FREE TRIAL**\nThen KES 1000/mo.")
        if st.button("Start Free Trial", key="btn_monthly", use_container_width=True):
            st.session_state.selected_plan = "Monthly"

    st.divider()

    if st.session_state.selected_plan == "Single":
        st.subheader("💳 One-Time Payment: Single Pass")
        pay_tab1, pay_tab2 = st.tabs(["🇰🇪 M-Pesa", "🌎 PayPal"])
        with pay_tab1:
            st.write("Pay **KES 50** to:")
            st.markdown(f"[**Click to Pay via IntaSend**]({LINK_SINGLE})")
        with pay_tab2:
            st.write("Pay **$0.50** to:")
            st.markdown(f"[**Click to Pay via PayPal**]({PAYPAL_ME_LINK}/0.50USD)")
        
        st.divider()
        c_code, c_btn = st.columns([3, 1])
        trans_code = c_code.text_input("Transaction Code:", placeholder="e.g. RJG829...", label_visibility="collapsed")
        if c_btn.button("Unlock Single Pass", type="primary"):
            if verify_transaction(trans_code):
                st.session_state.access_level = "PAID_SINGLE"
                st.session_state.expiry_time = datetime.now() + timedelta(hours=4)
                st.session_state.generation_count = 0 
                st.rerun()
            else:
                st.error("Invalid Code")

    elif st.session_state.selected_plan == "Monthly":
        st.subheader("📝 Start Your 3-Day Free Trial")
        st.info("Billing of **KES 1000** starts automatically after 3 days.")
        with st.form("trial_form"):
            col_email, col_phone = st.columns(2)
            email = col_email.text_input("Email Address", placeholder="name@example.com")
            phone = col_phone.text_input("Phone Number", placeholder="07...")
            pay_method = st.radio("Select Future Payment Method", ["M-Pesa (Auto-Debit)", "Visa / MasterCard", "PayPal"], horizontal=True)
            if "Visa" in pay_method:
                c_card, c_cvv = st.columns([3, 1])
                c_card.text_input("Card Number", placeholder="0000 0000 0000 0000")
                c_cvv.text_input("CVV", placeholder="123")
            st.markdown("---")
            if st.form_submit_button("✅ Confirm & Start Free Trial", type="primary"):
                if "@" in email and len(phone) > 5:
                    start_free_trial(email, pay_method)
                else:
                    st.error("Invalid details.")

# =========================================================
# ⚙️ APP LOGIC
# =========================================================
def show_main_app():
    st.markdown(PROTECTED_CSS, unsafe_allow_html=True)
    
    if st.session_state.access_level == "TRIAL_MONTHLY":
        remaining_time = st.session_state.expiry_time - datetime.now()
        st.markdown(f"<div class='trial-banner'>💎 <b>TRIAL ACTIVE:</b> {remaining_time.days} days remaining before billing.</div>", unsafe_allow_html=True)

    is_demo = st.session_state.access_level == "DEMO"
    access_type = st.session_state.access_level
    
    st.title("🚀 AI Resume Builder")
    
    # --- 🌍 TOP BAR CONFIGURATION ---
    st.subheader("1. Setup")
    col_cat, col_region, col_style = st.columns(3)
    
    with col_cat:
        cv_category = st.selectbox("Role / Industry", [
            "Corporate / Administration", 
            "NGO / United Nations / Development", 
            "Tech / Software / IT",
            "Medical / Healthcare",
            "Engineering / Construction",
            "Sales / Marketing",
            "Academic / Education",
            "Service / Hospitality",
            "Executive / C-Suite",
            "Entry-Level / Internship"
        ])

    with col_region:
        cv_region = st.selectbox("Region / Format Standard", [
            "🇰🇪 Kenya / UK / Commonwealth (Standard CV)",
            "🇺🇸 USA / North America (Resume - Concise)",
            "🇪🇺 Europe (Europass Standard)",
            "🇨🇦 Canada (Functional/Hybrid)",
            "🇦🇪 Middle East / Gulf (Detailed)",
            "🌏 International / Remote (Modern)"
        ])

    with col_style:
        visual_style = st.selectbox("Visual Template", ["Modern Clean", "Classic Professional", "Executive Minimalist", "Creative (Bold)"])

    st.divider()

    # --- SIDEBAR (STATUS ONLY) ---
    with st.sidebar:
        if is_demo:
            st.warning("👀 DEMO MODE")
            if st.button("🔓 Unlock Full Access"):
                st.session_state.access_level = "LOCKED"
                st.rerun()
        else:
            st.info(f"User: {st.session_state.user_email if st.session_state.user_email else 'Guest'}")
            if "MONTHLY" in access_type:
                st.success(f"💎 PRO: UNLIMITED")
            elif access_type == "PAID_SINGLE":
                remaining = 3 - st.session_state.generation_count
                if remaining > 0:
                    st.warning(f"⚡ PASS: {remaining}/3 Left")
                else:
                    st.error(f"⚡ PASS EXHAUSTED")
        st.markdown("---")
        st.caption("AI Resume Pro v2.0")

    # --- MAIN CONTENT AREA ---
    
    if is_demo:
        # Demo View
        st.subheader(f"👁️ Preview: {cv_region}")
        cache_key = f"{cv_category}_{cv_region}_{visual_style}"
        if cache_key not in st.session_state.demo_cache:
            with st.spinner("Generating sample..."):
                st.session_state.demo_cache[cache_key] = generate_demo_persona(cv_category, cv_region)
        st.markdown(f"<div class='protected-view'><div class='watermark'>DEMO</div>{st.session_state.demo_cache[cache_key]}</div>", unsafe_allow_html=True)
    
    else:
        # === ✅ USER INPUTS (CENTERED) ===
        st.header("2. Your Information")
        
        # Using columns to organize inputs cleanly
        c_left, c_right = st.columns(2)
        
        with c_left:
             st.info("💡 **Tip:** Paste the job advert here so the AI can match your skills to the requirements.")
             job_desc = st.text_area("Target Job Description (Optional):", height=250, placeholder="Paste the job advert here...")
        
        with c_right:
             st.info("💡 **Tip:** Paste your old CV text or type a summary of your experience.")
             resume_text = st.text_area("Your Info (Work History, Education, Skills):", height=250, placeholder="Name: John Doe\nEducation: ...\nExperience: ...")

        st.markdown("<br>", unsafe_allow_html=True)

        # === GENERATE ACTION ===
        limit_reached = False
        if access_type == "PAID_SINGLE" and st.session_state.generation_count >= 3:
            limit_reached = True

        if limit_reached:
            st.error("🚫 Limit Reached.")
            if st.button("Upgrade to Monthly"):
                st.session_state.access_level = "LOCKED"
                st.rerun()
        else:
            # Centered Generate Button
            col_spacer, col_btn, col_spacer2 = st.columns([1, 2, 1])
            with col_btn:
                if st.button("🚀 Generate Optimized CV Now", type="primary", use_container_width=True):
                    if not resume_text: 
                        st.warning("Please enter your information above first.")
                    else:
                        with st.spinner(f"Applying {cv_region} standards..."):
                            res = generate_ai_content(cv_category, cv_region, visual_style, resume_text, job_desc)
                            st.session_state.generated_resume = res
                            
                            if access_type == "PAID_SINGLE":
                                st.session_state.generation_count += 1
                                st.rerun() 
        
        # === RESULTS SECTION ===
        if st.session_state.generated_resume:
            st.divider()
            st.header("3. Review & Download")
            st.text_area("Editor (Make final tweaks here):", st.session_state.generated_resume, height=600)
            
            d_col1, d_col2, d_col3 = st.columns([1,2,1])
            with d_col2:
                st.download_button(f"📥 Download {cv_region} CV (.docx)", create_styled_docx(st.session_state.generated_resume), "Professional_CV.docx", type="primary", use_container_width=True)

# =========================================================
# 🧠 AI ENGINE
# =========================================================
def get_groq_response(prompt):
    if not API_KEY or "PASTE" in API_KEY: return "Error: API Key Missing"
    try:
        client = Groq(api_key=API_KEY)
        return client.chat.completions.create(messages=[{"role":"user","content":prompt}],model="llama-3.3-70b-versatile").choices[0].message.content
    except Exception as e: return str(e)

def generate_demo_persona(category, region):
    return get_groq_response(f"Generate a fictional, professional resume for a {category} role. strictly following the {region} format standard.")

def generate_ai_content(cat, region, style, res, job):
    prompt = f"""
    Act as an expert Global Resume Writer. Write a CV for a '{cat}' role.
    
    TARGET REGION/STANDARD: {region}
    VISUAL STYLE: {style}
    
    CRITICAL REGIONAL RULES:
    - If USA: Use 'Resume' format. Maximum 1-2 pages. NO personal details (age, religion, marital status, photo reference). Use American English. Focus on achievements.
    - If Kenya/UK: Use 'CV' format. British English. Can include referees.
    - If Europe: Follow 'Europass' logic. Include key competencies clearly.
    - If Middle East: You may include personal details if standard for the region.
    
    USER INFO:
    {res}
    
    TARGET JOB DESCRIPTION (Optimize for these keywords):
    {job}
    
    OUTPUT FORMAT:
    Return ONLY the text content of the resume, formatted clearly with distinct sections. Do not include chatty conversational text.
    """
    return get_groq_response(prompt)

def create_styled_docx(text):
    doc = Document()
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Calibri'
    font.size = Pt(11)
    
    for line in text.split('\n'):
        if line.isupper() and len(line) < 50:
            doc.add_heading(line, level=1)
        else:
            p = doc.add_paragraph(line)
            if line.strip().startswith(("-", "*", "•")):
                p.style = 'List Bullet'
                
    buffer = io.BytesIO(); doc.save(buffer); buffer.seek(0)
    return buffer

# --- MAIN RUN ---
if st.session_state.access_level == "LOCKED":
    show_payment_screen()
else:
    show_main_app()
