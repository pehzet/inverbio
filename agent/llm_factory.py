from langchain_openai import ChatOpenAI
from typing import Literal

Provider = Literal["openai"]
Model = Literal["gpt-4o-mini"]
def get_llm(provider: Provider, model: Model) -> ChatOpenAI:
    if provider == "openai":
        return ChatOpenAI(model=model)
    else:
        raise NotImplementedError(f"Provider {provider} not implemented")
    