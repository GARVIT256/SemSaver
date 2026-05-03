"""
Prompt builder for SemSaver.

Constructs the LLM prompt from retrieved context and graph facts.
Kept separate from the generation layer so it can be unit-tested in isolation.
"""

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

# Maximum characters of context to pass to the LLM (larger due to window expansion).
_MAX_CONTEXT_CHARS = 10_000


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
        for i, chunk in enumerate(chunks[:5], start=1):
            source = chunk.get("source_file") or chunk.get("file_name", "?")
            page = chunk.get("page_number", "?")
            text = chunk.get("text", "").strip()

            # Truncate individual chunk if it would blow the budget
            remaining = _MAX_CONTEXT_CHARS - context_chars
            if remaining <= 0:
                break
            if len(text) > remaining:
                text = text[:remaining] + "…"

            lines.append(f"--- Excerpt {i} [{source}, p.{page}] ---")
            lines.append(text)
            lines.append("")
            context_chars += len(text)
    else:
        lines += ["=== CONTEXT ===", "(No relevant content found.)", ""]

    lines += ["=== QUESTION ===", query]
    return "\n".join(lines)
