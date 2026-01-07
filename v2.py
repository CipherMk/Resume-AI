import streamlit as st
import requests
from groq import Groq
from docx import Document
from docx.shared import Pt
import io

# --- CONFIGURATION ---
st.set_page_config(page_title="CareerFlow | AI Resume Architect", page_icon="💼", layout="wide")

# Safe access to Secrets
try:
    GROQ_KEY = st.secrets["GROQ_API_KEY"]
    INTASEND_PUB_KEY = st.secrets["INTASEND_PUBLISHABLE_KEY"]
    INTASEND_SEC_KEY = st.secrets["INTASEND_SECRET_KEY"]
    # This is the link you created in IntaSend Dashboard
    PAYMENT_LINK_URL = st.secrets["INTASEND_PAYMENT_LINK"] 
except:
    st.error("⚠️ Secrets missing. Please set API keys in .streamlit/secrets.toml")
    st.stop()

# --- STATE MANAGEMENT ---
if 'is_pro' not in st.session_state: st.session_state.is_pro = False
if 'free_uses' not in st.session_state: st.session_state.free_uses = 0
if 'generated_resume' not in st.session_state: st.session_state.generated_resume = None

MAX_FREE_USES = 2

# =========================================================
# 💰 AUTOMATIC PAYMENT VERIFICATION
# =========================================================
def verify_intasend_payment():
    """
    Checks URL parameters for a tracking_id and verifies it with IntaSend.
    """
    # 1. Get Query Params (e.g. ?tracking_id=12345&signature=...)
    query_params = st.query_params
    tracking_id = query_params.get("tracking_id", None)

    if tracking_id:
        # 2. If we have an ID, call IntaSend API to verify status
        url = "https://payment.intasend.com/api/v1/payment/status/"
        headers = {
            "Authorization": f"Bearer {INTASEND_SEC_KEY}",
            "Content-Type": "application/json"
        }
        payload = {"invoice_id": tracking_id}

        try:
            response = requests.post(url, json=payload, headers=headers)
            data = response.json()
            
            # 3. Check if payment is marked as 'COMPLETE'
            if response.status_code == 200 and data['invoice']['state'] == 'COMPLETE':
                st.session_state.is_pro = True
                st.toast("✅ Payment Verified! Premium Access Unlocked.", icon="🎉")
                
                # Optional: Clear the URL so if they refresh, it doesn't re-verify
                # st.query_params.clear() 
                return True
            else:
                st.error("Payment verification failed or pending.")
                return False
        except Exception as e:
            st.error(f"Error contacting payment gateway: {e}")
            return False
    return False

# Run verification immediately on app load
if not st.session_state.is_pro:
    verify_intasend_payment()

# =========================================================
# 🎨 UI & LOGIC
# =========================================================

def show_hero():
    st.markdown("""
    <style>
        .hero {
            background-color: #f8fafc; padding: 40px; border-radius: 10px; text-align: center; border: 1px solid #e2e8f0;
        }
        .pro-badge {
            background-color: #dcfce7; color: #166534; padding: 5px 15px; border-radius: 15px; font-weight: bold; font-size: 0.9rem;
        }
    </style>
    """, unsafe_allow_html=True)
    
    if st.session_state.is_pro:
        st.markdown(f"<div class='hero'><h1>🚀 CareerFlow <span class='pro-badge'>PRO ACTIVE</span></h1><p>Unlimited AI Generations Enabled</p></div>", unsafe_allow_html=True)
    else:
        left = MAX_FREE_USES - st.session_state.free_uses
        st.markdown(f"<div class='hero'><h1>🚀 CareerFlow</h1><p>Free Generations Left: <b>{left}</b></p></div>", unsafe_allow_html=True)

def show_paywall():
    st.warning("🔒 Free Limit Reached")
    st.markdown("### Upgrade to Resume Pro")
    st.write("Get unlimited access for 24 hours. Instant activation.")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        st.metric("Price", "KES 150")
    with col2:
        # THIS BUTTON SENDS THEM TO INTASEND
        st.link_button("👉 Pay Now (M-Pesa / Card)", PAYMENT_LINK_URL, type="primary", use_container_width=True)
        
    st.caption("Once payment is complete, you will be automatically redirected back here with access.")

# =========================================================
# ⚙️ MAIN APP
# =========================================================

show_hero()

# Logic: If NOT pro AND used up free tries -> Show Paywall
if not st.session_state.is_pro and st.session_state.free_uses >= MAX_FREE_USES:
    st.divider()
    show_paywall()

else:
    # Show the Builder
    st.divider()
    c1, c2 = st.columns(2)
    job_desc = c1.text_area("Job Description", placeholder="Paste the job advert here...")
    user_cv = c2.text_area("Your Experience", placeholder="Paste your old CV here...")
    
    if st.button("Generate Resume", type="primary"):
        if job_desc and user_cv:
            # AI GENERATION MOCKUP
            # (Replace with your actual Groq call)
            time.sleep(1) 
            st.session_state.generated_resume = f"RESUME FOR JOB: {job_desc[:20]}...\n\nBased on: {user_cv[:20]}..."
            
            # Count usage if not pro
            if not st.session_state.is_pro:
                st.session_state.free_uses += 1
            st.rerun()
        else:
            st.warning("Please fill in both fields.")

    if st.session_state.generated_resume:
        st.success("Resume Generated!")
        st.text_area("Result", st.session_state.generated_resume, height=300)
