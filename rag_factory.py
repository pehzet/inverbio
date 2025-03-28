import os
import shutil
from langchain.text_splitter import MarkdownHeaderTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.tools.retriever import create_retriever_tool
from langchain.tools import Tool
CHROMA_PARENT_PATH = "rag_data"
def refresh_vector_store(markdown_path: str, chroma_dir: str):
    # Remove existing ChromaDB directory if exists to overwrite
    if not os.path.exists(CHROMA_PARENT_PATH):
        os.makedirs(CHROMA_PARENT_PATH)
    if not CHROMA_PARENT_PATH in chroma_dir:
        chroma_dir = os.path.join(CHROMA_PARENT_PATH, chroma_dir)
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

    # Persist ChromaDB to disk
    vector_store.persist()

    print(f"ChromaDB vector store refreshed and saved to '{chroma_dir}'.")


def get_vector_store(chroma_dir: str):
    embeddings = OpenAIEmbeddings()
    vector_store = Chroma(persist_directory=chroma_dir, embedding_function=embeddings)
    return vector_store.as_retriever()

def get_retriever_tool(tool_name:str) -> Tool:
    if tool_name == "retrieve_products":
        retriever = get_vector_store("chroma_db")
        retriever_tool = create_retriever_tool(
            retriever,
            "retrieve_products",
            "Search for food products that Farmely sells and get information about them.",
        )
        return retriever_tool
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

    # Persist ChromaDB to disk
    # vector_store.persist()

    print(f"ChromaDB vector store refreshed and saved to '{chroma_dir}'.")


if __name__ == "__main__":
    # Path to your markdown file and directory for ChromaDB
    from dotenv import load_dotenv
    load_dotenv(".env_vars")
    markdown_file = "products.md"
    file_path = os.path.join(CHROMA_PARENT_PATH, markdown_file)
    chroma_directory = "chroma_db"
    refresh_vector_store(file_path, chroma_directory)