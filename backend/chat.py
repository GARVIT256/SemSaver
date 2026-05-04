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
import time
from statistics import mean

from config import settings
from prompt_builder import build_prompt

logger = logging.getLogger(__name__)

# ── Lazy clients ──────────────────────────────────────────────────────────────
_groq_client = None
_gemini_client = None
_openai_client = None


def _get_groq():
    global _groq_client
    if _groq_client is None:
        from groq import Groq
        # Enforce strict timeout at the client level
        _groq_client = Groq(api_key=settings.GROQ_API_KEY, timeout=15.0)
    return _groq_client


def _get_gemini():
    global _gemini_client
    if _gemini_client is None:
        try:
            from google import genai
            _gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
        except ImportError:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            _gemini_client = genai.GenerativeModel(settings.GENERATION_MODEL)
    return _gemini_client


def _get_openai():
    global _openai_client
    if _openai_client is None:
        from openai import OpenAI
        # Enforce strict timeout at the client level
        _openai_client = OpenAI(api_key=settings.OPENAI_API_KEY, timeout=15.0)
    return _openai_client


def _call_openai(prompt: str) -> str:
    """Call OpenAI API."""
    client = _get_openai()
    resp = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=1024,
    )
    return resp.choices[0].message.content.strip()


def _call_groq(prompt: str) -> str:
    """Call Groq API."""
    client = _get_groq()
    resp = client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=1024,
    )
    return resp.choices[0].message.content.strip()


def _call_gemini(prompt: str) -> str:
    """Call Gemini API."""
    client = _get_gemini()
    try:
        from google import genai as _g
        if hasattr(client, 'models'):  # New SDK
            # request_options allows setting a timeout in the new SDK
            resp = client.models.generate_content(
                model=settings.GENERATION_MODEL,
                contents=prompt,
                config={'http_options': {'timeout': 15000}} # 15s in ms
            )
            return resp.text.strip()
    except Exception:
        pass
    # Old SDK fallback
    resp = client.generate_content(
        prompt,
        generation_config={"temperature": 0.2, "max_output_tokens": 1024},
        request_options={"timeout": 15.0}
    )
    return resp.text.strip()


# ── Public API ────────────────────────────────────────────────────────────────

def generate_answer(query: str, retrieval_result: dict) -> dict:
    """
    Generate the final answer from retrieval context.
    Priority: OpenAI -> Gemini -> Groq.
    """
    chunks: list[dict] = retrieval_result.get("chunks", [])
    graph_facts: str = retrieval_result.get("graph_facts", "")
    graph_path: list[str] = retrieval_result.get("graph_path", [])

    prompt = build_prompt(query, chunks, graph_facts)
    logger.info(f"Prompt ~{len(prompt) // 4} tokens")

    answer: str | None = None

    # ── 1. Try OpenAI (Primary - user's fresh key) ──────────────────────
    if settings.OPENAI_API_KEY:
        try:
            t0 = time.time()
            logger.info("Calling OpenAI...")
            answer = _call_openai(prompt)
            logger.info(f"Answer generated via OpenAI in {time.time()-t0:.1f}s.")
        except Exception as e:
            logger.warning(f"OpenAI failed ({time.time()-t0:.1f}s): {e}")

    # ── 2. Try Groq (Fallback 1 — fast, generous free tier) ─────────────
    if answer is None and settings.GROQ_API_KEY:
        try:
            t0 = time.time()
            logger.info("Calling Groq...")
            answer = _call_groq(prompt)
            logger.info(f"Answer generated via Groq in {time.time()-t0:.1f}s.")
        except Exception as e:
            logger.warning(f"Groq failed ({time.time()-t0:.1f}s): {e}")

    # ── 3. Try Gemini (Fallback 2) ───────────────────────────────────────
    if answer is None and settings.GEMINI_API_KEY:
        try:
            t0 = time.time()
            logger.info("Calling Gemini...")
            answer = _call_gemini(prompt)
            logger.info(f"Answer generated via Gemini in {time.time()-t0:.1f}s.")
        except Exception as e:
            logger.warning(f"Gemini failed ({time.time()-t0:.1f}s): {e}")

    if answer is None:
        answer = "⚠️ No LLM available. Please check your API keys in .env."

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
