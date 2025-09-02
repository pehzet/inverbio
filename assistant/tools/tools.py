from langchain.tools import Tool
from assistant.rag.rag_factory import get_vector_store
from langchain.tools.retriever import create_retriever_tool
from langgraph.prebuilt import ToolNode
from assistant.tools.farmely.farmely_api_langchain import fetch_product_stock
from assistant.tools.internal.get_product_information import get_product_information_by_id, get_all_products_by_supplier
from assistant.tools.internal.get_producer_information import get_producer_information_by_identifier, get_all_producer_names
from assistant.tools.internal.get_overview_of_product_categories import get_category_counts, get_products_per_categorie
def get_retriever_tool(tool_name:str, db:str, **kwargs) -> Tool:
    if tool_name == "retrieve_products":
        retriever = get_vector_store(db, **kwargs)
        retriever_tool = create_retriever_tool(
            retriever,
            "retrieve_products",
            """
            Use this to get an Overview of the farmely products. This tool uses similarity search. The Informations here are compact. For detailed information, use the other tools afterwards.""",
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
    elif name == "get_category_counts":
        return get_category_counts
    elif name == "get_all_products_per_categorie":
        return get_products_per_categorie
    elif name == "get_all_products_by_supplier":
        return get_all_products_by_supplier
    elif name == "get_all_producer_names":
        return get_all_producer_names
    else:
        raise ValueError(f"Tool '{name}' not recognized.")
    
def get_farmely_tools() -> list[Tool]:
    tools = [
        get_tool("retrieve_products", db="chroma", CHROMA_PRODUCT_DB="chroma_products"),
        get_tool("fetch_product_stock"),
        get_tool("get_product_information_by_id"),
        get_tool("get_producer_information_by_identifier"),
        get_tool("get_category_counts"),
        get_tool("get_all_products_per_categorie"),
        get_tool("get_all_products_by_supplier"),
        get_tool("get_all_producer_names"),
    ]
    return tools

if __name__ == "__main__":

    rag = get_retriever_tool("retrieve_products")
    result = rag.invoke("Duetto Kakao")
    print(result)
