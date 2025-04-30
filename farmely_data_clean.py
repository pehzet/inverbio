import json

# === Configuration ===
INPUT_FILE = "farmely_products_partly.json"         # Input file with a list of full product JSONs
OUTPUT_FILE = "products_simplified.json" # Output file with simplified product JSONs

# === Top-level fields to keep ===
TOP_LEVEL_FIELDS = [
    "name","id", "title", "brand", "description",
    "tags", "origin", "categories", "categoryGroups",
    "barcode", "organicInspection"
]

# === Simple boolean/numeric fields from 'dataNature' ===
DATANATURE_SIMPLE_FIELDS = [
    "ernhinweis_vegetarisch", "ernhinweis_vegan",
    "ernhinweis_laktosefrei", "ernhinweis_glutenfrei",
    "zut_zutatenverzeichnis", "zut_zutatenlegende_txt",
    "bio_verbandszugehoerigkeit", "zut_bnn_volldeklaration",
    "zut_e_nummern_vorhanden"
]

# === Nested fields (with 'value' inside) from 'dataNature' to flatten ===
DATANATURE_VALUE_FIELDS = [
    "nwae_energie_brennwert_kcal", "nwae_fett", "nwae_zucker",
    "nwae_eiweiss", "nwae_salz", "nwae_kohlenhydrate"
]

def extract_flattened_fields(product):
    result = {}

    # Top-level fields
    for field in TOP_LEVEL_FIELDS:
        if field in product:
            result[field] = product[field]

    # dataNature subfields
    data_nature = product.get("dataNature", {})

    # Simple fields
    for field in DATANATURE_SIMPLE_FIELDS:
        if field in data_nature:
            result[field] = data_nature[field]

    # Flattened value fields
    for field in DATANATURE_VALUE_FIELDS:
        if field in data_nature:
            nested = data_nature[field]
            if isinstance(nested, dict) and "value" in nested:
                result[field] = nested["value"]

    return result

def process_products():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        products = json.load(f)

    simplified = [extract_flattened_fields(p) for p in products]

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(simplified, f, ensure_ascii=False, indent=2)

    print(f"{len(simplified)} products processed and saved to '{OUTPUT_FILE}'.")

if __name__ == "__main__":
    process_products()
