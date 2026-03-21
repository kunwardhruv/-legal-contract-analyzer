# retrieval.py
# RAG ka BRAIN — Retrieval + Generation dono yahan hain
#
# Flow:
# User question → Vectorstore se chunks dhundo → LLM ko bhejo → Answer lo

from langchain_groq import ChatGroq
# ChatGroq = Groq API ke saath baat karne ka LangChain interface
# Groq = World's fastest LLM inference, free tier available

from langchain_huggingface import HuggingFaceEmbeddings
# Same embedding model jo ingestion mein use kiya
# Question ko bhi vector mein convert karta hai search ke liye

from langchain.prompts import PromptTemplate
# PromptTemplate = Dynamic prompts — variables inject kar sakte ho
# Jaise: {context} mein chunks aur {question} mein user ka sawaal

from langchain_core.output_parsers import JsonOutputParser
# JsonOutputParser = LLM ke text response ko automatically
# Python dictionary mein convert karta hai
# Bina iske LLM free text deta hai — parse karna mushkil hota


from langchain_chroma import Chroma


import config
from models import ClauseAnalysis, ContractSummary
from prompts import CLAUSE_ANALYSIS_PROMPT, CONTRACT_SUMMARY_PROMPT, CHAT_PROMPT


# ============================================
# LLM SETUP
# ============================================

def get_llm():
    """
    Groq LLM initialize karo

    Temperature = LLM ki "creativity" setting
    0.0 = Bilkul predictable, robotic jawab
    1.0 = Bahut creative, kabhi kabhi hallucinate karta hai
    0.1 = Legal analysis ke liye perfect:
          Accurate + consistent + thoda natural
    """

    llm = ChatGroq(
        api_key=config.GROQ_API_KEY,
        model=config.GROQ_MODEL,     # "llama-3.3-70b-versatile"
        temperature=0.1,              # Low = consistent legal analysis
        max_tokens=2048,              # Max response length
    )

    return llm


# ============================================
# HELPER — Chunks ko readable format mein
# ============================================

def format_docs(docs) -> str:
    """
    Retrieved chunks ko ek clean string mein join karo

    LLM ko clear context milna chahiye:
    --- Section 1 ---
    ...text...

    --- Section 2 ---
    ...text...

    Kyu? LLM clearly samjhe kahan ek chunk khatam hota hai
    """

    formatted = []
    for i, doc in enumerate(docs):
        formatted.append(f"--- Section {i+1} ---\n{doc.page_content}")

    return "\n\n".join(formatted)


# ============================================
# CONTRACT SUMMARY
# ============================================

def get_contract_summary(pdf_text: str) -> dict:
    """
    Poore contract ka overview banao

    Kyu sirf pehle 3000 chars?
    Summary ke liye poora contract padhna zaroori nahi
    Pehle 3000 chars mein usually:
    → Contract type
    → Parties ka naam
    → Effective date
    → Main purpose
    ...sab hota hai
    """

    print("📋 Contract summary bana raha hun...")

    llm = get_llm()

    # JsonOutputParser — LLM ko force karta hai structured JSON dene ke liye
    # ContractSummary = Pydantic model (models.py mein defined)
    # get_format_instructions() = LLM ko exact format batata hai
    parser = JsonOutputParser(pydantic_object=ContractSummary)

    prompt = PromptTemplate(
        template=CONTRACT_SUMMARY_PROMPT + "\n\n{format_instructions}",
        input_variables=["contract_text"],
        partial_variables={
            "format_instructions": parser.get_format_instructions()
            # Yeh LLM ko batata hai: "Sirf is JSON format mein jawab do"
        }
    )

    # Chain = prompt | llm | parser
    # | operator = LCEL (LangChain Expression Language)
    # Matlab: pehle prompt banao → LLM ko bhejo → output parse karo
    chain = prompt | llm | parser

    result = chain.invoke({
        "contract_text": pdf_text[:3000]  # Sirf pehle 3000 chars bhejo
    })

    print("✅ Summary ready!")
    return result


# ============================================
# RISK ANALYSIS — MAIN FUNCTION
# ============================================

def analyze_contract_risks(pdf_text: str, vectorstore) -> list:
    """
    Contract ke risky clauses dhundo aur analyze karo

    vectorstore PARAMETER kyu?
    Pehle get_vectorstore() use karte the — naya ChromaDB banata tha
    Problem: Naya instance = alag RAM location = "tenant not found" error!
    Solution: app.py se wahi vectorstore pass karo jo ingest_pdf ne banaya
              Ek hi instance = koi confusion nahi!

    Strategy:
    Common risky clause types ke liye search karo
    Har type ke liye top chunks lo → LLM se analyze karo
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

    # Pass kiye hue vectorstore se retriever banao
    # Yahi fix hai — naya instance nahi, wahi purana use karo
    retriever = vectorstore.as_retriever(
        search_type="similarity",           # Cosine similarity use karo
        search_kwargs={"k": config.TOP_K_RESULTS}  # Top 5 chunks lo
    )

    # Common risky clauses — inke liye search karenge
    # Legal contracts mein yeh clauses usually problematic hote hain
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
        try:
            # Step 1: ChromaDB se similar chunks dhundo
            relevant_docs = retriever.invoke(query)

            if relevant_docs:
                # Step 2: Chunks ko readable format mein convert karo
                context = format_docs(relevant_docs)

                # Step 3: Sabse relevant chunk = main clause
                main_chunk = relevant_docs[0].page_content

                # Step 4: LLM se analyze karo
                result = (prompt | llm | parser).invoke({
                    "clause_text": main_chunk,
                    "context": context
                })

                analyses.append(result)

        except Exception as e:
            # Ek clause fail ho toh baaki rukna nahi chahiye
            # Skip karo aur aage badho
            print(f"   ⚠️  Skip kiya ({query}): {e}")
            continue

    print(f"✅ {len(analyses)} clauses analyze ho gaye!")
    return analyses


# ============================================
# CHAT FUNCTION
# ============================================

def chat_with_contract(question: str, vectorstore) -> str:
    """
    User koi bhi question pooch sakta hai contract ke baare mein

    vectorstore PARAMETER kyu?
    Same reason as above — ek hi instance use karo
    app.py session state se pass karta hai

    Simple RAG flow:
    Question → Retrieve relevant chunks → LLM ko bhejo → Answer lo
    """

    print(f"\n💬 Question: {question}")

    llm = get_llm()

    # Same vectorstore — naya instance nahi bana rahe
    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": config.TOP_K_RESULTS}
    )

    prompt = PromptTemplate(
        template=CHAT_PROMPT,
        input_variables=["context", "question"]
    )

    # Step 1: Question se relevant chunks dhundo
    relevant_docs = retriever.invoke(question)

    # Step 2: Chunks format karo
    context = format_docs(relevant_docs)

    # Step 3: LLM ko bhejo
    chain = prompt | llm

    response = chain.invoke({
        "context": context,
        "question": question
    })

    # ChatGroq response object hota hai — .content se actual text milta hai
    return response.content