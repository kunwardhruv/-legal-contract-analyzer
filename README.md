# ⚖️ Legal Contract Analyzer

AI-powered legal contract review tool that automatically identifies 
risky clauses and explains them in plain English.

## 🚀 Live Demo
[Click here to try it →](YOUR_STREAMLIT_URL_YAHAN)

## ✨ Features
- 📄 Upload any PDF contract (NDA, Employment, Lease, etc.)
- 🔴 Automatically flags HIGH / MEDIUM / LOW risk clauses
- 🗣️ Plain English explanations — no legal jargon
- 💬 Chat with your contract — ask anything
- ⚡ Powered by Groq (Llama 3.3 70B) — ultra fast

## 🛠️ Tech Stack
| Tool | Purpose |
|------|---------|
| LangChain | AI orchestration framework |
| Groq (Llama 3.3 70B) | LLM — Free & Fast |
| HuggingFace Embeddings | Text → Vectors (Free, Local) |
| ChromaDB | Vector database |
| Streamlit | Frontend UI |
| PyMuPDF | PDF text extraction |

## 🏗️ Architecture
```
PDF Upload → PyMuPDF (extract) → LangChain Splitter (chunks)
→ HuggingFace Embeddings (vectors) → ChromaDB (store)
→ User Question → Retrieve chunks → Groq LLM → Risk Analysis
```

## ⚙️ Local Setup

### 1. Clone karo
```bash
git clone https://github.com/TERA_USERNAME/legal-contract-analyzer
cd legal-contract-analyzer
```

### 2. Virtual environment
```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux
```

### 3. Dependencies install karo
```bash
pip install -r requirements.txt
```

### 4. API Key setup
```bash
# .env file banao
GROQ_API_KEY=your_groq_api_key_here
```
Get free API key at: https://groq.com

### 5. Run karo
```bash
streamlit run app.py
```

## 📁 Project Structure
```
legal-contract-analyzer/
├── app.py              # Streamlit UI
├── ingestion.py        # PDF → ChromaDB pipeline
├── retrieval.py        # RAG + Risk Analysis
├── models.py           # Pydantic schemas
├── prompts.py          # LLM prompts
├── config.py           # Settings
└── requirements.txt    # Dependencies
```

## ⚠️ Disclaimer
This tool is for informational purposes only.
Always consult a qualified lawyer for legal advice.

---
Built with ❤️ using LangChain + Groq + ChromaDB
```

---

## 5.3 — GitHub Pe Repo Banao
```
1. github.com pe jaao
2. Login karo
3. Top right "+" icon → "New repository"
4. Repository name: legal-contract-analyzer
5. Description: AI-powered legal contract analyzer using RAG
6. Public select karo ✅ (portfolio ke liye)
7. README add mat karo (hamara apna hai)
8. "Create repository" click karo
```

**Repo banne ke baad ek page dikhega — wahan URL hoga:**
```
https://github.com/kunwardhruv/legal-contract-analyzer