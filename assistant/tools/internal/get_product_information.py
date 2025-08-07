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
@tool
def get_product_information_by_id(product_id: int) -> dict:
    """
    Retrieve a product by its ID from the database.
    """
    db_path = Path("products_db/products.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    product = cursor.fetchone()
    conn.close()
    if product:
        product = dict(product)  
        return json.dumps(product, indent=4, ensure_ascii=False)
    else:
        return f"No product found with the given ID {product_id}."


if __name__ == "__main__":
    # Example usage
    product_id = 10  # Replace with the actual product ID you want to retrieve
    product = get_product_information_by_id(product_id)
    if product:
        print(f"Product found: {product}")
    else:
        print(f"No product found with ID {product_id}.")
    # db_path = Path("products_db/products.db")
    # conn = sqlite3.connect(db_path)
    # cursor = conn.cursor()
    # cursor.execute("SELECT * FROM products LIMIT 1;")
    # products = cursor.fetchall()
    # products_json = [dict(zip([column[0] for column in cursor.description], row)) for row in products]
    # conn.close()
    # print(f"First 10 products in the database: {products_json}")