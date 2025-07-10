from chroma import create_vector_store_chroma
from pathlib import Path
import os
from icecream import ic
if __name__ == "__main__":
    # Create the vector store for products
    file_path = Path("data/products.md")
    chroma_dir = Path(os.getenv("CHROMA_PRODUCT_DB", "chroma_products"))
    ic(chroma_dir)
    # Ensure the directory exists
    chroma_dir.mkdir(parents=True, exist_ok=True)

    # Create the vector store
    print("Creating vector store. This may take a while...")
    create_vector_store_chroma(file_path=file_path, chroma_dir=chroma_dir)
    print(f"Vector store created at {chroma_dir}")