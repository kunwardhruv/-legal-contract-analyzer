# ingestion.py
# YEH HAI HEART OF RAG!
# PDF → Chunks → Vectors → ChromaDB

import fitz  # PyMuPDF — PDF padhne ke liye
from langchain.text_splitter import RecursiveCharacterTextSplitter
# RecursiveCharacterTextSplitter — smartly text ko chunks mein todta hai
# "Recursive" kyun? Pehle paragraphs pe try karta hai split karne ki
# Phir sentences, phir words — smart splitting!

from langchain_huggingface import HuggingFaceEmbeddings
# HuggingFace ka free embedding model use karega
# Text → Numbers (vectors) convert karta hai

from langchain_chroma import Chroma
# ChromaDB ke saath baat karne ka interface

import config  # Hamari settings file
import os

# ============================================
# STEP 1: PDF SE TEXT NIKALO
# ============================================

def extract_text_from_pdf(pdf_path: str) -> str:
    
    print(f"📄 PDF padh raha hun: {pdf_path}")
    
    doc = fitz.open(pdf_path)
    
    # Pehle page count save karo — close karne SE PEHLE!
    total_pages = len(doc)
    
    full_text = ""
    
    for page_num in range(total_pages):
        page = doc[page_num]
        text = page.get_text()
        full_text += f"\n--- Page {page_num + 1} ---\n"
        full_text += text
    
    doc.close()
    
    # Ab saved variable use karo — doc.close() ke baad bhi kaam karega ✅
    print(f"✅ {total_pages} pages padh liye!")
    print(f"📝 Total characters: {len(full_text)}")
    
    return full_text


# ============================================
# STEP 2: TEXT KO CHUNKS MEIN TODO
# ============================================

def split_text_into_chunks(text: str) -> list:
    """
    Bada text → Chote chote chunks
    
    Kyu chunking zaroori hai?
    - Poora contract ek saath LLM ko nahi bhej sakte (expensive + inaccurate)
    - Chote chunks se accurate retrieval hoti hai
    - Sirf relevant chunk bhejo → better answers
    """
    
    print("✂️  Text ko chunks mein tod raha hun...")
    
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,         # 1000 characters per chunk
        chunk_overlap=config.CHUNK_OVERLAP,   # 200 char overlap
        
        # Kahan pe split kare — priority order mein:
        separators=[
            "\n\n",   # Pehle paragraphs pe try karo
            "\n",     # Phir lines pe
            ". ",     # Phir sentences pe
            " ",      # Phir words pe
            ""        # Last resort — anywhere
        ]
    )
    
    chunks = splitter.split_text(text)
    
    print(f"✅ {len(chunks)} chunks bane!")
    print(f"📊 Average chunk size: {sum(len(c) for c in chunks) // len(chunks)} chars")
    
    return chunks


# ============================================
# STEP 3: EMBEDDINGS BANAO (Text → Vectors)
# ============================================

def get_embedding_model():
    """
    HuggingFace embedding model load karo
    
    all-MiniLM-L6-v2 kyu?
    - Free hai (local run hota hai)
    - 80MB only — lightweight
    - 384-dimensional vectors banata hai
    - Legal text ke liye accurate enough
    - Most popular open-source embedding model
    
    Pehli baar: Model download hoga (~80MB)
    Baad mein: Cache se load hoga (fast!)
    """
    
    print("🔢 Embedding model load ho raha hai...")
    print("   (Pehli baar: ~80MB download hoga, wait karo!)")
    
    embeddings = HuggingFaceEmbeddings(
        model_name=config.EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},  # CPU pe chalao (GPU nahi chahiye)
        encode_kwargs={"normalize_embeddings": True}
        # normalize = vectors ko 0-1 range mein laao
        # Better similarity search ke liye
    )
    
    print("✅ Embedding model ready!")
    return embeddings


# ============================================
# STEP 4: CHROMADB MEIN SAVE KARO
# ============================================

def store_in_chromadb(chunks: list, filename: str) -> Chroma:
    """
    Chunks → Vectors banao → ChromaDB mein store karo
    
    ChromaDB kaise kaam karta hai:
    - Har chunk ka vector banata hai (using embedding model)
    - Vector + original text saath store karta hai
    - Similarity search ke liye optimized
    
    filename kyun save kar rahe hain?
    - Metadata ke roop mein
    - Pata chale ki yeh chunk kaunse document ka hai
    """
    
    print(f"🗄️  ChromaDB mein store kar raha hun...")
    
    # Metadata banao har chunk ke liye
    # Metadata = extra info jo chunk ke saath store hogi
    metadatas = [
        {
            "source": filename,
            "chunk_index": i,
        }
        for i, _ in enumerate(chunks)
    ]
    
    # Embedding model lo
    embedding_model = get_embedding_model()
    
    # ChromaDB mein store karo
    # Yeh automatically:
    # 1. Har chunk ka vector banayega
    # 2. Vector + text + metadata store karega
    vectorstore = Chroma.from_texts(
        texts=chunks,                          # Hamare chunks
        embedding=embedding_model,             # Embedding model
        metadatas=metadatas,                   # Extra info
        persist_directory=config.CHROMA_DB_PATH,  # Kahan save karo
        collection_name=config.COLLECTION_NAME    # Database ka naam
    )
    
    print(f"✅ {len(chunks)} chunks ChromaDB mein save ho gaye!")
    print(f"📁 Location: {config.CHROMA_DB_PATH}")
    
    return vectorstore


# ============================================
# MAIN FUNCTION — Sab ek saath
# ============================================

def ingest_pdf(pdf_path: str) -> Chroma:
    """
    Ek PDF lo aur poori pipeline chalao
    
    PDF Path → Extract → Split → Embed → Store → Return VectorStore
    """
    
    print("\n" + "="*50)
    print("🚀 PDF Ingestion Pipeline shuru!")
    print("="*50)
    
    # Filename nikalo path se
    filename = os.path.basename(pdf_path)
    
    # Step 1: Text nikalo
    text = extract_text_from_pdf(pdf_path)
    
    # Agar text nahi mila toh error
    if not text.strip():
        raise ValueError("❌ PDF mein koi text nahi mila! Scanned image PDF hai kya?")
    
    # Step 2: Chunks banao
    chunks = split_text_into_chunks(text)
    
    # Step 3 + 4: Embed karo aur store karo
    vectorstore = store_in_chromadb(chunks, filename)
    
    print("\n" + "="*50)
    print("✅ Ingestion complete! PDF ready for analysis!")
    print("="*50 + "\n")
    
    return vectorstore


def load_existing_vectorstore() -> Chroma:
    """
    Agar pehle se ChromaDB mein data save hai
    Toh dobara process mat karo — seedha load karo
    
    Yeh kyun zaroori hai?
    - Har baar PDF upload karne pe dobara process karna slow hai
    - ChromaDB persist karta hai (local file mein save rehta hai)
    - Sirf load karo aur use karo!
    """
    
    embedding_model = get_embedding_model()
    
    vectorstore = Chroma(
        persist_directory=config.CHROMA_DB_PATH,
        embedding_function=embedding_model,
        collection_name=config.COLLECTION_NAME
    )
    
    return vectorstore