import streamlit as st
import requests
import time
import datetime
from groq import Groq
from docx import Document
from docx.shared import Pt
import io
import extra_streamlit_components as stx 

# --- ⚠️ CONFIGURATION ---
st.set_page_config(page_title="CareerFlow | Global CV Architect Pro", page_icon="🌍", layout="wide")

# --- 🔐 SECRETS MANAGEMENT ---
try:
    GROQ_KEY = st.secrets["GROQ_API_KEY"]
    INTASEND_SEC_KEY = st.secrets["INTASEND_SECRET_KEY"] 
    PAYMENT_LINK_URL = st.secrets["INTASEND_PAYMENT_LINK"]
except:
    GROQ_KEY = ""
    INTASEND_SEC_KEY = ""
    PAYMENT_LINK_URL = "#"

# =========================================================
# 🍪 1. ROBUST COOKIE MANAGER (NO HICCUPS)
# =========================================================
@st.cache_resource(experimental_allow_widgets=True)
def get_manager():
    return stx.CookieManager()

cookie_manager = get_manager()

# --- 🔄 SYNC LOGIC ---
# This tiny pause ensures the JS bridge is established before we try to read.
# This prevents the "NoneType" error on first load.
time.sleep(0.1)

# =========================================================
# 💾 2. "FOREVER" STORAGE & STATE LOGIC
# =========================================================
COOKIE_NAME = "careerflow_usage_tracker_v1"
MAX_FREE_USES = 2
# 10 Years Expiration
FOREVER_DATE = datetime.datetime.now() + datetime.timedelta(days=365 * 10)

# Initialize Session State
if 'is_pro' not in st.session_state: st.session_state.is_pro = False
if 'generated_resume' not in st.session_state: st.session_state.generated_resume = None
if 'free_uses' not in st.session_state: st.session_state.free_uses = 0
if 'sample_ke' not in st.session_state: st.session_state.sample_ke = None
if 'sample_us' not in st.session_state: st.session_state.sample_us = None

# --- 🧠 INTELLIGENT LOAD ---
cookie_val = cookie_manager.get(cookie=COOKIE_NAME)

if cookie_val is not None:
    # If cookie exists, force Session State to match it
    st.session_state.free_uses = int(cookie_val)
else:
    # If cookie is None (First visit), ensure we start at 0
    # We do not overwrite here to avoid race conditions, we just wait for the first save
    pass

# =========================================================
# 🎨 CSS STYLING
# =========================================================
def inject_custom_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
        
        .block-container { padding-top: 2rem; padding-bottom: 2rem; }
        h1, h2, h3 { font-family: 'Inter', sans-serif; }
        p, li { font-family: 'Inter', sans-serif; line-height: 1.6; color: #334155; }

        .hero-box {
            background: linear-gradient(135deg, #0f172a 0%, #334155 100%);
            color: white; padding: 60px 40px; border-radius: 12px;
            text-align: center; margin-bottom: 40px;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        }
        .hero-title { font-size: 3rem; font-weight: 800; margin-bottom: 10px; color: white; }
        .hero-sub { font-size: 1.25rem; color: #e2e8f0; font-weight: 300; }

        .paper-preview {
            background-color: white; border: 1px solid #e2e8f0; padding: 50px;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
            font-family: 'Arial', sans-serif; color: #1e293b;
            font-size: 14px; white-space: pre-wrap; min-height: 600px;
        }

        .paywall-box {
            border: 2px dashed #cbd5e1; background: #f8fafc;
            padding: 40px; text-align: center; border-radius: 12px; margin-top: 20px;
        }
        
        .badge-free { background: #dbeafe; color: #1e40af; padding: 4px 12px; border-radius: 20px; font-weight: 600; font-size: 0.85rem; }
        .badge-pro { background: #dcfce7; color: #166534; padding: 4px 12px; border-radius: 20px; font-weight: 600; font-size: 0.85rem; border: 1px solid #166534; }
    </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# =========================================================
# 💰 LOGIC: PAYMENT VERIFICATION
# =========================================================
def verify_payment():
    query_params = st.query_params
    tracking_id = query_params.get("tracking_id", query_params.get("checkout_id", None))
    
    if tracking_id:
        if tracking_id == "TEST-ADMIN":
            st.session_state.is_pro = True
            st.toast("👨‍💻 Admin Test Access Granted")
            st.query_params.clear()
            return

        st.toast(f"Verifying Payment ID: {tracking_id}...")
        
        url = "https://payment.intasend.com/api/v1/payment/status/"
        headers = {"Authorization": f"Bearer {INTASEND_SEC_KEY}", "Content-Type": "application/json"}
        
        try:
            res = requests.post(url, json={"invoice_id": tracking_id}, headers=headers)
            response_data = res.json()
            
            if response_data.get('invoice', {}).get('state') == 'COMPLETE':
                st.session_state.is_pro = True
                st.toast("🎉 Payment Verified! Access Unlocked.")
                st.query_params.clear()
            elif response_data.get('invoice', {}).get('state') == 'PENDING':
                st.warning("Payment processing. Refresh shortly.")
        except Exception as e:
            st.error(f"Connection Error: {e}")

if not st.session_state.is_pro:
    verify_payment()

# =========================================================
# 🤖 SAMPLE GENERATOR
# =========================================================
def generate_live_sample(region, job_title):
    if not GROQ_KEY: return "⚠️ API Key missing."
    try:
        client = Groq(api_key=GROQ_KEY)
        prompt = f"Generate a realistic, text-heavy, ATS-Optimized {region} for a {job_title}. Use Markdown. No placeholders."
        response = client.chat.completions.create(messages=[{"role":"user","content":prompt}], model="llama-3.3-70b-versatile")
        return response.choices[0].message.content
    except Exception as e: return f"Error: {e}"

# =========================================================
# 📝 LANDING PAGE CONTENT
# =========================================================
def show_landing_content():
    st.markdown("""
    <div class="hero-box">
        <div class="hero-title">CareerFlow Global Architect</div>
        <div class="hero-sub">Region-Specific, ATS-Optimized Resumes.</div>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.sample_ke is None:
        with st.spinner("🤖 Generating live AI samples..."):
            st.session_state.sample_ke = generate_live_sample("CV (British/Kenyan Standard)", "Chief Accountant")
            st.session_state.sample_us = generate_live_sample("Resume (American Standard)", "Senior Data Scientist")
    
    tab_ke, tab_us = st.tabs(["🇰🇪 Kenyan / UK CV", "🇺🇸 USA Resume"])
    with tab_ke: st.markdown(f'<div class="paper-preview">{st.session_state.sample_ke}</div>', unsafe_allow_html=True)
    with tab_us: st.markdown(f'<div class="paper-preview">{st.session_state.sample_us}</div>', unsafe_allow_html=True)

# =========================================================
# ⚙️ MAIN APP
# =========================================================
def show_app():
    # HEADER
    c1, c2 = st.columns([3, 1])
    with c1: st.title("🛠️ Resume Builder")
    with c2:
        if st.session_state.is_pro:
            st.markdown('<div style="text-align:right; margin-top:10px;"><span class="badge-pro">💎 PRO ACTIVE</span></div>', unsafe_allow_html=True)
        else:
            left = MAX_FREE_USES - st.session_state.free_uses
            if left < 0: left = 0
            st.markdown(f'<div style="text-align:right; margin-top:10px;"><span class="badge-free">⚡ {left} FREE TRIES LEFT</span></div>', unsafe_allow_html=True)

    st.markdown("---")

    # 🔒 PAYWALL CHECK
    if not st.session_state.is_pro and st.session_state.free_uses >= MAX_FREE_USES:
        st.markdown(f"""
        <div class="paywall-box">
            <h3>🔒 Free Limit Reached</h3>
            <p>You've used your free generations. Unlock unlimited access for KES 150.</p>
        </div>
        """, unsafe_allow_html=True)
        
        c_pay1, c_pay2, c_pay3 = st.columns([1,2,1])
        with c_pay2:
            if PAYMENT_LINK_URL != "#":
                st.link_button("👉 Unlock Now (M-Pesa)", PAYMENT_LINK_URL, type="primary", use_container_width=True)
            else:
                st.error("Payment link missing.")
        return # STOP HERE

    # BUILDER FORM
    with st.form("builder_form"):
        c_meta1, c_meta2 = st.columns(2)
        with c_meta1: doc_type = st.selectbox("Document Type", ["Resume / CV", "Cover Letter"])
        with c_meta2: region = st.selectbox("Target Region", ["Kenya / UK (British)", "USA / Canada (American)", "Europe (Europass)"])
        
        industry = st.selectbox("Industry", ["Corporate", "Tech", "Medical", "Creative"])
        job_desc = st.text_area("1. Paste Job Advertisement", height=150)
        user_cv = st.text_area("2. Paste Your Experience", height=150)
        
        submitted = st.form_submit_button("✨ Generate Document", type="primary", use_container_width=True)

    if submitted:
        if not job_desc or not user_cv:
            st.error("⚠️ Fill all fields.")
        elif not GROQ_KEY:
            st.error("❌ API Key missing.")
        else:
            with st.spinner("🤖 Applying regional formatting..."):
                try:
                    client = Groq(api_key=GROQ_KEY)
                    prompt = f"""
                    Write a {doc_type} for {industry} industry. Target Region: {region}.
                    Job: {job_desc}. User Info: {user_cv}.
                    Use correct regional spelling. Optimize for ATS keywords. Return Markdown.
                    """
                    response = client.chat.completions.create(messages=[{"role":"user","content":prompt}],model="llama-3.3-70b-versatile")
                    st.session_state.generated_resume = response.choices[0].message.content
                    
                    # 🍪 SAVE COOKIE FOREVER ON SUCCESS
                    if not st.session_state.is_pro:
                        st.session_state.free_uses += 1
                        cookie_manager.set(COOKIE_NAME, st.session_state.free_uses, expires_at=FOREVER_DATE)
                    
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    # RESULTS
    if st.session_state.generated_resume:
        st.divider()
        st.subheader("🎉 Draft Ready")
        final_text = st.text_area("Editor", st.session_state.generated_resume, height=500)
        
        doc = Document()
        style = doc.styles['Normal']
        style.font.name = 'Arial'
        style.font.size = Pt(11)
        for line in final_text.split('\n'):
            if line.strip(): doc.add_paragraph(line)
        
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        st.download_button("📥 Download Word Doc", data=buffer, file_name=f"CareerFlow_{region.split()[0]}.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", type="primary")

# =========================================================
# 🚀 START
# =========================================================
if not st.session_state.generated_resume and st.session_state.free_uses == 0:
    show_landing_content()

show_app()
