# ============================================
# INGESTION.PY
# PDF → Text → Smart Chunks → Vectors → FAISS
#
# Yeh hai poori RAG pipeline ka HEART!
# Yahan PDF ko process karke vector database mein store karte hain
# Taaki baad mein relevant parts quickly dhundh sakein
#
# Flow:
# PDF File
#    ↓
# PyMuPDF (text nikalo)
#    ↓
# Smart Legal Chunking (clause-aware split)
#    ↓
# HuggingFace Embeddings (text → numbers)
#    ↓
# FAISS (numbers store karo)
#    ↓
# Vectorstore return karo (app.py session state mein save hoga)
# ============================================

import fitz
# fitz = PyMuPDF ka Python naam
# PDF file kholta hai aur text nikalta hai
# Kyu PyMuPDF?
# → Fastest Python PDF library
# → Complex legal PDF formatting handle karta hai
# → Tables, headers, footers sab handle karta hai

import re
# re = Python ka built-in regex library
# Regular expressions = pattern matching
# Hum isse legal clause patterns dhundhne ke liye use karenge
# Jaise "1.", "1.1", "Section 2", "Article 3", "CLAUSE 4"

from langchain_huggingface import HuggingFaceEmbeddings
# HuggingFace ka embedding model use karne ka LangChain interface
# Embedding = Text ko numbers (vectors) mein convert karna
# Kyu? Computers meaning samajhte nahi — sirf numbers samajhte hain!

from langchain_community.vectorstores import FAISS
# FAISS = Facebook AI Similarity Search
# Vector database — chunks ko store karta hai
# Kyu FAISS aur ChromaDB nahi?
# ChromaDB = Global client maintain karta hai
#            Dusri PDF pe → "tenant not found" error!
# FAISS = Pure numpy arrays — koi client nahi, koi tenant nahi
#         Har baar fresh instance → zero conflicts ✅
#         Cloud pe bhi perfectly kaam karta hai ✅

import config
# Haari settings file — API keys, model names, chunk sizes
import os
# File system operations ke liye — os.path.basename() etc.


# ============================================
# STEP 1: PDF SE TEXT NIKALO
# ============================================

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    PDF file kholo aur saara text page by page nikalo.

    Parameter:
        pdf_path: PDF file ka disk pe path
                  jaise "C:/Users/dhruv/contract.pdf"

    Returns:
        full_text: Poora PDF ka text as string

    PyMuPDF kyu?
    → pdfplumber se faster hai
    → Legal PDFs mein complex layouts handle karta hai
    → Scanned PDFs mein warning deta hai (kaam karta rehta hai)
    """

    print(f"📄 PDF padh raha hun: {pdf_path}")

    # PDF file kholo
    # fitz.open() = PyMuPDF se PDF open karo
    doc = fitz.open(pdf_path)

    # CRITICAL: total_pages PEHLE save karo!
    # Kyu? doc.close() ke baad len(doc) call nahi kar sakte
    # Warna "document closed" ValueError aata hai
    # (Yeh bug humne already fix kiya tha!)
    total_pages = len(doc)

    full_text = ""

    # Har page pe jaao
    for page_num in range(total_pages):
        page = doc[page_num]

        # Page se text nikalo
        # get_text() = page ka saara text return karta hai
        text = page.get_text()

        # Page number bhi add karo header ki tarah
        # Kyu? Baad mein pata chale ki kaunsa clause kaunse page pe tha
        full_text += f"\n--- Page {page_num + 1} ---\n"
        full_text += text

    # File band karo — memory free karo
    doc.close()

    print(f"✅ {total_pages} pages padh liye!")
    print(f"📝 Total characters: {len(full_text)}")

    return full_text


# ============================================
# STEP 2A: SMART LEGAL CLAUSE CHUNKING ⭐ NEW!
# ============================================

def split_by_legal_clauses(text: str) -> list:
    """
    Legal document ko clause boundaries pe split karo.

    Yeh function SMART hai — sirf characters count nahi karta,
    balki LEGAL STRUCTURE samajhta hai!

    Kyu yeh better hai?
    ─────────────────────────────────────────
    OLD approach (character-based):
    "1.1 Employee agrees to...non-compete...1.2 Payment"
    → "1.1 Employee agrees to...non-com" (1000 chars)
    → "pete...1.2 Payment" (baaki)
    ← Clause beech mein toot gayi! ❌

    NEW approach (clause-aware):
    "1.1 Employee agrees to...non-compete..." → Ek chunk ✅
    "1.2 Payment terms..." → Alag chunk ✅
    ← Har clause apne aap mein complete! ✅
    ─────────────────────────────────────────

    Legal documents mein natural split points:
    → "1." "1.1" "1.2" (numbered clauses)
    → "Section 1" "Section 2" (section headers)
    → "Article 1" "Article 2" (article headers)
    → "CLAUSE 1" "CLAUSE 2" (CAPS clauses)

    Parameter:
        text: Poora PDF ka text

    Returns:
        clauses: List of clause strings
    """

    print("⚖️  Legal clause structure detect kar raha hun...")

    # Regex pattern — yeh legal document ke natural splits dhundta hai
    #
    # r'(?=...)' = Lookahead assertion
    # Matlab: "yahan split karo, lekin pattern ko chunk mein rakhna"
    #
    # (?:\d+\.\d*) = "1." ya "1.1" ya "1.1.1" jaise numbered clauses
    # |Section\s+\d+ = "Section 1" ya "Section 12"
    # |Article\s+\d+ = "Article 1" ya "Article 5"
    # |CLAUSE\s+\d+ = "CLAUSE 1" (caps mein)
    # [\s\.] = Space ya period ke baad (false matches avoid)
    #
    # flags=re.IGNORECASE = "section" aur "SECTION" dono match
    clause_pattern = r'(?=(?:\d+\.\d*|Section\s+\d+|Article\s+\d+|CLAUSE\s+\d+)[\s\.])'

    # Text ko pattern ke basis pe split karo
    sections = re.split(clause_pattern, text, flags=re.IGNORECASE)

    clauses = []
    for section in sections:
        section = section.strip()  # Whitespace hatao

        # 150 chars se chote fragments skip karo
        # Kyu? Page numbers, headers jaise "--- Page 1 ---" skip honge
        # Legal clauses usually 150+ chars ke hote hain
        if len(section) > 150:
            clauses.append(section)

    print(f"✅ {len(clauses)} legal clauses detect kiye!")

    # Agar clause detection fail ho (koi pattern na mile)
    # Toh fallback: character-based chunking use karo
    if len(clauses) < 3:
        print("⚠️  Legal structure nahi mili, character chunking use kar raha hun...")
        return split_by_characters(text)

    return clauses


# ============================================
# STEP 2B: FALLBACK CHARACTER CHUNKING
# ============================================

def split_by_characters(text: str) -> list:
    """
    Fallback chunking — jab legal structure detect na ho.

    Kab use hota hai?
    → Informal contracts jo numbered clauses use nahi karte
    → Scanned PDFs jahan text properly extract nahi hua
    → Simple agreements

    RecursiveCharacterTextSplitter kyu?
    → "Recursive" = Priority order mein split karta hai
    → Pehle paragraphs pe try karta hai (\n\n)
    → Phir lines pe (\n)
    → Phir sentences pe (". ")
    → Phir words pe (" ")
    → Last resort: kahi bhi ("")
    = Smart splitting, word beech mein nahi tootega
    """

    from langchain.text_splitter import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,        # Max 500 chars
        chunk_overlap=config.CHUNK_OVERLAP,  # 100 chars overlap
        separators=["\n\n", "\n", ". ", " ", ""]
    )

    chunks = splitter.split_text(text)
    print(f"✅ {len(chunks)} character-based chunks bane!")
    return chunks


# ============================================
# STEP 3: EMBEDDING MODEL LOAD KARO
# ============================================

def get_embedding_model():
    """
    HuggingFace ka free embedding model load karo.

    Embedding kya hai?
    ─────────────────────────────────────────
    "Non-compete clause" → [0.23, -0.87, 0.45, ... 384 numbers]
    "Employee restriction" → [0.21, -0.85, 0.43, ...]
                              ↑ similar numbers = similar meaning!

    Computer meaning nahi samajhta — sirf numbers samajhta hai
    Embedding = meaning ko numbers mein translate karna
    ─────────────────────────────────────────

    all-MiniLM-L6-v2 kyu?
    → Free hai — local machine pe run hota hai (koi API nahi)
    → Sirf 80MB — lightweight
    → 384-dimensional vectors — legal text ke liye accurate
    → Most popular open-source embedding model
    → Pehli baar: ~80MB download hoga
    → Baad mein: cache se load → fast!
    """

    print("🔢 Embedding model load ho raha hai...")

    embeddings = HuggingFaceEmbeddings(
        model_name=config.EMBEDDING_MODEL,           # "all-MiniLM-L6-v2"
        model_kwargs={"device": "cpu"},               # CPU pe chalao (GPU nahi chahiye)
        encode_kwargs={"normalize_embeddings": True}  # Vectors 0-1 range — better search
    )

    print("✅ Embedding model ready!")
    return embeddings


# ============================================
# STEP 4: FAISS MEIN STORE KARO
# ============================================

def store_in_faiss(chunks: list, filename: str):
    """
    Chunks → Vectors → FAISS mein store karo.

    FAISS kyu ChromaDB nahi?
    ─────────────────────────────────────────
    ChromaDB:
    → Global client maintain karta hai
    → Dusri PDF pe restart hone pe client gone
    → "Could not connect to tenant default_tenant" ERROR ❌

    FAISS:
    → Pure numpy arrays — koi client nahi
    → Koi tenant nahi, koi server nahi
    → Har baar fresh instance → zero conflicts ✅
    → Cloud pe bhi perfectly kaam karta hai ✅
    → Facebook/Meta production mein use karta hai
    ─────────────────────────────────────────

    Parameter:
        chunks: Text ke pieces (list of strings)
        filename: PDF ka naam (metadata ke liye)

    Returns:
        vectorstore: FAISS vectorstore object
                     (app.py session state mein save hoga)
    """

    print(f"🗄️  FAISS mein store kar raha hun...")

    # Har chunk ke saath metadata store karo
    # Metadata = Extra information jo chunk ke saath save hoti hai
    # Kyu? Baad mein pata chale ki chunk kaunse file ka hai
    metadatas = [
        {
            "source": filename,    # Kaunsi PDF se aaya
            "chunk_index": i,      # Kaunsa chunk number
            "chunk_length": len(chunk)  # Chunk kitna lamba hai
        }
        for i, chunk in enumerate(chunks)
    ]

    # Embedding model lo
    embedding_model = get_embedding_model()

    # FAISS.from_texts() = Ek call mein sab karo:
    # 1. Har chunk ka embedding banao (text → numbers)
    # 2. FAISS index mein store karo
    # 3. Vectorstore object return karo
    #
    # Koi client setup nahi, koi tenant nahi, bas direct!
    vectorstore = FAISS.from_texts(
        texts=chunks,               # Hamare text chunks
        embedding=embedding_model,  # Embedding model
        metadatas=metadatas         # Extra info
    )

    print(f"✅ {len(chunks)} chunks FAISS mein save ho gaye!")

    # Vectorstore return karo
    # app.py isko st.session_state.vectorstore mein save karega
    # Wahi ek instance poori app mein use hoga
    return vectorstore


# ============================================
# MAIN FUNCTION — Sab ek saath
# ============================================

def ingest_pdf(pdf_path: str):
    """
    Master function — poori ingestion pipeline chalao.

    Yeh function call karo aur sab automatically hoga:
    PDF → Text → Smart Chunks → Vectors → FAISS → Return

    Parameter:
        pdf_path: PDF file ka disk pe path

    Returns:
        vectorstore: Ready-to-use FAISS vectorstore
    """

    print("\n" + "="*50)
    print("🚀 PDF Ingestion Pipeline shuru!")
    print("="*50)

    # PDF ka sirf filename nikalo (full path nahi)
    # os.path.basename("C:/Users/dhruv/contract.pdf") → "contract.pdf"
    filename = os.path.basename(pdf_path)

    # ── STEP 1: Text nikalo ──
    text = extract_text_from_pdf(pdf_path)

    # Safety check — agar text empty hai
    # Scanned image PDFs mein text nahi hota — OCR chahiye hota hai
    if not text.strip():
        raise ValueError(
            "❌ PDF mein koi text nahi mila!\n"
            "Scanned/image PDF hai? OCR tool use karo pehle."
        )

    # ── STEP 2: Smart Legal Chunks banao ──
    # Pehle legal clause structure try karo
    # Fail hone pe character chunking fallback
    chunks = split_by_legal_clauses(text)

    # ── STEP 3 + 4: Embed karo aur FAISS mein store karo ──
    vectorstore = store_in_faiss(chunks, filename)

    print("\n" + "="*50)
    print(f"✅ Ingestion complete!")
    print(f"   📄 File: {filename}")
    print(f"   📦 Chunks: {len(chunks)}")
    print(f"   🗄️  Vector DB: FAISS (in-memory)")
    print("="*50 + "\n")

    return vectorstore