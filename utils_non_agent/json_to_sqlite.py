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


JSON_PATH = Path("C:/code/inverbio-langgraph/data_preparation/extracted_products.json")   # input
DB_PATH   = Path("C:/code/inverbio-langgraph/products_db/products.db")  # output

def quote_identifier(name: str) -> str:
    # Alle " durch "" ersetzen, dann in "…" packen
    safe = name.replace('"', '""')
    return f'"{safe}"'
def create_database_if_not_exists(db_path: Path) -> None:
    """
    Legt das Verzeichnis an (falls nötig), verbindet sich mit SQLite (erstellt DB-File)
    und setzt das UTF-8-Encoding für eine neu angelegte DB.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    # PRAGMA encoding wirkt nur beim Anlegen einer neuen DB
    con.execute('PRAGMA encoding = "UTF-8";')
    con.commit()
    con.close()
def json_to_sqlite(json_path: Path, db_path: Path) -> None:

    create_database_if_not_exists(db_path)
    data: List[Dict[str, Any]] = json.loads(json_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Die JSON-Datei muss ein Array aus Objekten enthalten.")

    # Sammle alle Keys
    all_keys = {k for obj in data for k in obj}

    # Erzeuge CREATE TABLE mit quoted identifiers
    cols_def = ", ".join(f'{quote_identifier(k)} TEXT' for k in all_keys)
    create_sql = f'CREATE TABLE IF NOT EXISTS products ({cols_def});'

    con = sqlite3.connect(db_path)
    cur = con.cursor()
    # Setze Encoding (nur wirksam, wenn DB neu angelegt wird)
    cur.executescript(create_sql)

    # INSERT-Vorbereitung
    quoted_cols = [quote_identifier(k) for k in all_keys]
    placeholders = ", ".join("?" for _ in all_keys)
    insert_sql = (
        f'INSERT INTO products ({", ".join(quoted_cols)}) '
        f'VALUES ({placeholders});'
    )

    # Einfügen der Daten
    for obj in data:
        row = [
            json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v
            for k, v in ((k, obj.get(k)) for k in all_keys)
        ]
        cur.execute(insert_sql, row)

    con.commit()
    con.close()
    print(f"✓ {len(data)} Datensätze in '{db_path}' geschrieben.")

if __name__ == "__main__":
    json_to_sqlite(JSON_PATH, DB_PATH)