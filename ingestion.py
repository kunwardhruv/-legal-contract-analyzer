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

from langchain_chroma import Chroma
# ChromaDB ke saath LangChain ka interface

import chromadb
# chromadb directly import karo — EphemeralClient ke liye
# EphemeralClient = Pure in-memory, fresh client har baar
# Yahi hai asli fix — global client nahi, fresh client!

import config
import os


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

    doc = fitz.open(pdf_path)

    # IMPORTANT: total_pages PEHLE save karo
    # doc.close() ke baad len(doc) call nahi kar sakte
    total_pages = len(doc)

    full_text = ""

    for page_num in range(total_pages):
        page = doc[page_num]
        text = page.get_text()

        # Page number bhi add karo — baad mein helpful hoga
        full_text += f"\n--- Page {page_num + 1} ---\n"
        full_text += text

    doc.close()

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
    → Poora contract ek saath LLM ko nahi bhej sakte (expensive + slow)
    → Chote chunks se accurate retrieval hoti hai
    → Sirf relevant chunk bhejo → better answers
    """

    print("✂️  Text ko chunks mein tod raha hun...")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,       # Max 1000 chars per chunk
        chunk_overlap=config.CHUNK_OVERLAP, # 200 chars overlap — context nahi toota
        separators=[
            "\n\n",  # Pehle paragraphs pe try karo
            "\n",    # Phir line breaks pe
            ". ",    # Phir sentences pe
            " ",     # Phir words pe
            ""       # Last resort
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

    all-MiniLM-L6-v2 kyu?
    → Free hai — local machine pe run hota hai
    → Sirf 80MB — lightweight
    → 384-dimensional vectors — accurate enough for legal text
    → Sabse popular open-source embedding model
    """

    print("🔢 Embedding model load ho raha hai...")

    embeddings = HuggingFaceEmbeddings(
        model_name=config.EMBEDDING_MODEL,           # "all-MiniLM-L6-v2"
        model_kwargs={"device": "cpu"},               # CPU pe chalao
        encode_kwargs={"normalize_embeddings": True}  # Better similarity search
    )

    print("✅ Embedding model ready!")
    return embeddings


# ============================================
# STEP 4: CHROMADB MEIN STORE KARO
# ============================================

def store_in_chromadb(chunks: list, filename: str):
    """
    Chunks → Vectors → ChromaDB mein store karo

    EphemeralClient kyu?
    Pehle Chroma.from_texts() directly use karte the
    Problem: Global ChromaDB client reuse hota tha
             Dusri PDF upload pe same tenant → "tenant not found" error!

    Fix: EphemeralClient() = Bilkul naya fresh client har baar
         Koi global state nahi = koi conflict nahi = koi error nahi! ✅

    EphemeralClient = In-memory = Cloud pe bhi kaam karta hai
    """

    print(f"🗄️  ChromaDB mein store kar raha hun...")

    # Har chunk ke saath metadata store karo
    # Kyu? Baad mein pata chale ki chunk kaunse file ka hai
    metadatas = [
        {
            "source": filename,   # Kaunsi file se aaya
            "chunk_index": i      # Kaunsa chunk number hai
        }
        for i, _ in enumerate(chunks)
    ]

    embedding_model = get_embedding_model()

    # EphemeralClient = Bilkul fresh in-memory ChromaDB client
    # Har PDF upload pe naya client → koi tenant conflict nahi
    # Yeh key fix hai jo dono PDFs ko kaam karwata hai!
    fresh_client = chromadb.EphemeralClient()

    vectorstore = Chroma(
        client=fresh_client,                          # Fresh client — no conflicts!
        collection_name=config.COLLECTION_NAME,       # Collection ka naam
        embedding_function=embedding_model,           # Embedding model
    )

    # Chunks add karo vectorstore mein
    vectorstore.add_texts(
        texts=chunks,
        metadatas=metadatas
    )

    print(f"✅ {len(chunks)} chunks ChromaDB mein save ho gaye!")

    # Vectorstore return karo — app.py session state mein save karega
    # Yahi ek instance poori app mein use hoga
    return vectorstore


# ============================================
# MAIN FUNCTION — Sab ek saath
# ============================================

def ingest_pdf(pdf_path: str):
    """
    Ek PDF path lo → poori pipeline chalao → vectorstore return karo

    Flow:
    PDF → Text nikalo → Chunks banao → Vectors banao → ChromaDB → Return
    """

    print("\n" + "="*50)
    print("🚀 PDF Ingestion Pipeline shuru!")
    print("="*50)

    filename = os.path.basename(pdf_path)

    # Step 1: PDF se text nikalo
    text = extract_text_from_pdf(pdf_path)

    # Safety check
    if not text.strip():
        raise ValueError("❌ PDF mein koi text nahi mila! Scanned image PDF ho sakti hai.")

    # Step 2: Text → Chunks
    chunks = split_text_into_chunks(text)

    # Step 3 + 4: Chunks → Vectors → ChromaDB (EphemeralClient)
    vectorstore = store_in_chromadb(chunks, filename)

    print("\n" + "="*50)
    print("✅ Ingestion complete! PDF ready for analysis!")
    print("="*50 + "\n")

    return vectorstore