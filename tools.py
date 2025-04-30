from langchain.tools import Tool
from rag_factory import get_vector_store
from langchain.tools.retriever import create_retriever_tool
from langgraph.prebuilt import ToolNode
def get_retriever_tool(tool_name:str) -> Tool:
    if tool_name == "retrieve_products":
        retriever = get_vector_store("chroma_db")
        retriever_tool = create_retriever_tool(
            retriever,
            "retrieve_products",
            "Search for food products that Farmely sells and get information about them.",
        )
        return retriever_tool
    else:
        raise ValueError(f"Tool '{tool_name}' not recognized.")



def get_tool(name:str) -> Tool:
    if name == "retrieve_products":
        return get_retriever_tool(name)
    elif name == "fetch_product_stock":
        from farmely_api_langchain import fetch_product_stock
        return fetch_product_stock
    else:
        raise ValueError(f"Tool '{name}' not recognized.")
    
def get_farmely_tools() -> list[Tool]:
    tools = [
        get_tool("retrieve_products"),
        get_tool("fetch_product_stock"),
    ]
    return tools

