import sqlite3
from pathlib import Path
from langchain_core.tools import tool

# just for logging 2025-08-13
# ['Körperpflege', 'Reinigungsmittel', 'Fertiggerichte & Konserven', 'Milchprodukte & Eier', 'Feinkost & Fertiggerichte', 'Haushaltswaren', 'Limonade', 'Fleisch & Fisch (tiefgekühlt)', 'Müsli, Flocken & Nüsse', 'Öl, Essig & Soßen', 'Sonstiges', 'Sonstige Getränke', 'Sonstige Drogerieartikel', 'Sonstiges Gebäck', 'Pasta, Getreide & Hülsenfrüchte', 'Salziges Gebäck & Snacks', 'Wurstwaren', 'Smoothies & Sirupe', 'Gewürze & Kochhilfen', 'Brotaufstriche & Honig', 'Süßwaren', 'Vegan & Vegetarisch', 'Gemüse', 'Wasser', 'Wein & Sekt', 'Tiernahrung', 'Baby-Körperpflege', 'Babynahrung', 'Backzutaten', 'Bier', 'Brot & Brötchen', 'Käse', 'Kakao & Kaffee-Alternativen', 'Kaffee', 'Fertiggerichte & Gebäck (tiefgekühlt)', 'Obst', 'Obst (tiefgekühlt)', 'Eis & Desserts (tiefgekühlt)', 'Säfte', 'Fleisch & Fisch', 'Haltbare Milch & Milchgetränke', 'Samen & Kerne', 'Spirituosen', 'Tee', 'Gemüse & Kräuter (tiefgekühlt)']
def get_connection() -> sqlite3.Connection:
    db_path = Path("products_db/products_categories.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Allows accessing columns by name
    return conn
# @tool
def get_all_categories() -> list[str]:
    """
    returns all categories as german titles as a list
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT Kategorie FROM categories")
    categories = [row["Kategorie"] for row in cursor.fetchall()]
    conn.close()
    return categories

@tool
def get_products_per_categorie(categorie:str, limit:int=10) -> list[dict]:
    """
    Parameters:
    - categorie: The category to filter products by.
    - limit: The maximum number of products to return (default is 10) (max 10)

    Returns:
    - A list of dictionaries representing the products in the specified category.
    Returns "Kategorie nicht gefunden" if the category is not found.
    """
    if categorie not in get_all_categories():
        return "Kategorie nicht gefunden"
    if limit > 10:
        limit = 10
    conn = get_connection()
    cursor = conn.cursor()
    # order by random to prevent bias
    cursor.execute("SELECT * FROM products_categories WHERE Kategorie = ? ORDER BY RANDOM() LIMIT ?", (categorie, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
#categories_product_count

@tool
def get_category_counts() -> dict:
    """
    returns the count of products per category as a dict with {product : count}


    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * from categories_product_count")
    rows = cursor.fetchall()
    conn.close()
    # flat dict
    return {row["Kategorie"]: row["anzahl_produkte"] for row in rows}


if __name__ == "__main__":
    # # print(get_all_categories())
    # all_ids = []
    # for i in range(10):
    #     products = get_products_per_categorie("Bier")
    #     ids = [product["id"] for product in products]
    #     all_ids.append(ids)

    # # check for duplicate sets
    # all_ids_sets = [set(ids) for ids in all_ids]
    # duplicates = set([frozenset(x) for x in all_ids_sets if all_ids_sets.count(x) > 1])
    # print(f"Duplicate product ID sets found: {duplicates}")
    print(get_category_counts())