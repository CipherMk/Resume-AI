import streamlit as st
import requests
import datetime
import time
from groq import Groq
from docx import Document
from docx.shared import Pt
import io
import extra_streamlit_components as stx 

# --- ⚠️ CONFIGURATION & PAGE SETUP ---
st.set_page_config(page_title="CareerFlow | Professional CV Architect", page_icon="💼", layout="wide")

# --- 🔐 SECRETS ---
try:
    GROQ_KEY = st.secrets["GROQ_API_KEY"]
    INTASEND_SEC_KEY = st.secrets["INTASEND_SECRET_KEY"] 
    PAYMENT_LINK_URL = st.secrets["INTASEND_PAYMENT_LINK"]
except:
    # Fallback to prevent crash, but app won't work fully
    GROQ_KEY = ""
    INTASEND_SEC_KEY = ""
    PAYMENT_LINK_URL = "#"

# --- 🍪 COOKIE MANAGER (Persistence Engine) ---
@st.cache_resource
def get_manager():
    return stx.CookieManager()

cookie_manager = get_manager()
# --- 🍪 COOKIE MANAGER (Persistence Engine) ---
#@st.cache_resource(experimental_allow_widgets=True)
#def get_manager():
#    return stx.CookieManager()
#
#cookie_manager = get_manager()

# --- 🎨 PROFESSIONAL STYLING (CSS) ---
def inject_custom_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
        
        /* Base Styles */
        .block-container { padding-top: 1.5rem; }
        h1, h2, h3, h4, p, div { font-family: 'Inter', sans-serif; }
        
        /* HERO SECTION */
        .hero-box {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            color: white;
            padding: 50px 30px;
            border-radius: 16px;
            text-align: center;
            margin-bottom: 30px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.2);
        }
        .hero-title { font-size: 2.5rem; font-weight: 800; color: white; margin-bottom: 10px; }
        .hero-sub { color: #cbd5e1; font-size: 1.1rem; max-width: 600px; margin: 0 auto; }

        /* CREDIT BADGES */
        .badge-pro { 
            background: #dcfce7; color: #15803d; border: 1px solid #15803d; 
            padding: 5px 15px; border-radius: 50px; font-weight: 700; font-size: 0.9rem;
        }
        .badge-free { 
            background: #fff7ed; color: #c2410c; border: 1px solid #c2410c; 
            padding: 5px 15px; border-radius: 50px; font-weight: 700; font-size: 0.9rem;
        }

        /* PAPER PREVIEW */
        .paper-preview {
            background: white; border: 1px solid #e2e8f0; padding: 40px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            min-height: 500px; font-family: 'Times New Roman', serif; color: #333;
            margin-top: 20px; border-radius: 4px;
        }
    </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# =========================================================
# 💾 CREDIT LOGIC (The Brain)
# =========================================================

# 1. Initialize Session State
if 'generated_resume' not in st.session_state: st.session_state.generated_resume = None

# 2. Load Credits from Cookie (Priority) or Default to 2
if 'credits' not in st.session_state:
    saved_credits = cookie_manager.get("careerflow_credits")
    if saved_credits is not None:
        st.session_state.credits = int(saved_credits)
    else:
        st.session_state.credits = 2 # 🎁 Start with 2 Free Credits

# =========================================================
# 💰 PAYMENT VERIFICATION (Robust Connection)
# =========================================================
def verify_payment():
    # Get params
    query_params = st.query_params
    tracking_id = query_params.get("tracking_id", None) or query_params.get("checkout_id", None)
    
    if tracking_id:
        # Admin Bypass
        if tracking_id == "TEST-ADMIN":
            st.session_state.credits = 100
            cookie_manager.set("careerflow_credits", 100, expires_at=datetime.datetime.now() + datetime.timedelta(days=30))
            st.toast("👨‍💻 Admin: 100 Credits Loaded")
            st.query_params.clear()
            return

        st.toast("Connecting to Payment Gateway...", icon="💳")
        
        # 🔗 INTASEND CONNECTION
        # Note: We add a User-Agent to prevent '403 Forbidden' errors
        url = "https://payment.intasend.com/api/v1/payment/status/"
        headers = {
            "Authorization": f"Bearer {INTASEND_SEC_KEY}", 
            "Content-Type": "application/json",
            "User-Agent": "StreamlitApp/1.0"
        }
        
        try:
            res = requests.post(url, json={"invoice_id": tracking_id}, headers=headers, timeout=10)
            response_data = res.json()
            
            # Check for success
            if response_data.get('invoice', {}).get('state') == 'COMPLETE':
                # ✅ UPDATE CREDITS TO 100
                st.session_state.credits = 100
                
                # 💾 SAVE TO COOKIE (So they stay wealthy on refresh)
                cookie_manager.set("careerflow_credits", 100, 
                                 expires_at=datetime.datetime.now() + datetime.timedelta(days=30))
                
                st.toast("🎉 Payment Confirmed! 100 Credits Added.", icon="✅")
                
                # Cleanup
                st.query_params.clear()
                time.sleep(2)
                st.rerun()
                
            elif response_data.get('invoice', {}).get('state') == 'PENDING':
                st.info("Payment is processing... please wait a moment.")
            else:
                st.error("Payment was not completed. Please try again.")
                
        except Exception as e:
            # Handle connection refusals gracefully
            st.error(f"Connection Error: {e}")

# Run verification immediately on load
verify_payment()

# =========================================================
# 📝 LANDING CONTENT (For First Time Users)
# =========================================================
def show_hero():
    st.markdown("""
    <div class="hero-box">
        <div class="hero-title">CareerFlow CV Architect</div>
        <div class="hero-sub"> ATS-Optimized Resumes & CVs for Kenya, USA, and Europe.<br>Built by AI. Trusted by Professionals.</div>
    </div>
    """, unsafe_allow_html=True)

# =========================================================
# ⚙️ MAIN APP INTERFACE
# =========================================================
def show_app():
    
    # 1. Show Header
    c_head1, c_head2 = st.columns([3, 1])
    with c_head1:
        st.title("🛠️ Resume Builder")
    with c_head2:
        # 💎 Credit Badge Logic
        creds = st.session_state.credits
        if creds > 10:
             st.markdown(f'<div style="text-align:right; margin-top:15px;"><span class="badge-pro">💎 {creds} CREDITS (PRO)</span></div>', unsafe_allow_html=True)
        else:
             st.markdown(f'<div style="text-align:right; margin-top:15px;"><span class="badge-free">⚡ {creds} FREE CREDITS</span></div>', unsafe_allow_html=True)

    st.divider()

    # 2. 🔒 Paywall Check (Block if 0 credits)
    if st.session_state.credits <= 0:
        st.warning("🔒 You have run out of free credits.")
        
        col_pay1, col_pay2 = st.columns([2, 1])
        with col_pay1:
            st.markdown("""
            ### 🚀 Upgrade to Pro
            **Get 100 Credits for KES 150**
            * ✅ Generates 100 Resumes or Cover Letters
            * ✅ Unlocks All Regional Formats
            * ✅ Instant Access
            """)
        with col_pay2:
            st.markdown("<br>", unsafe_allow_html=True)
            if PAYMENT_LINK_URL != "#":
                st.link_button("👉 Buy 100 Credits (KES 150)", PAYMENT_LINK_URL, type="primary", use_container_width=True)
            else:
                st.error("Payment link missing in secrets.")
        return

    # 3. 🛠️ The Builder Form
    with st.form("builder_form"):
        col_meta1, col_meta2 = st.columns(2)
        with col_meta1:
            doc_type = st.selectbox("Document Type", ["Resume / CV", "Cover Letter"])
        with col_meta2:
            region = st.selectbox("Target Region format", [
                "Kenya / UK (British English, A4)", 
                "USA / Canada (American English, Letter)",
                "Europe (Europass Standard)"
            ])

        industry = st.selectbox("Industry", ["Corporate / Business", "Tech / IT", "Medical / Health", "Creative / Design", "General"])

        st.markdown("### 📄 Job Details")
        job_desc = st.text_area("1. Paste Job Advertisement (The AI will extract keywords)", height=150)
        user_cv = st.text_area("2. Paste Your Experience (Work history, education, skills)", height=150)
        
        # Submit Button with Cost Indication
        submitted = st.form_submit_button(f"✨ Generate Document (Cost: 1 Credit)", type="primary", use_container_width=True)

    # 4. 🧠 Generation Logic
    if submitted:
        if not job_desc or not user_cv:
            st.error("⚠️ Please fill in all fields.")
        elif not GROQ_KEY:
            st.error("⚠️ System Error: AI Key missing.")
        else:
            with st.spinner("🤖 Analyzing keywords & formatting document..."):
                try:
                    client = Groq(api_key=GROQ_KEY)
                    
                    # Region-Specific Prompting
                    prompt = f"""
                    Act as an expert Resume Writer for the {industry} industry.
                    Write a {doc_type} targeting {region}.
                    
                    STRICT FORMATTING RULES:
                    - If Kenya/UK: Use British spelling (Colour, Organised), Date DD/MM/YYYY.
                    - If USA: Use American spelling (Color, Organized), Date MM/DD/YYYY.
                    
                    INPUT DATA:
                    Job Description: {job_desc}
                    Candidate Info: {user_cv}
                    
                    INSTRUCTIONS:
                    1. Use professional, dense headers.
                    2. Use Markdown formatting.
                    3. Quantify achievements where possible.
                    """
                    
                    response = client.chat.completions.create(messages=[{"role":"user","content":prompt}],model="llama-3.3-70b-versatile")
                    result_text = response.choices[0].message.content
                    
                    st.session_state.generated_resume = result_text
                    
                    # 💸 DEDUCT CREDIT
                    st.session_state.credits -= 1
                    # 💾 UPDATE COOKIE
                    cookie_manager.set("careerflow_credits", st.session_state.credits, expires_at=datetime.datetime.now() + datetime.timedelta(days=30))
                    
                    st.rerun()
                except Exception as e:
                    st.error(f"AI Generation Error: {e}")

    # 5. 📄 Result Display
    if st.session_state.generated_resume:
        st.markdown("---")
        st.subheader("🎉 Your Document is Ready")
        
        # Create Word Doc
        doc = Document()
        doc.add_paragraph(st.session_state.generated_resume) # Simplified for stability
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        
        c_res1, c_res2 = st.columns([1, 1])
        with c_res1:
            st.download_button("📥 Download Word (.docx)", data=buffer, file_name=f"CareerFlow_Resume.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", type="primary", use_container_width=True)
        
        # Preview
        st.markdown(f'<div class="paper-preview">{st.session_state.generated_resume}</div>', unsafe_allow_html=True)

# =========================================================
# 🚀 APP STARTUP
# =========================================================

# Only show Hero if they haven't generated anything yet
if not st.session_state.generated_resume:
    show_hero()

show_app()

