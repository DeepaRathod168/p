import streamlit as st
import datetime
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import os

st.set_page_config(
    page_title="ResearchAI — Multi Agent System",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── CSS ──────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Syne:wght@700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'JetBrains Mono', monospace;
    background-color: #07090F;
    color: #E2E8F0;
}
#MainMenu, footer, header { visibility: hidden; }
.stApp { background: #07090F; }
[data-testid="stSidebar"] {
    background: #0D1117 !important;
    border-right: 1px solid #1E293B !important;
}
.main-title {
    font-family: 'Syne', sans-serif;
    font-size: 2.8rem;
    font-weight: 800;
    background: linear-gradient(135deg, #00FFB2, #38BDF8, #A78BFA);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    line-height: 1.1;
    margin-bottom: 0.2rem;
}
.sub-title {
    color: #475569;
    font-size: 0.85rem;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    margin-bottom: 2rem;
}
.stTextInput > div > div > input {
    background: #0D1117 !important;
    border: 1px solid #1E293B !important;
    border-radius: 12px !important;
    color: #E2E8F0 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 1rem !important;
    padding: 1rem 1.2rem !important;
}
.stTextInput > div > div > input:focus {
    border: 1px solid #00FFB2 !important;
    box-shadow: 0 0 0 3px #00FFB220 !important;
}
.stButton > button {
    background: linear-gradient(135deg, #00FFB2, #38BDF8) !important;
    color: #07090F !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 0.75rem 2rem !important;
    width: 100% !important;
}
.agent-card {
    background: #0D1117;
    border: 1px solid #1E293B;
    border-radius: 12px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.75rem;
}
.agent-name { font-weight: 700; font-size: 0.95rem; color: #F8FAFC; }
.agent-desc { color: #475569; font-size: 0.78rem; margin-top: 0.2rem; }
.metric-row { display: flex; gap: 1rem; margin-bottom: 1.5rem; }
.metric-card {
    flex: 1;
    background: #0D1117;
    border: 1px solid #1E293B;
    border-radius: 12px;
    padding: 1rem;
    text-align: center;
}
.metric-value { font-size: 1.5rem; font-weight: 800; color: #00FFB2; }
.metric-label {
    font-size: 0.72rem; color: #475569;
    margin-top: 0.2rem; text-transform: uppercase; letter-spacing: 0.1em;
}
.report-box {
    background: #0D1117;
    border: 1px solid #1E293B;
    border-radius: 16px;
    padding: 2rem;
    margin-top: 1.5rem;
}
.stat-badge {
    display: inline-block;
    background: #1E293B;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 0.4rem 0.9rem;
    font-size: 0.78rem;
    color: #94A3B8;
    margin: 0.2rem;
}
.step-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: #00FFB2;
    flex-shrink: 0;
    animation: pulse 1.5s infinite;
    display: inline-block;
    margin-right: 10px;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
}
hr { border-color: #1E293B !important; margin: 1.5rem 0 !important; }
.stDownloadButton > button {
    background: #1E293B !important;
    color: #94A3B8 !important;
    border: 1px solid #334155 !important;
    border-radius: 10px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.85rem !important;
    width: 100% !important;
}
.stDownloadButton > button:hover {
    border-color: #00FFB2 !important;
    color: #00FFB2 !important;
}
.stSelectbox > div > div {
    background: #0D1117 !important;
    border: 1px solid #1E293B !important;
    border-radius: 10px !important;
    color: #E2E8F0 !important;
}
.stTextArea textarea {
    background: #0D1117 !important;
    border: 1px solid #1E293B !important;
    border-radius: 12px !important;
    color: #E2E8F0 !important;
    font-family: 'JetBrains Mono', monospace !important;
}
</style>
""", unsafe_allow_html=True)


# ── Helper Functions ──────────────────────────────────────

def count_words(text):
    return len(re.findall(r'\w+', text))

def reading_time(text):
    return max(1, round(count_words(text) / 200))

HISTORY_FILE = "research_history.json"

def save_history(history):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.warning(f"Could not save history: {e}")

def load_history():
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return []

def send_email(to_email, topic, report, smtp_user, smtp_pass):
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"ResearchAI Report: {topic}"
        msg["From"]    = smtp_user
        msg["To"]      = to_email
        now = datetime.datetime.now().strftime("%d %b %Y, %H:%M")
        body = f"""ResearchAI — Research Report
{'='*50}
Topic     : {topic}
Generated : {now}
{'='*50}

{report}

{'='*50}
Sent by ResearchAI Multi-Agent System
"""
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, to_email, msg.as_string())
        return True
    except Exception as e:
        return str(e)

def get_ai_topic_suggestions(seed):
    if not seed.strip():
        return []
    return [
        f"Latest breakthroughs in {seed}",
        f"Future of {seed} in 2026",
        f"How {seed} is changing industries",
        f"Key challenges in {seed} today",
        f"Investment opportunities in {seed}",
    ]

def generate_pdf_text(topic, result, wc, rt):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"""RESEARCHAI — RESEARCH REPORT
{"="*50}
Topic     : {topic}
Generated : {now}
Words     : {wc}
Read Time : {rt} min
{"="*50}

{result}

{"="*50}
Generated by ResearchAI Multi-Agent System
"""

def get_topics_for_category(category):
    return {
        "Technology": [
            "AI agents transforming software 2026",
            "Quantum computing future",
            "Cybersecurity threats 2026",
            "Blockchain beyond crypto",
        ],
        "Health": [
            "AI in drug discovery 2026",
            "Mental health tech trends",
            "Longevity research breakthroughs",
            "Wearable health monitors",
        ],
        "Business": [
            "Remote work trends 2026",
            "Impact of AI on jobs",
            "Green energy investment",
            "Startup funding landscape 2026",
        ],
        "Science": [
            "Space exploration missions 2026",
            "Climate change solutions",
            "Gene editing CRISPR advances",
            "Ocean exploration technology",
        ],
    }.get(category, [])

def safe_filename(text, length=20):
    return re.sub(r'[^a-zA-Z0-9_]', '_', text[:length])

def escape_for_js(text):
    return (text
        .replace("\\", "\\\\")
        .replace("`", "'")
        .replace("\n", "\\n")
        .replace("\r", "")
    )


# ── Session State Init ────────────────────────────────────

for key, default in {
    "history": load_history(),
    "selected_topic": "",
    "current_result": None,
    "current_topic": None,
    "light_mode": False,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

st.session_state.total_reports = len(st.session_state.history)


# ── Light Mode CSS ────────────────────────────────────────

if st.session_state.light_mode:
    st.markdown("""
    <style>
    .stApp { background: #F1F5F9 !important; color: #0F172A !important; }
    [data-testid="stSidebar"] { background: #E2E8F0 !important; border-right: 1px solid #CBD5E1 !important; }
    .agent-card  { background: #FFFFFF !important; border-color: #CBD5E1 !important; }
    .metric-card { background: #FFFFFF !important; border-color: #CBD5E1 !important; }
    .report-box  { background: #FFFFFF !important; border-color: #CBD5E1 !important; }
    .stat-badge  { background: #E2E8F0 !important; border-color: #CBD5E1 !important; color: #475569 !important; }
    .agent-name  { color: #0F172A !important; }
    .metric-value { color: #059669 !important; }
    .main-title {
        background: linear-gradient(135deg, #059669, #0284C7, #7C3AED) !important;
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
    }
    .stTextInput > div > div > input {
        background: #FFFFFF !important;
        border-color: #CBD5E1 !important;
        color: #0F172A !important;
    }
    .stSelectbox > div > div {
        background: #FFFFFF !important;
        border-color: #CBD5E1 !important;
        color: #0F172A !important;
    }
    </style>
    """, unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div style='padding:0.5rem 0 1rem 0;'>
        <div style='font-family:Syne,sans-serif;font-size:1.4rem;font-weight:800;
            background:linear-gradient(135deg,#00FFB2,#38BDF8);
            -webkit-background-clip:text;-webkit-text-fill-color:transparent;'>
            ResearchAI
        </div>
        <div style='color:#475569;font-size:0.72rem;margin-top:0.2rem;'>
            Multi-Agent System v2.0
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Theme toggle
    st.markdown("**🌓 Theme**")
    light = st.toggle("Light Mode", value=st.session_state.light_mode)
    if light != st.session_state.light_mode:
        st.session_state.light_mode = light
        st.rerun()

    st.markdown("---")

    # Agents
    st.markdown("**🤖 Active Agents**")
    for icon, name, desc, color in [
        ("🔍", "Researcher",   "Searches the web for facts",  "#00FFB2"),
        ("✅", "Fact Checker", "Verifies every claim",         "#38BDF8"),
        ("📊", "Analyst",      "Extracts key insights",        "#A78BFA"),
        ("✍️", "Writer",       "Drafts the final report",      "#F472B6"),
    ]:
        st.markdown(f"""
        <div class='agent-card' style='border-left:3px solid {color};'>
            <div class='agent-name'>{icon} {name}</div>
            <div class='agent-desc'>{desc}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Report settings
    st.markdown("**⚙️ Report Settings**")
    report_format = st.selectbox(
        "Format",
        ["Detailed Report", "Executive Summary", "Bullet Points Only"],
        label_visibility="collapsed"
    )

    st.markdown("**📂 Topic Category**")
    category = st.selectbox(
        "Category",
        ["Technology", "Health", "Business", "Science"],
        label_visibility="collapsed"
    )

    st.markdown("---")

    # Email configuration
    st.markdown("**📧 Email Report**")
    with st.expander("Configure Email Settings"):
        smtp_user = st.text_input("Your Gmail Address", placeholder="you@gmail.com")
        smtp_pass = st.text_input("Gmail App Password", placeholder="xxxx xxxx xxxx xxxx", type="password")
        to_email  = st.text_input("Send Report To", placeholder="recipient@email.com")
        st.caption("⚠️ Use a Gmail App Password (not your regular password). Get it: Google Account → Security → 2FA → App Passwords")

    st.markdown("---")

    # Session stats
    st.markdown(f"""
    <div style='background:#0D1117;border:1px solid #1E293B;border-radius:10px;padding:0.9rem;margin-bottom:1rem;'>
        <div style='color:#475569;font-size:0.7rem;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:0.4rem;'>
            All-Time Stats
        </div>
        <div style='color:#00FFB2;font-size:1.6rem;font-weight:800;'>{st.session_state.total_reports}</div>
        <div style='color:#475569;font-size:0.72rem;'>Reports generated</div>
    </div>
    """, unsafe_allow_html=True)

    if st.button("🗑️ Clear All History"):
        st.session_state.history = []
        save_history([])
        st.rerun()


# ── Main Layout ───────────────────────────────────────────

col_main, _ = st.columns([3, 1])

with col_main:

    # Header
    st.markdown("<div class='main-title'>Multi-Agent<br>Research System</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub-title'>4 AI Agents · Real-time Web Search · Auto Report Generation</div>", unsafe_allow_html=True)

    # Metrics bar
    st.markdown(f"""
    <div class='metric-row'>
        <div class='metric-card'><div class='metric-value'>4</div><div class='metric-label'>AI Agents</div></div>
        <div class='metric-card'><div class='metric-value'>~3m</div><div class='metric-label'>Avg Time</div></div>
        <div class='metric-card'><div class='metric-value'>5+</div><div class='metric-label'>Sources</div></div>
        <div class='metric-card'><div class='metric-value'>{st.session_state.total_reports}</div><div class='metric-label'>Generated</div></div>
    </div>
    """, unsafe_allow_html=True)

    # ── Category Quick Topics ─────────────────────────────
    suggested = get_topics_for_category(category)
    st.markdown(f"**💡 {category} Quick Topics:**")
    c1, c2 = st.columns(2)
    for i, t in enumerate(suggested):
        with (c1 if i % 2 == 0 else c2):
            if st.button(t, key=f"cat_{i}"):
                st.session_state.selected_topic = t
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # ── AI Topic Suggestions ──────────────────────────────
    st.markdown("**🤖 AI Topic Suggestions**")
    seed = st.text_input(
        "Type a keyword for AI suggestions:",
        placeholder="e.g. robotics, climate, fintech...",
        label_visibility="collapsed",
        key="seed_input"
    )
    if seed.strip():
        ai_sugg = get_ai_topic_suggestions(seed)
        s1, s2 = st.columns(2)
        for i, s in enumerate(ai_sugg):
            with (s1 if i % 2 == 0 else s2):
                if st.button(s, key=f"ai_{i}"):
                    st.session_state.selected_topic = s
                    st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Main Topic Input ──────────────────────────────────
    st.markdown("**🔎 Your Research Topic**")
    topic = st.text_input(
        "topic",
        value=st.session_state.selected_topic,
        placeholder="e.g. How is AI transforming healthcare in 2026?",
        label_visibility="collapsed"
    )
    if topic:
        st.markdown(
            f"<div style='color:#334155;font-size:0.72rem;margin-top:-0.5rem;'>{len(topic)} characters</div>",
            unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)
    run = st.button("🚀 Start Research", type="primary")

    # ── Research Execution ────────────────────────────────
    if run:
        if not topic.strip():
            st.warning("⚠️ Please enter a research topic first.")
        else:
            # Lazy import to avoid errors if crew isn't set up yet
            try:
                from crew import run_research
            except Exception as e:
                st.error(f"Failed to load research crew: {e}")
                st.stop()

            st.markdown("---")
            st.markdown("**🤖 Agent Pipeline Running...**")

            steps_ph = st.empty()
            steps_ph.markdown("""
            <div style='background:#0D1117;border:1px solid #1E293B;border-radius:12px;padding:1.2rem;'>
                <div style='padding:0.4rem 0;color:#64748B;font-size:0.85rem;'>
                    <span class='step-dot'></span>Researcher Agent searching the web...
                </div>
                <div style='padding:0.4rem 0;color:#64748B;font-size:0.85rem;'>
                    <span class='step-dot'></span>Fact Checker verifying every claim...
                </div>
                <div style='padding:0.4rem 0;color:#64748B;font-size:0.85rem;'>
                    <span class='step-dot'></span>Analyst extracting key insights...
                </div>
                <div style='padding:0.4rem 0;color:#64748B;font-size:0.85rem;'>
                    <span class='step-dot'></span>Writer drafting final report...
                </div>
            </div>
            """, unsafe_allow_html=True)

            pb = st.progress(0, text="Initializing agents...")

            try:
                fmt_map = {
                    "Detailed Report":    "Write a comprehensive detailed report with all sections including Executive Summary, Introduction, Key Findings, Analysis and Conclusion.",
                    "Executive Summary":  "Write a concise executive summary under 300 words covering only the most critical points.",
                    "Bullet Points Only": "Return all findings as clean structured bullet points only. No long paragraphs.",
                }
                enhanced_topic = f"{topic.strip()}. Format instruction: {fmt_map[report_format]}"

                pb.progress(10, text="🔍 Researcher searching...")
                pb.progress(30, text="✅ Fact checking...")
                pb.progress(60, text="📊 Analyzing insights...")
                pb.progress(85, text="✍️ Writing report...")

                result = run_research(enhanced_topic)
                result = str(result)

                pb.progress(100, text="✅ Complete!")
                steps_ph.empty()

                wc  = count_words(result)
                rt  = reading_time(result)
                now = datetime.datetime.now().strftime("%d %b %Y, %H:%M")

                # Save to session + disk
                st.session_state.current_result = result
                st.session_state.current_topic  = topic
                entry = {
                    "topic":  topic,
                    "result": result,
                    "format": report_format,
                    "words":  wc,
                    "time":   now,
                }
                st.session_state.history.append(entry)
                save_history(st.session_state.history)

                st.success("✅ Research Complete!")

                # Stats row
                st.markdown(f"""
                <div style='display:flex;gap:0.5rem;margin:0.5rem 0 1rem;flex-wrap:wrap;'>
                    <span class='stat-badge'>📄 {wc} words</span>
                    <span class='stat-badge'>⏱️ {rt} min read</span>
                    <span class='stat-badge'>📅 {now}</span>
                    <span class='stat-badge'>📋 {report_format}</span>
                </div>
                """, unsafe_allow_html=True)

                # ── Copy to Clipboard (FEATURE 1) ─────────
                escaped = escape_for_js(result)
                st.markdown(f"""
                <button id="copyBtn"
                    onclick="navigator.clipboard.writeText(`{escaped}`)
                        .then(() => {{ this.innerText = '✅ Copied!'; setTimeout(() => this.innerText='📋 Copy Report to Clipboard', 2000); }})
                        .catch(() => this.innerText = '❌ Copy failed')"
                    style='background:#1E293B;border:1px solid #334155;border-radius:8px;
                        padding:0.55rem 1.4rem;color:#94A3B8;font-size:0.82rem;
                        cursor:pointer;font-family:JetBrains Mono,monospace;margin-bottom:1rem;
                        transition:all 0.2s;'>
                    Copy Report to Clipboard
                </button>
                """, unsafe_allow_html=True)

                # Report display
                st.markdown("<div class='report-box'>", unsafe_allow_html=True)
                st.markdown(f"### {topic}")
                st.markdown(f"*{report_format} &nbsp;·&nbsp; {wc} words &nbsp;·&nbsp; {rt} min read*")
                st.markdown("---")
                st.markdown(result)
                st.markdown("</div>", unsafe_allow_html=True)

                # ── Downloads (FEATURE 2 — 3 formats) ─────
                st.markdown("<br>**⬇️ Download Report**", unsafe_allow_html=True)
                d1, d2, d3 = st.columns(3)
                fname = safe_filename(topic)
                with d1:
                    st.download_button(
                        "📝 Markdown (.md)",
                        data=result,
                        file_name=f"report_{fname}.md",
                        mime="text/markdown",
                        key="dl_md"
                    )
                with d2:
                    st.download_button(
                        "📄 Plain Text (.txt)",
                        data=result,
                        file_name=f"report_{fname}.txt",
                        mime="text/plain",
                        key="dl_txt"
                    )
                with d3:
                    pdf_content = generate_pdf_text(topic, result, wc, rt)
                    st.download_button(
                        "🖨️ PDF-ready (.txt)",
                        data=pdf_content,
                        file_name=f"report_{fname}_pdf.txt",
                        mime="text/plain",
                        key="dl_pdf"
                    )

                # ── Email Report (FEATURE 3) ───────────────
                st.markdown("<br>**📧 Email This Report**", unsafe_allow_html=True)
                if st.button("📨 Send Report to Email", key="send_email_btn"):
                    if not smtp_user or not smtp_pass or not to_email:
                        st.warning("⚠️ Please fill in your Gmail, App Password, and recipient email in the sidebar first.")
                    elif "@" not in to_email:
                        st.warning("⚠️ Please enter a valid email address.")
                    else:
                        with st.spinner("Sending email..."):
                            email_result = send_email(to_email, topic, result, smtp_user, smtp_pass)
                        if email_result is True:
                            st.success(f"✅ Report sent to {to_email} successfully!")
                        else:
                            st.error(f"❌ Email failed: {email_result}")
                            st.info("💡 Make sure you're using a Gmail App Password, not your regular password.")

            except Exception as e:
                steps_ph.empty()
                pb.empty()
                st.error(f"❌ Error: {str(e)}")
                st.info("💡 Check your API key in the .env file and try again.")

    # ── Compare Reports (FEATURE 4) ───────────────────────
    if len(st.session_state.history) >= 2:
        st.markdown("---")
        with st.expander("📊 Compare Two Reports Side by Side"):
            topics_list = [h["topic"] for h in st.session_state.history]
            ca, cb = st.columns(2)
            with ca:
                pick_a = st.selectbox("Report A", topics_list, key="cmp_a")
            with cb:
                default_b = min(1, len(topics_list) - 1)
                pick_b = st.selectbox("Report B", topics_list, index=default_b, key="cmp_b")

            if st.button("🔍 Compare Now", key="compare_btn"):
                if pick_a == pick_b:
                    st.warning("Please pick two different reports to compare.")
                else:
                    ra = next(h for h in st.session_state.history if h["topic"] == pick_a)
                    rb = next(h for h in st.session_state.history if h["topic"] == pick_b)
                    r1, r2 = st.columns(2)
                    with r1:
                        st.markdown(f"**{pick_a}**")
                        st.markdown(f"""
                        <div style='margin-bottom:0.8rem;'>
                            <span class='stat-badge'>{ra['words']} words</span>
                            <span class='stat-badge'>{ra['format']}</span>
                        </div>
                        """, unsafe_allow_html=True)
                        st.markdown(ra["result"][:2000] + ("..." if len(ra["result"]) > 2000 else ""))
                    with r2:
                        st.markdown(f"**{pick_b}**")
                        st.markdown(f"""
                        <div style='margin-bottom:0.8rem;'>
                            <span class='stat-badge'>{rb['words']} words</span>
                            <span class='stat-badge'>{rb['format']}</span>
                        </div>
                        """, unsafe_allow_html=True)
                        st.markdown(rb["result"][:2000] + ("..." if len(rb["result"]) > 2000 else ""))

    # ── History (FEATURE 5 — saved across sessions) ───────
    if st.session_state.history:
        st.markdown("---")
        count = len(st.session_state.history)
        st.markdown(f"**📚 Research History — {count} report{'s' if count != 1 else ''} (saved across sessions)**")

        for i, item in enumerate(reversed(st.session_state.history)):
            idx = len(st.session_state.history) - 1 - i
            with st.expander(f"🔍 {item['topic']}  ·  {item['time']}"):
                st.markdown(f"""
                <div style='display:flex;gap:0.5rem;margin-bottom:0.8rem;flex-wrap:wrap;'>
                    <span class='stat-badge'>📄 {item['words']} words</span>
                    <span class='stat-badge'>📋 {item['format']}</span>
                    <span class='stat-badge'>📅 {item['time']}</span>
                    <span class='stat-badge'>⏱️ {reading_time(item['result'])} min read</span>
                </div>
                """, unsafe_allow_html=True)
                st.markdown(item["result"])
                hc1, hc2 = st.columns(2)
                with hc1:
                    st.download_button(
                        "⬇️ Download MD",
                        data=item["result"],
                        file_name=f"report_{safe_filename(item['topic'])}.md",
                        mime="text/markdown",
                        key=f"hist_dl_{idx}"
                    )
                with hc2:
                    if st.button("🗑️ Delete", key=f"del_{idx}"):
                        st.session_state.history.pop(idx)
                        save_history(st.session_state.history)
                        st.rerun()