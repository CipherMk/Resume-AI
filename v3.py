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
st.set_page_config(page_title="CareerFlow | Global CV Architect", page_icon="🌍", layout="wide")

# --- 🔐 SECRETS MANAGEMENT ---
try:
    GROQ_KEY = st.secrets["GROQ_API_KEY"]
    INTASEND_SEC_KEY = st.secrets["INTASEND_SECRET_KEY"] 
    PAYMENT_LINK_URL = st.secrets["INTASEND_PAYMENT_LINK"]
except FileNotFoundError:
    st.error("Secrets file not found. Please configure .streamlit/secrets.toml")
    st.stop()
except KeyError:
    # Fail gracefully for UI testing if keys are missing
    GROQ_KEY = ""
    INTASEND_SEC_KEY = ""
    PAYMENT_LINK_URL = "#"

# --- 🍪 COOKIE MANAGER SETUP ---
# using st.cache_resource to ensure manager isn't reloaded unnecessarily
@st.cache_resource(experimental_allow_widgets=True)
def get_manager():
    return stx.CookieManager()

cookie_manager = get_manager()

# --- 🎨 CSS STYLING (Professional SaaS Look) ---
def inject_custom_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
        
        /* Global Reset */
        .block-container { padding-top: 2rem; padding-bottom: 2rem; }
        h1, h2, h3, h4, h5, h6 { font-family: 'Inter', sans-serif; letter-spacing: -0.5px; color: #0f172a; }
        p, li, div { font-family: 'Inter', sans-serif; line-height: 1.6; color: #334155; }
        
        /* HERO SECTION */
        .hero-box {
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            color: white;
            padding: 60px 40px;
            border-radius: 16px;
            text-align: center;
            margin-bottom: 40px;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
        }
        .hero-title { font-size: 3.5rem; font-weight: 800; margin-bottom: 10px; color: white; }
        .hero-sub { font-size: 1.25rem; color: #94a3b8; font-weight: 300; max-width: 700px; margin: 0 auto; }

        /* VALUE PROPS CARD */
        .value-card {
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 30px;
            height: 100%;
            transition: all 0.3s ease;
        }
        .value-card:hover { transform: translateY(-5px); border-color: #3b82f6; box-shadow: 0 10px 20px rgba(0,0,0,0.05); }
        .icon-header { font-size: 2.5rem; margin-bottom: 15px; display: block; }
        .card-title { font-weight: 700; color: #0f172a; font-size: 1.2rem; margin-bottom: 8px; }

        /* PAPER PREVIEW EFFECT */
        .paper-preview {
            background-color: white;
            border: 1px solid #e2e8f0;
            padding: 50px;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
            font-family: 'Times New Roman', Times, serif; /* CV Standard */
            color: #1e293b;
            font-size: 14px;
            line-height: 1.4;
            border-radius: 2px;
            min-height: 500px; 
            margin-top: 20px;
            white-space: pre-wrap; 
        }

        /* STATUS BADGES */
        .badge-free { background: #eff6ff; color: #1d4ed8; padding: 6px 16px; border-radius: 20px; font-weight: 700; font-size: 0.85rem; border: 1px solid #bfdbfe; }
        .badge-pro { background: #f0fdf4; color: #15803d; padding: 6px 16px; border-radius: 20px; font-weight: 700; font-size: 0.85rem; border: 1px solid #86efac; box-shadow: 0 0 10px #86efac66; }
        
        /* PAYWALL BOX */
        .paywall-container {
            border: 2px dashed #cbd5e1;
            background-color: #f8fafc;
            border-radius: 12px;
            padding: 40px;
            text-align: center;
            margin-top: 20px;
        }
    </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# --- STATE MANAGEMENT ---
MAX_FREE_USES = 1 # Set strict limit for testing (Change to 2 or 3 for prod)

# Initialize Session State Variables
if 'is_pro' not in st.session_state: st.session_state.is_pro = False
if 'generated_resume' not in st.session_state: st.session_state.generated_resume = None
if 'free_uses' not in st.session_state: st.session_state.free_uses = 0

# Sync with Cookies (Persist Free Limit)
time.sleep(0.1) # Brief pause for cookie manager to load
cookie_uses = cookie_manager.get(cookie="careerflow_uses")

if cookie_uses:
    st.session_state.free_uses = int(cookie_uses)

# =========================================================
# 💰 LOGIC: PREMIUM ACCESS VERIFICATION
# =========================================================
def verify_payment():
    """
    Checks URL parameters for IntaSend transaction ID.
    Verifies status with API and unlocks PRO mode.
    """
    # 1. Get Query Parameters (New Streamlit Syntax)
    query_params = st.query_params
    
    # 2. Check for ID (IntaSend can send 'tracking_id' OR 'checkout_id')
    tracking_id = query_params.get("tracking_id", None)
    if not tracking_id:
        tracking_id = query_params.get("checkout_id", None)
    
    if tracking_id:
        # Admin Bypass for Testing
        if tracking_id == "TEST-ADMIN":
            st.session_state.is_pro = True
            st.toast("👨‍💻 Admin Test Access Granted", icon="🔓")
            st.query_params.clear() 
            return

        # 3. Verify with IntaSend API
        st.toast(f"Verifying Payment ID: {tracking_id}...", icon="⏳")
        
        url = "https://payment.intasend.com/api/v1/payment/status/"
        headers = {
            "Authorization": f"Bearer {INTASEND_SEC_KEY}", 
            "Content-Type": "application/json"
        }
        
        try:
            res = requests.post(url, json={"invoice_id": tracking_id}, headers=headers)
            response_data = res.json()
            
            # Check for specific "COMPLETE" state
            state = response_data.get('invoice', {}).get('state')
            
            if state == 'COMPLETE':
                st.session_state.is_pro = True
                st.balloons()
                st.toast("🎉 Payment Verified! Premium Unlocked.", icon="✅")
                # Clear URL so refresh doesn't re-trigger
                st.query_params.clear()
            
            elif state == 'PENDING':
                st.warning("Payment is processing. Please wait a moment and refresh.")
            
            elif state == 'FAILED':
                st.error("Payment failed. Please try again.")

        except Exception as e:
            st.error(f"Connection Error: {e}")

# Run verification on every reload if not Pro
if not st.session_state.is_pro:
    verify_payment()

# =========================================================
# 📝 CONTENT: LANDING PAGE
# =========================================================
def show_landing_content():
    # HERO
    st.markdown("""
    <div class="hero-box">
        <div class="hero-title">CareerFlow AI</div>
        <div class="hero-sub">ATS-Optimized Resumes for the Global Market.<br>Built for the US, UK, Kenya, and Europe.</div>
    </div>
    """, unsafe_allow_html=True)

    # VALUE PROPS
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
        <div class="value-card">
            <span class="icon-header">🌍</span>
            <div class="card-title">Region Intelligence</div>
            <p>A US Resume is not a Kenyan CV. We auto-adjust spelling, paper size, and layout standards.</p>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="value-card">
            <span class="icon-header">🤖</span>
            <div class="card-title">ATS Optimization</div>
            <p>Our AI analyzes the job description to inject the exact keywords required to pass screening bots.</p>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown("""
        <div class="value-card">
            <span class="icon-header">✨</span>
            <div class="card-title">Pro Formatting</div>
            <p>Clean, executive formatting that hiring managers love. No broken layouts or messy tables.</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

# =========================================================
# ⚙️ MAIN APP (BUILDER)
# =========================================================
def show_app():
    # HEADER & STATUS
    c_head1, c_head2 = st.columns([3, 1])
    with c_head1:
        st.title("🛠️ Resume Architect")
    with c_head2:
        if st.session_state.is_pro:
            st.markdown('<div style="text-align:right; margin-top:10px;"><span class="badge-pro">💎 PRO ACCESS ACTIVE</span></div>', unsafe_allow_html=True)
        else:
            left = MAX_FREE_USES - st.session_state.free_uses
            # Clamp to 0
            if left < 0: left = 0
            st.markdown(f'<div style="text-align:right; margin-top:10px;"><span class="badge-free">⚡ {left} FREE TRIES LEFT</span></div>', unsafe_allow_html=True)

    # --- 🔒 PAYWALL LOGIC ---
    # Logic: If User is NOT pro AND has exceeded free uses -> Show Paywall
    if not st.session_state.is_pro and st.session_state.free_uses >= MAX_FREE_USES:
        st.markdown(f"""
        <div class="paywall-container">
            <h2>🔒 Free Limit Reached</h2>
            <p>You have used your free generations. Upgrade to <b>Premium</b> for unlimited access.</p>
            <br>
        </div>
        """, unsafe_allow_html=True)
        
        col_pay1, col_pay2, col_pay3 = st.columns([1,2,1])
        with col_pay2:
             if PAYMENT_LINK_URL != "#":
                st.link_button(
                    label="👉 Unlock Unlimited Access (KES 150)", 
                    url=PAYMENT_LINK_URL, 
                    type="primary", 
                    use_container_width=True
                )
             else:
                st.error("Payment integration missing. Contact Admin.")
        return # Stop execution here so form doesn't render

    # --- BUILDER FORM (Only shows if allowed) ---
    with st.form("builder_form"):
        # ROW 1: Type & Region
        col_meta1, col_meta2 = st.columns(2)
        with col_meta1:
            doc_type = st.selectbox("Document Type", ["Resume / CV", "Cover Letter"])
        with col_meta2:
            region = st.selectbox("Target Region", [
                "Kenya / UK (British English, A4)", 
                "USA / Canada (American English, Letter)",
                "Europe (Europass Standard)"
            ])

        # ROW 2: Industry
        industry = st.selectbox("Industry / Role", ["Corporate", "Tech", "Medical", "Creative", "Legal"])

        # ROW 3: Inputs
        st.markdown("#### 1. The Job You Want")
        job_desc = st.text_area("Paste the Job Advertisement here", height=150, help="The AI will extract keywords from here to beat the ATS.")
        
        st.markdown("#### 2. Your Experience")
        user_cv = st.text_area("Paste your current CV/Resume content here", height=150, placeholder="Work history, education, skills, and summary...")
        
        submitted = st.form_submit_button("✨ Generate Document", type="primary", use_container_width=True)

    if submitted:
        if not job_desc or not user_cv:
            st.error("⚠️ Please fill in all fields.")
        else:
            if not GROQ_KEY:
                st.error("System Error: AI Key missing.")
            else:
                with st.spinner("🤖 Analyzing keywords & formatting document..."):
                    try:
                        client = Groq(api_key=GROQ_KEY)
                        
                        prompt = f"""
                        Act as an expert Resume Writer. Write a {doc_type} for the {industry} industry.
                        
                        TARGET REGION: {region}
                        
                        STRICT FORMATTING RULES:
                        - If Kenya/UK: Use British spelling ('Organised'), date format DD/MM/YYYY.
                        - If USA: Use American spelling ('Organized'), date format MM/DD/YYYY.
                        - Structure: Professional Summary, Core Competencies, Professional Experience (with metrics), Education.
                        - Output format: Clean Markdown.
                        
                        CONTEXT:
                        - Target Job: {job_desc}
                        - Candidate Info: {user_cv}
                        
                        INSTRUCTIONS:
                        1. Optimize heavily for ATS keywords found in the Target Job.
                        2. Quantify achievements (add % and numbers where implied).
                        3. Do not include placeholders like [Your Name], just use the data provided or generic placeholders if data is missing.
                        """
                        
                        response = client.chat.completions.create(
                            messages=[{"role":"user","content":prompt}],
                            model="llama-3.3-70b-versatile"
                        )
                        result_text = response.choices[0].message.content
                        
                        st.session_state.generated_resume = result_text
                        
                        # 🍪 INCREMENT USAGE (If not pro)
                        if not st.session_state.is_pro:
                            st.session_state.free_uses += 1
                            # Update cookie to expire in 30 days
                            cookie_manager.set("careerflow_uses", st.session_state.free_uses, expires_at=datetime.datetime.now() + datetime.timedelta(days=30))
                        
                        st.rerun() # Rerun to refresh the state/UI
                    except Exception as e:
                        st.error(f"AI Error: {e}")

    # --- RESULT DISPLAY ---
    if st.session_state.generated_resume:
        st.divider()
        st.subheader("🎉 Your Draft is Ready")
        
        c_res1, c_res2 = st.columns([3, 2])
        
        with c_res1:
            st.markdown("### Preview")
            st.markdown(f"""<div class="paper-preview">{st.session_state.generated_resume}</div>""", unsafe_allow_html=True)
            
        with c_res2:
            st.markdown("### Export")
            st.info("💡 You can edit the text below before downloading.")
            final_text = st.text_area("Final Edit", st.session_state.generated_resume, height=400)
            
            # Word Doc Generation
            doc = Document()
            style = doc.styles['Normal']
            font = style.font
            font.name = 'Arial'
            font.size = Pt(11)
            
            for line in final_text.split('\n'):
                if line.startswith('#'):
                    # Simple clean up of markdown headers for docx
                    clean_line = line.replace('#', '').strip()
                    doc.add_heading(clean_line, level=1)
                elif line.strip(): 
                    doc.add_paragraph(line)
            
            buffer = io.BytesIO()
            doc.save(buffer)
            buffer.seek(0)
            
            st.download_button(
                label="📥 Download Word (.docx)", 
                data=buffer, 
                file_name=f"CareerFlow_CV.docx", 
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", 
                type="primary",
                use_container_width=True
            )

# =========================================================
# 🚀 APP ENTRY POINT
# =========================================================

# Show landing page only if user is new and hasn't generated anything
if st.session_state.free_uses == 0 and not st.session_state.generated_resume:
    show_landing_content()

show_app()