from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
class AgentResponseFormat(BaseModel):
    """
    Represents the format of the response from an agent.
    """
    response: str = Field(description="Antwort des Agenten in natürlicher Sprache.")
    suggestions: List[str] = Field(
        default_factory=list,
        description="Liste von Aktionen oder Vorschlägen, die dem User vorgeschlagen werden können.",
    )
