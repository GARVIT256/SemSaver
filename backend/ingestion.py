"""
Ingestion pipeline orchestrator.

Flow per file:
  1. Extract text (PDF / PPTX)
  2. Clean text
  3. Chunk pages with keyword annotation
  4. Embed chunks → FAISS
  5. Build graph (RELATED_TO / PREREQUISITE / PART_OF) → Neo4j
"""
import logging
from pathlib import Path

from config import settings
import extraction
import chunking
import vector_store
import graph_store

logger = logging.getLogger(__name__)


def ingest_file(file_path: str) -> dict:
    """
    Run the full ingestion pipeline for one file.
    Returns a summary dict: {file, chunks, keywords, entities, relations}
    """
    file_name = Path(file_path).name
    logger.info(f"━━ Ingesting: {file_name} ━━")

    # ── 1. Extract ────────────────────────────────────────────────────────
    try:
        raw_pages = extraction.extract(file_path)
    except Exception as e:
        raise RuntimeError(f"Extraction failed: {e}") from e

    if not raw_pages:
        logger.warning(f"No text extracted from {file_name}")
        return {"file": file_name, "chunks": 0, "keywords": 0}

    # ── 2. Clean ──────────────────────────────────────────────────────────
    pages = [
        {"text": extraction.clean(p["text"]), "page_number": p["page_number"]}
        for p in raw_pages
        if extraction.clean(p["text"])
    ]

    if not pages:
        logger.warning(f"All pages empty after cleaning: {file_name}")
        return {"file": file_name, "chunks": 0, "keywords": 0}

    # ── 3. Chunk + keyword extraction (KeyBERT / KeyphraseVectorizers) ────
    logger.info(f"  Chunking {len(pages)} pages…")
    chunks = chunking.chunk_pages(pages, file_name)

    if not chunks:
        logger.warning(f"No chunks produced for {file_name}")
        return {"file": file_name, "chunks": 0, "keywords": 0}

    total_keywords = sum(len(c.get("keywords", [])) for c in chunks)
    logger.info(f"  {len(chunks)} chunks, {total_keywords} keyword assignments")

    # ── 4. Embed + FAISS storage (local Jina) ────────────────────────────
    logger.info(f"  Embedding {len(chunks)} chunks locally…")
    try:
        vector_store.add_chunks(chunks)
    except Exception as e:
        logger.error(f"FAISS storage failed: {e}")
        raise

    # ── 5. Build graph ────────────────────────────────────────────────────
    logger.info(f"  Building graph…")
    try:
        graph_store.build_graph_from_chunks(chunks)
    except Exception as e:
        # Graph is optional — warn but don't fail ingestion
        logger.warning(f"Graph build failed (Neo4j may not be running): {e}")

    logger.info(f"━━ Done: {file_name} ━━")
    return {
        "file": file_name,
        "chunks": len(chunks),
        "keywords": total_keywords,
    }
