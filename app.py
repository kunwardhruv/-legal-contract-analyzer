# ============================================
# APP.PY
# Streamlit UI — Project ka face!
#
# Yahan sab kuch ek jagah aata hai:
# Upload → Process → Show Results → Chat
#
# Streamlit kyu?
# → Python mein hi UI banana — no HTML/CSS/JS
# → File upload, chat, metrics — sab ready made
# → Free deployment on Streamlit Cloud
# → data science/AI projects ke liye industry standard
# ============================================

import streamlit as st
# Streamlit = Python UI framework
# st.button(), st.file_uploader(), st.chat_input() etc.

import tempfile
# tempfile = Temporary files banana
# Kyu? Streamlit uploaded file memory mein hota hai
# PyMuPDF ko actual disk path chahiye
# Solution: Temp file banao → use karo → delete karo

import os
# File system operations
# os.path.exists(), os.unlink() etc.

# Hamare modules import karo
from ingestion import ingest_pdf, extract_text_from_pdf
# ingest_pdf = Poori pipeline: PDF → FAISS
# extract_text_from_pdf = Sirf text extraction

from retrieval import (
    get_contract_summary,      # Contract ka overview
    analyze_contract_risks,    # Clause by clause risk analysis
    chat_with_contract         # Q&A with contract
)


# ============================================
# PAGE CONFIG
# Yeh SABSE PEHLE hona chahiye — koi bhi st. call se pehle!
# ============================================

st.set_page_config(
    page_title="Legal Contract Analyzer",  # Browser tab ka title
    page_icon="⚖️",                        # Browser tab ka icon
    layout="wide",                          # Full width layout
    initial_sidebar_state="collapsed"       # Sidebar band rakho
)


# ============================================
# CUSTOM CSS
# Streamlit ke default styles override karo
# ============================================

st.markdown("""
<style>
    /* Risk level badges ke liye custom styles */
    .risk-high {
        background: #EF444420;
        border: 1px solid #EF4444;
        color: #EF4444;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 14px;
    }
    .risk-medium {
        background: #F59E0B20;
        border: 1px solid #F59E0B;
        color: #F59E0B;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 14px;
    }
    .risk-low {
        background: #10B98120;
        border: 1px solid #10B981;
        color: #10B981;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 14px;
    }
</style>
""", unsafe_allow_html=True)


# ============================================
# SESSION STATE — Streamlit ka Memory System
#
# Problem: Streamlit mein har button click pe
#          POORA script dobara run hota hai!
#          Sab variables reset ho jaate hain!
#
# Solution: st.session_state = Permanent storage
#           Page refresh tak data safe rehta hai
#
# Analogy:
# Normal variable = RAM → power off pe reset
# session_state = SSD → power off pe bhi safe
# ============================================

# PDF process hua kya? (button dikhane/chhupane ke liye)
if "pdf_processed" not in st.session_state:
    st.session_state.pdf_processed = False

# Contract ka overview (summary section ke liye)
if "contract_summary" not in st.session_state:
    st.session_state.contract_summary = None

# Saare clause analyses (risk section ke liye)
if "risk_analyses" not in st.session_state:
    st.session_state.risk_analyses = []

# Chat history (chat section ke liye)
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Raw PDF text (summary generation ke liye)
if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = ""

# FAISS vectorstore — SABSE IMPORTANT!
# ingest_pdf() yahan save karta hai
# analyze_contract_risks() aur chat_with_contract() yahan se lete hain
# Ek hi instance = consistent data = no errors
if "vectorstore" not in st.session_state:
    st.session_state.vectorstore = None


# ============================================
# HELPER FUNCTIONS
# ============================================

def get_risk_emoji(risk_level: str) -> str:
    """
    Risk level string → Emoji convert karo.

    Kyu? Visual indicator — ek nazar mein risk samajh aaye
    RED = HIGH = Danger!
    YELLOW = MEDIUM = Caution
    GREEN = LOW = OK
    WHITE = NEUTRAL = No risk
    """
    emojis = {
        "HIGH": "🔴",
        "MEDIUM": "🟡",
        "LOW": "🟢",
        "NEUTRAL": "⚪"
    }
    return emojis.get(risk_level, "❓")


def process_pdf(uploaded_file):
    """
    Uploaded PDF ko complete process karo.

    Steps:
    1. Temp file banao (Streamlit file → disk path)
    2. Text extract karo
    3. FAISS mein ingest karo → vectorstore save karo
    4. Contract summary lo
    5. Risk analysis karo
    6. Temp file delete karo

    Kyu try/except?
    → Agar koi bhi step fail ho
    → Error clearly dikhao user ko
    → Temp file cleanup karo (memory waste na ho)
    """

    # Temp file kyu?
    # Streamlit ka uploaded_file = BytesIO object (memory mein)
    # PyMuPDF ko actual disk path chahiye: "C:/temp/abc.pdf"
    # Solution: Disk pe temporarily save karo
    with tempfile.NamedTemporaryFile(
        delete=False,    # Hum manually delete karenge
        suffix=".pdf"    # .pdf extension dena zaroori hai
    ) as tmp_file:
        tmp_file.write(uploaded_file.getvalue())  # File content likho
        tmp_path = tmp_file.name                   # Path save karo

    try:
        # Progress bar dikhao — user ko pata chale kya ho raha hai
        progress = st.progress(0, text="PDF padh raha hun...")

        # ── STEP 1: Text extract ──
        pdf_text = extract_text_from_pdf(tmp_path)
        st.session_state.pdf_text = pdf_text
        progress.progress(25, text="PDF padh liya! ✅")

        # ── STEP 2: FAISS mein ingest ──
        progress.progress(40, text="Smart legal chunks bana raha hun...")
        vectorstore = ingest_pdf(tmp_path)

        # CRITICAL: Vectorstore session state mein save karo!
        # Agar yahan save nahi kiya toh:
        # analyze_contract_risks() ko pass karte waqt
        # naya empty vectorstore banta
        # = Koi data nahi = Koi analysis nahi!
        st.session_state.vectorstore = vectorstore
        progress.progress(60, text="FAISS ready! ✅")

        # ── STEP 3: Summary ──
        progress.progress(70, text="Contract summary bana raha hun...")
        summary = get_contract_summary(pdf_text)
        st.session_state.contract_summary = summary
        progress.progress(80, text="Summary ready! ✅")

        # ── STEP 4: Risk Analysis ──
        progress.progress(85, text="Risky clauses analyze kar raha hun...")
        analyses = analyze_contract_risks(
            pdf_text,
            vectorstore=st.session_state.vectorstore  # Same instance pass karo!
        )
        st.session_state.risk_analyses = analyses
        progress.progress(100, text="Analysis complete! ✅")

        st.session_state.pdf_processed = True
        os.unlink(tmp_path)  # Temp file cleanup
        return True

    except Exception as e:
        st.error(f"❌ Error aaya: {str(e)}")
        # Error pe bhi temp file delete karo — disk space waste na ho
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        return False


# ============================================
# MAIN UI
# ============================================

# ── HEADER ──
st.markdown("# ⚖️ Legal Contract Analyzer")
st.markdown("### AI-powered contract review — Risky clauses dhundo, plain English mein samjho")
st.divider()

# ── UPLOAD SECTION ──
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📄 Contract Upload Karo")
    uploaded_file = st.file_uploader(
        label="PDF contract yahan drop karo",
        type=["pdf"],
        help="Koi bhi PDF contract — NDA, Employment, Lease, etc."
    )

with col2:
    st.subheader("ℹ️ Supported Contracts")
    st.markdown("""
    - 📝 NDA / Confidentiality
    - 💼 Employment Agreements
    - 🏠 Lease / Rental
    - 🤝 Vendor / Service
    - 💰 Investment / Equity
    """)

# Analyze button — sirf tab dikhao jab:
# 1. File upload hui ho (uploaded_file is not None)
# 2. Abhi process nahi hua ho (not pdf_processed)
if uploaded_file is not None and not st.session_state.pdf_processed:
    st.info(f"📎 File ready: **{uploaded_file.name}**")

    if st.button("🔍 Analyze Contract", type="primary", use_container_width=True):
        with st.spinner("Analysis chal rahi hai... (1-2 minute lag sakte hain)"):
            success = process_pdf(uploaded_file)
            if success:
                st.success("✅ Analysis complete!")
                st.rerun()  # Page refresh → results dikhenge

# Naya contract analyze karne ka button
# Sirf tab dikhao jab koi contract already processed ho
if st.session_state.pdf_processed:
    if st.button("📄 Naya Contract Analyze Karo", type="secondary"):
        # Saara state reset — fresh start
        st.session_state.pdf_processed = False
        st.session_state.contract_summary = None
        st.session_state.risk_analyses = []
        st.session_state.chat_history = []
        st.session_state.pdf_text = ""
        st.session_state.vectorstore = None  # FAISS bhi reset
        st.rerun()


# ============================================
# RESULTS SECTION
# Sirf tab dikhao jab PDF process ho chuka ho
# ============================================

if st.session_state.pdf_processed:

    st.divider()

    # ── CONTRACT SUMMARY ──
    summary = st.session_state.contract_summary

    if summary:
        st.subheader("📋 Contract Overview")

        # 4 metrics ek line mein — quick snapshot
        m1, m2, m3, m4 = st.columns(4)

        with m1:
            st.metric(
                label="Contract Type",
                value=summary.get('contract_type', 'N/A')
            )

        with m2:
            risk = summary.get('overall_risk', 'N/A')
            emoji = get_risk_emoji(risk)
            st.metric(
                label="Overall Risk",
                value=f"{emoji} {risk}"
            )

        with m3:
            parties = summary.get('parties_involved', [])
            st.metric(
                label="Parties Involved",
                value=len(parties)
            )

        with m4:
            analyses = st.session_state.risk_analyses
            high_risk = sum(
                1 for a in analyses
                if isinstance(a, dict) and a.get('risk_level') == 'HIGH'
            )
            st.metric(
                label="High Risk Clauses",
                value=f"🔴 {high_risk}"
            )

        with st.expander("📖 Contract Summary Details", expanded=True):
            st.markdown(f"**Overview:** {summary.get('summary', 'N/A')}")

            col_a, col_b = st.columns(2)

            with col_a:
                st.markdown("**👥 Parties:**")
                for party in summary.get('parties_involved', []):
                    st.markdown(f"  • {party}")

            with col_b:
                st.markdown("**📅 Key Dates:**")
                dates = summary.get('key_dates', [])
                if dates:
                    for date in dates:
                        st.markdown(f"  • {date}")
                else:
                    st.markdown("  • No specific dates mentioned")

            st.markdown("**🚨 Red Flags:**")
            for flag in summary.get('red_flags', []):
                st.error(f"⚠️ {flag}")

    st.divider()

    # ── CLAUSE RISK ANALYSIS ──
    st.subheader("🔍 Clause-by-Clause Risk Analysis")

    analyses = st.session_state.risk_analyses

    if analyses:
        # HIGH risk pehle dikhao
        risk_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "NEUTRAL": 3}
        sorted_analyses = sorted(
            analyses,
            key=lambda x: risk_order.get(
                x.get('risk_level', 'NEUTRAL') if isinstance(x, dict)
                else 'NEUTRAL', 3
            )
        )

        for analysis in sorted_analyses:
            a = analysis if isinstance(analysis, dict) else analysis.dict()

            risk = a.get('risk_level', 'NEUTRAL')
            emoji = get_risk_emoji(risk)
            clause_type = a.get('clause_type', 'Unknown Clause')

            # HIGH risk = auto-open, baaki collapsed
            with st.expander(
                f"{emoji} {clause_type} — {risk} RISK",
                expanded=(risk == "HIGH")
            ):
                tab1, tab2, tab3 = st.tabs([
                    "🗣️ Plain English",
                    "⚠️ Why Risky?",
                    "📜 Original Text"
                ])

                with tab1:
                    st.info(a.get('plain_english', 'N/A'))
                    st.success(
                        f"💡 **Recommendation:** {a.get('recommendation', 'N/A')}"
                    )

                with tab2:
                    st.warning(a.get('risk_reason', 'N/A'))

                with tab3:
                    st.code(a.get('original_text', 'N/A'), language=None)
    else:
        st.info("Koi risky clauses nahi mile — contract clean lag raha hai!")

    st.divider()

    # ── CHAT SECTION ──
    st.subheader("💬 Contract se Pooch Kuch Bhi")
    st.caption("Hindi ya English mein pooch lo!")

    # Pehle existing chat history dikhao
    for message in st.session_state.chat_history:
        if message["role"] == "user":
            with st.chat_message("user"):
                st.write(message["content"])
        else:
            with st.chat_message("assistant", avatar="⚖️"):
                st.write(message["content"])

    # Chat input
    if question := st.chat_input("Pooch lo... jaise: 'Can I work for a competitor?'"):

        st.session_state.chat_history.append({
            "role": "user",
            "content": question
        })
        with st.chat_message("user"):
            st.write(question)

        with st.chat_message("assistant", avatar="⚖️"):
            with st.spinner("Soch raha hun..."):
                response = chat_with_contract(
                    question,
                    vectorstore=st.session_state.vectorstore  # Same FAISS instance!
                )
            st.write(response)

        st.session_state.chat_history.append({
            "role": "assistant",
            "content": response
        })


# ============================================
# FOOTER
# ============================================

st.divider()
st.markdown("""
<div style='text-align: center; color: #4B5563; font-size: 12px;'>
⚖️ Legal Contract Analyzer | LangChain + Groq + FAISS<br>
⚠️ AI analysis is for informational purposes only.
Consult a qualified lawyer for legal advice.
</div>
""", unsafe_allow_html=True)