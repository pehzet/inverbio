from langchain_core.tools import tool
from assistant.farmely_api import fetch_product_stock_api
import json
import os
def _get_product_id_by_name(product_name: str) -> str:
    """
    Fetches the product ID by its name.
    :param product_name: The name of the product
    :return: The product ID as a string or None if not found
    """
    curr_dir = os.path.dirname(os.path.abspath(__file__))
    file_name = "produkte_deutsch.json"
    file_path = os.path.join(curr_dir, "rag_data", file_name)
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            products = json.load(f)
    except FileNotFoundError:
        print(f"File {file_name} not found.")
        return product_name
 
    produkt_id = next((p.get("ID", p.get("Id", p.get("id", None))) for p in products if p["Name"] == product_name), None)
    return str(produkt_id)

@tool
def fetch_product_stock(product_id: str):
    """
    Fetches the stock of a product by its ID. 


    :param product_id: The product ID 
    :return: JSON string with stock information or None on error
    """
    print(f"Fetching stock for product ID: {product_id}")
    try:
        _id = int(product_id)
    except ValueError:
        print(f"Invalid product ID: {product_id}. Must be an integer. I try to check the product name.")
        product_id = _get_product_id_by_name(product_id)
        if not product_id:
            print(f"Product with name {product_id} not found.")
            return None
        
    stock_json = fetch_product_stock_api(str(product_id))
    if not stock_json:
        return None
    stock_json["product_id"] = product_id
    stock_json_str = json.dumps(stock_json, indent=4, ensure_ascii=False)
    return stock_json_str

if __name__ == "__main__":
    product_id = "4"
    product_name = "Duetto Kakao"
    result = _get_product_id_by_name(product_name)
    print("result", result)

# if __name__ == "__main__":
#     from langchain_core.messages import AIMessage
#     # from langchain_core.tools import tool

#     from langgraph.prebuilt import ToolNode
#     tools = [fetch_product_stock]
#     tool_node = ToolNode(tools)
#     message_with_single_tool_call = AIMessage(
#     content="",
#     tool_calls=[
#         {
#             "name": "fetch_product_stock",
#             "args": {"product_id": "4"},
#             "id": "tool_call_id",
#             "type": "tool_call",
#         }
#     ],
#     )

#     result = tool_node.invoke({"messages": [message_with_single_tool_call]})
#     print("result", result)