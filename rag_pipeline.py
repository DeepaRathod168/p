"""
rag_pipeline.py
───────────────
Retrieval-Augmented Generation (RAG) pipeline.

Workflow
--------
1. Load all .txt / .md / .pdf files from the /data directory.
2. Split them into overlapping chunks.
3. Embed with HuggingFace sentence-transformers (all-MiniLM-L6-v2)
   — no OpenAI key required.  Swap to OpenAIEmbeddings if preferred.
4. Store / load the FAISS index from disk (data/faiss_index/).
5. Expose retrieve_context(query, k=4) → str  for use by agents.

Environment variables (optional):
  EMBEDDING_MODEL  = sentence-transformers model name
                     default: "all-MiniLM-L6-v2"
  DATA_DIR         = path to document folder  default: "./data"
  FAISS_INDEX_DIR  = path for persisted index default: "./data/faiss_index"
"""

import os
import logging
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    DirectoryLoader,
    TextLoader,
)
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

load_dotenv()
logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────────────
DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))
FAISS_INDEX_DIR = Path(os.getenv("FAISS_INDEX_DIR", "./data/faiss_index"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

_vector_store: FAISS | None = None  # module-level singleton


# ── Internal helpers ─────────────────────────────────────────────────────────

def _load_documents():
    """Load .txt and .md files from DATA_DIR."""
    loader = DirectoryLoader(
        str(DATA_DIR),
        glob="**/*.txt",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
        show_progress=False,
        silent_errors=True,
    )
    docs = loader.load()

    # Also load markdown files
    md_loader = DirectoryLoader(
        str(DATA_DIR),
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
        show_progress=False,
        silent_errors=True,
    )
    docs += md_loader.load()

    logger.info("Loaded %d documents from %s", len(docs), DATA_DIR)
    return docs


def _build_vector_store() -> FAISS:
    """Chunk documents and build (or load) a FAISS vector store."""
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    # Return cached index if available on disk
    if FAISS_INDEX_DIR.exists():
        logger.info("Loading existing FAISS index from %s", FAISS_INDEX_DIR)
        return FAISS.load_local(
            str(FAISS_INDEX_DIR),
            embeddings,
            allow_dangerous_deserialization=True,
        )

    logger.info("Building new FAISS index …")
    docs = _load_documents()
    if not docs:
        logger.warning("No documents found in %s — RAG context will be empty.", DATA_DIR)
        # Return a stub store so the pipeline does not crash
        from langchain.schema import Document
        docs = [Document(page_content="No background documents available.", metadata={})]

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=512,
        chunk_overlap=64,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(docs)
    logger.info("Created %d chunks from documents.", len(chunks))

    store = FAISS.from_documents(chunks, embeddings)

    # Persist for next run
    FAISS_INDEX_DIR.mkdir(parents=True, exist_ok=True)
    store.save_local(str(FAISS_INDEX_DIR))
    logger.info("FAISS index saved to %s", FAISS_INDEX_DIR)
    return store


def _get_store() -> FAISS:
    """Return module-level singleton vector store, building it if needed."""
    global _vector_store
    if _vector_store is None:
        _vector_store = _build_vector_store()
    return _vector_store


# ── Public API ───────────────────────────────────────────────────────────────

def retrieve_context(query: str, k: int = 4) -> str:
    """
    Retrieve the top-k most relevant document chunks for a given query.

    Parameters
    ----------
    query : str
        The user's research question.
    k : int
        Number of chunks to retrieve (default 4).

    Returns
    -------
    str
        Concatenated text of the top-k document chunks, separated by newlines.
        Returns an empty string if retrieval fails.
    """
    try:
        store = _get_store()
        docs = store.similarity_search(query, k=k)
        if not docs:
            logger.info("No relevant documents found for query: %s", query)
            return ""
        context = "\n\n---\n\n".join(d.page_content for d in docs)
        logger.info("Retrieved %d context chunks for query.", len(docs))
        return context
    except Exception as exc:
        logger.error("RAG retrieval failed: %s", exc)
        return ""


def rebuild_index() -> None:
    """
    Force-rebuild the FAISS index by deleting the cached version on disk.
    Call this after adding new documents to /data.
    """
    global _vector_store
    import shutil
    if FAISS_INDEX_DIR.exists():
        shutil.rmtree(FAISS_INDEX_DIR)
        logger.info("Deleted old FAISS index at %s", FAISS_INDEX_DIR)
    _vector_store = None
    _get_store()
    logger.info("FAISS index rebuilt successfully.")
