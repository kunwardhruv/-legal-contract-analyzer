# ingestion.py
# PDF → Text → Chunks → Vectors → ChromaDB
# Yeh hai RAG ka HEART!

import fitz  # PyMuPDF — PDF se text nikalne ke liye
from langchain.text_splitter import RecursiveCharacterTextSplitter
# RecursiveCharacterTextSplitter — text ko smartly chunks mein todta hai
# "Recursive" kyun? Priority order mein split karta hai:
# Pehle paragraphs → phir lines → phir sentences → phir words

from langchain_huggingface import HuggingFaceEmbeddings
# HuggingFace ka free local embedding model
# Text → Numbers (vectors) convert karta hai
# "Meaning" ko numbers mein represent karta hai

from langchain_chroma import Chroma
# ChromaDB ke saath baat karne ka LangChain interface
# Vectors store aur search karta hai

import config
import os
import chromadb


# ============================================
# STEP 1: PDF SE TEXT NIKALO
# ============================================

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    PDF file kholo aur saara text nikalo
    PyMuPDF kyu? — Fastest Python PDF library
    Legal PDFs mein complex formatting hoti hai, yeh sab handle karta hai
    """

    print(f"📄 PDF padh raha hun: {pdf_path}")

    doc = fitz.open(pdf_path)  # PDF file kholo

    # IMPORTANT: total_pages PEHLE save karo
    # doc.close() ke baad len(doc) call nahi kar sakte
    total_pages = len(doc)

    full_text = ""

    # Har page pe jaao aur text nikalo
    for page_num in range(total_pages):
        page = doc[page_num]
        text = page.get_text()  # Page ka text nikalo

        # Page number bhi add karo — baad mein helpful hoga
        full_text += f"\n--- Page {page_num + 1} ---\n"
        full_text += text

    doc.close()  # File band karo — memory free karo

    print(f"✅ {total_pages} pages padh liye!")
    print(f"📝 Total characters: {len(full_text)}")

    return full_text


# ============================================
# STEP 2: TEXT KO CHUNKS MEIN TODO
# ============================================

def split_text_into_chunks(text: str) -> list:
    """
    Bada text → Chote chote pieces (chunks)

    Kyu chunking zaroori hai?
    Problem: Poora contract (50,000 words) ek saath LLM ko bhejne pe:
    → Bahut expensive (tokens = paise)
    → LLM "lost in middle" — beech ka content bhool jaata hai
    → Slow response

    Solution: Sirf RELEVANT chunks bhejo
    User question → similar chunks dhundo → sirf woh bhejo → fast + cheap + accurate!
    """

    print("✂️  Text ko chunks mein tod raha hun...")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,       # Max 1000 chars per chunk
        chunk_overlap=config.CHUNK_OVERLAP, # 200 chars overlap — context nahi toota

        # Split priority order — pehle bada, phir chota
        separators=[
            "\n\n",  # Pehle paragraphs pe try karo (best split point)
            "\n",    # Phir line breaks pe
            ". ",    # Phir sentences pe
            " ",     # Phir words pe
            ""       # Last resort — kahi bhi
        ]
    )

    chunks = splitter.split_text(text)

    print(f"✅ {len(chunks)} chunks bane!")
    print(f"📊 Average chunk size: {sum(len(c) for c in chunks) // len(chunks)} chars")

    return chunks


# ============================================
# STEP 3: EMBEDDING MODEL LOAD KARO
# ============================================

def get_embedding_model():
    """
    HuggingFace ka free embedding model load karo

    Embedding kya hai?
    "Non-compete clause" → [0.23, -0.87, 0.45, ... 384 numbers]
    "Employee restriction" → [0.21, -0.85, 0.43, ...]  ← similar numbers!
    Similar meaning = similar numbers = ChromaDB dhundh sakta hai!

    all-MiniLM-L6-v2 kyu?
    → Free hai — local machine pe run hota hai
    → Sirf 80MB — lightweight
    → 384-dimensional vectors — accurate enough for legal text
    → Sabse popular open-source embedding model

    Pehli baar: ~80MB download hoga
    Baar baar: Cache se load hoga — fast!
    """

    print("🔢 Embedding model load ho raha hai...")
    print("   (Pehli baar: ~80MB download hoga, wait karo!)")

    embeddings = HuggingFaceEmbeddings(
        model_name=config.EMBEDDING_MODEL,          # "all-MiniLM-L6-v2"
        model_kwargs={"device": "cpu"},              # CPU pe chalao — GPU nahi chahiye
        encode_kwargs={"normalize_embeddings": True} # Vectors 0-1 range mein — better search
    )

    print("✅ Embedding model ready!")
    return embeddings


# ============================================
# STEP 4: CHROMADB MEIN STORE KARO
# ============================================

def store_in_chromadb(chunks: list, filename: str):
    
    print(f"🗄️  ChromaDB mein store kar raha hun...")
    
    metadatas = [
        {"source": filename, "chunk_index": i}
        for i, _ in enumerate(chunks)
    ]
    
    embedding_model = get_embedding_model()
    
    # Har baar BILKUL naya fresh client banao
    # Yahi asli fix hai — purana client reuse nahi hoga
    fresh_client = chromadb.EphemeralClient()
    
    vectorstore = Chroma(
        client=fresh_client,
        collection_name="legal_contracts",
        embedding_function=embedding_model,
    )
    
    # Chunks add karo
    vectorstore.add_texts(
        texts=chunks,
        metadatas=metadatas
    )
    
    print(f"✅ {len(chunks)} chunks store ho gaye!")
    return vectorstore
# ============================================
# MAIN FUNCTION — Upar sab ek saath
# ============================================

def ingest_pdf(pdf_path: str):
    """
    Ek PDF path lo → poori pipeline chalao → vectorstore return karo

    Flow:
    PDF file → Text nikalo → Chunks banao → Vectors banao → ChromaDB → Return
    """

    print("\n" + "="*50)
    print("🚀 PDF Ingestion Pipeline shuru!")
    print("="*50)

    filename = os.path.basename(pdf_path)  # "contract.pdf" nikalo full path se

    # Step 1: PDF se text nikalo
    text = extract_text_from_pdf(pdf_path)

    # Safety check — agar text empty hai toh scanned PDF hai
    if not text.strip():
        raise ValueError("❌ PDF mein koi text nahi mila! Scanned image PDF ho sakti hai.")

    # Step 2: Text → Chunks
    chunks = split_text_into_chunks(text)

    # Step 3 + 4: Chunks → Vectors → ChromaDB
    vectorstore = store_in_chromadb(chunks, filename)

    print("\n" + "="*50)
    print("✅ Ingestion complete! PDF ready for analysis!")
    print("="*50 + "\n")

    # Vectorstore return karo — app.py isko session state mein save karega
    return vectorstore