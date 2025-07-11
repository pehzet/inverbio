from assistant.rag.chroma import create_vector_store_chroma
from pathlib import Path
import os
from icecream import ic

def setup_product_db_chroma():
    """
    Set up the Chroma vector store for product data.
    This function creates a vector store using the specified file and directory.
    """
    BASE_DIR = Path(__file__).resolve().parent.parent

    file_path = Path("assistant/data/products.md")
    file_path = BASE_DIR / file_path
    chroma_dir = Path(os.getenv("CHROMA_PRODUCT_DB", "chroma_products"))
    chroma_dir = BASE_DIR / chroma_dir
    
    # Ensure the directory exists
    chroma_dir.mkdir(parents=True, exist_ok=True)

    # Create the vector store
    print("Creating vector store. This may take a while...")
    try:
        create_vector_store_chroma(file_path=file_path, chroma_dir=chroma_dir, overwrite=False)
        print(f"Vector store created at {chroma_dir}")
        return True
    except Exception as e:
        print(f"Error creating vector store: {e}")
        return False

if __name__ == "__main__":
    # Create the vector store for products
    setup_product_db_chroma()
