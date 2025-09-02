from typing import Optional, Dict, List, Union
import duckdb
from pathlib import Path
import os
DUCKDB_FILE = Path(os.environ.get("PRODUCT_DB_PATH", "products_db/products.duckdb"))

def _normalize_barcodes(value) -> list[str]:
    """
    Akzeptiert str | int | list/tuple/set gemischt und gibt eine eindeutige
    Liste von Ziffernstrings zurück (EAN/UPC üblich 8–14 Stellen).
    Nicht-Ziffern werden verworfen; Reihenfolge bleibt stabil.
    """
    if value is None:
        return []
    # in Sequenz verwandeln
    if isinstance(value, (str, int)):
        items = [value]
    elif isinstance(value, (list, tuple, set)):
        items = list(value)
    else:
        items = [value]

    norm = []
    for x in items:
        if x is None:
            continue
        s = str(x).strip().replace(" ", "")
        if not s:
            continue
        # nur Ziffern (gewöhnliche EAN/UPC)
        if s.isdigit():
            # optional: nur plausible Längen zulassen
            if 8 <= len(s) <= 14:
                norm.append(s)
            else:
                norm.append(s)  # oder weglassen, wenn du strikt sein willst
    # Dedupe mit Reihenfolge
    seen = set()
    out = []
    for s in norm:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out

def _sql_escape(value: str) -> str:
    # Minimal-escaping für SQL-Literale (ANSI)
    return value.replace("'", "''")

def _execute_query(sql) -> List[Dict]:
    con = duckdb.connect(DUCKDB_FILE.as_posix())
    try:
        res = con.execute(sql)
        cols = [d[0] for d in res.description]
        return [dict(zip(cols, row)) for row in res.fetchall()]
    finally:
        con.close()

def get_products_by_barcodes(barcodes) -> List[Dict]:
    products = []
    for bc in barcodes:
        product = get_product_by_barcode(bc)
        if product:
            products.append(product)
    return products

def get_product_by_barcode(barcode: str) -> Optional[Dict]:
    """
    Liefert das erste Produkt (als Dict) anhand des Barcodes zurück.
    Nutzt SELECT * über alle LLM-Views (p, a, c, n, o, x, r).
    """
    if not isinstance(barcode, str) or not barcode.strip():
        raise ValueError("Bitte einen gültigen Barcode (String) übergeben.")

    bc = _sql_escape(barcode.strip())

    # Hinweis: Dein Tool fügt nur dann ein LIMIT an, wenn keins vorhanden ist.
    # Wir setzen bewusst LIMIT 1, damit keine Dubletten zurückkommen.
    sql = f"""
    SELECT *
    FROM v_product_core p
    LEFT JOIN v_product_allergens a USING (id)
    LEFT JOIN v_product_claims c USING (id)
    LEFT JOIN v_product_nutrition n USING (id)
    LEFT JOIN v_product_origin o USING (id)
    LEFT JOIN v_product_certifications x USING (id)
    LEFT JOIN v_product_processing r USING (id)
    WHERE p.barcode = '{bc}'
    ORDER BY p.id
    LIMIT 1;
    """
    try:
        res: Union[str, List[Dict]] = _execute_query(sql)
    except Exception as e:
        raise RuntimeError(f"Error executing query: {e}")
    return res[0] if res else None