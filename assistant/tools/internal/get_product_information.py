import sqlite3
import os
from pathlib import Path
import json
from langchain_core.tools import tool
def list_all_tables():
    """
    Returns a list of all table names in the SQLite database.
    """
    db_path = Path("products_db/products.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    return tables

def _get_connection():
    db_path = Path("products_db/products.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row 
    return conn
    
@tool
def get_product_information_by_id(product_id: int) -> dict:
    """
    Retrieve a product by its ID from the database.

    Args:
        product_id (int): The ID of the product to retrieve.

    Returns:
        dict: The product information as a dictionary.
    """
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    product = cursor.fetchone()
    conn.close()
    if product:
        product = dict(product)  
        return json.dumps(product, indent=4, ensure_ascii=False)
    else:
        return f"No product found with the given ID {product_id}."

@tool
def get_all_products_by_supplier(name: str, only_count: bool = False) -> list[dict]:
    """
    returns all products  by a specific supplier as a list of dicts. 
    Searches with a LIKE %name% in the field "Hersteller" because Supplier is not listet explizitly.
    Returns id, name and description per product. All in german. Limit is 100.

    Args:
        name (str): The name of the supplier to search for.
        only_count (bool): If True, only the count of products is returned.

    Returns:
        list[dict]: A list of products from the specified supplier.
    """
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, Name, Beschreibung FROM products WHERE Hersteller LIKE ? COLLATE NOCASE ORDER BY RANDOM()", (f"%{name}%",))
    rows = cursor.fetchall()
    conn.close()
    if only_count:
        return len(rows)
    if len(rows) > 100:
        rows = rows[:100]
    return [dict(row) for row in rows]

if __name__ == "__main__":
    prods = get_all_products_by_supplier("Weiling", only_count=True)
    # print(prods)
    print(len(prods))
    # prods_str = json.dumps(prods, indent=4, ensure_ascii=False)
    # print(prods_str)
    # with open("products_weiling_100.json", "w", encoding="utf-8") as f:
    #     f.write(prods_str)