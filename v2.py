import streamlit as st
import requests
import datetime
import time
from groq import Groq
from docx import Document
from docx.shared import Pt
import io
import extra_streamlit_components as stx 

# --- ⚠️ CONFIGURATION ---
st.set_page_config(page_title="CareerFlow | Global CV Architect", page_icon="🌍", layout="wide")

# --- 🔐 SECRETS ---
try:
    GROQ_KEY = st.secrets["GROQ_API_KEY"]
    INTASEND_SEC_KEY = st.secrets["INTASEND_SECRET_KEY"] 
    PAYMENT_LINK_URL = st.secrets["INTASEND_PAYMENT_LINK"]
except:
    GROQ_KEY = ""
    INTASEND_SEC_KEY = ""
    PAYMENT_LINK_URL = "#"

# --- 🍪 COOKIE MANAGER ---
def get_manager():
    return stx.CookieManager()

cookie_manager = get_manager()

# --- 🎨 STYLING ---
def inject_custom_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
        .block-container { padding-top: 2rem; }
        .hero-box {
            background: linear-gradient(135deg, #0f172a 0%, #334155 100%);
            color: white; padding: 60px 40px; border-radius: 12px; text-align: center; margin-bottom: 40px;
        }
        .hero-title { font-size: 3rem; font-weight: 800; color: white; }
        .badge-credits { background: #dcfce7; color: #166534; padding: 6px 16px; border-radius: 20px; font-weight: 700; border: 1px solid #166534; }
        .badge-low { background: #fee2e2; color: #991b1b; padding: 6px 16px; border-radius: 20px; font-weight: 700; border: 1px solid #991b1b; }
    </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# =========================================================
# 💾 STATE & CREDIT MANAGEMENT
# =========================================================

# 1. Initialize result container if missing
if 'generated_resume' not in st.session_state: 
    st.session_state.generated_resume = None

# 2. LOAD CREDITS (Priority: Cookie -> Default to 2)
if 'credits' not in st.session_state:
    saved_credits = cookie_manager.get("careerflow_credits")
    if saved_credits is not None:
        st.session_state.credits = int(saved_credits)
    else:
        st.session_state.credits = 2 # Default Free Trial

# =========================================================
# 💰 LOGIC: PAYMENT & CREDIT TOP-UP
# =========================================================
def verify_payment():
    query_params = st.query_params
    tracking_id = query_params.get("tracking_id", None) or query_params.get("checkout_id", None)
    
    if tracking_id:
        if tracking_id == "TEST-ADMIN":
            st.session_state.credits = 100
            st.toast("👨‍💻 Admin: 100 Credits Added")
            st.query_params.clear()
            return

        st.toast("Verifying Payment...", icon="💳")
        
        # Verify with IntaSend
        url = "https://payment.intasend.com/api/v1/payment/status/"
        headers = {"Authorization": f"Bearer {INTASEND_SEC_KEY}", "Content-Type": "application/json"}
        
        try:
            res = requests.post(url, json={"invoice_id": tracking_id}, headers=headers)
            response_data = res.json()
            
            if response_data.get('invoice', {}).get('state') == 'COMPLETE':
                # ✅ PAYMENT SUCCESS -> GIVE 100 CREDITS
                st.session_state.credits = 100
                
                # 💾 Save to Cookie (Persist for 30 days)
                cookie_manager.set("careerflow_credits", 100, 
                                 expires_at=datetime.datetime.now() + datetime.timedelta(days=30))
                
                st.toast("🎉 Payment Verified! 100 Credits Added.", icon="✅")
                
                st.query_params.clear() 
                time.sleep(1.5)
                st.rerun()
                
            elif response_data.get('invoice', {}).get('state') == 'PENDING':
                st.info("Payment processing...")
            else:
                st.error("Payment failed.")
        except Exception as e:
            st.error(f"Error: {e}")

# Run verification on load
verify_payment()

# =========================================================
# 🤖 SAMPLE GENERATOR (AUTO-RUNS ON LOAD)
# =========================================================
def generate_live_sample(region, job_title):
    if not GROQ_KEY: return "⚠️ API Key missing."
    try:
        client = Groq(api_key=GROQ_KEY)
        prompt = f"Generate a short, dense {region} summary for a {job_title}. Use Markdown."
        response = client.chat.completions.create(messages=[{"role":"user","content":prompt}], model="llama-3.3-70b-versatile")
        return response.choices[0].message.content
    except Exception as e: return f"Error: {e}"

# =========================================================
# ⚙️ MAIN APP
# =========================================================
def show_app():
    # HEADER with CREDIT DISPLAY
    c1, c2 = st.columns([3, 1])
    with c1: 
        st.title("🛠️ Resume Builder")
    with c2:
        # Display Credits
        creds = st.session_state.credits
        if creds > 5:
            st.markdown(f'<div style="text-align:right; margin-top:10px;"><span class="badge-credits">⚡ {creds} CREDITS LEFT</span></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div style="text-align:right; margin-top:10px;"><span class="badge-low">⚠️ ONLY {creds} LEFT</span></div>', unsafe_allow_html=True)

    st.divider()

    # 🔒 CREDIT WALL (If 0 credits)
    if st.session_state.credits <= 0:
        st.warning("🔒 You are out of credits.")
        st.markdown(f"""
        <div style="background:#f8f9fa; padding:30px; border-radius:10px; border:1px solid #ddd; text-align:center;">
            <h3>🚀 Top Up Your Account</h3>
            <p>Get <b>100 Credits</b> for KES 150.</p>
            <br>
            <a href="{PAYMENT_LINK_URL}" target="_self">
                <button style="background:#0F172A; color:white; padding:12px 25px; border-radius:6px; border:none; cursor:pointer; font-weight:bold; font-size:16px;">
                    👉 Buy 100 Credits (KES 150)
                </button>
            </a>
        </div>
        """, unsafe_allow_html=True)
        return

    # 🛠️ BUILDER FORM
    with st.form("builder"):
        doc_type = st.selectbox("Document Type", ["Resume / CV", "Cover Letter"])
        region = st.selectbox("Target Region", ["Kenya / UK", "USA / Canada", "Europe"])
        job_desc = st.text_area("Job Description", height=100)
        user_cv = st.text_area("Your Experience", height=100)
        
        # Show cost on button
        submitted = st.form_submit_button("✨ Generate Document (Costs 1 Credit)", type="primary", use_container_width=True)

    if submitted:
        if not GROQ_KEY:
            st.error("Missing API Key")
        elif not job_desc or not user_cv:
            st.error("Please fill in all fields.")
        else:
            with st.spinner("Generating..."):
                try:
                    client = Groq(api_key=GROQ_KEY)
                    prompt = f"Write a {doc_type} for {region}. Job: {job_desc}. My Info: {user_cv}"
                    res = client.chat.completions.create(messages=[{"role":"user","content":prompt}], model="llama-3.3-70b-versatile")
                    
                    st.session_state.generated_resume = res.choices[0].message.content
                    
                    # 💸 DEDUCT CREDIT & SAVE TO COOKIE
                    st.session_state.credits -= 1
                    cookie_manager.set("careerflow_credits", st.session_state.credits, expires_at=datetime.datetime.now() + datetime.timedelta(days=30))
                    
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    # RESULT DISPLAY
    if st.session_state.generated_resume:
        st.subheader("Result")
        st.text_area("Copy your text", st.session_state.generated_resume, height=400)
        
        # Simple Download Logic
        doc = Document()
        doc.add_paragraph(st.session_state.generated_resume)
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        st.download_button("📥 Download Word Doc", data=buffer, file_name="resume.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

# Start App
show_app()
