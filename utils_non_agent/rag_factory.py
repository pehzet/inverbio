import os
import shutil
from langchain.text_splitter import MarkdownHeaderTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain.tools.retriever import create_retriever_tool
from langchain.tools import Tool
import chromadb
from langchain_google_firestore import FirestoreVectorStore 
from firebase_utils import get_firestore_client
def get_vector_store_firestore(collection_name: str, firebase_config: dict):
    """
    Initialize a vector store using Firebase Firestore.
    """


    # Initialize Firebase client
 
    client = get_firestore_client()
    # Create a vector store using the Firestore collection
    vector_store = FirestoreVectorStore(
        client=client,
        collection_name=collection_name,
        embedding_function=OpenAIEmbeddings(),
    )

    return vector_store.as_retriever()

def get_vector_store_chroma(chroma_dir: str):
    embeddings = OpenAIEmbeddings()
    persistent_client = chromadb.PersistentClient(path=chroma_dir)
    vector_store = Chroma(
    client=persistent_client,
    embedding_function=embeddings,
)

    return vector_store.as_retriever()


def refresh_vector_store(markdown_path: str, chroma_dir: str):
    # Remove existing ChromaDB directory if exists to overwrite
    if os.path.exists(chroma_dir):
        shutil.rmtree(chroma_dir)

    # Load markdown document as raw text
    with open(markdown_path, "r", encoding="utf-8") as file:
        markdown_text = file.read()

    # Split the document into chunks at first-level markdown headings
    headers_to_split_on = [("#", "Header1")]
    text_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    texts = text_splitter.split_text(markdown_text)

    # Initialize embeddings (ensure your OpenAI API key is set in the environment)
    embeddings = OpenAIEmbeddings()

    # Create ChromaDB vector store from document chunks
    vector_store = Chroma.from_documents(texts, embeddings, persist_directory=chroma_dir)
    

    print(f"ChromaDB vector store refreshed and saved to '{chroma_dir}'.")


if __name__ == "__main__":
    # Path to your markdown file and directory for ChromaDB
    from dotenv import load_dotenv
    load_dotenv(".env_vars")
    markdown_file = "products.md"
    file_path = os.path.join("rag_data", markdown_file)
    chroma_directory = "chroma_db"
    refresh_vector_store(file_path, chroma_directory)