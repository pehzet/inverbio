from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal
import os
import duckdb
from langchain.tools import tool
from icecream import ic
# Adjust to your environment
DUCKDB_FILE = Path(os.environ.get("PRODUCT_DB_PATH", "products_db/products.duckdb"))
MAX_QUERY_ROWS = 100
# Whitelisted views/tables the LLM may use
ALLOWED_OBJECTS = {
    # core groups
    "v_product_core",
    "v_product_allergens",
    "v_product_claims",
    "v_product_nutrition",
    "v_product_origin",
    "v_product_certifications",
    "v_product_processing",
    # source (optional; prefer views)
    "products",
}

_READONLY_SQL = re.compile(r"^\s*(with\s+.+)?\s*select\b", re.IGNORECASE | re.DOTALL)

@tool
def run_product_sql(
    sql: str,
) -> list[dict] | str:
    """
    Execute a **read-only** SQL SELECT query against the DuckDB database that hosts the
    product field-group tables, and return results  as a list of dicts ("records")

    The DuckDB contains detailed product information across multiple views. Including Allergenes and Product origins (for regional requests).
    Use this Tool for detailled information and special requests. Otherwise use the similiarity search to search for products in general.

    max_rows is set to an hard limit of 100

    ─────────────────────────────────────────────────────────────────────────────
    HOW THE LLM SHOULD BUILD QUERIES (context & schema)
    ─────────────────────────────────────────────────────────────────────────────
    Use these LLM-friendly views and always join by `id`:

      • v_product_core (alias p)
        - id, identifier, product_name (COALESCE(title,name)), brand
        - barcode, barcodeType
        - description, ingredients
        - categories (STRUCT[group,name][]) , categoryGroups[], categoryGroup, tags[]
        - netPrice, pricePerUnit, priceUnit, taxes, deposit
        - fillingQuantity, weight, volume
        - image_url  (prefix applied)
      
      • v_product_allergens (alias a)
        - *_present booleans: value IN (1,2) means "present or traces"
          e.g., allergen_gluten_present, allergen_wheat_present, …, lactose_present
        - *_text columns: human-readable mapping (ENUM 1..4)
          1='Ja (laut Rezeptur enthalten)', 2='Kann in Spuren enthalten sein',
          3='Nein (kein Nachweis und nicht in Produktion)', 4='Garantiert nein (mit Analyse)'
        - allergens_dynamic (array of structs with {name, flag_id})

      • v_product_claims (alias c)
        - claim_vegan, claim_vegetarian, claim_gluten_free, claim_lactose_free,
          claim_sugar_free, claim_no_added_sugar, claim_palm_oil_free,
          claim_halal, claim_kosher, claim_raw,
          claim_text, claim_gluten_free_pkg, claim_lactose_free_pkg

      • v_product_nutrition (alias n)
        - kj, kcal
        - fat_total_g, fat_sat_g, carbs_g, sugars_g, protein_g, salt_g,
          fiber_g, starch_g, polyols_g, mono_ufa_g, poly_ufa_g
        - portion_size, portions_per_pack

      • v_product_origin (alias o)
        - origin, regionalType ("PROCESSED", "PRODUCED"), 
        - distance_km (TRY_CAST(distance AS DOUBLE))
        - region_text, origin_country_list (ARRAY of {value, iso_code})
        - processing_country, packaging_country
        - lat, lon
        - Producer fields (all flattened):
          producer_id, producer_name, producer_street, producer_zip, producer_city,
          producer_country, producer_email, producer_phone, producer_website, producer_vat,
          producer_organic_certification, producer_organic_inspection,
          producer_logo_path_raw, producer_logo_url (prefix applied),
          producer_last_modified_at, producer_title, producer_created_at,
          producer_address, producer_distance_raw ["LOWER50","LOWER100","GREATER100"], producer_distance_raw_text (["Weniger als 50 km", "Weniger als 100 km", "Mehr als 100 km"]), producer_distance_km,
          producer_description, producer_slogan

      • v_product_certifications (alias x)
        - organicCertification, organicInspection
        - bio_control_body, producer_org_cert, producer_org_inspection
        - bio_cert_ids, bio_cert_text, eu_bio_logo, eu_bio_origin_country
        - is_association_member, srl_compliant
        - fairtradeCertification

      • v_product_processing (alias r)
        - milk_* / cheese_* important fields (e.g., cheese_aging_days, cheese_milk_species_ids)
        - meat_*, fish_* (e.g., meat_species_ids, fish_catch_method)
        - beer_non_alcoholic, wine_vintage
        - cook_time_min, cook_time_max, usage_instructions, storage_notes
        - temperature_controlled

    General guidance:
      - Always qualify columns with table aliases (p, a, c, n, o, x, r).
      - Always join on `USING (id)` or `ON p.id = a.id`, etc.
      - Prefer filtering with booleans (e.g., c.claim_vegan = TRUE, a.allergen_gluten_present = FALSE).
      - For “regional” constraints, use `o.producer_distance_raw/producer_distance_raw_text`.
      - If you need countries, `o.origin_country_list` is an array of structs; DuckDB supports UNNEST:
          SELECT * FROM v_product_origin o, UNNEST(o.origin_country_list) t
      - Return only the necessary columns.
      - Always include an ORDER BY when meaningful (e.g., price asc, distance asc).
      - Keep result sets small; a LIMIT ≤ 200 is preferred unless the user requests more.

    Example queries the LLM can emit:
      1) OVERVIEW: Vegan & glutenfrei:
         SELECT id, p.product_name, p.brand, 
         FROM v_product_core p
         JOIN v_product_claims c USING (id)
         JOIN v_product_allergens a USING (id)
         WHERE c.claim_vegan = TRUE AND c.claim_gluten_free = TRUE
               AND COALESCE(a.allergen_gluten_present, FALSE) = FALSE

         LIMIT 100;

      2) LOCAL: local produced products with description:
         SELECT id, p.product_name, o.producer_name, p.description
         FROM v_product_core p
         JOIN v_product_origin o USING (id)
         WHERE o.producer_distance_raw = 'LOWER50'
         AND o.regionalType ='PRODUCED'
         AND p.description IS NOT NULL

      3) SPECIAL: Käse mit Reifung > 60 Tage, ohne Nüsse:
         SELECT p.product_name, r.cheese_aging_days
         FROM v_product_core p
         JOIN v_product_processing r USING (id)
         LEFT JOIN v_product_allergens a USING (id)
         WHERE r.cheese_aging_days > 60
           AND COALESCE(a.allergen_almond_present, FALSE) = FALSE
           AND COALESCE(a.allergen_hazelnut_present, FALSE) = FALSE
           AND COALESCE(a.allergen_walnut_present, FALSE) = FALSE
         ORDER BY r.cheese_aging_days DESC
         LIMIT 50;
      4) ALLERGENS: all allergens of product 123:
         SELECT a.*, 
         FROM v_product_allergens a
         WHERE id = 123
    ─────────────────────────────────────────────────────────────────────────────
    SAFETY & CONSTRAINTS (enforced by this function)
    ─────────────────────────────────────────────────────────────────────────────
      - Only a single statement is allowed and it must start with SELECT or WITH.
      - No writes/DDL (INSERT/UPDATE/DELETE/CREATE/DROP/ALTER/ATTACH/COPY/PRAGMA, etc.).
      - Queries must only reference whitelisted objects: {sorted(ALLOWED_OBJECTS)}.
      - If `require_limit=True` and no LIMIT is present, a LIMIT {max_rows} is appended.


    Parameters:
      sql:        The SQL query (SELECT/WITH) 



    Returns:
      list[dict] 
    """
    # was parameter before
    format = "records"
    ic(sql)
    _ensure_single_readonly_statement(sql)
    _ensure_only_allowed_objects(sql, ALLOWED_OBJECTS)

    final_sql = sql
    if  not _has_limit(sql):
      # Append a LIMIT as a safety net; keep it simple (no OFFSET merge)
        final_sql = f"{sql.rstrip().rstrip(';')}\nLIMIT {int(MAX_QUERY_ROWS)}"

    con = duckdb.connect(DUCKDB_FILE.as_posix())

    try:
        if format == "records":
            res = con.execute(final_sql)
            cols = [d[0] for d in res.description]
            return [dict(zip(cols, row)) for row in res.fetchall()]
        elif format == "json":
            df = con.execute(final_sql).fetchdf()
            return df.to_json(orient="records", force_ascii=False)
        else:
            raise ValueError("Unsupported format. Use 'records' or 'json'.")
    finally:
        con.close()


# ── helpers ───────────────────────────────────────────────────────────────────

_FORBIDDEN_TOKENS = re.compile(
    r"\b(attach|copy|create|drop|alter|insert|update|delete|merge|replace|truncate|vacuum|pragma)\b",
    re.IGNORECASE,
)

_ALLOWED_NAME = re.compile(r"\b(from|join)\s+([a-zA-Z_][\w\.]*)", re.IGNORECASE)


def _ensure_single_readonly_statement(sql: str) -> None:
    """Reject multi-statement strings and anything that isn't a single read-only SELECT/WITH."""
    # crude multi-statement check
    if ";" in sql.strip().rstrip(";"):
        raise ValueError("Only a single SQL statement is allowed.")
    if not _READONLY_SQL.match(sql or ""):
        raise ValueError("Only read-only SELECT/WITH queries are allowed.")
    if _FORBIDDEN_TOKENS.search(sql):
        raise ValueError("Write/DDL operations are not allowed.")


def _ensure_only_allowed_objects(sql: str, allowed: set[str]) -> None:
    """Ensure all referenced FROM/JOIN objects are whitelisted."""
    referenced = {m.group(2) for m in _ALLOWED_NAME.finditer(sql or "")}
    # Strip potential schema prefixes; DuckDB typically doesn't need them,
    # but we keep the check lenient by allowing exact matches only here.
    disallowed = {name for name in referenced if name not in allowed}
    if disallowed:
        raise ValueError(f"Query references non-whitelisted objects: {sorted(disallowed)}")


_LIMIT_RE = re.compile(r"\blimit\b\s+\d+", re.IGNORECASE)


def _has_limit(sql: str) -> bool:
    """Detect whether a LIMIT clause exists."""
    return bool(_LIMIT_RE.search(sql or ""))
