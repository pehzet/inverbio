from __future__ import annotations
# TODO: implement add document method to Chroma vector store; put helper functions in a separate file
"""Utility helpers to build a Chroma vector‑store retriever that can ingest
Markdown, JSON, plain‑text, or text‑based PDF files.

Two ingestion modes are supported:
1. Natural‑chunk mode (``chunking=False``):
   ‑ Markdown: split by first‑level headings (``# ``)
   ‑ JSON    : each top‑level element/string value becomes one chunk
   ‑ TXT/PDF : single chunk containing the whole document
2. RAG‑style fixed‑size chunks (``chunking=True``):
   Any input is recursively split into roughly ``chunk_size`` character
   fragments with 10 % overlap (default 1000 chars when not provided).

Example
-------
>>> retriever = create_vector_store_chroma(
...     file_path="duetto_kakao.md",
...     chroma_dir="./chroma_duetto",
...     overwrite=True,
...     chunking=False,
... )
>>> docs = retriever.get_relevant_documents("Zutaten Duetto Kakao")
"""

from pathlib import Path
import json
import os
import shutil
from typing import List, Sequence

import chromadb
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)
from langchain.schema import Document
from langchain_chroma import Chroma
import sys
from icecream import ic
from chromadb.config import Settings
from pypdf import PdfReader  

TEXT_EMBEDDING_MODEL = "text-embedding-3-small"

def _extract_text_pdf(path: Path) -> str:
    """Extract **text only** from a PDF. Raises ``RuntimeError`` if pypdf is absent."""
    if PdfReader is None:
        raise RuntimeError(
            "PDF support requires the 'pypdf' package (pip install pypdf).")

    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _load_raw_text(path: Path) -> str:
    """Return the raw text from *path* regardless of file type."""
    suffix = path.suffix.lower()
    if suffix in {".md", ".markdown", ".txt"}:
        return path.read_text(encoding="utf‑8")

    if suffix == ".json":
        obj = json.loads(path.read_text(encoding="utf‑8"))
        # Dump with consistent spacing so that downstream chunking
        # positions stay deterministic.
        return json.dumps(obj, ensure_ascii=False, indent=2)

    if suffix == ".pdf":
        return _extract_text_pdf(path)

    raise ValueError(f"Unsupported file extension: {suffix}")



def _split_markdown(text: str) -> List[Document]:
    splitter = MarkdownHeaderTextSplitter(headers_to_split_on=[("#", "Header1")])
    texts = splitter.split_text(text)

    return texts


def _split_json(text: str) -> List[Document]:
    """Each top-level JSON element (object or primitive) -> one Document."""
    data = json.loads(text)
    docs: List[Document] = []
    if isinstance(data, list):
        for idx, item in enumerate(data):
            docs.append(Document(page_content=json.dumps(item, ensure_ascii=False), metadata={"idx": idx}))
    else:
        # Dict or primitive
        docs.append(Document(page_content=json.dumps(data, ensure_ascii=False), metadata={"idx": 0}))
    return docs


def _split_single(text: str) -> List[Document]:
    return [Document(page_content=text)]



def _split_recursive(text: str, chunk_size: int) -> List[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=max(chunk_size // 10, 20),  # 10 % overlap, ≥20 chars
    )
    return splitter.split_text(text)



def get_vector_store_chroma(chroma_dir: str, *, client: chromadb.Client | None = None, n_docs: int = 10):
    """Return a ``VectorStoreRetriever`` from an existing *chroma_dir*."""
    embeddings = OpenAIEmbeddings(model=TEXT_EMBEDDING_MODEL)
    persistent_client = client or chromadb.PersistentClient(path=str(chroma_dir),settings=Settings(anonymized_telemetry=False))
    search_kwargs={"k": n_docs}
    return Chroma(client=persistent_client, embedding_function=embeddings).as_retriever(search_kwargs=search_kwargs)


def create_vector_store_chroma(
    file_path: str,
    chroma_dir: str,
    overwrite: bool = True,
    chunking: bool = False,
    chunk_size: int | None = None,
) -> Chroma:
    """Build a Chroma vector store from *file_path*.

    Parameters
    ----------
    file_path: str
        Path to .md/.markdown, .json, .txt, or text‑based .pdf document.
    chroma_dir: str
        Directory where Chroma will persist its data. Will be created.
    overwrite: bool, default True
        If *chroma_dir* already exists, delete its contents first.
    chunking: bool, default False
        When *False*, use a natural splitting strategy (see module docstring).
        When *True*, disregard natural structure and break into fixed‑size
        fragments suited for classic RAG pipelines.
    chunk_size: int | None, default 1000
        Desired character length of chunks when *chunking=True*.
    """
    # Prepare output directory
    out_dir = Path(chroma_dir)
    if out_dir.exists() and overwrite:
        print(f"[vector‑store] Overwriting existing directory: {out_dir}")
        shutil.rmtree(out_dir)
    elif out_dir.exists():
        raise ValueError(
            f"Output directory '{out_dir}' already exists. "
            "Set 'overwrite=True' to delete it."
        )

    path = file_path
    # path = Path(file_path).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(path)
    if path.is_dir():
        raise ValueError("file_path must be a file, not a directory")



    # Ingest & split 
    raw_text = _load_raw_text(path)
    suffix = path.suffix.lower()

    if chunking:
        size = chunk_size or 1000
        docs = _split_recursive(raw_text, size)
    else:
        if suffix in {".md", ".markdown"}:
            docs = _split_markdown(raw_text)
        elif suffix == ".json":
            docs = _split_json(raw_text)
        else:  # .txt or .pdf fall back to a single chunk
            docs = _split_single(raw_text)

    # Vector‑store build  
    ic(len(docs), "documents")

    embeddings = OpenAIEmbeddings(model=TEXT_EMBEDDING_MODEL)

    # store = Chroma.from_documents(docs, embeddings, persist_directory=str(out_dir))
    store: Chroma = Chroma(
        embedding_function=embeddings,
        persist_directory=str(out_dir),
    )

    batch_size = 50  # embed & add in smaller chunks → avoids 300 k‑token limit
    for i in range(0, len(docs), batch_size):
        store.add_documents(docs[i : i + batch_size])

    print(f"[vector‑store] Created and saved to '{out_dir}'.")
    return store

