import sqlite3
import os
from pathlib import Path
import json
from typing import Any
from langchain_core.tools import tool
#    Otherwise you can get all producers by setting identifier to * (string) or all (string). 
@tool
def get_producer_information_by_identifier(identifier:Any) -> dict:
    """
    Retrieve a producer by its identifier from the database.
    Identifier can be the Name (string) or ID (int).

    params:
    identifier (int or str): The ID or name of the producer to retrieve.
    Returns:
    dict: A dictionary containing the producer's information, or a message if not found.

    """
    db_path = Path("producers_db/producers.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row 
    cursor = conn.cursor()

    if isinstance(identifier, int):
        cursor.execute("SELECT * FROM producers WHERE id = ?", (identifier,))
    elif isinstance(identifier, str):
        cursor.execute("SELECT * FROM producers WHERE name = ?", (identifier,))
    producers = cursor.fetchall()

    conn.close()

    if producers:
        producers = [dict(producer) for producer in producers]
        return json.dumps(producers, indent=4, ensure_ascii=False)
    else:
        return f"No producer found with the given identifier {identifier}."
    
if __name__ == "__main__":
    # Example usage
    # identifier = 1  # Replace with the actual producer ID or name you want to retrieve
    identifier = "TerraSana Natuurvoeding B.V."
    producer = get_producer_information_by_identifier(identifier)
    if producer:
        print(f"Producer found: {producer}")
    else:
        print(f"No producer found with identifier {identifier}.")