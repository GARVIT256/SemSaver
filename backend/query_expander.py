"""
query_expander.py — Multi-Query Expansion  (Improvement B)
===========================================================
Uses the Groq LLM to generate N alternative phrasings of the user's query.
All variants are searched in FAISS and results are merged + deduplicated.

Why this helps:
  If a student asks "What does super do?" but the PDF says "the super keyword
  refers to the parent class", the direct embedding match may be weak.
  A re-phrased variant like "purpose of super keyword in Java inheritance"
  will score much higher against the correct chunk.
"""
import logging

logger = logging.getLogger(__name__)

_N_VARIANTS = 3


def expand_query(query: str, groq_api_key: str, model: str) -> list[str]:
    """
    Generate N rephrased variants of the query.
    Returns [original_query] + [up to N variants].
    Falls back to Gemini if Groq fails, then just [original_query] on any error.
    """
    variants = []
    
    prompt = (
        f"You are an expert at query reformulation for a Java programming course.\n"
        f"Generate exactly {_N_VARIANTS} alternative phrasings of the following question.\n"
        f"Each phrasing should capture the same intent but use different terminology.\n"
        f"Return ONLY the {_N_VARIANTS} questions, one per line, with no numbering or bullets.\n\n"
        f"Original question: {query}"
    )

    # 1. Try Groq
    if groq_api_key:
        try:
            from groq import Groq
            client = Groq(api_key=groq_api_key)
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=256,
            )
            text = resp.choices[0].message.content.strip()
            variants = [line.strip() for line in text.splitlines() if line.strip()][:_N_VARIANTS]
            if variants:
                logger.info(f"Query expansion (Groq): {len(variants)} variants generated")
                return [query] + variants
        except Exception as e:
            logger.debug(f"Groq expansion failed ({e}) -- trying Gemini fallback.")

    # 2. Fallback: Gemini
    from config import settings
    if settings.GEMINI_API_KEY:
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model_obj = genai.GenerativeModel(settings.GENERATION_MODEL)
            resp = model_obj.generate_content(prompt)
            text = resp.text.strip()
            variants = [line.strip() for line in text.splitlines() if line.strip()][:_N_VARIANTS]
            if variants:
                logger.info(f"Query expansion (Gemini): {len(variants)} variants generated")
                return [query] + variants
        except Exception as e:
            logger.warning(f"Gemini expansion failed ({e})")

    return [query]
