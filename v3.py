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
    # Ensure you use the SECRET KEY (starts with ISSecretKey_), not the Publishable Key
    INTASEND_SEC_KEY = st.secrets["INTASEND_SECRET_KEY"] 
    PAYMENT_LINK_URL = st.secrets["INTASEND_PAYMENT_LINK"]
except:
    # Fail gracefully if secrets aren't set yet
    GROQ_KEY = ""
    INTASEND_SEC_KEY = ""
    PAYMENT_LINK_URL = "#"

# --- 🍪 COOKIE MANAGER SETUP ---
def get_manager():
    return stx.CookieManager()

cookie_manager = get_manager()

# --- 🎨 CSS STYLING ---
def inject_custom_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
        
        /* Global Reset */
        .block-container { padding-top: 2rem; padding-bottom: 2rem; }
        h1, h2, h3 { font-family: 'Inter', sans-serif; letter-spacing: -0.5px; }
        p, li { font-family: 'Inter', sans-serif; line-height: 1.6; color: #334155; }

        /* HERO SECTION */
        .hero-box {
            background: linear-gradient(135deg, #0f172a 0%, #334155 100%);
            color: white;
            padding: 60px 40px;
            border-radius: 12px;
            text-align: center;
            margin-bottom: 40px;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
        }
        .hero-title { font-size: 3rem; font-weight: 800; margin-bottom: 10px; color: white; }
        .hero-sub { font-size: 1.25rem; color: #e2e8f0; font-weight: 300; max-width: 700px; margin: 0 auto; }

        /* VALUE PROPS */
        .value-card {
            background: white;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 25px;
            height: 100%;
            transition: all 0.3s ease;
        }
        .value-card:hover { transform: translateY(-5px); border-color: #3b82f6; box-shadow: 0 10px 20px rgba(0,0,0,0.05); }
        .icon-header { font-size: 2rem; margin-bottom: 15px; display: block; }
        .card-title { font-weight: 700; color: #1e293b; font-size: 1.1rem; margin-bottom: 8px; }

        /* PAPER PREVIEW EFFECT */
        .paper-preview {
            background-color: white;
            border: 1px solid #e2e8f0;
            padding: 50px;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
            font-family: 'Arial', 'Helvetica', sans-serif;
            color: #1e293b;
            font-size: 14px;
            line-height: 1.5;
            border-radius: 4px;
            min-height: 600px; 
            margin-top: 20px;
            max-width: 850px;
            margin-left: auto;
            margin-right: auto;
            white-space: pre-wrap; /* Preserves formatting from AI */
        }

        /* STATUS BADGES */
        .badge-free { background: #dbeafe; color: #1e40af; padding: 4px 12px; border-radius: 20px; font-weight: 600; font-size: 0.85rem; }
        .badge-pro { background: #dcfce7; color: #166534; padding: 4px 12px; border-radius: 20px; font-weight: 600; font-size: 0.85rem; border: 1px solid #166534; }
    </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# --- STATE MANAGEMENT ---
MAX_FREE_USES = 20

# Initialize Session State Variables
if 'is_pro' not in st.session_state: st.session_state.is_pro = False
if 'generated_resume' not in st.session_state: st.session_state.generated_resume = None
if 'sample_ke' not in st.session_state: st.session_state.sample_ke = None
if 'sample_us' not in st.session_state: st.session_state.sample_us = None

# Load Free Uses from Cookie
cookie_uses = cookie_manager.get(cookie="careerflow_uses")
if cookie_uses is None:
    if 'free_uses' not in st.session_state:
        st.session_state.free_uses = 0
else:
    st.session_state.free_uses = int(cookie_uses)

# =========================================================
# 💰 LOGIC: PAYMENT VERIFICATION (DEBUG & FIX)
# =========================================================
def verify_payment():
    # 1. Get Query Parameters
    query_params = st.query_params
    
    # 2. Check for ID (IntaSend can send 'tracking_id' OR 'checkout_id')
    tracking_id = query_params.get("tracking_id", None)
    if not tracking_id:
        tracking_id = query_params.get("checkout_id", None)
    
    if tracking_id:
        # Admin Bypass
        if tracking_id == "TEST-ADMIN":
            st.session_state.is_pro = True
            st.toast("👨‍💻 Admin Test Access Granted")
            st.query_params.clear() 
            return

        # 3. Verify with IntaSend API
        st.toast(f"Verifying Payment ID: {tracking_id}...")
        
        url = "https://payment.intasend.com/api/v1/payment/status/"
        headers = {
            "Authorization": f"Bearer {INTASEND_SEC_KEY}", 
            "Content-Type": "application/json"
        }
        
        try:
            res = requests.post(url, json={"invoice_id": tracking_id}, headers=headers)
            response_data = res.json()
            
            # DEBUG: Uncomment the line below if it still fails to see the exact error
            # st.write("Debug API Response:", response_data) 
            
            # Check for specific "COMPLETE" state
            if response_data.get('invoice', {}).get('state') == 'COMPLETE':
                st.session_state.is_pro = True
                st.toast("🎉 Payment Verified! Access Unlocked.")
                # IMPORTANT: Clear URL so refresh doesn't re-trigger
                st.query_params.clear()
            
            elif response_data.get('invoice', {}).get('state') == 'PENDING':
                st.warning("Payment is processing. Please refresh in a moment.")
            
            else:
                st.error(f"Payment Status: {response_data.get('invoice', {}).get('state')}")

        except Exception as e:
            st.error(f"Connection Error: {e}")

# Only run verification if they are NOT pro yet
if not st.session_state.is_pro:
    verify_payment()

# =========================================================
# 🤖 SAMPLE GENERATOR (AUTO-RUNS ON LOAD)
# =========================================================
def generate_live_sample(region, job_title):
    """Generates a sample CV using the AI to demonstrate capability."""
    if not GROQ_KEY:
        return "⚠️ System Error: API Key missing. Cannot generate sample."
    
    try:
        client = Groq(api_key=GROQ_KEY)
        prompt = f"""
        Generate a realistic, text-heavy, ATS-Optimized {region} for a Senior {job_title}. 
        
        RULES:
        1. Use Markdown formatting.
        2. Create a "Professional Summary" of 4 lines.
        3. Create 2 roles in "Work Experience" with 5 detailed bullet points each (include metrics).
        4. Do NOT use placeholders. Invent realistic companies and dates.
        5. If Kenya/UK: Use British English (e.g. 'Optimised').
        6. If USA: Use American English (e.g. 'Optimized').
        7. Make it look dense and professional.
        """
        response = client.chat.completions.create(messages=[{"role":"user","content":prompt}], model="llama-3.3-70b-versatile")
        return response.choices[0].message.content
    except Exception as e:
        return f"Could not generate sample: {e}"

# =========================================================
# 📝 CONTENT: SAMPLES & EDUCATION
# =========================================================
def show_landing_content():
    # 1. HERO SECTION
    st.markdown("""
    <div class="hero-box">
        <div class="hero-title">CareerFlow Global Architect</div>
        <div class="hero-sub">Region-Specific, ATS-Optimized Resumes & CVs. <br>Built for the US, UK, Kenya, and Europe.</div>
    </div>
    """, unsafe_allow_html=True)

    # 2. WHY IT MATTERS
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
        <div class="value-card">
            <span class="icon-header">🌍</span>
            <div class="card-title">Region Smart</div>
            <p>A US Resume is different from a Kenyan CV. We automatically adjust spelling (Color vs Colour), paper size, and layout based on your target country.</p>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="value-card">
            <span class="icon-header">🤖</span>
            <div class="card-title">Beat the ATS</div>
            <p>We analyze the job description to inject the exact keywords required to pass the Applicant Tracking System (ATS) filters.</p>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown("""
        <div class="value-card">
            <span class="icon-header">✨</span>
            <div class="card-title">Executive Formatting</div>
            <p>Clean, modern, and readable. Whether for Corporate, Tech, or Medical, we provide the standard that hiring managers expect.</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 3. LIVE AUTO-GENERATED SAMPLES
    st.subheader("👁️ Live AI Samples")
    st.markdown("We don't use templates. The samples below are **being generated live by our AI** right now to demonstrate the quality.")
    
    # Check if samples exist, if not generate them (Lazy Loading)
    if st.session_state.sample_ke is None or st.session_state.sample_us is None:
        with st.spinner("🤖 Waking up AI to generate fresh samples for you..."):
            # We generate both to have them ready
            st.session_state.sample_ke = generate_live_sample("CV (British/Kenyan Standard)", "Chief Accountant")
            st.session_state.sample_us = generate_live_sample("Resume (American Standard)", "Senior Data Scientist")
    
    # Display
    tab_ke, tab_us = st.tabs(["🇰🇪 Kenyan / UK CV Sample", "🇺🇸 USA Resume Sample"])
    
    with tab_ke:
        st.markdown(f"""<div class="paper-preview">{st.session_state.sample_ke}</div>""", unsafe_allow_html=True)
        
    with tab_us:
        st.markdown(f"""<div class="paper-preview">{st.session_state.sample_us}</div>""", unsafe_allow_html=True)

# =========================================================
# ⚙️ MAIN APP (BUILDER)
# =========================================================
def show_app():
    # HEADER
    c_head1, c_head2 = st.columns([3, 1])
    with c_head1:
        st.title("🛠️ Resume Builder")
    with c_head2:
        if st.session_state.is_pro:
            st.markdown('<div style="text-align:right; margin-top:10px;"><span class="badge-pro">💎 PRO ACCESS ACTIVE</span></div>', unsafe_allow_html=True)
        else:
            left = MAX_FREE_USES - st.session_state.free_uses
            st.markdown(f'<div style="text-align:right; margin-top:10px;"><span class="badge-free">⚡ {left} FREE TRIES LEFT</span></div>', unsafe_allow_html=True)

    st.markdown("---")

    # CHECK LIMITS
    if not st.session_state.is_pro and st.session_state.free_uses >= MAX_FREE_USES:
        st.warning("🔒 Free Limit Reached")
        col_pay1, col_pay2 = st.columns(2)
        with col_pay1:
            st.markdown("### 🚀 Get the Day Pass\n**Price:** KES 150\n\n* ✅ Unlimited Generations\n* ✅ All Region Formats")
        with col_pay2:
            st.markdown("<br>", unsafe_allow_html=True)
            if PAYMENT_LINK_URL != "#":
                st.link_button("👉 Pay with M-Pesa", PAYMENT_LINK_URL, type="primary", use_container_width=True)
            else:
                st.error("Payment Link not configured.")
        return

    # --- BUILDER FORM ---
    with st.form("builder_form"):
        # ROW 1: Type & Region
        col_meta1, col_meta2 = st.columns(2)
        with col_meta1:
            doc_type = st.selectbox("Document Type", ["Resume / CV", "Cover Letter"])
        with col_meta2:
            region = st.selectbox("Target Region format", [
                "Kenya / UK (British English, A4, 'CV')", 
                "USA / Canada (American English, Letter, 'Resume')",
                "Europe (Europass Standard)"
            ])

        # ROW 2: Industry
        industry = st.selectbox("Industry", ["Corporate", "Tech", "Medical", "Creative"])

        job_desc = st.text_area("1. Paste Job Advertisement", height=150, placeholder="The AI will extract keywords from here...")
        user_cv = st.text_area("2. Paste Your Experience", height=150, placeholder="Your work history, education, and skills...")
        
        submitted = st.form_submit_button("✨ Generate Document", type="primary", use_container_width=True)

    if submitted:
        if not job_desc or not user_cv:
            st.error("⚠️ Please fill in all fields.")
        else:
            if not GROQ_KEY:
                st.error("System Error: AI Key missing.")
            else:
                with st.spinner("🤖 Applying regional formatting & keywords..."):
                    try:
                        client = Groq(api_key=GROQ_KEY)
                        
                        prompt = f"""
                        Act as a professional career coach. Write a {doc_type} for the {industry} industry.
                        
                        TARGET REGION: {region}
                        
                        STRICT REGIONAL RULES:
                        - If Kenya/UK: Use British spelling (e.g., 'Organised', 'Colour'), date format DD/MM/YYYY, and header "Curriculum Vitae".
                        - If USA: Use American spelling (e.g., 'Organized', 'Color'), date format MM/DD/YYYY, and header "Resume".
                        - No Photos (indicate [Photo Placeholder] only if region is Europe).
                        
                        CONTEXT:
                        - Job Description: {job_desc}
                        - User Experience: {user_cv}
                        
                        INSTRUCTIONS:
                        1. Optimize heavily for ATS keywords found in the Job Description.
                        2. Use strong action verbs.
                        3. Format clearly with headers.
                        """
                        
                        response = client.chat.completions.create(messages=[{"role":"user","content":prompt}],model="llama-3.3-70b-versatile")
                        result_text = response.choices[0].message.content
                        
                        st.session_state.generated_resume = result_text
                        
                        # 🍪 UPDATE COOKIE & STATE
                        if not st.session_state.is_pro:
                            st.session_state.free_uses += 1
                            cookie_manager.set("careerflow_uses", st.session_state.free_uses, expires_at=datetime.datetime.now() + datetime.timedelta(days=30))
                            
                        st.rerun()
                    except Exception as e:
                        st.error(f"AI Error: {e}")

    # RESULT DISPLAY
    if st.session_state.generated_resume:
        st.divider()
        st.subheader("🎉 Your Draft is Ready")
        final_text = st.text_area("Editor", st.session_state.generated_resume, height=500)
        
        # Word Doc Generation
        doc = Document()
        style = doc.styles['Normal']
        font = style.font
        font.name = 'Arial'
        font.size = Pt(11)
        for line in final_text.split('\n'):
            if line.strip(): doc.add_paragraph(line)
        
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        
        st.download_button("📥 Download Word Doc", data=buffer, file_name=f"CareerFlow_{region.split()[0]}.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", type="primary")

# =========================================================
# 🚀 APP START
# =========================================================

# Only show marketing if they haven't generated anything yet
if not st.session_state.generated_resume and st.session_state.free_uses == 0:
    show_landing_content()

show_app()
