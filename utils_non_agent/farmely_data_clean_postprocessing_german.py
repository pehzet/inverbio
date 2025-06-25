import json

# === Konfiguration ===
INPUT_FILE = "products_simplified.json"
OUTPUT_FILE = "produkte_deutsch.json"

# === Übersetzung & Umbenennung der Keys ===
FIELD_TRANSLATIONS = {
    "name": "Name",
    "id": "ID",
    "title": "Titel",
    "brand": "Marke",
    "description": "Beschreibung",
    "tags": "Tags",
    "origin": "Herkunft",
    "categories": "Kategorien",
    "categoryGroups": "Kategoriegruppen",
    "barcode": "Barcode",
    "organicInspection": "Bio-Kontrollstelle",

    # Ernährungshinweise
    "ernhinweis_vegetarisch": "Ist vegetarisch",
    "ernhinweis_vegan": "Ist vegan",
    "ernhinweis_laktosefrei": "Ist laktosefrei",
    "ernhinweis_glutenfrei": "Ist glutenfrei",

    # Zutaten & Hinweise
    "zut_zutatenverzeichnis": "Zutatenverzeichnis",
    "zut_zutatenlegende_txt": "Hinweis zu Zutaten",
    "zut_bnn_volldeklaration": "Vollständige Deklaration vorhanden",
    "zut_e_nummern_vorhanden": "E-Nummern vorhanden",

    # Bio
    "bio_verbandszugehoerigkeit": "Mit Bio-Verbandszugehörigkeit",

    # Nährwerte
    "nwae_fett": "Fett (g)",
    "nwae_zucker": "Zucker (g)",
    "nwae_eiweiss": "Eiweiß (g)",
    "nwae_salz": "Salz (g)",
    "nwae_kohlenhydrate": "Kohlenhydrate (g)",
    "nwae_energie_brennwert_kcal": "Brennwert (kcal)"
}

def translate_keys(product):
    translated = {}
    for key, value in product.items():
        german_key = FIELD_TRANSLATIONS.get(key, key)  # fallback to original if not found
        translated[german_key] = value
    return translated

def convert_to_german_json():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        products = json.load(f)

    translated_products = [translate_keys(p) for p in products]

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(translated_products, f, ensure_ascii=False, indent=2)

    print(f"{len(translated_products)} Produkte übersetzt und gespeichert in '{OUTPUT_FILE}'.")

if __name__ == "__main__":
    convert_to_german_json()
