# models.py
# Pydantic = Data ka blueprint/schema define karta hai
# Jab LLM jawab de, toh EXACTLY is format mein aana chahiye

from pydantic import BaseModel, Field
from typing import Literal

class ClauseAnalysis(BaseModel):
    """
    Ek single clause ka analysis
    LLM yahi format mein jawab dega
    """
    
    clause_type: str = Field(
        description="Clause ka type — jaise 'Non-Compete', 'Payment Terms', 'Termination'"
    )
    
    risk_level: Literal["HIGH", "MEDIUM", "LOW", "NEUTRAL"] = Field(
        description="Risk kitna hai is clause mein"
    )
    # Literal = sirf yeh 4 values allowed hain, kuch aur nahi
    
    risk_reason: str = Field(
        description="Kyu yeh risky hai — technical explanation"
    )
    
    plain_english: str = Field(
        description="Simple Hindi/English mein — aam aadmi samjhe"
    )
    
    original_text: str = Field(
        description="Contract ka actual text jo analyze kiya"
    )
    
    recommendation: str = Field(
        description="User ko kya karna chahiye — negotiate, accept, or reject"
    )


class ContractSummary(BaseModel):
    """
    Poore contract ka summary
    """
    
    contract_type: str = Field(
        description="Contract ka type — NDA, Employment, Lease, etc."
    )
    
    parties_involved: list[str] = Field(
        description="Contract mein kaun kaun involved hai"
    )
    
    key_dates: list[str] = Field(
        description="Important dates — start date, end date, deadlines"
    )
    
    overall_risk: Literal["HIGH", "MEDIUM", "LOW"] = Field(
        description="Overall contract kitna risky hai"
    )
    
    summary: str = Field(
        description="2-3 lines mein contract ka overview"
    )
    
    red_flags: list[str] = Field(
        description="Sabse important risky cheezein — list mein"
    )