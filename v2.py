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

# --- 🍪 COOKIE MANAGER (The Secret to Automatic Access) ---
def get_manager():
    return stx.CookieManager()

cookie_manager = get_manager()

# --- 🎨 CSS STYLING ---
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
        .badge-pro { background: #dcfce7; color: #166534; padding: 4px 12px; border-radius: 20px; font-weight: 600; border: 1px solid #166534; }
    </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# --- STATE MANAGEMENT ---
MAX_FREE_USES = 2

# 1. Initialize State
if 'is_pro' not in st.session_state: st.session_state.is_pro = False
if 'generated_resume' not in st.session_state: st.session_state.generated_resume = None

# 2. CHECK COOKIES FOR EXISTING PRO ACCESS
# This runs every time the app loads. If they paid yesterday, this unlocks them today.
pro_cookie = cookie_manager.get("careerflow_pro_status")
if pro_cookie == "active":
    st.session_state.is_pro = True

# 3. Load Free Uses
cookie_uses = cookie_manager.get("careerflow_uses")
if cookie_uses is None:
    if 'free_uses' not in st.session_state: st.session_state.free_uses = 0
else:
    st.session_state.free_uses = int(cookie_uses)

# =========================================================
# 💰 AUTOMATIC PAYMENT VERIFICATION
# =========================================================
def verify_payment():
    # Get ID from URL (e.g. ?tracking_id=123)
    query_params = st.query_params
    tracking_id = query_params.get("tracking_id", None) or query_params.get("checkout_id", None)
    
    if tracking_id:
        # Admin Bypass
        if tracking_id == "TEST-ADMIN":
            st.session_state.is_pro = True
            st.toast("👨‍💻 Admin Access")
            st.query_params.clear()
            return

        # Check with IntaSend
        st.toast("Verifying Payment...", icon="💳")
        url = "https://payment.intasend.com/api/v1/payment/status/"
        headers = {"Authorization": f"Bearer {INTASEND_SEC_KEY}", "Content-Type": "application/json"}
        
        try:
            res = requests.post(url, json={"invoice_id": tracking_id}, headers=headers)
            response_data = res.json()
            
            if response_data.get('invoice', {}).get('state') == 'COMPLETE':
                # ✅ SUCCESS!
                st.session_state.is_pro = True
                
                # 💾 SAVE TO COOKIE (Expires in 30 days)
                # This ensures they stay Pro even if they refresh the page
                cookie_manager.set("careerflow_pro_status", "active", 
                                 expires_at=datetime.datetime.now() + datetime.timedelta(days=30))
                
                st.toast("🎉 Payment Successful! Unlocking Pro Mode...", icon="✅")
                
                # 🧹 CLEANUP & REFRESH
                st.query_params.clear() # Remove the ID from URL
                time.sleep(1.5)         # Give time for cookie to set
                st.rerun()              # Force reload to show Pro interface
                
            elif response_data.get('invoice', {}).get('state') == 'PENDING':
                st.info("Payment is processing... Please wait.")
            else:
                st.error("Payment not completed. Please try again.")
        except Exception as e:
            st.error(f"Verification Error: {e}")

# Run verification ONLY if they aren't Pro yet
if not st.session_state.is_pro:
    verify_payment()

# =========================================================
# 🤖 APP LOGIC
# =========================================================
def show_app():
    # HEADER
    c1, c2 = st.columns([3, 1])
    with c1: st.title("🛠️ Resume Builder")
    with c2:
        if st.session_state.is_pro:
            st.markdown('<div style="text-align:right; margin-top:10px;"><span class="badge-pro">💎 UNLIMITED PRO ACCESS</span></div>', unsafe_allow_html=True)
        else:
            left = MAX_FREE_USES - st.session_state.free_uses
            st.markdown(f'<div style="text-align:right; margin-top:10px;">⚡ {left} FREE TRIES LEFT</div>', unsafe_allow_html=True)

    st.divider()

    # LIMIT CHECKER
    if not st.session_state.is_pro and st.session_state.free_uses >= MAX_FREE_USES:
        st.warning("🔒 Free Limit Reached")
        st.markdown(f"""
        <div style="background:#f8f9fa; padding:20px; border-radius:10px; border:1px solid #ddd; text-align:center;">
            <h3>🚀 Upgrade to Pro</h3>
            <p>Get unlimited AI generations and all regional formats.</p>
            <a href="{PAYMENT_LINK_URL}" target="_self">
                <button style="background:#0F172A; color:white; padding:10px 20px; border-radius:5px; border:none; cursor:pointer; font-size:16px;">
                    👉 Pay KES 150 to Unlock
                </button>
            </a>
        </div>
        """, unsafe_allow_html=True)
        return

    # BUILDER FORM
    with st.form("builder"):
        doc_type = st.selectbox("Document Type", ["Resume / CV", "Cover Letter"])
        region = st.selectbox("Target Region", ["Kenya / UK", "USA / Canada", "Europe"])
        job_desc = st.text_area("Job Description", height=100)
        user_cv = st.text_area("Your Experience", height=100)
        submitted = st.form_submit_button("Generate", type="primary", use_container_width=True)

    if submitted:
        if not GROQ_KEY:
            st.error("Missing API Key")
        else:
            with st.spinner("Generating..."):
                try:
                    client = Groq(api_key=GROQ_KEY)
                    prompt = f"Write a {doc_type} for {region}. Job: {job_desc}. My Info: {user_cv}"
                    res = client.chat.completions.create(messages=[{"role":"user","content":prompt}], model="llama-3.3-70b-versatile")
                    st.session_state.generated_resume = res.choices[0].message.content
                    
                    # Deduct Credit if Free
                    if not st.session_state.is_pro:
                        st.session_state.free_uses += 1
                        cookie_manager.set("careerflow_uses", st.session_state.free_uses, expires_at=datetime.datetime.now() + datetime.timedelta(days=30))
                    
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    if st.session_state.generated_resume:
        st.subheader("Result")
        st.text_area("Copy your text", st.session_state.generated_resume, height=400)

# Start
show_app()
