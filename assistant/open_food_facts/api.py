import requests
import json

# Global EAN barcode for product lookup
ean_code = "0123456789012"

def search_product_by_ean(ean):
    """
    Input: ean (str) - product barcode
    Output: dict - JSON response containing product data
    """
    url = f"https://world.openfoodfacts.org/api/v0/product/{ean}.json"
    response = requests.get(url)
    return response.json()

# Execute search using global variable
product = search_product_by_ean(ean_code)

# Output product JSON
print(json.dumps(product, indent=2))