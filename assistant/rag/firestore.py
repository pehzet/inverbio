
from langchain_google_firestore import FirestoreVectorStore 
from assistant.utils.firebase_utils import get_firestore_client
from langchain_openai import OpenAIEmbeddings
def get_vector_store_firestore(collection_name: str):
    """
    Initialize a vector store using Firebase Firestore.
    """


    # Initialize Firebase client
 
    client = get_firestore_client()
    # Create a vector store using the Firestore collection
    vector_store = FirestoreVectorStore(
        client=client,
        collection=collection_name,
        embedding_service=OpenAIEmbeddings(),
    )

    return vector_store.as_retriever()