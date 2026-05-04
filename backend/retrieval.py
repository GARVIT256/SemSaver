"""
retrieval.py — Enhanced Hybrid Retrieval Pipeline
==================================================
Improvements applied:
  A. Semantic Reranking   — cross-encoder rescores top FAISS hits
  B. Query Expansion      — LLM generates 3 query variants; results merged
  C. Small-to-Big Window  — expanded text window sent to LLM for richer context
  E. Graph-Augmented      — prerequisites AND related concepts always injected
"""
import re
import time
import logging

from config import settings
import vector_store
import graph_store
from keyword_extraction import extract_keywords
from reranker import rerank
from query_expander import expand_query

logger = logging.getLogger(__name__)

# ── Graph intent detection ────────────────────────────────────────────────────
_GRAPH_TRIGGERS = re.compile(
    r"\b(prerequisite|prereq|before|depends?|dependency|foundation|"
    r"need to know|required|what do i need|what should i learn)\b",
    re.IGNORECASE,
)


def _detect_graph_intent(query: str) -> bool:
    return bool(_GRAPH_TRIGGERS.search(query))


# ── C. Small-to-Big Window ────────────────────────────────────────────────────

def _expand_window(chunk: dict, all_meta: list[dict], window: int = 1) -> dict:
    """
    Given a retrieved chunk, merge it with `window` neighboring chunks from
    the same source file and page-adjacent pages to create a richer context.

    The expanded text is stored under 'text' while the original small text
    is preserved under 'text_small' for logging / debugging.
    """
    source = chunk.get("source_file", "")
    page   = chunk.get("page_number", 0)

    # Collect texts from neighboring pages of the same source
    neighbor_texts = []
    for meta in all_meta:
        if meta.get("source_file") == source:
            pg = meta.get("page_number", 0)
            if abs(pg - page) <= window and meta.get("chunk_id") != chunk.get("chunk_id"):
                neighbor_texts.append((pg, meta.get("text", "")))

    if not neighbor_texts:
        return chunk

    # Sort by page order and prepend/append neighbors around the anchor
    before = sorted([(pg, t) for pg, t in neighbor_texts if pg < page], key=lambda x: x[0])
    after  = sorted([(pg, t) for pg, t in neighbor_texts if pg > page], key=lambda x: x[0])

    combined_parts = (
        [t for _, t in before[-window:]]
        + [chunk.get("text", "")]
        + [t for _, t in after[:window]]
    )
    expanded_text = "\n\n".join(p.strip() for p in combined_parts if p.strip())

    expanded = dict(chunk)
    expanded["text_small"] = chunk.get("text", "")
    expanded["text"]       = expanded_text
    return expanded


# ── E. Graph-Augmented Context (enhanced) ────────────────────────────────────

def _get_graph_context(query: str, chunks: list[dict], always_inject: bool = True) -> tuple[list[str], str]:
    """
    Enhanced graph retrieval:
      - Always inject top related concepts (not just on prerequisite triggers)
      - Follow PREREQUISITE chains
      - Follow RELATED_TO edges for richer concept linking

    Returns (graph_path, graph_facts_string).
    """
    graph_path: list[str] = []
    graph_facts_parts: list[str] = []

    try:
        # Extract keywords from query + retrieved chunks
        query_kws = extract_keywords(query, top_n=5)
        chunk_kws: list[str] = []
        for chunk in chunks:
            chunk_kws.extend(chunk.get("keywords", []))

        candidates = list({kw.strip().lower() for kw in query_kws + chunk_kws if kw.strip()})[:15]
        logger.info(f"Graph context: {len(candidates)} candidates identified.")
    except Exception as e:
        logger.warning(f"Keyword extraction for graph context failed: {e}")
        return [], ""

    try:
        existing = graph_store.find_existing_concepts(candidates)
        logger.info(f"Graph context: {len(existing)} existing concepts found in Neo4j.")
    except Exception as e:
        logger.warning(f"Graph lookup (find_existing_concepts) failed or timed out: {e}")
        return [], ""

    if not existing:
        return [], ""

    # E.1  Always retrieve RELATED_TO neighbours for context enrichment
    if always_inject:
        try:
            all_related: set[str] = set()
            for concept in existing[:5]:
                try:
                    related = graph_store.get_related(concept, limit=3)
                    all_related.update(related)
                except Exception as e:
                    logger.debug(f"Failed to get related for {concept}: {e}")
            
            if all_related:
                graph_facts_parts.append(
                    "Related concepts: " + ", ".join(sorted(all_related)[:10])
                )
        except Exception as e:
            logger.warning(f"Related concepts traversal failed: {e}")

    # E.2  Follow prerequisite chains
    for concept in existing[:3]:
        try:
            chain = graph_store.get_prereq_chain(concept)
            if len(chain) > 1:
                graph_path = chain
                graph_facts_parts.append(
                    "Prerequisite chain: " + " → ".join(chain)
                )
                break
        except Exception as e:
            logger.warning(f"Prereq traversal failed for {concept!r}: {e}")

    graph_facts = "\n".join(graph_facts_parts)
    return graph_path, graph_facts


# ── Public API ────────────────────────────────────────────────────────────────

def retrieve(query: str) -> dict:
    """
    Enhanced hybrid retrieve.

    Pipeline:
      1. B: Expand query into N variants via LLM
      2. FAISS search all variants, merge + deduplicate results
      3. A: Cross-encoder rerank merged candidates
      4. C: Expand each top chunk into a larger context window
      5. E: Inject graph context (prerequisites + related concepts)

    Returns:
        chunks       — list of enriched chunk dicts
        graph_path   — prerequisite chain (may be empty)
        graph_facts  — formatted string for prompt injection
        use_graph    — bool flag
    """
    use_graph = _detect_graph_intent(query)
    logger.info(f"Query: {query!r} | graph_intent={use_graph}")

    # ── B. Query Expansion ───────────────────────────────────────────────────
    if settings.QUERY_EXPANSION_ENABLED:
        logger.info("Expanding query...")
        queries = expand_query(query, settings.GROQ_API_KEY, settings.GROQ_MODEL)
    else:
        queries = [query]

    # ── FAISS search for all variants ────────────────────────────────────────
    # Fetch extra candidates (TOP_K * 2) so reranker has material to work with
    k_fetch = settings.TOP_K_VECTOR * 2
    seen_ids: set[str] = set()
    merged_chunks: list[dict] = []

    for q in queries:
        hits = vector_store.search(q, k=k_fetch)
        for hit in hits:
            cid = hit.get("chunk_id", "")
            if cid and cid not in seen_ids:
                seen_ids.add(cid)
                merged_chunks.append(hit)

    logger.info(
        f"Multi-query: {len(queries)} variants -> {len(merged_chunks)} unique candidates"
    )

    # ── A. Cross-Encoder Reranking ───────────────────────────────────────────
    if settings.RERANKER_ENABLED:
        try:
            logger.info(f"Reranking {len(merged_chunks)} candidates...")
            top_chunks = rerank(query, merged_chunks, top_n=settings.TOP_K_VECTOR)
            logger.info("Reranking complete.")
        except Exception as e:
            logger.warning(f"Reranking stage failed: {e}")
            top_chunks = merged_chunks[:settings.TOP_K_VECTOR]
    else:
        top_chunks = merged_chunks[:settings.TOP_K_VECTOR]

    # ── C. Small-to-Big Window Expansion ────────────────────────────────────
    if settings.WINDOW_SIZE > 0:
        try:
            logger.info("Expanding context windows...")
            all_meta = vector_store.get_all_metadata()
            expanded_chunks = [_expand_window(c, all_meta, window=settings.WINDOW_SIZE) for c in top_chunks]
            logger.info("Window expansion complete.")
        except Exception as e:
            logger.warning(f"Window expansion failed ({e}) -- using original chunks.")
            expanded_chunks = top_chunks
    else:
        expanded_chunks = top_chunks

    # ── E. Graph-Augmented Context ───────────────────────────────────────────
    try:
        logger.info("Retrieving graph context...")
        graph_path, graph_facts = _get_graph_context(
            query, top_chunks, always_inject=settings.GRAPH_ALWAYS_INJECT
        )
        logger.info(f"Graph retrieval complete. Path length: {len(graph_path)}")
    except Exception as e:
        logger.warning(f"Graph context stage failed: {e}")
        graph_path, graph_facts = [], ""

    if graph_path:
        logger.info(f"Graph path: {graph_path}")

    logger.info("Retrieval pipeline finished.")
    return {
        "chunks":      expanded_chunks,
        "graph_path":  graph_path,
        "graph_facts": graph_facts,
        "use_graph":   use_graph,
    }
