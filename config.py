# config.py

from dotenv import load_dotenv
import os

load_dotenv()

# Groq Settings
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama-3.3-70b-versatile"

# Embedding Model
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# ChromaDB Settings
CHROMA_DB_PATH = "./chroma_db"
COLLECTION_NAME = "legal_contracts"

# Chunking Settings
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# Retrieval Settings
TOP_K_RESULTS = 5