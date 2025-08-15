import sqlite3
from pathlib import Path
import json
from typing import Iterable, List, Dict, Any

from icecream import ic
import os
PRODUCTS_DB_PATH = Path(os.environ.get("PRODUCT_DB_PATH", "products_db/products.db"))
def _decode_row(row, parse_json: bool) -> Dict[str, Any]:
    d = dict(row)
    if parse_json:
        for k, v in d.items():
            if isinstance(v, str) and v and v[0] in "[{":
                try:
                    d[k] = json.loads(v)
                except json.JSONDecodeError:
                    pass
    return d
def get_product_by_barcode(
    barcode: str,
    db_path: Path = PRODUCTS_DB_PATH,
    parse_json: bool = True
) -> dict | None:
    """
    Get a single product by its barcode (EAN/GTIN).
    Args:
        barcode:     EAN/GTIN as a string (e.g. "4016249010201")
        db_path:     Path to the SQLite database
        parse_json:  If True, attempts to decode JSON-like strings in the result.
    Returns:
        A dictionary with product details or None if not found.
    """
    BASE_DIR = os.environ.get("BASE_DIR", Path(__file__).resolve().parent.parent)
    db_path = BASE_DIR / db_path
    if not db_path.exists():
        raise FileNotFoundError(f"Database file '{db_path}' does not exist.")
    with sqlite3.connect(db_path) as con:
        con.row_factory = sqlite3.Row           # Rows wie Dicts ansprechbar
        cur = con.execute(
            "SELECT * FROM products WHERE barcode = ? LIMIT 1",
            (barcode,)
        )
        row = cur.fetchone()
        if row is None:
            return None

        result = dict(row)
        if parse_json:
            result = _decode_row(result, parse_json)

        return result

def get_products_by_barcodes(
    barcodes: Iterable[str],
    db_path: Path = PRODUCTS_DB_PATH,
    parse_json: bool = True,
    as_mapping: bool = False
) -> List[Dict[str, Any]] | Dict[str, Dict[str, Any]]:
    """
    Get all products by their barcodes.
    Args:
        barcodes:    Iterable of EAN/GTIN strings (e.g. ["4016249010201"])
        db_path:     Path to the SQLite database
        parse_json:  If True, attempts to decode JSON-like strings in the result.
        as_mapping:  If True, returns a dict mapping barcodes to product dicts,
                     otherwise returns a list of product dicts.
    Returns:
        A list of product dictionaries or a mapping of barcodes to product dicts.
    """
    BASE_DIR = os.environ.get("BASE_DIR", Path(__file__).resolve().parent.parent)
    db_path = BASE_DIR / db_path
    if not db_path.exists():
        raise FileNotFoundError(f"Database file '{db_path}' does not exist.")
    barcodes = list(dict.fromkeys(barcodes))    # Duplikate entfernen, Reihenfolge wahren
    if not barcodes:
        return {} if as_mapping else []


    # ChatGPT sagt ist besser gegen SQL-Injection. Daher keine direkte String-Interpolation.
    placeholders = ",".join(["?"] * len(barcodes))   # "?, ?, ?, …"
    query = f"SELECT * FROM products WHERE barcode IN ({placeholders})"

    with sqlite3.connect(db_path) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute(query, barcodes).fetchall()

    if not rows:
        return {} if as_mapping else []
    

    decoded = [_decode_row(r, parse_json) for r in rows]

    if as_mapping:
        return {d["barcode"]: d for d in decoded}
    return decoded

def test_get_product_by_barcode():
    """
    Test function to demonstrate usage.
    """
    # barcode = "4016249010201"  # Beispiel-Barcode
    barcode = "4022381034098"  # Beispiel-Barcode
    product = get_product_by_barcode(barcode)
    if product:
        print(f"Produkt gefunden: {product}")
    else:
        print("Produkt nicht gefunden.")


def setup_product_db_sqlite() -> None:
    """
    Set up the SQLite product database from a JSON file.
    This function reads product data from a JSON file and creates a SQLite database.
    Specify the paths in the environment variables:
    - PRODUCT_DB_PATH: Path to the SQLite database file (default: "products_db/products.db")
    - PRODUCTS_PATH: Path to the JSON file containing product data (default: "data/produkte_deutsch.json")
    """
    # determine paths
    BASE_DIR = Path(__file__).parent.parent
    db_file = BASE_DIR / os.environ.get("PRODUCT_DB_PATH", "products_db/products.db")
    json_file = BASE_DIR / os.environ.get("PRODUCTS_PATH", "data/produkte_deutsch.json")

    # load products
    with json_file.open("r", encoding="utf-8") as f:
        products: List[Dict[str, Any]] = json.load(f)
    if not products:
        raise ValueError("No products found in JSON")

    # collect keys, skip 'id'
    raw_keys = set().union(*(p.keys() for p in products))
    columns = sorted(k for k in raw_keys if k.lower() != "id")

    # infer types
    type_map: Dict[str, str] = {}
    for col in columns:
        vals = [p.get(col) for p in products if p.get(col) is not None]
        if all(isinstance(v, int) for v in vals):
            type_map[col] = "INTEGER"
        elif all(isinstance(v, (int, float)) for v in vals):
            type_map[col] = "REAL"
        else:
            type_map[col] = "TEXT"

    # ensure db dir exists
    db_file.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_file)
    cur = conn.cursor()

    # create table
    cols_def = ", ".join(f'"{col}" {type_map[col]}' for col in columns)
    cur.execute(f'CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY, {cols_def})')

    # prepare insert
    cols_list = ", ".join(f'"{col}"' for col in columns)
    placeholders = ", ".join("?" for _ in columns)
    insert_sql = f'INSERT INTO products ({cols_list}) VALUES ({placeholders})'
    # insert each product, serializing lists/dicts
    for p in products:
        row: List[Any] = []
        for col in columns:
            val = p.get(col)
            if isinstance(val, (list, dict)):
                val = json.dumps(val, ensure_ascii=False)
            row.append(val)
        cur.execute(insert_sql, row)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    # Direktstart ohne Kommandozeilen-Parameter
    test_get_product_by_barcode()
    # Weitere Tests oder Funktionen können hier hinzugefügt werden.