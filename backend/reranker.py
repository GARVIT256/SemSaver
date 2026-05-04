"""
reranker.py — Cross-Encoder Semantic Reranker  (Improvement A)
==============================================================
Uses BAAI/bge-reranker-base to re-score the top-K FAISS candidates.
Falls back to original FAISS scores if the model is unavailable.

Why cross-encoders beat bi-encoders for reranking:
  Bi-encoders (FAISS) encode query & chunk INDEPENDENTLY → fast but coarser.
  Cross-encoders see BOTH query+chunk TOGETHER → much more precise scoring,
  at the cost of speed (only used on top-K, not the whole index).
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_reranker = None
_RERANKER_MODEL = "BAAI/bge-reranker-base"


def _get_reranker():
    global _reranker
    if _reranker is None:
        try:
            from sentence_transformers import CrossEncoder
            logger.info(f"Loading cross-encoder reranker: {_RERANKER_MODEL}")
            _reranker = CrossEncoder(_RERANKER_MODEL, max_length=512)
            logger.info("Reranker ready.")
        except Exception as e:
            logger.warning(f"Reranker unavailable ({e}) — skipping reranking.")
            _reranker = False  # Mark as failed so we don't retry every call
    return _reranker if _reranker is not False else None


def rerank(query: str, chunks: list[dict], top_n: int = 5) -> list[dict]:
    """
    Rerank chunks using the cross-encoder. Returns top_n chunks sorted by
    reranker score (highest first). Falls back to original order if reranker
    is unavailable.

    Args:
        query:  The user's question.
        chunks: Candidate chunks from FAISS (already top-K).
        top_n:  How many reranked chunks to return to the LLM.
    """
    if not chunks:
        return chunks

    reranker = _get_reranker()
    if reranker is None:
        logger.debug("Reranker not available — returning FAISS order.")
        return chunks[:top_n]

    try:
        pairs = [[query, c.get("text", "")] for c in chunks]
        logger.info(f"Reranker: Predicting scores for {len(pairs)} pairs...")
        # CrossEncoder.predict returns a numpy array of scores
        scores = reranker.predict(pairs)
        if hasattr(scores, "tolist"):
            scores = scores.tolist()

        scored = sorted(
            zip(scores, chunks),
            key=lambda x: x[0],
            reverse=True,
        )
        reranked = []
        for score, chunk in scored[:top_n]:
            chunk = dict(chunk)
            chunk["reranker_score"] = float(score)
            reranked.append(chunk)

        logger.info(
            f"Reranker: {len(chunks)} -> {len(reranked)} chunks "
            f"| top score={reranked[0]['reranker_score']:.3f}"
        )
        return reranked

    except Exception as e:
        logger.warning(f"Reranking failed ({e}) — using FAISS order.")
        return chunks[:top_n]
