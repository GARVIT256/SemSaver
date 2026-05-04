"""
Prompt builder for SemSaver.

Constructs the LLM prompt from retrieved context and graph facts.
Kept separate from the generation layer so it can be unit-tested in isolation.
"""
import logging

logger = logging.getLogger(__name__)

# ── System instruction ────────────────────────────────────────────────────────

SYSTEM_INSTRUCTION = """You are a helpful academic study assistant.

RULES:
1. Answer the student's question using ONLY the excerpts provided below.
2. Even if the context mentions the topic briefly, extract and explain what is there.
3. Synthesize a clear, complete answer from the context.
4. Do NOT invent facts not present in the context.
5. ONLY if the topic is completely absent from ALL provided excerpts, respond with:
   "Insufficient information in uploaded material."

Be concise and direct."""

# Increased character budget to ~20k chars (~5k tokens)
_MAX_CONTEXT_CHARS = 20_000


def build_prompt(query: str, chunks: list[dict], graph_facts: str = "") -> str:
    """
    Build the full LLM prompt.

    Structure:
      === SYSTEM ===
      <SYSTEM_INSTRUCTION>

      === GRAPH FACTS ===          (only if graph_facts is non-empty)
      <graph_facts>

      === CONTEXT ===
      --- Excerpt N [source, page] ---
      <chunk text>
      ...

      === QUESTION ===
      <query>

    Context is capped at _MAX_CONTEXT_CHARS to keep token usage predictable.
    """
    lines: list[str] = ["=== SYSTEM ===", SYSTEM_INSTRUCTION, ""]

    if graph_facts:
        lines += ["=== GRAPH FACTS ===", graph_facts, ""]

    if chunks:
        lines.append("=== CONTEXT ===")
        context_chars = 0
        added_count = 0
        
        # Sort chunks by similarity if scores exist
        sorted_chunks = sorted(
            chunks, 
            key=lambda x: x.get("similarity", 0.0) + x.get("reranker_score", 0.0), 
            reverse=True
        )

        for i, chunk in enumerate(sorted_chunks, start=1):
            source = chunk.get("source_file") or chunk.get("file_name", "unknown_source")
            page = chunk.get("page_number", "?")
            
            # Prefer 'text' (window-expanded) over 'text_small'
            text = (chunk.get("text") or chunk.get("text_small") or "").strip()

            if not text:
                logger.warning(f"Chunk {i} from {source} is empty! Skipping.")
                continue

            # Truncate individual chunk if it would blow the budget
            remaining = _MAX_CONTEXT_CHARS - context_chars
            if remaining <= 100: # Stop if we have less than 100 chars left
                break
                
            if len(text) > remaining:
                logger.info(f"Truncating chunk {i} from {len(text)} to {remaining} chars.")
                text = text[:remaining] + "…"

            lines.append(f"--- Excerpt {i} [{source}, p.{page}] ---")
            lines.append(text)
            lines.append("")
            
            context_chars += len(text)
            added_count += 1
            
        logger.info(f"Prompt builder: Injected {added_count} chunks, total {context_chars} chars context.")
    else:
        logger.warning("Prompt builder: No chunks provided!")
        lines += ["=== CONTEXT ===", "(No relevant content found.)", ""]

    lines += ["=== QUESTION ===", query]
    return "\n".join(lines)
