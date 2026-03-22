# ============================================
# CONFIG.PY
# Saari settings ek jagah — easy to change
# Agar kuch change karna ho toh sirf yahan aao
# ============================================

import os
import streamlit as st
from dotenv import load_dotenv

# .env file load karo
# .env mein GROQ_API_KEY=gsk_xxx likha hota hai
# load_dotenv() usse os.environ mein load karta hai
load_dotenv()


def get_api_key():
    """
    API key do jagah se lo:
    1. Streamlit Cloud pe: st.secrets se (secrets.toml se)
    2. Local pe: .env file se

    Kyu dono jagah?
    Local pe .env file hoti hai → st.secrets nahi hota
    Cloud pe secrets.toml hota hai → .env nahi hoti
    Isliye dono try karo!
    """
    try:
        # Pehle Streamlit secrets try karo (cloud ke liye)
        return st.secrets["GROQ_API_KEY"]
    except:
        # Local pe .env se lo
        return os.getenv("GROQ_API_KEY")


# ============================================
# API SETTINGS
# ============================================

# Groq API key — function se lo
GROQ_API_KEY = get_api_key()

# Groq model — Llama 3.3 70B
# Kyu yeh model?
# → GPT-4 ke barabar quality
# → Free hai Groq pe
# → Ultra fast inference
GROQ_MODEL = "llama-3.3-70b-versatile"


# ============================================
# EMBEDDING SETTINGS
# ============================================

# HuggingFace embedding model
# Kyu all-MiniLM-L6-v2?
# → Free + Local (koi API nahi)
# → Sirf 80MB download
# → 384-dimensional vectors
# → Legal text ke liye accurate enough
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


# ============================================
# CHUNKING SETTINGS
# ============================================

# Chunk size = Har chunk mein max kitne characters
# 500 kyu? (Pehle 1000 tha)
# → Chote chunks = specific clauses better capture hote hain
# → Legal clauses usually 200-400 chars ke hote hain
# → Zyada focused retrieval
CHUNK_SIZE = 500

# Chunk overlap = Do consecutive chunks mein kitne chars common
# 100 kyu? (Pehle 200 tha)
# → Context nahi toota clause ke beech mein
# → Sentence boundary pe split hone pe bhi meaning preserve hota hai
CHUNK_OVERLAP = 100


# ============================================
# RETRIEVAL SETTINGS
# ============================================

# Top K = User ke question ke liye kitne chunks fetch karo
# 10 kyu? (Pehle 5 tha)
# → Zyada chunks = zyada context = better analysis
# → Legal docs mein ek clause multiple chunks mein hoti hai
# → 10 se poori clause ka context milta hai
TOP_K_RESULTS = 10