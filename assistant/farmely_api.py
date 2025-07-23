import os
import requests
from typing import Optional
import time


HOST_VAR_NAME = "FARMELY_HOST"
API_KEY_VAR_NAME = "FARMELY_API_KEY"


def fetch_customer_history(customer_id: str, timestamp: Optional[int] = None):
    """
    Ruft die Customer-History über die API ab.

    :param customer_id: ID des Kunden
    :param timestamp: Optionaler UNIX-Timestamp (int)
    :return: Response JSON oder Fehlermeldung
    """
    # Umgebungsvariablen lesen
    host = os.getenv(HOST_VAR_NAME)
    api_key = os.getenv(API_KEY_VAR_NAME)

    if not host or not api_key:
        raise EnvironmentError("HOST oder APIKEY ist nicht in den Umgebungsvariablen gesetzt.")

    # Timestamp validieren (wenn gesetzt)
    if timestamp is not None:
        if not isinstance(timestamp, int) or timestamp < 0:
            raise ValueError("Timestamp muss ein positiver UNIX-Zeitstempel (int) sein.")

    # URL zusammenbauen
    url = f"{host}/api/v1/customer/{customer_id}/history"
    params = {"since": timestamp} if timestamp is not None else {}

    # Header setzen
    headers = {
        "Accept": "text/plain, application/json",
        "X-API-KEY": api_key
    }

    # API Request
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Fehler beim API-Request: {e}")
        return None
    
def fetch_changed_products(timestamp: int, sample: Optional[int] = None):
    """
    Ruft geänderte Produkte ab (per Timestamp oder zufällige Auswahl via Sample).
    Der 'changed' Parameter ist verpflichtend.

    :param timestamp: Optionaler UNIX-Timestamp (int), ignoriert wenn sample gesetzt ist
    :param sample: Optionaler Sample-Wert (int), gibt Zufallsprodukte zurück
    :return: Response JSON oder None bei Fehler
    """
    # Umgebungsvariablen lesen
    host = os.getenv(HOST_VAR_NAME)
    api_key = os.getenv(API_KEY_VAR_NAME)

    if not host or not api_key:
        raise EnvironmentError("HOST oder APIKEY ist nicht in den Umgebungsvariablen gesetzt.")


    params = {}
    # Sample überschreibt Timestamp

    if not isinstance(timestamp, int) or timestamp < 0:
        raise ValueError("Timestamp muss ein positiver UNIX-Zeitstempel (int) sein.")
    params["since"] = timestamp
    if sample is not None:
        if not isinstance(sample, int) or sample <= 0:
            raise ValueError("Sample muss ein positiver Integer sein.")
        params["test"] = sample

    # URL & Header
    url = f"{host}/api/v1/product/changed"
    headers = {
        "Accept": "application/json",
        "X-API-KEY": api_key
    }

    # Request senden
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Fehler beim API-Request: {e}")
        print(f"Status Code: {response.status_code if 'response' in locals() else 'N/A'}")
        print(f"Response Text: {response.text if 'response' in locals() else 'N/A'}")
        return None


def fetch_product_stock_api(product_id: str):
    """
    Ruft den Lagerbestand eines Produkts anhand seiner ID ab.

    :param product_id: Die Produkt-ID
    :return: JSON-Antwort mit Lagerbestand oder None bei Fehler
    """
    if not product_id:
        raise ValueError("Product ID ist erforderlich.")
        return None

    # Umgebungsvariablen lesen
    host = os.getenv(HOST_VAR_NAME)
    api_key = os.getenv(API_KEY_VAR_NAME)

    if not host or not api_key:
        raise EnvironmentError("HOST oder APIKEY ist nicht in den Umgebungsvariablen gesetzt.")

    # URL & Header vorbereiten
    url = f"{host}/api/v1/product/{product_id}/stock"
    headers = {
        "Accept": "application/json",
        "X-API-KEY": api_key
    }

    # API-Call
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        response_json = response.json()
        print(response_json)
        return response_json
    except requests.RequestException as e:
        print(f"Fehler beim Abrufen des Lagerbestands: {e}")
        print(f"Status Code: {response.status_code if 'response' in locals() else 'N/A'}")
        print(f"Response Text: {response.text if 'response' in locals() else 'N/A'}")
        return None
def fetch_product(product_id: str):
    """
    Ruft den Lagerbestand eines Produkts anhand seiner ID ab.

    :param product_id: Die Produkt-ID
    :return: JSON-Antwort mit Lagerbestand oder None bei Fehler
    """
    # Umgebungsvariablen lesen
    host = os.getenv(HOST_VAR_NAME)
    api_key = os.getenv(API_KEY_VAR_NAME)

    if not host or not api_key:
        raise EnvironmentError("HOST oder APIKEY ist nicht in den Umgebungsvariablen gesetzt.")

    # URL & Header vorbereiten
    url = f"{host}/api/v1/product/{product_id}"
    headers = {
        "Accept": "application/json",
        "X-API-KEY": api_key
    }

    # API-Call
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Fehler beim Abrufen des Lagerbestands: {e}")
        print(f"Status Code: {response.status_code if 'response' in locals() else 'N/A'}")
        print(f"Response Text: {response.text if 'response' in locals() else 'N/A'}")
        return None

 
if __name__ == "__main__":
    product_id = "4"
    stock = fetch_product_stock_api(product_id)
    print(stock)