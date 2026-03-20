# app.py
# Streamlit UI — Hamare project ka face!
# Yahan sab kuch ek jagah aata hai

import streamlit as st
import tempfile
import os

# Hamare modules
from ingestion import ingest_pdf, extract_text_from_pdf
from retrieval import (
    get_contract_summary,
    analyze_contract_risks,
    chat_with_contract
)

# ============================================
# PAGE CONFIG — Sabse pehle yeh hona chahiye
# ============================================

st.set_page_config(
    page_title="Legal Contract Analyzer",
    page_icon="⚖️",
    layout="wide",           # Wide layout — zyada space
    initial_sidebar_state="collapsed"
)

# ============================================
# CUSTOM CSS — Thoda sundar dikhao
# ============================================

st.markdown("""
<style>
    /* Main background */
    .main { background-color: #0a0a0f; }
    
    /* Risk badges */
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
    .risk-neutral {
        background: #6B728020;
        border: 1px solid #6B7280;
        color: #6B7280;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 14px;
    }
    
    /* Clause card */
    .clause-card {
        background: #111827;
        border-radius: 10px;
        padding: 16px;
        margin: 8px 0;
        border: 1px solid #1F2937;
    }
    
    /* Chat messages */
    .chat-user {
        background: #1E3A5F;
        border-radius: 10px;
        padding: 10px 14px;
        margin: 6px 0;
        text-align: right;
    }
    .chat-ai {
        background: #111827;
        border-radius: 10px;
        padding: 10px 14px;
        margin: 6px 0;
        border-left: 3px solid #00FFB2;
    }
</style>
""", unsafe_allow_html=True)


# ============================================
# SESSION STATE — Streamlit ka Memory System
# ============================================

# Session State kya hai?
# Streamlit mein har interaction pe
# poora page dobara run hota hai!
#
# Problem: Variable reset ho jaate hain
# Solution: st.session_state = Permanent memory
#           Jab tak browser tab band na ho

if "pdf_processed" not in st.session_state:
    st.session_state.pdf_processed = False  # PDF upload hua kya?

if "contract_summary" not in st.session_state:
    st.session_state.contract_summary = None  # Summary store karo

if "risk_analyses" not in st.session_state:
    st.session_state.risk_analyses = []  # Sare analyses store karo

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []  # Chat messages store karo

if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = ""  # Raw PDF text


# ============================================
# HELPER FUNCTIONS
# ============================================

def get_risk_badge(risk_level: str) -> str:
    """Risk level ke liye colored badge banao"""
    badges = {
        "HIGH": '<span class="risk-high">🔴 HIGH RISK</span>',
        "MEDIUM": '<span class="risk-medium">🟡 MEDIUM RISK</span>',
        "LOW": '<span class="risk-low">🟢 LOW RISK</span>',
        "NEUTRAL": '<span class="risk-neutral">⚪ NEUTRAL</span>',
    }
    return badges.get(risk_level, risk_level)


def get_risk_emoji(risk_level: str) -> str:
    """Simple emoji for risk"""
    emojis = {
        "HIGH": "🔴",
        "MEDIUM": "🟡", 
        "LOW": "🟢",
        "NEUTRAL": "⚪"
    }
    return emojis.get(risk_level, "❓")


def process_pdf(uploaded_file):
    """
    Uploaded PDF ko process karo

    Steps:
    1. Temp file mein save karo
       (Streamlit uploaded file = memory object,
        PyMuPDF ko actual file path chahiye)
    2. Text extract karo
    3. ChromaDB mein ingest karo
    4. Summary aur analysis lo
    """

    # Temp file banao
    # tempfile.NamedTemporaryFile kyu?
    # Streamlit ka uploaded_file directly disk pe nahi hota
    # PyMuPDF ko real file path chahiye
    # Toh temporarily disk pe save karte hain
    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".pdf"
    ) as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name

    try:
        # Progress bar dikhao
        progress = st.progress(0, text="PDF padh raha hun...")

        # Step 1: Text extract karo
        pdf_text = extract_text_from_pdf(tmp_path)
        st.session_state.pdf_text = pdf_text
        progress.progress(25, text="PDF padh liya! ✅")

        # Step 2: ChromaDB mein ingest karo
        progress.progress(40, text="Vectors bana raha hun...")
        ingest_pdf(tmp_path)
        progress.progress(60, text="ChromaDB mein save ho gaya! ✅")

        # Step 3: Summary lo
        progress.progress(70, text="Contract summary bana raha hun...")
        summary = get_contract_summary(pdf_text)
        st.session_state.contract_summary = summary
        progress.progress(80, text="Summary ready! ✅")

        # Step 4: Risk analysis lo
        progress.progress(85, text="Risky clauses dhundh raha hun... (thoda time lagega)")
        analyses = analyze_contract_risks(pdf_text)
        st.session_state.risk_analyses = analyses
        progress.progress(100, text="Analysis complete! ✅")

        st.session_state.pdf_processed = True
        
        # Temp file delete karo
        os.unlink(tmp_path)

        return True

    except Exception as e:
        st.error(f"❌ Error aaya: {str(e)}")
        os.unlink(tmp_path)
        return False


# ============================================
# MAIN UI
# ============================================

# Header
st.markdown("""
# ⚖️ Legal Contract Analyzer
### AI-powered contract review — Risky clauses dhundo, plain English mein samjho
""")

st.divider()

# ============================================
# SECTION 1: PDF UPLOAD
# ============================================

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

# Analyze button
if uploaded_file is not None and not st.session_state.pdf_processed:
    st.info(f"📎 File ready: **{uploaded_file.name}**")
    
    if st.button(
        "🔍 Analyze Contract",
        type="primary",
        use_container_width=True
    ):
        with st.spinner("Analysis chal rahi hai... (1-2 minute lag sakte hain)"):
            success = process_pdf(uploaded_file)
            
            if success:
                st.success("✅ Analysis complete! Results dekho neeche 👇")
                st.rerun()  # Page refresh karo results dikhane ke liye

# Naya contract analyze karne ka option
if st.session_state.pdf_processed:
    if st.button("📄 Naya Contract Analyze Karo", type="secondary"):
        # Session state reset karo
        st.session_state.pdf_processed = False
        st.session_state.contract_summary = None
        st.session_state.risk_analyses = []
        st.session_state.chat_history = []
        st.session_state.pdf_text = ""
        st.rerun()


# ============================================
# SECTION 2: RESULTS (sirf tab dikhao jab PDF process ho)
# ============================================

if st.session_state.pdf_processed:
    
    st.divider()
    
    # ── CONTRACT SUMMARY ──
    summary = st.session_state.contract_summary
    
    if summary:
        st.subheader("📋 Contract Overview")
        
        # Top metrics — 4 columns mein
        m1, m2, m3, m4 = st.columns(4)
        
        with m1:
            st.metric(
                label="Contract Type",
                value=summary.get('contract_type', 'Unknown')
            )
        
        with m2:
            risk = summary.get('overall_risk', 'UNKNOWN')
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
        
        # Summary text
        with st.expander("📖 Contract Summary Details", expanded=True):
            
            # Summary
            st.markdown(f"**Overview:** {summary.get('summary', 'N/A')}")
            
            col_a, col_b = st.columns(2)
            
            with col_a:
                # Parties
                st.markdown("**👥 Parties:**")
                for party in summary.get('parties_involved', []):
                    st.markdown(f"  • {party}")
            
            with col_b:
                # Key dates
                st.markdown("**📅 Key Dates:**")
                dates = summary.get('key_dates', [])
                if dates:
                    for date in dates:
                        st.markdown(f"  • {date}")
                else:
                    st.markdown("  • No specific dates mentioned")
            
            # Red flags
            st.markdown("**🚨 Red Flags:**")
            for flag in summary.get('red_flags', []):
                st.error(f"⚠️ {flag}")
    
    st.divider()
    
    # ── CLAUSE RISK ANALYSIS ──
    st.subheader("🔍 Clause-by-Clause Risk Analysis")
    
    analyses = st.session_state.risk_analyses
    
    if analyses:
        # Risk ke hisaab se sort karo — HIGH pehle
        risk_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "NEUTRAL": 3}
        
        sorted_analyses = sorted(
            analyses,
            key=lambda x: risk_order.get(
                x.get('risk_level', 'NEUTRAL') if isinstance(x, dict) 
                else 'NEUTRAL', 
                3
            )
        )
        
        for i, analysis in enumerate(sorted_analyses):
            # Dict ya Pydantic object dono handle karo
            if isinstance(analysis, dict):
                a = analysis
            else:
                a = analysis.dict()
            
            risk = a.get('risk_level', 'NEUTRAL')
            emoji = get_risk_emoji(risk)
            clause_type = a.get('clause_type', 'Unknown Clause')
            
            # Expander mein har clause dikhao
            with st.expander(
                f"{emoji} {clause_type} — {risk} RISK",
                expanded=(risk == "HIGH")  # HIGH risk auto-open
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
                    st.code(
                        a.get('original_text', 'N/A'),
                        language=None
                    )
    else:
        st.info("Koi risky clauses nahi mile — contract clean hai!")
    
    st.divider()
    
    # ── CHAT SECTION ──
    st.subheader("💬 Contract se Pooch Kuch Bhi")
    st.caption(
        "Contract ke baare mein koi bhi question — "
        "Hindi ya English mein!"
    )
    
    # Chat history dikhao
    for message in st.session_state.chat_history:
        if message["role"] == "user":
            with st.chat_message("user"):
                st.write(message["content"])
        else:
            with st.chat_message("assistant", avatar="⚖️"):
                st.write(message["content"])
    
    # Chat input
    if question := st.chat_input(
        "Pooch lo... jaise: 'Can I work for a competitor after leaving?'"
    ):
        # User message add karo
        st.session_state.chat_history.append({
            "role": "user",
            "content": question
        })
        
        with st.chat_message("user"):
            st.write(question)
        
        # AI response lo
        with st.chat_message("assistant", avatar="⚖️"):
            with st.spinner("Soch raha hun..."):
                response = chat_with_contract(question)
            st.write(response)
        
        # Response bhi save karo
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