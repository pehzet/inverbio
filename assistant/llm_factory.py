from langchain_openai import ChatOpenAI
from typing import Literal

Provider = Literal["openai"]
Model = Literal["gpt-5-mini"]
def get_llm(provider: Provider, model: Model) -> ChatOpenAI:
    if provider == "openai":

        if model.startswith("gpt-5"):
            # apply reasoning because gpt-5 is a reasoning model
            reasoning = {"effort": "low"}
            return ChatOpenAI(model=model, reasoning=reasoning)
        else:
            return ChatOpenAI(model=model)
    else:
        raise NotImplementedError(f"Provider {provider} not implemented")
    