import streamlit as st
import requests
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from bs4 import BeautifulSoup
import google.generativeai as genai

# --- 1. CONFIGURATION & BRANDING ---
st.set_page_config(page_title="AlationDoc Communicator", page_icon="📑", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 5px; background-color: #1E293B; color: white; }
    .stTextArea>div>div>textarea { font-family: 'Inter', sans-serif; font-size: 14px; }
    .release-card { padding: 20px; border: 1px solid #e1e4e8; border-radius: 8px; background-color: white; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. THE INTELLIGENCE ENGINE ---
class AlationIntelligence:
    def __init__(self, api_key):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        # Point this to your published Sphinx llms.txt
        self.llms_txt_url = "https://www.alation.com/docs/en/latest/llms.txt"

    def get_published_context(self):
        try:
            res = requests.get(self.llms_txt_url, timeout=5)
            return res.text if res.status_code == 200 else "Standard Alation Brand Context"
        except:
            return "General Alation Product Context"

    def draft_slack_reply(self, question, context):
        prompt = f"Using this context: {context}\n\nDraft a polite Slack reply for this question: {question}"
        return self.model.generate_content(prompt).text

    def draft_release_summary(self, tech_notes, context):
        prompt = f"""
        Context: {context}
        Technical Notes: {tech_notes}
        
        Task: Create a 'Stakeholder Release Summary' for Customer Success and Sales.
        Format: HTML. 
        Focus on: Business value, 'Why this matters', and links to official docs.
        Tone: Professional, Alation-branded.
        """
        return self.model.generate_content(prompt).text

# --- 3. COMMUNICATIONS (SLACK & GMAIL) ---
def send_release_email(to_email, subject, body_html, sender_email, app_password):
    msg = MIMEMultipart()
    msg['From'] = f"AlationDoc Updates <{sender_email}>"
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body_html, 'html'))
    
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, app_password)
            server.send_message(msg)
        return True
    except Exception as e:
        st.error(f"Email Error: {e}")
        return False

def post_slack_reply(token, channel, thread_ts, text):
    url = "https://slack.com/api/chat.postMessage"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"channel": channel, "thread_ts": thread_ts, "text": text}
    res = requests.post(url, json=payload, headers=headers).json()
    return res.get("ok")

# --- 4. MAIN UI DASHBOARD ---
def main():
    st.title("📑 AlationDoc Communicator")
    
    # Secrets Check
    try:
        creds = st.secrets
        intel = AlationIntelligence(creds["GEMINI_API_KEY"])
    except:
        st.error("Please set GEMINI_API_KEY in Streamlit Secrets.")
        st.stop()

    tab1, tab2 = st.tabs(["🧵 Slack Response Assistant", "✉️ Release Summary Dispatcher"])

    # --- TAB 1: SLACK TRIAGE ---
    with tab1:
        st.subheader("Internal #Alation-doc Rotation")
        if st.button("📥 Pull Latest Slack Messages"):
            # Logic to fetch from Slack API
            st.session_state.messages = [{"ts": "123", "text": "How do I set up OIDC?", "user": "U1"}] # Example
        
        if "messages" in st.session_state:
            for m in st.session_state.messages:
                with st.expander(f"Question: {m['text']}"):
                    if st.button("🧠 Draft AI Reply", key=f"d_{m['ts']}"):
                        ctx = intel.get_published_context()
                        st.session_state[f"rep_{m['ts']}"] = intel.draft_slack_reply(m['text'], ctx)
                    
                    if f"rep_{m['ts']}" in st.session_state:
                        final_msg = st.text_area("Final Reply:", value=st.session_state[f"rep_{m['ts']}"], key=f"t_{m['ts']}")
                        if st.button("🚀 Post to Slack Thread", key=f"p_{m['ts']}"):
                            if post_slack_reply(creds["SLACK_USER_TOKEN"], creds["DOC_CHANNEL_ID"], m['ts'], final_msg):
                                st.success("Replied!")

    # --- TAB 2: RELEASE SUMMARY ---
    with tab2:
        st.subheader("Multi-Channel Release Dispatcher")
        raw_tech_notes = st.text_area("Paste Technical GitHub PR Notes / RST Content...", height=200)
        
        if st.button("✨ Generate Stakeholder Summary"):
            with st.spinner("Translating technical notes to business value..."):
                ctx = intel.get_published_context()
                st.session_state.summary_html = intel.draft_release_summary(raw_tech_notes, ctx)
        
        if "summary_html" in st.session_state:
            st.markdown("### Preview: Stakeholder Email")
            st.divider()
            st.markdown(st.session_state.summary_html, unsafe_allow_html=True)
            st.divider()
            
            # Email Dispatch Section
            st.subheader("📧 Dispatch to Stakeholders")
            target_email = st.text_input("Recipient(s)", "cs-team@alation.com, sales-enablement@alation.com")
            email_subject = st.text_input("Email Subject", "Product Spotlight: Latest Alation Updates")
            
            if st.button("🚀 Send Release Email"):
                success = send_release_email(
                    target_email, 
                    email_subject, 
                    st.session_state.summary_html, 
                    creds["MY_EMAIL"], 
                    creds["GMAIL_APP_PWD"]
                )
                if success:
                    st.balloons()
                    st.success(f"Release summary dispatched to {target_email}!")

if __name__ == "__main__":
    main()
