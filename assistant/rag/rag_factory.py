

from typing import Literal
from assistant.rag.chroma import get_vector_store_chroma
from assistant.rag.firestore import get_vector_store_firestore
def get_vector_store(db=Literal["firestore", "chroma"], **kwargs) :
    """
    Initialize a vector store based on the specified database type.
    """
    if db == "firestore":
        raise NotImplementedError("Firestore vector store is not implemented yet.")
        #return get_vector_store_firestore(kwargs.get("collection_name", "default_collection"))
    elif db == "chroma":
        return get_vector_store_chroma(kwargs.get("CHROMA_PRODUCT_DB", "chroma_db"))
    else:
        raise ValueError(f"Unsupported database type: {db}")




