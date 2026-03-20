# retrieval.py
# RAG ka BRAIN — Retrieval + Generation dono yahan hain

from langchain_groq import ChatGroq
# ChatGroq = Groq API ke saath baat karne ka interface
# Groq = Free + Ultra fast LLM API

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain.prompts import PromptTemplate
# PromptTemplate = Dynamic prompts banane ke liye
# Variables inject kar sakte ho: {context}, {question}

from langchain_core.output_parsers import JsonOutputParser
# JsonOutputParser = LLM ke text response ko
# automatically Python dict/object mein convert karta hai

from langchain_core.runnables import RunnablePassthrough
# RunnablePassthrough = Data ko chain mein aage pass karta hai
# LangChain Expression Language (LCEL) ka part hai

import config
from models import ClauseAnalysis, ContractSummary
from prompts import CLAUSE_ANALYSIS_PROMPT, CONTRACT_SUMMARY_PROMPT, CHAT_PROMPT


# ============================================
# STEP 1: LLM SETUP (GROQ)
# ============================================

def get_llm():
    """
    Groq LLM setup karo

    ChatGroq kyu?
    - Groq = World's fastest LLM inference
    - Free tier mein generous limits
    - Llama 3.3 70B = GPT-4 level quality
    - LangChain ke saath native integration

    temperature=0.1 kyu?
    - Temperature = LLM ki "creativity"
    - 0.0 = Bilkul predictable, robotic
    - 1.0 = Bahut creative, kabhi kabhi hallucinate
    - 0.1 = Legal analysis ke liye perfect
            Accurate + consistent answers
            Thoda variation allowed
    """

    llm = ChatGroq(
        api_key=config.GROQ_API_KEY,
        model=config.GROQ_MODEL,
        temperature=0.1,
        max_tokens=2048,  # Max response length
    )

    return llm


# ============================================
# STEP 2: VECTORSTORE LOAD KARO
# ============================================

def get_vectorstore():
    
    embedding_model = HuggingFaceEmbeddings(
        model_name=config.EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True}
    )
    
    import os
    if os.path.exists("/mount/src"):
        # Cloud — in-memory
        vectorstore = Chroma(
            embedding_function=embedding_model,
            collection_name=config.COLLECTION_NAME
        )
    else:
        # Local — persistent
        vectorstore = Chroma(
            persist_directory=config.CHROMA_DB_PATH,
            embedding_function=embedding_model,
            collection_name=config.COLLECTION_NAME
        )
    
    return vectorstore


# ============================================
# STEP 3: RETRIEVER BANAO
# ============================================

def get_retriever():
    """
    Retriever = ChromaDB se relevant chunks dhundne wala

    search_type="similarity" kyu?
    - Cosine similarity use karta hai
    - Question vector aur chunk vectors compare karta hai
    - Most similar chunks return karta hai

    k=5 kyu?
    - Top 5 chunks bhejo LLM ko
    - Kam bhejo → Context kam → Poor answers
    - Zyada bhejo → Expensive + Confusing
    - 5 = Sweet spot for legal docs
    """

    vectorstore = get_vectorstore()

    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": config.TOP_K_RESULTS}
    )

    return retriever


# ============================================
# STEP 4: CONTEXT FORMAT KARO
# ============================================

def format_docs(docs) -> str:
    """
    Retrieved chunks ko ek clean string mein join karo

    LLM ko aise bhejenge:
    --- Chunk 1 ---
    ...text...

    --- Chunk 2 ---
    ...text...

    Kyu format karo?
    - LLM clearly samjhe kahan ek chunk khatam hota hai
    - Better context understanding
    """

    formatted = []
    for i, doc in enumerate(docs):
        formatted.append(f"--- Section {i+1} ---\n{doc.page_content}")

    return "\n\n".join(formatted)


# ============================================
# STEP 5: CONTRACT SUMMARY
# ============================================

def get_contract_summary(pdf_text: str) -> ContractSummary:
    """
    Poore contract ka overview banao

    Yeh function:
    1. Contract ke pehle 3000 chars lo (overview ke liye kaafi)
    2. LLM ko summary prompt ke saath bhejo
    3. Structured ContractSummary object return karo
    """

    print("📋 Contract summary bana raha hun...")

    llm = get_llm()

    # JsonOutputParser batata hai LLM ko —
    # "Sirf JSON mein jawab do, kuch aur mat likho"
    parser = JsonOutputParser(pydantic_object=ContractSummary)

    # PromptTemplate mein variables inject karte hain
    prompt = PromptTemplate(
        template=CONTRACT_SUMMARY_PROMPT + "\n\n{format_instructions}",
        input_variables=["contract_text"],
        partial_variables={
            "format_instructions": parser.get_format_instructions()
        }
    )

    # Chain banao: Prompt → LLM → Parser
    # | operator = LangChain Expression Language (LCEL)
    # Matlab: pehle prompt banao, phir LLM ko bhejo,
    #         phir output parse karo
    chain = prompt | llm | parser

    # Pehle 3000 chars — summary ke liye kaafi hai
    result = chain.invoke({
        "contract_text": pdf_text[:3000]
    })

    print("✅ Summary ready!")
    return result


# ============================================
# STEP 6: CLAUSE RISK ANALYSIS — MAIN FUNCTION
# ============================================

def analyze_contract_risks(pdf_text: str) -> list:
    """
    Contract ke risky clauses dhundo aur analyze karo

    Strategy:
    - Specific legal clause types ke liye search karo
    - Har type ke liye RAG karo
    - Risk analysis return karo
    """

    print("🔍 Risk analysis shuru kar raha hun...")

    llm = get_llm()
    retriever = get_retriever()
    parser = JsonOutputParser(pydantic_object=ClauseAnalysis)

    prompt = PromptTemplate(
        template=CLAUSE_ANALYSIS_PROMPT + "\n\n{format_instructions}",
        input_variables=["clause_text", "context"],
        partial_variables={
            "format_instructions": parser.get_format_instructions()
        }
    )

    # Jin clauses ke liye search karenge
    # Yeh common risky clauses hain legal contracts mein
    risky_clause_queries = [
        "non-compete clause employee restriction",
        "termination clause notice period",
        "intellectual property ownership rights",
        "confidentiality obligation duration",
        "liquidated damages penalty",
        "governing law jurisdiction dispute",
        "indemnification liability clause",
        "payment terms late fees penalty",
    ]

    analyses = []

    for query in risky_clause_queries:
        print(f"   🔎 Dhundh raha hun: {query}")

        # ChromaDB se relevant chunks lo
        relevant_docs = retriever.invoke(query)

        # Agar koi relevant chunk mila toh analyze karo
        if relevant_docs:
            context = format_docs(relevant_docs)

            # Top relevant chunk ko main clause maano
            main_chunk = relevant_docs[0].page_content

            try:
                # LLM se analysis lo
                result = (prompt | llm | parser).invoke({
                    "clause_text": main_chunk,
                    "context": context
                })

                analyses.append(result)

            except Exception as e:
                # Agar ek clause fail ho toh
                # baaki ko rokna nahi chahiye
                print(f"   ⚠️  Skip kiya ({query}): {e}")
                continue

    print(f"✅ {len(analyses)} clauses analyze ho gaye!")
    return analyses


# ============================================
# STEP 7: CHAT FUNCTION — Q&A
# ============================================

def chat_with_contract(question: str, chat_history: list = []) -> str:
    """
    User koi bhi question pooch sakta hai contract ke baare mein

    Simple RAG chain:
    Question → Retrieve chunks → LLM → Answer

    chat_history kyu?
    - Future mein multi-turn conversation ke liye
    - Abhi simple Q&A hai
    """

    print(f"\n💬 Question: {question}")

    retriever = get_retriever()
    llm = get_llm()

    prompt = PromptTemplate(
        template=CHAT_PROMPT,
        input_variables=["context", "question"]
    )

    # Retrieved docs ko format karo
    relevant_docs = retriever.invoke(question)
    context = format_docs(relevant_docs)

    # Chain chalao
    chain = prompt | llm

    response = chain.invoke({
        "context": context,
        "question": question
    })

    # ChatGroq response mein .content se text milta hai
    return response.content