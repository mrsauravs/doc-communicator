import streamlit as st
import requests
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import google.generativeai as genai

# --- 1. CONFIGURATION & STYLING ---
st.set_page_config(page_title="AlationDoc Communicator", page_icon="📑", layout="wide")

st.markdown("""
    <style>
    .stButton>button { border-radius: 5px; height: 3em; background-color: #1E293B; color: white; }
    .status-card { padding: 15px; border-radius: 10px; border: 1px solid #ddd; background-color: #f9f9f9; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. INTELLIGENCE LOGIC ---
class AlationIntel:
    def __init__(self, api_key):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.llms_txt_url = "https://www.alation.com/docs/en/latest/llms.txt"

    def get_published_context(self):
        try:
            res = requests.get(self.llms_txt_url, timeout=5)
            return res.text if res.status_code == 200 else "Standard Alation Brand Context"
        except:
            return "General Alation Product Context"

    def draft_slack_reply(self, question, context):
        prompt = f"Using this official Alation context: {context}\n\nDraft a concise Slack reply to this question: {question}"
        return self.model.generate_content(prompt).text

    def draft_release_summary(self, tech_notes, context):
        prompt = f"Using this context: {context}\n\nTransform these tech notes into a business-value email summary for CS and Sales: {tech_notes}"
        return self.model.generate_content(prompt).text

# --- 3. UI LAYOUT ---
def main():
    st.title("📑 AlationDoc Communicator")
    st.info("The self-service hub for Doc-Rotation and Release Management.")

    # --- SIDEBAR: SELF-SERVICE CREDENTIALS ---
    with st.sidebar:
        st.header("👤 Your Credentials")
        st.caption("These are not stored; they stay in your session.")
        
        user_gemini_key = st.text_input("Gemini API Key", type="password")
        
        st.divider()
        st.subheader("✉️ Gmail SMTP Settings")
        user_email = st.text_input("Your Alation/Gmail Email")
        user_app_pwd = st.text_input("Gmail App Password", type="password", help="Generated in Google Account > Security")
        
        if not user_gemini_key:
            st.warning("Enter your Gemini Key to begin.")
            st.stop()
        
        intel = AlationIntel(user_gemini_key)

    tab1, tab2 = st.tabs(["🧵 Slack Response Assistant", "✉️ Release Summary Dispatcher"])

    # --- TAB 1: SLACK ASSISTANT (Manual Copy-Paste Mode) ---
    with tab1:
        st.header("Internal Doc-Gap Assistant")
        st.write("Since Slack Apps are restricted, use this to draft perfect, brand-accurate replies.")
        
        user_question = st.text_area("Paste the Slack question here:", placeholder="e.g., How do I enable OIDC for Okta?")
        
        if st.button("🧠 Draft Official Response"):
            with st.spinner("Analyzing published docs..."):
                ctx = intel.get_published_context()
                reply = intel.draft_slack_reply(user_question, ctx)
                st.session_state.slack_draft = reply
        
        if "slack_draft" in st.session_state:
            st.success("Draft ready! Copy it to the Slack thread.")
            st.text_area("Reply Content:", value=st.session_state.slack_draft, height=200)
            st.button("📋 Copy to Clipboard (Simulated)")

    # --- TAB 2: RELEASE SUMMARY & EMAIL ---
    with tab2:
        st.header("Release Summary Hub")
        tech_notes = st.text_area("Paste Technical PR/RST Notes:", height=150)
        
        if st.button("✨ Generate Stakeholder Email"):
            with st.spinner("Generating..."):
                ctx = intel.get_published_context()
                st.session_state.email_body = intel.draft_release_summary(tech_notes, ctx)
        
        if "email_body" in st.session_state:
            st.markdown("### Preview")
            st.markdown(f"<div class='status-card'>{st.session_state.email_body}</div>", unsafe_allow_html=True)
            
            st.divider()
            st.subheader("🚀 Dispatch via Your Gmail")
            recipient = st.text_input("To:", "stakeholders@alation.com")
            subject = st.text_input("Subject:", "Product Update: New Features & Documentation")
            
            if st.button("📧 Send Email Now"):
                if not user_email or not user_app_pwd:
                    st.error("Please enter your Email and App Password in the sidebar.")
                else:
                    try:
                        msg = MIMEMultipart()
                        msg['From'] = user_email
                        msg['To'] = recipient
                        msg['Subject'] = subject
                        msg.attach(MIMEText(st.session_state.email_body, 'plain')) # Using plain for reliability
                        
                        with smtplib.SMTP("smtp.gmail.com", 587) as server:
                            server.starttls()
                            server.login(user_email, user_app_pwd)
                            server.send_message(msg)
                        st.balloons()
                        st.success(f"Email sent from {user_email} to {recipient}!")
                    except Exception as e:
                        st.error(f"Failed to send: {e}")

if __name__ == "__main__":
    main()
