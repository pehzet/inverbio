from pydantic import BaseModel, Field
from typing import List, Optional

class AgentResponseFormat(BaseModel):
    """
    Represents the format of the response from an agent.
    """
    response: str = Field(
        description="Antwort des Agenten in natürlicher Sprache."
    )
    suggestions: Optional[List[str]] = Field(
        default=None,
        description="Optionale Liste von potenziellen Anfragen, die der Benutzer stellen könnte. "
                    "Basierend auf dem aktuellen Kontext. Nur ausfüllen, wenn wirklich notwendig.",
        example=[
            "Zeige mir ähnliche Artikel.",
            "Ist das Produkt verfügbar?",
            "Ist das Produkt glutenfrei?",
            "Woher kommt der Erzeuger?",
        ],
    )
