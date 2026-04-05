"""
Hybrid retrieval: vector (FAISS + local Jina) + graph (Neo4j).

Intent detection triggers graph traversal for prerequisite queries.
"""
import re
import logging

from config import settings
import vector_store
import graph_store
from keyword_extraction import extract_keywords

logger = logging.getLogger(__name__)

# Keywords that trigger prerequisite graph traversal
_GRAPH_TRIGGERS = re.compile(
    r"\b(prerequisite|prereq|before|depends?|dependency|foundation|need to know|required)\b",
    re.IGNORECASE,
)


def _detect_graph_intent(query: str) -> bool:
    return bool(_GRAPH_TRIGGERS.search(query))


def retrieve(query: str) -> dict:
    """
    Hybrid retrieve for a user query.

    Returns:
        chunks       — list of chunk dicts with similarity scores
        graph_path   — prerequisite chain (may be empty)
        graph_facts  — formatted string for prompt injection
        use_graph    — bool flag
    """
    use_graph = _detect_graph_intent(query)
    logger.info(f"Query: {query!r} | graph_intent={use_graph}")

    # ── 1. Vector retrieval (local Jina query embedding) ─────────────────
    chunks = vector_store.search(query, k=settings.TOP_K_VECTOR)

    # ── 2. Graph retrieval (if triggered) ────────────────────────────────
    graph_path: list[str] = []
    graph_facts: str = ""

    if use_graph:
        # Extract keywords from query using KeyBERT
        query_kws = extract_keywords(query, top_n=5)
        query_kws_lower = [kw.strip().lower() for kw in query_kws]

        # Also pull keywords from retrieved chunks
        chunk_kws = []
        for chunk in chunks:
            chunk_kws.extend(chunk.get("keywords", []))
        chunk_kws_lower = list({kw.strip().lower() for kw in chunk_kws})

        # Find which keywords exist in Neo4j
        candidates = list(set(query_kws_lower + chunk_kws_lower))[:10]
        try:
            existing = graph_store.find_existing_concepts(candidates)
        except Exception as e:
            logger.warning(f"Graph lookup failed: {e}")
            existing = []

        # Traverse prerequisite chain for first matched concept
        for concept in existing[:3]:
            try:
                chain = graph_store.get_prereq_chain(concept)
                if len(chain) > 1:
                    graph_path = chain
                    break
            except Exception as e:
                logger.warning(f"Prereq traversal failed for {concept!r}: {e}")

        if graph_path:
            graph_facts = "Prerequisite chain: " + " → ".join(graph_path)
            logger.info(f"Graph path: {graph_path}")

    return {
        "chunks": chunks,
        "graph_path": graph_path,
        "graph_facts": graph_facts,
        "use_graph": use_graph,
    }
