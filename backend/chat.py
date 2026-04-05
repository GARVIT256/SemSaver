"""
Chat module: LLM answer generation only.

Priority:
  1. Groq  (if GROQ_API_KEY is set)  — fast, generous free tier
  2. Gemini (fallback)               — if Groq key absent

Prompt construction is delegated to prompt_builder.py.
No blocking retries — rate limit errors are returned immediately.
"""
import logging
import re
from statistics import mean

from config import settings
from prompt_builder import build_prompt

logger = logging.getLogger(__name__)

# ── Lazy clients ──────────────────────────────────────────────────────────────
_groq_client = None
_gemini_client = None


def _get_groq():
    global _groq_client
    if _groq_client is None:
        from groq import Groq
        _groq_client = Groq(api_key=settings.GROQ_API_KEY)
    return _groq_client


def _get_gemini():
    global _gemini_client
    if _gemini_client is None:
        from google import genai
        _gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _gemini_client


# ── Generation ────────────────────────────────────────────────────────────────

def _call_groq(prompt: str) -> str:
    """Call Groq API — primary LLM."""
    client = _get_groq()
    resp = client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=1024,
    )
    return resp.choices[0].message.content.strip()


def _call_gemini(prompt: str) -> str:
    """Call Gemini API — fallback LLM."""
    from google.genai import types
    client = _get_gemini()
    resp = client.models.generate_content(
        model=settings.GENERATION_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.2, max_output_tokens=1024),
    )
    return resp.text.strip()


# ── Public API ────────────────────────────────────────────────────────────────

def generate_answer(query: str, retrieval_result: dict) -> dict:
    """
    Generate the final answer from retrieval context.

    Args:
        query:            Sanitised user query.
        retrieval_result: Dict returned by retrieval.retrieve().

    Returns:
        Dict with keys: answer, sources, confidence, graph_path.
    """
    chunks: list[dict] = retrieval_result.get("chunks", [])
    graph_facts: str = retrieval_result.get("graph_facts", "")
    graph_path: list[str] = retrieval_result.get("graph_path", [])

    prompt = build_prompt(query, chunks, graph_facts)
    logger.info(f"Prompt ~{len(prompt) // 4} tokens")

    answer: str | None = None

    # ── 1. Try Groq first ─────────────────────────────────────────────────
    if settings.GROQ_API_KEY:
        try:
            answer = _call_groq(prompt)
            logger.info("Answer generated via Groq.")
        except Exception as e:
            err = str(e)
            if "429" in err or "rate" in err.lower():
                answer = "⚠️ Groq rate limit reached. Please try again in a moment."
            else:
                logger.error(f"Groq error: {e}")
                # Fall through to Gemini

    # ── 2. Fallback: Gemini ───────────────────────────────────────────────
    if answer is None and settings.GEMINI_API_KEY:
        try:
            answer = _call_gemini(prompt)
            logger.info("Answer generated via Gemini (fallback).")
        except Exception as e:
            err = str(e)
            if "429" in err or "RESOURCE_EXHAUSTED" in err:
                m = re.search(r"retryDelay['\"]:\s*['\"](\\d+)", err)
                wait = int(m.group(1)) if m else 30
                answer = f"⚠️ Rate limit reached. Please wait {wait}s and try again."
            else:
                logger.error(f"Gemini error: {e}")

    if answer is None:
        answer = "⚠️ No LLM available. Set GROQ_API_KEY or GEMINI_API_KEY in .env."

    sources = list({
        c.get("source_file") or c.get("file_name", "")
        for c in chunks
        if c.get("source_file") or c.get("file_name")
    })
    confidence = (
        round(mean([c.get("similarity", 0.0) for c in chunks]), 4)
        if chunks else 0.0
    )

    return {
        "answer": answer,
        "sources": sources,
        "confidence": confidence,
        "graph_path": graph_path,
    }
