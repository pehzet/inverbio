import sqlite3
import os
from pathlib import Path
import json
from typing import Any
from langchain_core.tools import tool
#    Otherwise you can get all producers by setting identifier to * (string) or all (string). 

def _get_connection():
    db_path = Path("producers_db/producers.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

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
    conn = _get_connection()
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


    
@tool
def get_all_producer_names() -> list[str]:
    """
    Retrieve names of all producers from the database.
    Returns:
        list[str]: A list of all producer names.
    """
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT name FROM producers")
    rows = cursor.fetchall()
    conn.close()
    return json.dumps([dict(row).get("name") for row in rows], ensure_ascii=False)


if __name__ == "__main__":
    alle = get_all_producer_names()
    print(alle)
    print(len(alle))