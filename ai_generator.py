import streamlit as st
from groq import Groq
from docx import Document
from docx.shared import Pt
import io

# --- CONFIG CHECK ---
GROQ_API_KEY = st.secrets.get("groq", {}).get("api_key") or st.secrets.get("GROQ_API_KEY")

if not GROQ_API_KEY:
    st.error("❌ CRITICAL ERROR: Groq API Key missing.")
    st.stop()

def generate_resume_text(cat, region, style, user_info, job_desc):
    """Calls the Groq API"""
    if cat == "DEMO": return "This is demo content."
    
    prompt = f"""
    Act as a professional Resume Writer.
    Write a {region} style resume for a {cat} role. Visual Style: {style}.
    
    USER EXPERIENCE: {user_info}
    JOB DESCRIPTION: {job_desc}
    
    Return ONLY the resume text. No conversational filler.
    """
    
    try:
        client = Groq(api_key=GROQ_API_KEY)
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile"
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"AI Generation Failed: {e}"

def create_docx(text):
    """Converts text to downloadable DOCX"""
    try:
        doc = Document()
        style = doc.styles['Normal']
        font = style.font
        font.name = 'Calibri'
        font.size = Pt(11)
        
        for line in text.split('\n'):
            doc.add_paragraph(line)
            
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer
    except Exception as e:
        st.error(f"Document Creation Failed: {e}")
        return None