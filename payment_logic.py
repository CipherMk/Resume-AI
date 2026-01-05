import streamlit as st
import time
import auth_db  # Importing File 1

# --- LOAD LINKS ---
LINK_SINGLE = st.secrets.get("LINK_SINGLE", "#")
LINK_MONTHLY = st.secrets.get("LINK_MONTHLY", "#")
PAYPAL_ME_LINK = st.secrets.get("PAYPAL_ME_LINK", "#")

def render_payment_screen():
    st.markdown("<h1 style='text-align: center;'>🌍 Global AI Resume Builder</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center;'>Select a plan to start.</p>", unsafe_allow_html=True)

    # --- LOGIN BLOCK ---
    with st.expander("🔑 Already have an account? Login here"):
        c1, c2 = st.columns([3, 1])
        login_email = c1.text_input("Enter Email:")
        if c2.button("Login"):
            user = auth_db.login_user(login_email)
            if user:
                st.session_state.user_data = user
                st.success("Welcome back!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("User not found.")

    st.divider()

    # --- PRICING CARDS ---
    c1, c2, c3 = st.columns(3)
    
    # 1. DEMO
    with c1:
        st.info("👶 **Free Demo**")
        if st.button("Enter Demo Mode", use_container_width=True):
            st.session_state.user_data = {"email": "guest", "plan_type": "DEMO", "credits": 0}
            st.rerun()

    # 2. SINGLE
    with c2:
        st.warning("⚡ **Single Pass (KES 50)**")
        if st.button("Select Single", use_container_width=True):
            st.session_state.selected_plan = "Single"

    # 3. MONTHLY
    with c3:
        st.success("🏆 **Monthly Trial**")
        if st.button("Start Free Trial", use_container_width=True):
            st.session_state.selected_plan = "Monthly"

    st.divider()

    # --- PAYMENT PROCESSING ---
    if st.session_state.get("selected_plan") == "Single":
        st.subheader("Verify Payment")
        st.markdown(f"[Pay KES 50 via M-Pesa]({LINK_SINGLE})")
        
        email = st.text_input("Your Email:")
        code = st.text_input("Transaction Code:")
        
        if st.button("Activate Pass"):
            if len(code) > 5 and "@" in email:
                # CALL FILE 1 TO REGISTER
                if auth_db.register_user_in_db(email, "SINGLE", 3, 1):
                    st.session_state.user_data = auth_db.login_user(email)
                    st.balloons()
                    st.rerun()
            else:
                st.error("Invalid details.")

    elif st.session_state.get("selected_plan") == "Monthly":
        st.subheader("Start 3-Day Free Trial")
        with st.form("trial"):
            email = st.text_input("Email:")
            phone = st.text_input("Phone:")
            if st.form_submit_button("Start Trial"):
                if "@" in email and len(phone) > 5:
                    # CALL FILE 1 TO REGISTER
                    if auth_db.register_user_in_db(email, "TRIAL_MONTHLY", 9999, 3):
                        st.session_state.user_data = auth_db.login_user(email)
                        st.balloons()
                        st.rerun()
                else:
                    st.error("Invalid details.")