"""
Local embedding module using Jina / SentenceTransformer models.
Model is lazy-loaded once per process. Dimension is detected automatically.

Supports:
  - Jina v3 task-specific encoding (retrieval.passage / retrieval.query)
  - Standard SentenceTransformer models (incl. fine-tuned local paths)
  - Automatic fallback when `task` parameter is not supported

Fine-Tuned Model Integration:
  Set EMBEDDING_MODEL to a local path in backend/.env:
      EMBEDDING_MODEL=../finetuning/semsaver-ft-model
  The model will be loaded from disk on next server start.
  Re-index FAISS first with:  python finetuning/reindex.py
"""
import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

_model = None


def _get_model():
    global _model
    if _model is None:
        from config import settings
        from sentence_transformers import SentenceTransformer

        model_name = settings.EMBEDDING_MODEL

        # Resolve local paths relative to the backend directory
        model_path = Path(model_name)
        if not model_path.is_absolute():
            # Try resolving relative to backend dir
            backend_relative = Path(__file__).parent / model_path
            if backend_relative.exists():
                model_name = str(backend_relative.resolve())
                logger.info(f"Resolved local model path: {model_name}")

        logger.info(f"Loading embedding model: {model_name}")

        # trust_remote_code only needed for Jina models
        needs_remote_code = "jina" in str(model_name).lower()
        _model = SentenceTransformer(
            model_name,
            trust_remote_code=needs_remote_code,
        )
        logger.info(
            f"Embedding model ready. "
            f"Dim={_model.get_embedding_dimension()}"
        )
    return _model


def _encode(texts: list[str], task: str | None = None) -> np.ndarray:
    model = _get_model()
    try:
        if task:
            vecs = model.encode(texts, task=task, normalize_embeddings=True)
        else:
            vecs = model.encode(texts, normalize_embeddings=True)
    except TypeError:
        # Model doesn't support `task` parameter (non-Jina / fine-tuned model)
        vecs = model.encode(texts, normalize_embeddings=True)
    return np.array(vecs, dtype=np.float32)


def embed_passages(texts: list[str]) -> np.ndarray:
    """Embed document passages for FAISS storage."""
    return _encode(texts, task="retrieval.passage")


def embed_query(text: str) -> np.ndarray:
    """Embed a user query for retrieval. Returns shape (1, dim)."""
    return _encode([text], task="retrieval.query")


def get_dim() -> int:
    """Return the embedding dimension of the loaded model."""
    return _get_model().get_embedding_dimension()
