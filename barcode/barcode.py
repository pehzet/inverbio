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
    barcode = "4016249010201"  # Beispiel-Barcode
    product = get_product_by_barcode(barcode)
    if product:
        print(f"Produkt gefunden: {product}")
    else:
        print("Produkt nicht gefunden.")

if __name__ == "__main__":
    # Direktstart ohne Kommandozeilen-Parameter
    test_get_product_by_barcode()
    # Weitere Tests oder Funktionen können hier hinzugefügt werden.