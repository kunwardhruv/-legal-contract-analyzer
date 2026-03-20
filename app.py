# app.py
# Streamlit UI — Project ka face!
# Yahan sab kuch ek jagah aata hai:
# Upload → Process → Show Results → Chat

import streamlit as st
import tempfile
import os

from ingestion import ingest_pdf, extract_text_from_pdf
from retrieval import (
    get_contract_summary,
    analyze_contract_risks,
    chat_with_contract
)

# ============================================
# PAGE CONFIG — Sabse pehle hona chahiye
# ============================================

st.set_page_config(
    page_title="Legal Contract Analyzer",
    page_icon="⚖️",
    layout="wide",                    # Wide layout — zyada space
    initial_sidebar_state="collapsed" # Sidebar band rakho
)

# ============================================
# CUSTOM CSS — UI thoda sundar banao
# ============================================

st.markdown("""
<style>
    .risk-high {
        background: #EF444420; border: 1px solid #EF4444;
        color: #EF4444; padding: 4px 12px;
        border-radius: 20px; font-weight: bold; font-size: 14px;
    }
    .risk-medium {
        background: #F59E0B20; border: 1px solid #F59E0B;
        color: #F59E0B; padding: 4px 12px;
        border-radius: 20px; font-weight: bold; font-size: 14px;
    }
    .risk-low {
        background: #10B98120; border: 1px solid #10B981;
        color: #10B981; padding: 4px 12px;
        border-radius: 20px; font-weight: bold; font-size: 14px;
    }
</style>
""", unsafe_allow_html=True)


# ============================================
# SESSION STATE — Streamlit ka Memory System
# ============================================

# Session State kya hai aur kyu chahiye?
# Streamlit mein problem: Har button click pe POORA script dobara run hota hai!
# Matlab sab variables reset ho jaate hain
#
# Solution: st.session_state = Permanent storage
# Jab tak browser tab band na ho, data yahan safe rehta hai
#
# Analogy: Normal variable = RAM (reset hoti hai)
#          session_state = Hard disk (persist hoti hai)

if "pdf_processed" not in st.session_state:
    st.session_state.pdf_processed = False   # PDF analyze hua kya?

if "contract_summary" not in st.session_state:
    st.session_state.contract_summary = None # Contract ka overview

if "risk_analyses" not in st.session_state:
    st.session_state.risk_analyses = []      # Saare clause analyses

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []       # Chat messages

if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = ""           # Raw PDF text

if "vectorstore" not in st.session_state:
    st.session_state.vectorstore = None
    # SABSE IMPORTANT session state variable!
    # ingest_pdf() jo vectorstore return karta hai, woh yahan save hoga
    # analyze_contract_risks() aur chat_with_contract() yahan se lenge
    # Ek hi instance = "tenant not found" error nahi aayega


# ============================================
# HELPER FUNCTIONS
# ============================================

def get_risk_emoji(risk_level: str) -> str:
    """Risk level ko emoji mein convert karo — visual indicator"""
    emojis = {
        "HIGH": "🔴",
        "MEDIUM": "🟡",
        "LOW": "🟢",
        "NEUTRAL": "⚪"
    }
    return emojis.get(risk_level, "❓")


def process_pdf(uploaded_file):
    """
    Uploaded PDF ko process karo — poori pipeline chalao

    Steps:
    1. Temp file banao (Streamlit file = memory object, PyMuPDF ko real path chahiye)
    2. Text extract karo
    3. ingest_pdf() → vectorstore milega → SESSION STATE mein save karo
    4. Summary lo
    5. Risk analysis karo — SAME vectorstore pass karo
    """

    # Temp file kyu?
    # Streamlit ka uploaded_file = memory mein hota hai
    # PyMuPDF ko actual disk path chahiye
    # Solution: Temporarily disk pe save karo → use karo → delete karo
    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".pdf"
    ) as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name  # Yeh path PyMuPDF ko denge

    try:
        progress = st.progress(0, text="PDF padh raha hun...")

        # Step 1: Text extract karo
        pdf_text = extract_text_from_pdf(tmp_path)
        st.session_state.pdf_text = pdf_text
        progress.progress(25, text="PDF padh liya! ✅")

        # Step 2: PDF ingest karo — vectorstore return hoga
        progress.progress(40, text="Vectors bana raha hun...")
        vectorstore = ingest_pdf(tmp_path)

        # CRITICAL STEP: Vectorstore session state mein save karo
        # Yeh wahi instance hai jo ChromaDB mein data store karta hai
        # Baad mein analysis aur chat mein yahi pass karenge
        st.session_state.vectorstore = vectorstore
        progress.progress(60, text="ChromaDB ready! ✅")

        # Step 3: Contract summary lo (vectorstore ki zarurat nahi — direct text se)
        progress.progress(70, text="Summary bana raha hun...")
        summary = get_contract_summary(pdf_text)
        st.session_state.contract_summary = summary
        progress.progress(80, text="Summary ready! ✅")

        # Step 4: Risk analysis — SESSION STATE wala vectorstore pass karo
        # Naya instance mat banao — wahi use karo jo upar save kiya
        progress.progress(85, text="Risky clauses dhundh raha hun...")
        analyses = analyze_contract_risks(
            pdf_text,
            vectorstore=st.session_state.vectorstore  # ← Same instance!
        )
        st.session_state.risk_analyses = analyses
        progress.progress(100, text="Analysis complete! ✅")

        st.session_state.pdf_processed = True
        os.unlink(tmp_path)  # Temp file delete karo — cleanup
        return True

    except Exception as e:
        st.error(f"❌ Error aaya: {str(e)}")
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)  # Error pe bhi temp file delete karo
        return False


# ============================================
# MAIN UI
# ============================================

# Header
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

# Analyze button — sirf tab dikhao jab file upload ho aur process na hua ho
if uploaded_file is not None and not st.session_state.pdf_processed:
    st.info(f"📎 File ready: **{uploaded_file.name}**")

    if st.button("🔍 Analyze Contract", type="primary", use_container_width=True):
        with st.spinner("Analysis chal rahi hai... (1-2 minute lag sakte hain)"):
            success = process_pdf(uploaded_file)
            if success:
                st.success("✅ Analysis complete!")
                st.rerun()  # Page refresh karo taaki results dikhein

# Naya contract analyze karne ka button
if st.session_state.pdf_processed:
    if st.button("📄 Naya Contract Analyze Karo", type="secondary"):
        # Saara session state reset karo — fresh start
        st.session_state.pdf_processed = False
        st.session_state.contract_summary = None
        st.session_state.risk_analyses = []
        st.session_state.chat_history = []
        st.session_state.pdf_text = ""
        st.session_state.vectorstore = None  # Vectorstore bhi reset karo
        st.rerun()


# ============================================
# RESULTS SECTION — Sirf tab dikhao jab PDF process hua ho
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
            st.metric("Contract Type", summary.get('contract_type', 'N/A'))

        with m2:
            risk = summary.get('overall_risk', 'N/A')
            emoji = get_risk_emoji(risk)
            st.metric("Overall Risk", f"{emoji} {risk}")

        with m3:
            parties = summary.get('parties_involved', [])
            st.metric("Parties Involved", len(parties))

        with m4:
            analyses = st.session_state.risk_analyses
            high_risk = sum(
                1 for a in analyses
                if isinstance(a, dict) and a.get('risk_level') == 'HIGH'
            )
            st.metric("High Risk Clauses", f"🔴 {high_risk}")

        # Detailed summary expandable section
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
        # HIGH risk pehle dikhao — priority order
        risk_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "NEUTRAL": 3}
        sorted_analyses = sorted(
            analyses,
            key=lambda x: risk_order.get(
                x.get('risk_level', 'NEUTRAL') if isinstance(x, dict)
                else 'NEUTRAL', 3
            )
        )

        for analysis in sorted_analyses:
            # Dict ya Pydantic object — dono handle karo
            a = analysis if isinstance(analysis, dict) else analysis.dict()

            risk = a.get('risk_level', 'NEUTRAL')
            emoji = get_risk_emoji(risk)
            clause_type = a.get('clause_type', 'Unknown Clause')

            # HIGH risk clauses automatically open dikhao
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
        st.info("Koi risky clauses nahi mile — contract clean hai!")

    st.divider()

    # ── CHAT SECTION ──
    st.subheader("💬 Contract se Pooch Kuch Bhi")
    st.caption("Contract ke baare mein koi bhi question — Hindi ya English mein!")

    # Pehle existing chat history dikhao
    for message in st.session_state.chat_history:
        if message["role"] == "user":
            with st.chat_message("user"):
                st.write(message["content"])
        else:
            with st.chat_message("assistant", avatar="⚖️"):
                st.write(message["content"])

    # Chat input — user ka question lo
    if question := st.chat_input("Pooch lo... jaise: 'Can I work for a competitor?'"):

        # User message save karo aur dikhao
        st.session_state.chat_history.append({
            "role": "user",
            "content": question
        })
        with st.chat_message("user"):
            st.write(question)

        # AI response lo — SESSION STATE wala vectorstore pass karo
        with st.chat_message("assistant", avatar="⚖️"):
            with st.spinner("Soch raha hun..."):
                response = chat_with_contract(
                    question,
                    vectorstore=st.session_state.vectorstore  # ← Same instance!
                )
            st.write(response)

        # AI response bhi save karo
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
⚖️ Legal Contract Analyzer | Built with LangChain + Groq + ChromaDB<br>
⚠️ AI analysis is for informational purposes only.
Consult a qualified lawyer for legal advice.
</div>
""", unsafe_allow_html=True)