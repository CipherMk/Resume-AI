import streamlit as st
import dateutil.parser
from datetime import datetime

# --- PAGE CONFIG ---
st.set_page_config(page_title="AI Resume Pro", page_icon="🌍", layout="wide")

# --- IMPORT MODULES (With Error Check) ---
try:
    import auth_db
    import payment_logic
    import ai_generator
except ImportError as e:
    st.error(f"❌ CRITICAL: Missing module files. Ensure auth_db.py, payment_logic.py, and ai_generator.py exist. {e}")
    st.stop()

# --- SESSION STATE ---
if 'user_data' not in st.session_state: st.session_state.user_data = None
if 'generated_resume' not in st.session_state: st.session_state.generated_resume = None

# =========================================================
# 🎮 MAIN CONTROLLER
# =========================================================
def main():
    user = st.session_state.user_data

    # 1. SHOW PAYMENT SCREEN IF NOT LOGGED IN
    if not user:
        payment_logic.render_payment_screen()
        return

    # 2. CHECK EXPIRY (If logged in)
    if user['plan_type'] != "DEMO":
        try:
            expiry = dateutil.parser.isoparse(user['expiry_date'])
            # Localize datetime to handle timezone issues
            if user['expiry_date'].endswith('Z'):
                now = datetime.utcnow().replace(tzinfo=expiry.tzinfo)
            else:
                now = datetime.now()

            if now.replace(tzinfo=None) > expiry.replace(tzinfo=None):
                st.error("⏳ Plan Expired. Please Renew.")
                if st.button("Back to Payment"):
                    st.session_state.user_data = None
                    st.rerun()
                return
        except Exception as e:
            # If date parsing fails, ignore safely or log
            pass

    # 3. SHOW MAIN APP
    st.title("🚀 AI Resume Builder")
    
    # SETUP
    st.subheader("1. Setup")
    c1, c2, c3 = st.columns(3)
    cv_cat = c1.selectbox("Role", ["Corporate", "Tech", "NGO", "Medical", "Sales"])
    cv_reg = c2.selectbox("Region", ["Kenya/UK", "USA", "Europass", "Canada"])
    cv_sty = c3.selectbox("Style", ["Modern", "Classic", "Creative"])

    # SIDEBAR
    with st.sidebar:
        st.info(f"User: {user.get('email')}")
        st.metric("Credits", user.get('credits', 0))
        if st.button("Logout"):
            st.session_state.user_data = None
            st.rerun()

    # INPUTS
    st.header("2. Details")
    c_left, c_right = st.columns(2)
    job_desc = c_left.text_area("Job Description", height=200)
    user_info = c_right.text_area("Your History", height=200)

    # GENERATE
    if st.button("🚀 Generate Resume", type="primary"):
        fresh_user = auth_db.login_user(user['email'])
        creds = fresh_user['credits'] if fresh_user else user.get('credits', 0)

        if creds < 1 and user['plan_type'] != "DEMO":
            st.error("🚫 No credits left.")
        elif not user_info:
            st.warning("Enter your history.")
        else:
            with st.spinner("AI Working..."):
                # CALL FILE 3 (AI)
                res = ai_generator.generate_resume_text(cv_cat, cv_reg, cv_sty, user_info, job_desc)
                st.session_state.generated_resume = res
                
                # DEDUCT CREDIT (FILE 1)
                if user['plan_type'] != "DEMO":
                    new_creds = auth_db.deduct_credit(user['email'], creds)
                    st.session_state.user_data['credits'] = new_creds
                st.rerun()

    # DOWNLOAD
    if st.session_state.generated_resume:
        st.divider()
        st.subheader("3. Result")
        st.text_area("Editor", st.session_state.generated_resume, height=500)
        
        docx = ai_generator.create_docx(st.session_state.generated_resume)
        if docx:
            st.download_button("📥 Download DOCX", docx, "CV.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

if __name__ == "__main__":
    main()