# ⚖️ Legal Contract Analyzer

AI-powered legal contract review tool that automatically identifies
risky clauses and explains them in plain English.

## 🚀 Live Demo
[Click here to try it →](https://yhb7fsvwweywrnj36ufpkf.streamlit.app/)

## ✨ Features
- 📄 Upload any PDF contract (NDA, Employment, Lease, etc.)
- ⚖️ Smart legal clause detection — splits by "Section 1", "1.1", "Article 2" etc.
- 🔴 Automatically flags HIGH / MEDIUM / LOW risk clauses
- 🗣️ Plain English explanations — no legal jargon
- 💬 Chat with your contract — ask anything in Hindi or English
- ⚡ Powered by Groq (Llama 3.3 70B) — ultra fast & free

## 🛠️ Tech Stack
| Tool | Purpose |
|------|---------|
| LangChain | AI orchestration framework |
| Groq (Llama 3.3 70B) | LLM — Free & Ultra Fast |
| HuggingFace Embeddings | Text → Vectors (Free, Local) |
| FAISS | Vector database — in-memory, zero conflicts |
| PyMuPDF | PDF text extraction |
| Pydantic | Structured LLM output validation |
| Streamlit | Frontend UI + Deployment |

## 🏗️ Architecture
```
PDF Upload
    ↓
PyMuPDF — Text Extract
    ↓
Smart Legal Chunking — Split by "Section 1", "1.1", "Article 2"
    ↓
HuggingFace Embeddings — Text → Vectors (384 dimensions)
    ↓
FAISS — In-memory Vector Store
    ↓
User Question → Top 10 Relevant Chunks → Groq LLM
    ↓
Structured Risk Analysis (Pydantic)
```

## ⚙️ Local Setup

### 1. Clone karo
```bash
git clone https://github.com/kunwardhruv/-legal-contract-analyzer
cd -legal-contract-analyzer
```

### 2. Virtual environment
```bash
python -m venv venv
venv\Scripts\activate   # Windows
source venv/bin/activate # Mac/Linux
```

### 3. Dependencies install karo
```bash
pip install -r requirements.txt
```

### 4. API Key setup
```bash
# .env file banao aur yeh likho:
GROQ_API_KEY=your_groq_api_key_here
```
Free API key: [groq.com](https://groq.com)

### 5. Run karo
```bash
streamlit run app.py
```

## 📁 Project Structure
```
legal-contract-analyzer/
├── app.py              # Streamlit UI + Session State
├── ingestion.py        # PDF → Smart Chunks → FAISS
├── retrieval.py        # RAG + Risk Analysis + Chat
├── models.py           # Pydantic schemas (ClauseAnalysis, ContractSummary)
├── prompts.py          # LLM prompts
├── config.py           # Settings (chunk size, model names, etc.)
└── requirements.txt    # Dependencies
```

## 🧠 How It Works

1. **PDF Upload** — PyMuPDF se text extract hota hai
2. **Smart Chunking** — Regex se legal clause boundaries detect hoti hain
   - "1.", "1.1", "Section 2", "Article 3", "CLAUSE 4" pe split
   - Character-based fallback bhi available
3. **Embedding** — HuggingFace `all-MiniLM-L6-v2` se vectors banate hain
4. **FAISS** — In-memory vector store mein save hota hai
5. **Risk Analysis** — 8 common risky clause types ke liye search karta hai
6. **LLM** — Groq (Llama 3.3 70B) structured JSON output deta hai
7. **Chat** — Koi bhi question pooch sakte hain contract ke baare mein

## ⚠️ Disclaimer
This tool is for informational purposes only.
Always consult a qualified lawyer for legal advice.

---
Built with ❤️ using LangChain + Groq + FAISS