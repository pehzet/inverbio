#!/usr/bin/env python3
"""
json2sqlite.py  –  Lies eine JSON-Datei mit Produktdaten
und schreibe sie in eine SQLite-DB.
"""

from pathlib import Path
import json
import re
import sqlite3
from typing import Any, Dict, List

# --------------------------------------------------------------------------- #
# Globale Pfade – hier anpassen:
JSON_PATH = Path("C:/code/inverbio-langgraph/rag_data/produkte_deutsch.json")   # ← dein JSON-Export
DB_PATH   = Path("C:/code/inverbio-langgraph/products_db/products.db")  # ← Ziel-Datenbank
# --------------------------------------------------------------------------- #

def sanitize(key: str) -> str:
    key = key.lower()
    key = (
        key.replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("ß", "ss")
    )
    key = re.sub(r"\s+", "_", key)
    key = re.sub(r"[^0-9a-z_]", "", key)
    return key

def json_to_sqlite(json_path: Path, db_path: Path) -> None:
    data: List[Dict[str, Any]] = json.loads(json_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Die JSON-Datei muss ein Array aus Objekten enthalten.")

    all_keys = {k for obj in data for k in obj}
    columns = {k: sanitize(k) for k in all_keys}

    cols_sql = ", ".join(f'"{col}" TEXT' for col in columns.values())
    create_sql = f"CREATE TABLE IF NOT EXISTS products ({cols_sql});"

    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute(create_sql)

    insert_cols = ", ".join(f'"{c}"' for c in columns.values())
    placeholders = ", ".join("?" for _ in columns)
    insert_sql = f"INSERT INTO products ({insert_cols}) VALUES ({placeholders});"

    for obj in data:
        row = [
            json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v
            for k, v in ((k, obj.get(k)) for k in columns)
        ]
        cur.execute(insert_sql, row)

    con.commit()
    con.close()
    print(f"✓ {len(data)} Datensätze in '{db_path}' geschrieben.")

# --------------------------------------------------------------------------- #
# Direktstart ohne Kommandozeilen-Parameter
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    json_to_sqlite(JSON_PATH, DB_PATH)
