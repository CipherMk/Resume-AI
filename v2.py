import streamlit as st
import requests
import time
from groq import Groq
from docx import Document
from docx.shared import Pt
import io

# --- ⚠️ CONFIGURATION ---
st.set_page_config(page_title="CareerFlow | Professional CV Architect", page_icon="👔", layout="wide")

# Safe Secret Access
try:
    GROQ_KEY = st.secrets["GROQ_API_KEY"]
    INTASEND_PUB_KEY = st.secrets["INTASEND_PUBLISHABLE_KEY"]
    INTASEND_SEC_KEY = st.secrets["INTASEND_SECRET_KEY"]
    PAYMENT_LINK_URL = st.secrets["INTASEND_PAYMENT_LINK"]
except:
    # Fallback for first run/debugging
    GROQ_KEY = ""
    INTASEND_PUB_KEY = ""
    INTASEND_SEC_KEY = ""
    PAYMENT_LINK_URL = "#"

# --- 🎨 ENTERPRISE STYLING ---
def inject_custom_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&family=Merriweather:wght@300;700&display=swap');
        
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
            border: 1px solid #cbd5e1;
            padding: 40px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            font-family: 'Merriweather', serif; /* Serif for that "Document" feel */
            color: #0f172a;
            font-size: 0.95rem;
            line-height: 1.7;
            border-radius: 2px;
            min-height: 400px;
            margin-top: 20px;
        }
        .paper-header { border-bottom: 2px solid #0f172a; padding-bottom: 10px; margin-bottom: 20px; }
        .paper-h1 { font-size: 1.8rem; font-weight: bold; text-transform: uppercase; margin:0; }
        .paper-sub { color: #64748b; font-size: 0.9rem; font-family: 'Inter', sans-serif; }
        
        /* STATUS BADGES */
        .badge-free { background: #dbeafe; color: #1e40af; padding: 4px 12px; border-radius: 20px; font-weight: 600; font-size: 0.85rem; }
        .badge-pro { background: #dcfce7; color: #166534; padding: 4px 12px; border-radius: 20px; font-weight: 600; font-size: 0.85rem; border: 1px solid #166534; }
    </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# --- STATE MANAGEMENT ---
if 'is_pro' not in st.session_state: st.session_state.is_pro = False
if 'free_uses' not in st.session_state: st.session_state.free_uses = 0
if 'generated_resume' not in st.session_state: st.session_state.generated_resume = None

MAX_FREE_USES = 2

# =========================================================
# 💰 LOGIC: PAYMENT & ACCESS
# =========================================================
def verify_payment():
    query_params = st.query_params
    tracking_id = query_params.get("tracking_id", None)
    
    if tracking_id:
        # TEST BACKDOOR (REMOVE IN PRODUCTION)
        if tracking_id == "TEST-ADMIN":
            st.session_state.is_pro = True
            st.toast("👨‍💻 Admin Test Access Granted")
            return

        # REAL VERIFICATION
        url = "https://payment.intasend.com/api/v1/payment/status/"
        headers = {"Authorization": f"Bearer {INTASEND_SEC_KEY}", "Content-Type": "application/json"}
        try:
            res = requests.post(url, json={"invoice_id": tracking_id}, headers=headers).json()
            if res.get('invoice', {}).get('state') == 'COMPLETE':
                st.session_state.is_pro = True
                st.toast("🎉 Payment Verified! Welcome to Pro.")
        except:
            st.error("Verification connection failed.")

if not st.session_state.is_pro:
    verify_payment()

# =========================================================
# 📝 CONTENT: SAMPLES & EDUCATION
# =========================================================
def show_landing_content():
    # 1. HERO SECTION
    st.markdown("""
    <div class="hero-box">
        <div class="hero-title">CareerFlow AI Architect</div>
        <div class="hero-sub">Stop getting rejected by robots. Build ATS-optimized, executive-grade resumes and cover letters in seconds.</div>
    </div>
    """, unsafe_allow_html=True)

    # 2. WHY IT MATTERS (3 Columns)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""
        <div class="value-card">
            <span class="icon-header">🤖</span>
            <div class="card-title">Beat the ATS Algorithm</div>
            <p>75% of resumes are deleted by software before a human sees them. Our AI injects the exact keywords and formatting required to pass the screen.</p>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown("""
        <div class="value-card">
            <span class="icon-header">✍️</span>
            <div class="card-title">Persuasive Cover Letters</div>
            <p>Don't just summarize your CV. We generate narrative-driven letters that connect your past achievements to the company's future goals.</p>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown("""
        <div class="value-card">
            <span class="icon-header">✨</span>
            <div class="card-title">Executive Formatting</div>
            <p>Clean, modern, and readable. Whether you are in Tech, Finance, or Healthcare, we provide the standard that hiring managers expect.</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br><hr><br>", unsafe_allow_html=True)

    # 3. LIVE SAMPLES (The user asked for this)
    st.subheader("👁️ See What You Get")
    st.markdown("Unlike other tools, we don't hide our quality. Here are **real examples** of what CareerFlow generates.")
    
    tab_res, tab_cov = st.tabs(["📄 Resume Sample (Tech)", "✉️ Cover Letter Sample"])
    
    with tab_res:
        st.markdown("""
        <div class="paper-preview">
            <div class="paper-header">
                <div class="paper-h1">ALEX J. MERCER</div>
                <div class="paper-sub">San Francisco, CA | alex.mercer@email.com | (555) 123-4567</div>
            </div>
            <p><strong>PROFESSIONAL SUMMARY</strong><br>
            Results-oriented Senior Project Manager with 7+ years of experience leading cross-functional teams in the Fintech sector. Proven track record of reducing deployment cycles by 40% and managing budgets up to $2M. Expert in Agile methodologies and stakeholder management.</p>
            
            <p><strong>EXPERIENCE</strong></p>
            <p><strong>Global Tech Solutions</strong> | <em>Senior Product Manager</em> | 2019 – Present</p>
            <ul>
                <li>Spearheaded the launch of "PayFlow 2.0", resulting in a <strong>25% increase in user retention</strong> within Q1.</li>
                <li>Optimized internal workflows using JIRA automation, saving the engineering team 15 hours per week.</li>
                <li>Mentored 4 junior PMs, facilitating their promotion to mid-level roles within 18 months.</li>
            </ul>
            <p><strong>Innovate Corp</strong> | <em>Product Analyst</em> | 2016 – 2019</p>
            <ul>
                <li>Analyzed user data using SQL and Python to identify bottlenecks in the onboarding process.</li>
                <li>Collaborated with UX designers to redesign the mobile interface, boosting conversion rates by 12%.</li>
            </ul>
            
            <p><strong>SKILLS</strong></p>
            <p>Agile/Scrum, Python, SQL, Tableau, Stakeholder Management, Strategic Planning.</p>
        </div>
        """, unsafe_allow_html=True)
        
    with tab_cov:
        st.markdown("""
        <div class="paper-preview">
            <p><strong>Date:</strong> October 24, 2024<br>
            <strong>To:</strong> Hiring Manager, Stripe<br>
            <strong>Re:</strong> Application for Senior Product Manager</p>
            <br>
            <p>Dear Hiring Team,</p>
            <p>When I saw that Stripe was looking for a Senior Product Manager to lead the Global Payments expansion, I knew I had to apply. Having spent the last seven years optimizing fintech payment gateways at Global Tech Solutions, I have developed not just the technical expertise to manage complex APIs, but the strategic vision to scale them across new markets.</p>
            <p>In my current role, I faced a challenge similar to what Stripe is tackling in Southeast Asia: high transaction failure rates due to local banking fragmentation. By leading a cross-functional team of 15 engineers, I implemented a dynamic routing algorithm that reduced failure rates by 40% and recovered $2M in annual revenue. I am eager to bring this same data-driven, problem-solving approach to your team.</p>
            <p>Beyond the metrics, I am passionate about user experience. I believe that payment infrastructure should be invisible to the user, and I admire Stripe’s commitment to that seamlessness. I would welcome the opportunity to discuss how my background in Agile leadership and API product management can help Stripe achieve its Q4 expansion goals.</p>
            <p>Sincerely,</p>
            <p>Alex J. Mercer</p>
        </div>
        """, unsafe_allow_html=True)

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
        # --- PAYWALL VIEW ---
        st.warning("🔒 Free Trial Limit Reached")
        col_pay1, col_pay2 = st.columns(2)
        with col_pay1:
            st.markdown("""
            ### 🚀 Unlock Pro Access
            **Price:** KES 150 / $1.20 (24 Hour Pass)
            
            **What you get:**
            * ✅ Unlimited AI Generations
            * ✅ Advanced ATS Optimization
            * ✅ Cover Letter & Resume Modes
            * ✅ Instant Download
            """)
        with col_pay2:
            st.markdown("<br>", unsafe_allow_html=True)
            st.link_button("👉 Pay Securely with M-Pesa / Card", PAYMENT_LINK_URL, type="primary", use_container_width=True)
            st.caption("Auto-redirects back here after payment.")
        return

    # --- BUILDER FORM ---
    with st.form("builder_form"):
        col_meta1, col_meta2 = st.columns(2)
        with col_meta1:
            doc_type = st.selectbox("Document Type", ["Resume (ATS Optimized)", "Cover Letter (Persuasive)"])
        with col_meta2:
            industry = st.selectbox("Target Industry", ["Corporate / General", "Tech / Software", "Medical / Healthcare", "Creative / Design"])

        job_desc = st.text_area("1. Paste the Job Description (Required)", height=150, placeholder="Paste the full job advert here. The AI needs this to extract keywords...")
        user_cv = st.text_area("2. Paste Your Experience / Old CV", height=150, placeholder="Paste your work history, skills, and education here...")
        
        submitted = st.form_submit_button("✨ Generate Document", type="primary", use_container_width=True)

    if submitted:
        if not job_desc or not user_cv:
            st.error("⚠️ Please fill in both the Job Description and your Experience.")
        else:
            if not GROQ_KEY:
                st.error("System Error: AI Key missing.")
            else:
                with st.spinner("🤖 Analyzing keywords & drafting content..."):
                    # SIMULATE AI CALL (Replace with real call below)
                    try:
                        client = Groq(api_key=GROQ_KEY)
                        prompt = f"Write a {doc_type} for {industry}. Job: {job_desc}. My Info: {user_cv}. Professional tone."
                        response = client.chat.completions.create(messages=[{"role":"user","content":prompt}],model="llama-3.3-70b-versatile")
                        result_text = response.choices[0].message.content
                        
                        st.session_state.generated_resume = result_text
                        if not st.session_state.is_pro:
                            st.session_state.free_uses += 1
                        st.rerun()
                    except Exception as e:
                        st.error(f"AI Error: {e}")

    # RESULT DISPLAY
    if st.session_state.generated_resume:
        st.divider()
        st.subheader("🎉 Your Draft is Ready")
        
        # EDITABLE AREA
        final_text = st.text_area("Editor", st.session_state.generated_resume, height=500)
        
        # WORD DOC GENERATOR
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
        
        st.download_button("📥 Download Word Doc", data=buffer, file_name="CareerFlow_Draft.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document", type="primary")

# =========================================================
# 🚀 APP ORCHESTRATION
# =========================================================

# 1. SHOW MARKETING CONTENT (If no generation yet)
if not st.session_state.generated_resume and st.session_state.free_uses == 0:
    show_landing_content()
    st.markdown("<h2 style='text-align:center'>👇 Start Building Now</h2>", unsafe_allow_html=True)

# 2. SHOW APP
show_app()
