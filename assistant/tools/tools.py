from langchain.tools import Tool
from assistant.rag.rag_factory import get_vector_store
from langchain.tools.retriever import create_retriever_tool
from langgraph.prebuilt import ToolNode
from assistant.tools.farmely.farmely_api_langchain import fetch_product_stock
from assistant.tools.internal.get_product_information import get_product_information_by_id
from assistant.tools.internal.get_producer_information import get_producer_information_by_identifier
def get_retriever_tool(tool_name:str, db:str, **kwargs) -> Tool:
    if tool_name == "retrieve_products":
        retriever = get_vector_store(db, **kwargs)
        retriever_tool = create_retriever_tool(
            retriever,
            "retrieve_products",
            "Search for food products that Farmely sells and get information about them.",
        )
        return retriever_tool
    else:
        raise ValueError(f"Tool '{tool_name}' not recognized.")



def get_tool(name:str, **kwargs) -> Tool:

    if name == "retrieve_products":
        return get_retriever_tool(name, **kwargs)
    elif name == "fetch_product_stock":
        return fetch_product_stock
    elif name == "get_product_information_by_id":
        return get_product_information_by_id
    elif name == "get_producer_information_by_identifier":
        return get_producer_information_by_identifier
    else:
        raise ValueError(f"Tool '{name}' not recognized.")
    
def get_farmely_tools() -> list[Tool]:
    tools = [
        get_tool("retrieve_products", db="chroma", CHROMA_PRODUCT_DB="chroma_products"),
        get_tool("fetch_product_stock"),
        get_tool("get_product_information_by_id"),
        get_tool("get_producer_information_by_identifier"),
    ]
    return tools

if __name__ == "__main__":

    rag = get_retriever_tool("retrieve_products")
    result = rag.invoke("Duetto Kakao")
    print(result)
