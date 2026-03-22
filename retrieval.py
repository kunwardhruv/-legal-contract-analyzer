# ============================================
# RETRIEVAL.PY
# RAG ka BRAIN — Retrieval + Generation
#
# Yahan do kaam hote hain:
# 1. RETRIEVAL: User question se relevant chunks dhundo
# 2. GENERATION: Chunks + question → LLM → Answer
#
# Flow:
# User Question
#    ↓
# Question → Embedding (vector mein convert)
#    ↓
# FAISS mein similar vectors dhundo (top 10)
#    ↓
# Relevant chunks + question → LLM (Groq)
#    ↓
# Structured answer (Pydantic schema ke according)
# ============================================

from langchain_groq import ChatGroq
# ChatGroq = Groq API ke saath baat karne ka LangChain interface
# Groq kyu?
# → World's fastest LLM inference (seriously fast!)
# → Free tier mein generous limits
# → Llama 3.3 70B = GPT-4 level quality
# → LangChain ke saath native integration

from langchain_huggingface import HuggingFaceEmbeddings
# Same embedding model jo ingestion.py mein use kiya
# Consistency zaroori hai!
# Agar ingestion mein all-MiniLM-L6-v2 use kiya
# Toh retrieval mein bhi wahi use karo
# Warna vectors match nahi karenge!

from langchain.prompts import PromptTemplate
# PromptTemplate = Dynamic prompts banane ka tool
# Variables inject kar sakte ho: {context}, {question}
# Jaise: "Answer this: {question} based on: {context}"

from langchain_core.output_parsers import JsonOutputParser
# JsonOutputParser = LLM ke free text ko
# automatically Python dictionary mein convert karta hai
#
# Bina iske:
# LLM → "The risk level is HIGH because..."
#
# Iske saath:
# LLM → {"risk_level": "HIGH", "reason": "..."}
# ← Direct use kar sakte hain code mein!

from langchain_community.vectorstores import FAISS
# FAISS import — retrieval ke liye
# (Ingestion mein store kiya, yahan se retrieve karenge)

import config
# Settings file — model names, API keys, TOP_K_RESULTS etc.

from models import ClauseAnalysis, ContractSummary
# Pydantic models — LLM output ka blueprint
# ClauseAnalysis = ek clause ka analysis format
# ContractSummary = poore contract ka overview format

from prompts import CLAUSE_ANALYSIS_PROMPT, CONTRACT_SUMMARY_PROMPT, CHAT_PROMPT
# Saare LLM prompts alag file mein
# Kyu alag file? Prompts ko tune karna easy ho


# ============================================
# LLM SETUP
# ============================================

def get_llm():
    """
    Groq LLM initialize karo.

    Temperature kya hai?
    ─────────────────────────────────────────
    0.0 = Bilkul robotic, predictable
          "Risk level is HIGH." (always same)

    1.0 = Bahut creative, kabhi hallucinate karta hai
          "This clause might destroy the universe!"

    0.1 = Legal analysis ke liye perfect sweet spot
          Accurate + Consistent + Thoda natural
    ─────────────────────────────────────────

    max_tokens = Response kitna lamba ho sakta hai
    2048 = ~1500 words — analysis ke liye kaafi
    """

    llm = ChatGroq(
        api_key=config.GROQ_API_KEY,  # .env se aaya
        model=config.GROQ_MODEL,       # "llama-3.3-70b-versatile"
        temperature=0.1,               # Low = consistent legal analysis
        max_tokens=2048,               # Max response length
    )

    return llm


# ============================================
# HELPER — Chunks ko readable format mein convert karo
# ============================================

def format_docs(docs) -> str:
    """
    FAISS se retrieved Document objects ko
    ek clean readable string mein join karo.

    LLM ko exactly yeh format mein context milna chahiye:

    --- Section 1 ---
    ...clause text...

    --- Section 2 ---
    ...clause text...

    Kyu yeh format?
    → LLM clearly samjhe kahan ek chunk khatam hota hai
    → Alag alag sources clearly separated dikhein
    → LLM better context understanding kare

    Parameter:
        docs: List of LangChain Document objects
              (FAISS.similarity_search() se milte hain)

    Returns:
        formatted string ready to send to LLM
    """

    formatted = []
    for i, doc in enumerate(docs):
        # doc.page_content = actual text chunk
        formatted.append(f"--- Section {i+1} ---\n{doc.page_content}")

    # Sab ko blank line se join karo
    return "\n\n".join(formatted)


# ============================================
# CONTRACT SUMMARY
# ============================================

def get_contract_summary(pdf_text: str) -> dict:
    """
    Poore contract ka quick overview banao.

    Yeh function vectorstore use nahi karta!
    Direct PDF text se kaam karta hai.

    Kyu sirf pehle 3000 chars?
    → Summary ke liye poora contract padhna wasteful hai
    → Contract ke pehle 3000 chars mein usually hota hai:
       - Contract ka type (NDA/Employment/Lease)
       - Parties ke naam
       - Effective date
       - Main purpose
    → Token limit bhi save hoti hai (Groq free tier)

    Returns:
        dict with keys:
        - contract_type
        - parties_involved
        - key_dates
        - overall_risk
        - summary
        - red_flags
    """

    print("📋 Contract summary bana raha hun...")

    llm = get_llm()

    # JsonOutputParser setup
    # pydantic_object=ContractSummary → LLM ko exact format batata hai
    # get_format_instructions() → Returns JSON schema as string
    parser = JsonOutputParser(pydantic_object=ContractSummary)

    # PromptTemplate mein variables:
    # {contract_text} = PDF ka text
    # {format_instructions} = JSON format ka blueprint
    prompt = PromptTemplate(
        template=CONTRACT_SUMMARY_PROMPT + "\n\n{format_instructions}",
        input_variables=["contract_text"],
        partial_variables={
            "format_instructions": parser.get_format_instructions()
        }
    )

    # Chain = prompt | llm | parser
    # | operator = LCEL (LangChain Expression Language)
    #
    # Kya hota hai step by step:
    # 1. prompt.invoke({"contract_text": text}) → formatted prompt string
    # 2. llm.invoke(formatted_prompt) → LLM ka raw text response
    # 3. parser.invoke(raw_text) → Python dict
    chain = prompt | llm | parser

    result = chain.invoke({
        "contract_text": pdf_text[:3000]  # Sirf pehle 3000 chars
    })

    print("✅ Summary ready!")
    return result


# ============================================
# RISK ANALYSIS
# ============================================

def analyze_contract_risks(pdf_text: str, vectorstore) -> list:
    """
    Contract mein risky clauses dhundo aur analyze karo.

    Strategy:
    ─────────────────────────────────────────
    8 common risky clause types ke liye search karo
    Har type ke liye:
    1. FAISS se top 10 relevant chunks lo
    2. Top chunk = main clause
    3. Baaki chunks = context
    4. LLM se structured analysis lo
    ─────────────────────────────────────────

    Parameter:
        pdf_text: Raw PDF text (abhi use nahi hota, future ke liye)
        vectorstore: FAISS instance (session state se pass hota hai)
                     Kyu pass karte hain?
                     Agar yahan naya banate toh naya empty DB hota!
                     Session state wale mein actual data hai!

    Returns:
        analyses: List of ClauseAnalysis dicts
    """

    print("🔍 Risk analysis shuru kar raha hun...")

    llm = get_llm()
    parser = JsonOutputParser(pydantic_object=ClauseAnalysis)

    prompt = PromptTemplate(
        template=CLAUSE_ANALYSIS_PROMPT + "\n\n{format_instructions}",
        input_variables=["clause_text", "context"],
        partial_variables={
            "format_instructions": parser.get_format_instructions()
        }
    )

    # FAISS retriever banao
    # as_retriever() = FAISS ko LangChain retriever interface deta hai
    # search_type="similarity" = Cosine similarity use karo
    # k=10 = Top 10 most relevant chunks fetch karo
    #        Kyu 10? Legal clauses spread out hote hain
    #        Zyada chunks = zyada context = better analysis
    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": config.TOP_K_RESULTS}  # 10
    )

    # 8 common risky clause types
    # Yeh queries FAISS mein search hongi
    # FAISS inke similar chunks dhundhega contract se
    risky_clause_queries = [
        "non-compete clause employee restriction",      # Job ke baad restrictions
        "termination clause notice period",             # Contract todne ke rules
        "intellectual property ownership rights",       # IP kaun ka hai
        "confidentiality obligation duration",          # Secret kab tak rakhna hai
        "liquidated damages penalty",                   # Breach pe penalty
        "governing law jurisdiction dispute",           # Kahan case chalega
        "indemnification liability clause",             # Liability rules
        "payment terms late fees penalty",              # Payment ke rules
    ]

    analyses = []

    for query in risky_clause_queries:
        print(f"   🔎 Dhundh raha hun: {query}")
        try:
            # FAISS se similar chunks lo
            relevant_docs = retriever.invoke(query)

            if relevant_docs:
                # Sab chunks ko readable format mein join karo
                context = format_docs(relevant_docs)

                # Pehla (most relevant) chunk = main clause for analysis
                main_chunk = relevant_docs[0].page_content

                # LLM chain chalao
                # prompt → llm → parser → dict
                result = (prompt | llm | parser).invoke({
                    "clause_text": main_chunk,  # Main clause
                    "context": context           # Additional context
                })

                analyses.append(result)

        except Exception as e:
            # Ek clause fail ho toh skip karo — baaki continue karo
            # Kyu? Agar ek query fail ho toh poori analysis nahi rukni chahiye
            print(f"   ⚠️  Skip kiya ({query}): {e}")
            continue

    print(f"✅ {len(analyses)} clauses analyze ho gaye!")
    return analyses


# ============================================
# CHAT FUNCTION
# ============================================

def chat_with_contract(question: str, vectorstore) -> str:
    """
    User koi bhi question pooch sakta hai contract ke baare mein.

    Yeh simple RAG hai:
    Question → FAISS search → Relevant chunks → LLM → Answer

    Parameter:
        question: User ka sawaal (Hindi ya English)
        vectorstore: FAISS instance (session state se)
                     Same instance use karo!
                     Naya banate toh data nahi hota!

    Returns:
        response.content: LLM ka answer string
    """

    print(f"\n💬 Question: {question}")

    llm = get_llm()

    # Same FAISS vectorstore se retriever
    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": config.TOP_K_RESULTS}  # Top 10 chunks
    )

    prompt = PromptTemplate(
        template=CHAT_PROMPT,
        input_variables=["context", "question"]
    )

    # Step 1: Question se relevant chunks dhundo
    relevant_docs = retriever.invoke(question)

    # Step 2: Chunks ko readable format mein convert karo
    context = format_docs(relevant_docs)

    # Step 3: LLM ko bhejo
    # Note: Yahan parser nahi use kar rahe
    # Kyu? Chat mein free text answer chahiye, JSON nahi
    chain = prompt | llm

    response = chain.invoke({
        "context": context,
        "question": question
    })

    # ChatGroq response = AIMessage object hota hai
    # .content se actual text string milta hai
    return response.content