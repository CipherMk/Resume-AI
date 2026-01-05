import streamlit as st
from groq import Groq
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
import io
import time
import uuid
from datetime import datetime, timedelta

# --- ⚠️ CONFIGURATION ---
API_KEY = "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"

# --- 💰 PAYMENT LINKS ---
LINK_SINGLE = "https://payment.intasend.com/pay/YOUR_LINK_FOR_50_BOB" 
LINK_MONTHLY = "https://payment.intasend.com/pay/YOUR_LINK_FOR_1000_BOB"
PAYPAL_ME_LINK = "https://www.paypal.com/qrcodes/p2pqrc/9UARHMAVPN77Y"

# --- PAGE CONFIG ---
st.set_page_config(page_title="AI Resume Pro", page_icon="💎", layout="wide")

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
</style>
"""

# --- SESSION STATE ---
if 'access_level' not in st.session_state: st.session_state.access_level = "LOCKED" 
if 'expiry_time' not in st.session_state: st.session_state.expiry_time = None
if 'generated_resume' not in st.session_state: st.session_state.generated_resume = None
if 'demo_cache' not in st.session_state: st.session_state.demo_cache = {}

# 🚨 NEW: Track Usage Limit
if 'generation_count' not in st.session_state: st.session_state.generation_count = 0

# =========================================================
# 🕒 ACCESS CHECKER
# =========================================================
def check_access():
    if st.session_state.access_level == "LOCKED": return
    if st.session_state.expiry_time and datetime.now() > st.session_state.expiry_time:
        st.session_state.access_level = "LOCKED"
        st.session_state.expiry_time = None
        st.warning("⏳ Session expired. Please renew.")
        st.rerun()
check_access()

# =========================================================
# 💰 VERIFICATION (SIMULATED)
# =========================================================
def verify_transaction(code):
    """
    Simulated verification. In real app, check against DB/API.
    """
    code = code.strip().upper()
    if len(code) >= 10: return True
    return False

# =========================================================
# 🔒 PAYMENT SCREEN (FIXED)
# =========================================================
def show_payment_screen():
    st.markdown("<h1 style='text-align: center;'>💎 Unlock AI Resume Pro</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Choose a plan to start generating professional CVs.</p>", unsafe_allow_html=True)
    
    # --- PRICING ---
    c1, c2, c3 = st.columns(3)
    with c1:
        st.info("👶 **Free Demo**\n\nNo Download.\nView Examples Only.")
        if st.button("Enter Demo Mode", use_container_width=True):
            st.session_state.access_level = "DEMO"
            st.session_state.expiry_time = datetime.now() + timedelta(minutes=10)
            st.rerun()
    with c2:
        st.warning("⚡ **Single CV Pass**\n\n**KES 50 / $0.50**\n1 Generation Limit.")
    with c3:
        # FIXED: Replaced st.primary (which doesn't exist) with st.success
        st.success("🏆 **Monthly Pro**\n\n**KES 1000 / $8.00**\nUnlimited Access.")

    st.divider()

    # --- PAYMENT TABS ---
    st.subheader("💳 Choose Payment Method")
    pay_tab1, pay_tab2 = st.tabs(["🇰🇪 M-Pesa / Visa (Instant)", "🌎 PayPal"])

    with pay_tab1:
        st.markdown("### Pay securely via IntaSend")
        plan = st.radio("Select Plan:", ["Single CV Pass (KES 50)", "Monthly Pro (KES 1000)"], horizontal=True)
        pay_url = LINK_MONTHLY if "1000" in plan else LINK_SINGLE
        
        st.markdown(f"""
        <a href="{pay_url}" target="_blank">
            <button style="background-color:#00C853; color:white; border:none; padding:10px 20px; border-radius:5px; font-size:16px; cursor:pointer; width:100%;">
                👉 Click Here to Pay {plan}
            </button>
        </a>
        """, unsafe_allow_html=True)

    with pay_tab2:
        st.markdown(f"[**Click to Pay via PayPal**]({PAYPAL_ME_LINK})")
        st.write("Send **$0.50** (Single) or **$8.00** (Monthly).")

    st.divider()

    # --- VERIFICATION ---
    st.subheader("🔓 Verify Payment to Unlock")
    col_v1, col_v2 = st.columns([3, 1])
    with col_v1:
        trans_code = st.text_input("Transaction Code:", placeholder="e.g. RJG829D...", label_visibility="collapsed")
    with col_v2:
        # We need to know WHICH plan they paid for to verify correctly
        plan_verified = st.selectbox("I Paid For:", ["Single Pass (50 KES)", "Monthly Pro (1000 KES)"], label_visibility="collapsed")
        
        if st.button("Verify & Unlock", type="primary", use_container_width=True):
            if verify_transaction(trans_code):
                st.balloons()
                
                # 🚨 ASSIGN SPECIFIC ACCESS LEVEL
                if "Single" in plan_verified:
                    st.session_state.access_level = "PAID_SINGLE"
                    st.session_state.expiry_time = datetime.now() + timedelta(hours=2)
                    st.session_state.generation_count = 0 # Reset count
                else:
                    st.session_state.access_level = "PAID_MONTHLY"
                    st.session_state.expiry_time = datetime.now() + timedelta(days=30)
                
                st.success("✅ Payment Verified!")
                time.sleep(1.5)
                st.rerun()
            else:
                st.error("❌ Invalid Code.")

# =========================================================
# ⚙️ APP LOGIC (RESTRICTED)
# =========================================================
def show_main_app():
    st.markdown(PROTECTED_CSS, unsafe_allow_html=True)
    is_demo = st.session_state.access_level == "DEMO"
    access_type = st.session_state.access_level
    
    st.title("🚀 AI Resume Builder")
    
    # Selectors
    c1, c2, c3 = st.columns([1, 2, 1]) 
    with c2:
        st.write("**Professional Category**")
        cv_category = st.selectbox("Cat", ["Standard (Corporate)", "NGO / Development", "Service (Driver/Tech)", "Entry-Level", "Executive", "Technical"], label_visibility="collapsed")
    
    st.write("<p style='text-align: center;'><b>Visual Style</b></p>", unsafe_allow_html=True)
    visual_style = st.radio("Style", ["Classic", "Modern", "Functional"], horizontal=True, label_visibility="collapsed")
    st.divider()

    # Sidebar Inputs
    with st.sidebar:
        if is_demo:
            st.warning("👀 DEMO MODE")
            if st.button("🔓 Unlock Full Access"):
                st.session_state.access_level = "LOCKED"
                st.rerun()
        else:
            # SHOW USER THEIR PLAN STATUS
            if access_type == "PAID_MONTHLY":
                st.success(f"💎 PRO: UNLIMITED")
            elif access_type == "PAID_SINGLE":
                remaining = 1 - st.session_state.generation_count
                if remaining > 0:
                    st.warning(f"⚡ SINGLE PASS: {remaining} Left")
                else:
                    st.error(f"⚡ SINGLE PASS: EXHAUSTED")
        
        st.header("Details")
        job_desc = st.text_area("Target Job:", disabled=is_demo, height=150)
        resume_text = st.text_area("Your Info:", disabled=is_demo, height=200)

    # Content Area
    if is_demo:
        st.subheader(f"👁️ Preview: {cv_category}")
        cache_key = f"{cv_category}_{visual_style}"
        if cache_key not in st.session_state.demo_cache:
            with st.spinner("AI generating example..."):
                st.session_state.demo_cache[cache_key] = generate_demo_persona(cv_category, visual_style)
        
        st.markdown(f"<div class='protected-view'><div class='watermark'>DEMO</div>{st.session_state.demo_cache[cache_key]}</div>", unsafe_allow_html=True)
    
    else:
        # === PAID AREA WITH RESTRICTIONS ===
        limit_reached = False
        if access_type == "PAID_SINGLE" and st.session_state.generation_count >= 1:
            limit_reached = True

        if limit_reached:
            st.error("🚫 You have used your 1 generation for this Single Pass.")
            st.info("To generate more CVs (e.g. for different jobs), upgrade to Monthly Pro.")
            if st.button("Upgrade to Pro"):
                st.session_state.access_level = "LOCKED"
                st.rerun()
        else:
            if st.button("🚀 Generate My Resume", type="primary"):
                if not resume_text: 
                    st.warning("Enter info first.")
                else:
                    with st.spinner("Thinking..."):
                        res = generate_ai_content(cv_category, visual_style, resume_text, job_desc)
                        st.session_state.generated_resume = res
                        
                        # 🚨 INCREMENT COUNTER
                        if access_type == "PAID_SINGLE":
                            st.session_state.generation_count += 1
                            st.rerun() # Rerun to update the UI immediately
        
        if st.session_state.generated_resume:
            st.text_area("Editor", st.session_state.generated_resume, height=600)
            st.download_button("Download .docx", create_styled_docx(st.session_state.generated_resume, visual_style), "Resume.docx")

# =========================================================
# 🧠 AI HELPERS
# =========================================================
def get_groq_response(prompt):
    if not API_KEY or "PASTE" in API_KEY: return "Error: API Key Missing"
    try:
        client = Groq(api_key=API_KEY)
        return client.chat.completions.create(messages=[{"role":"user","content":prompt}],model="llama-3.3-70b-versatile").choices[0].message.content
    except Exception as e: return str(e)

def generate_demo_persona(category, style):
    return get_groq_response(f"Generate fictional resume for {category} in {style} style.")

def generate_ai_content(cat, style, res, job):
    return get_groq_response(f"Write resume. Role: {cat}. Style: {style}. Info: {res}. Job: {job}")

def create_styled_docx(text, style):
    doc = Document()
    for line in text.split('\n'): doc.add_paragraph(line)
    buffer = io.BytesIO(); doc.save(buffer); buffer.seek(0)
    return buffer

# --- MAIN RUN ---
if st.session_state.access_level == "LOCKED":
    show_payment_screen()
else:
    show_main_app()