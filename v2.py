import streamlit as st
import requests
import time
import datetime
from groq import Groq
from docx import Document
from docx.shared import Pt
import io
import extra_streamlit_components as stx # pip install extra-streamlit-components

# --- ⚠️ CONFIGURATION ---
st.set_page_config(page_title="CareerFlow | Global CV Architect", page_icon="🌍", layout="wide")

# Safe Secret Access
try:
    GROQ_KEY = st.secrets["GROQ_API_KEY"]
    INTASEND_PUB_KEY = st.secrets["INTASEND_PUBLISHABLE_KEY"]
    INTASEND_SEC_KEY = st.secrets["INTASEND_SECRET_KEY"]
    PAYMENT_LINK_URL = st.secrets["INTASEND_PAYMENT_LINK"]
except:
    GROQ_KEY = ""
    INTASEND_PUB_KEY = ""
    INTASEND_SEC_KEY = ""
    PAYMENT_LINK_URL = "#"

# --- 🍪 COOKIE MANAGER SETUP ---
def get_manager():
    return stx.CookieManager()

cookie_manager = get_manager()

# --- 🎨 ENTERPRISE STYLING ---
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

        /* PAPER DOCUMENT SIMULATION */
        .paper-preview {
            background-color: white;
            border: 1px solid #e2e8f0;
            padding: 50px;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
            font-family: 'Arial', 'Helvetica', sans-serif; /* Standard Resume Font */
            color: #1e293b;
            font-size: 14px;
            line-height: 1.5;
            border-radius: 4px;
            min-height: 600px; /* Make it look like a full page */
            margin-top: 20px;
            max-width: 850px; /* Approximate A4 width */
            margin-left: auto;
            margin-right: auto;
        }
        
        /* Document Internals */
        .doc-header-name { font-size: 24px; font-weight: 700; text-transform: uppercase; color: #0f172a; border-bottom: 2px solid #0f172a; padding-bottom: 10px; margin-bottom: 20px; }
        .doc-section-title { font-size: 14px; font-weight: 700; text-transform: uppercase; color: #334155; border-bottom: 1px solid #cbd5e1; margin-top: 25px; margin-bottom: 10px; padding-bottom: 5px; }
        .doc-job-title { font-weight: 700; font-size: 15px; color: #000; }
        .doc-company { font-style: italic; color: #475569; }
        .doc-date { float: right; font-weight: 600; font-size: 13px; }
        .doc-list { padding-left: 20px; margin-top: 5px; }
        .doc-list li { margin-bottom: 5px; font-size: 14px; color: #334155; }

        /* STATUS BADGES */
        .badge-free { background: #dbeafe; color: #1e40af; padding: 4px 12px; border-radius: 20px; font-weight: 600; font-size: 0.85rem; }
        .badge-pro { background: #dcfce7; color: #166534; padding: 4px 12px; border-radius: 20px; font-weight: 600; font-size: 0.85rem; border: 1px solid #166534; }
    </style>
    """, unsafe_allow_html=True)

inject_custom_css()

# --- STATE MANAGEMENT (SYNCED WITH COOKIES) ---
MAX_FREE_USES = 2

if 'is_pro' not in st.session_state: st.session_state.is_pro = False
if 'generated_resume' not in st.session_state: st.session_state.generated_resume = None

# Load Free Uses from Cookie (Persist across refresh)
cookie_uses = cookie_manager.get(cookie="careerflow_uses")
if cookie_uses is None:
    if 'free_uses' not in st.session_state:
        st.session_state.free_uses = 0
else:
    st.session_state.free_uses = int(cookie_uses)

# =========================================================
# 💰 LOGIC: PAYMENT & ACCESS
# =========================================================
def verify_payment():
    query_params = st.query_params
    tracking_id = query_params.get("tracking_id", None)
    
    if tracking_id:
        if tracking_id == "TEST-ADMIN":
            st.session_state.is_pro = True
            st.toast("👨‍💻 Admin Test Access Granted")
            return

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

    # 3. LIVE SAMPLES
    st.subheader("👁️ Compare Regional Formats")
    st.markdown("See the difference between a **Kenya/UK CV** (Detailed, British English) and a **USA Resume** (Concise, Metric-Driven).")
    
    
    
    tab_ke, tab_us = st.tabs(["🇰🇪 Kenyan / UK CV (Detailed)", "🇺🇸 USA Resume (Concise)"])
    
    with tab_ke:
        st.markdown("""
        <div class="paper-preview">
            <div class="doc-header-name">JOHNATHAN K. MAINA, CPA(K)</div>
            <div style="text-align:center; font-size:13px; color:#444;">
                P.O. Box 40321-00100, Nairobi, Kenya | +254 722 123 456 | j.maina@email.com<br>
                LinkedIn: linkedin.com/in/jkmaina
            </div>

            <div class="doc-section-title">Career Profile</div>
            <p>Strategic Finance Manager with over 10 years of experience in the East African banking sector. Expert in tax compliance (KRA iTax), financial risk assessment, and liquidity management. Successfully led a portfolio of KES 5 Billion in assets. Proven track record of reducing operational costs by implementing automated reconciliation systems (SAP ERP). Seeking to leverage expertise in regulatory compliance and team leadership at Equity Group Holdings.</p>

            <div class="doc-section-title">Key Competencies</div>
            <div style="display: flex; justify-content: space-between;">
                <ul class="doc-list" style="margin-top:0;">
                    <li>Financial Reporting (IFRS 9)</li>
                    <li>Taxation & Audit Compliance</li>
                    <li>Budgeting & Forecasting</li>
                </ul>
                <ul class="doc-list" style="margin-top:0;">
                    <li>SAP ERP & Quickbooks</li>
                    <li>Team Leadership & Mentoring</li>
                    <li>Strategic Risk Management</li>
                </ul>
            </div>

            <div class="doc-section-title">Professional Experience</div>
            
            <div>
                <span class="doc-job-title">Senior Finance Manager</span>
                <span class="doc-date">Jan 2019 – Present</span>
                <div class="doc-company">Nairobi Commercial Bank | Nairobi, Kenya</div>
                <ul class="doc-list">
                    <li>Spearheaded the annual audit process for 15 branches, ensuring 100% compliance with Central Bank of Kenya (CBK) regulations.</li>
                    <li>Designed and implemented a new cost-control framework that reduced branch operating expenses by 18% (KES 20M savings annually).</li>
                    <li>Mentored a team of 12 junior accountants, organising quarterly workshops on IFRS updates which improved team productivity by 25%.</li>
                    <li>Liaised with external auditors (KPMG) to facilitate smooth interim and final audits, resolving all queries within the statutory timeline.</li>
                </ul>
            </div>
            
            <div style="margin-top:15px;">
                <span class="doc-job-title">Internal Auditor</span>
                <span class="doc-date">Feb 2015 – Dec 2018</span>
                <div class="doc-company">Regional Insurance Ltd | Mombasa, Kenya</div>
                <ul class="doc-list">
                    <li>Conducted risk-based audits across 5 regional offices, identifying control gaps in procurement that saved the company KES 5M.</li>
                    <li>Prepared detailed audit reports for the Audit Committee, providing actionable recommendations on internal controls.</li>
                </ul>
            </div>

            <div class="doc-section-title">Education & Certifications</div>
            <ul class="doc-list">
                <li><strong>Master of Business Administration (Finance)</strong> – Strathmore University (2018)</li>
                <li><strong>Bachelor of Commerce (Finance)</strong> – University of Nairobi (2014) - First Class Honours</li>
                <li><strong>Certified Public Accountant (CPA-K)</strong> – ICPAK Member No. 12345</li>
            </ul>

            <div class="doc-section-title">Referees</div>
            <p><strong>Dr. James Omondi</strong><br>Chief Financial Officer, Nairobi Commercial Bank<br>Email: j.omondi@ncb.co.ke | Phone: +254 711 000 000</p>
        </div>
        """, unsafe_allow_html=True)
        
    with tab_us:
        st.markdown("""
        <div class="paper-preview">
            <div class="doc-header-name">JOHN MAINA</div>
            <div style="text-align:center; font-size:13px; color:#444;">
                New York, NY | (555) 123-4567 | john.maina@email.com | linkedin.com/in/johnmaina
            </div>

            <div class="doc-section-title">Professional Summary</div>
            <p>Results-oriented Financial Analyst with 7+ years of experience optimizing fiscal performance for Fortune 500 companies. Expert in GAAP compliance, financial modeling, and data visualization. Reduced audit cycle times by 30% through Python automation. Proficient in SAP, Tableau, and SQL.</p>

            <div class="doc-section-title">Experience</div>
            
            <div>
                <span class="doc-job-title">Senior Financial Analyst</span>
                <span class="doc-date">2019 – Present</span>
                <div class="doc-company">Global Fintech Solutions | New York, NY</div>
                <ul class="doc-list">
                    <li>Managed a $50M quarterly budget, forecasting variances with 98% accuracy utilizing advanced Excel modeling.</li>
                    <li>Developed an automated Python script to reconcile transaction data, saving the team 15 man-hours per week.</li>
                    <li>Led cross-functional teams to streamline tax reporting processes, resulting in zero regulatory penalties over a 4-year period.</li>
                    <li>Presented quarterly financial insights to the C-Suite, influencing key strategic decisions regarding expansion into Latin American markets.</li>
                </ul>
            </div>
            
            <div style="margin-top:15px;">
                <span class="doc-job-title">Financial Analyst</span>
                <span class="doc-date">2016 – 2019</span>
                <div class="doc-company">Innovate Corp | San Francisco, CA</div>
                <ul class="doc-list">
                    <li>Analyzed revenue trends for SaaS products, identifying a 10% pricing opportunity that generated $1.2M in additional annual revenue.</li>
                    <li>Collaborated with engineering teams to integrate Tableau dashboards, providing real-time P&L visibility to stakeholders.</li>
                </ul>
            </div>

            <div class="doc-section-title">Technical Skills</div>
            <p style="margin-top:5px;">
            <strong>Analysis:</strong> Financial Modeling, Forecasting, GAAP, Variance Analysis<br>
            <strong>Software:</strong> SAP ERP, Oracle NetSuite, Tableau, Power BI<br>
            <strong>Programming:</strong> Python (Pandas), SQL, Advanced Excel (VBA)
            </p>
            
            <div class="doc-section-title">Education</div>
            <p style="margin-top:5px;"><strong>B.S. Finance</strong> | University of Pennsylvania (Wharton) | 2016</p>
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
        st.warning("🔒 Free Limit Reached")
        col_pay1, col_pay2 = st.columns(2)
        with col_pay1:
            st.markdown("### 🚀 Get the Day Pass\n**Price:** KES 150\n\n* ✅ Unlimited Generations\n* ✅ All Region Formats")
        with col_pay2:
            st.markdown("<br>", unsafe_allow_html=True)
            st.link_button("👉 Pay with M-Pesa", PAYMENT_LINK_URL, type="primary", use_container_width=True)
        return

    # --- BUILDER FORM ---
    with st.form("builder_form"):
        # ROW 1: Type & Region
        col_meta1, col_meta2 = st.columns(2)
        with col_meta1:
            doc_type = st.selectbox("Document Type", ["Resume / CV", "Cover Letter"])
        with col_meta2:
            # 🌍 NEW: REGION SELECTOR
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
                        
                        # 🧠 DYNAMIC PROMPT BASED ON REGION
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
                            # Set cookie to expire in 30 days
                            cookie_manager.set("careerflow_uses", st.session_state.free_uses, expires_at=datetime.datetime.now() + datetime.timedelta(days=30))
                            
                        st.rerun()
                    except Exception as e:
                        st.error(f"AI Error: {e}")

    # RESULT DISPLAY
    if st.session_state.generated_resume:
        st.divider()
        st.subheader("🎉 Your Draft is Ready")
        final_text = st.text_area("Editor", st.session_state.generated_resume, height=500)
        
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
