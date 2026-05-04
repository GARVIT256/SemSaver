"""
FAISS vector store using local Jina embeddings (no API calls).
Index dimension is detected automatically from the first embed call.
"""
import json
import os
import logging
import numpy as np
import faiss

from config import settings
import embeddings as emb

logger = logging.getLogger(__name__)

_index = None
_metadata: list[dict] = []


def _load_or_create(dim: int = 0):
    global _index, _metadata
    if _index is not None:
        return
    if os.path.exists(settings.FAISS_INDEX_PATH):
        _index = faiss.read_index(settings.FAISS_INDEX_PATH)
        with open(settings.FAISS_META_PATH, "r", encoding="utf-8") as f:
            _metadata = json.load(f)
        logger.info(f"FAISS index loaded: {_index.ntotal} vectors, dim={_index.d}")
    elif dim > 0:
        _index = faiss.IndexFlatIP(dim)
        _metadata = []
        logger.info(f"FAISS index created fresh, dim={dim}")


def save():
    """Explicitly commit the in-memory FAISS index and metadata to disk."""
    if _index is None:
        logger.warning("FAISS: Nothing to save (index is None).")
        return
    faiss.write_index(_index, settings.FAISS_INDEX_PATH)
    with open(settings.FAISS_META_PATH, "w", encoding="utf-8") as f:
        json.dump(_metadata, f, ensure_ascii=False, indent=2)
    logger.info(f"FAISS: Saved index and metadata to disk ({_index.ntotal} vectors).")


def add_chunks(chunks: list[dict]):
    """
    Embed chunks locally and add to FAISS.
    chunks: list of dicts with keys: chunk_id, text, source_file, page_number, keywords
    """
    global _index, _metadata   # needed: both read and reassigned in this function

    if not chunks:
        return

    texts = [c["text"] for c in chunks]
    vectors = emb.embed_passages(texts)   # local Jina inference
    dim = vectors.shape[1]

    _load_or_create(dim=dim)

    # Safety: if loaded index has mismatched dim, reset it
    if _index is not None and _index.d != dim:
        logger.warning(
            f"FAISS dim mismatch ({_index.d} vs {dim}). Resetting index."
        )
        _index = faiss.IndexFlatIP(dim)
        _metadata = []

    _index.add(vectors)
    _metadata.extend(chunks)
    save()
    logger.info(f"FAISS: added {len(chunks)} chunks → total {_index.ntotal}")


def search(query: str, k: int = 5) -> list[dict]:
    """Return top-k chunks for query using local Jina query embedding."""
    _load_or_create()
    if _index is None or _index.ntotal == 0:
        return []

    k = min(k, _index.ntotal)
    query_vec = emb.embed_query(query)
    scores, indices = _index.search(query_vec, k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0:
            continue
        meta = dict(_metadata[idx])
        meta["similarity"] = float(score)
        results.append(meta)
    return results


def get_total_chunks() -> int:
    _load_or_create()
    return _index.ntotal if _index is not None else 0


def get_all_metadata() -> list[dict]:
    """Return the in-memory metadata list (already loaded — no disk I/O)."""
    _load_or_create()
    return _metadata


def reset():
    """Delete index and metadata from disk and memory."""
    global _index, _metadata
    _index = None
    _metadata = []
    for path in [settings.FAISS_INDEX_PATH, settings.FAISS_META_PATH]:
        if os.path.exists(path):
            os.remove(path)
    logger.info("FAISS index reset.")
