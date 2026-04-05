"""
Keyword extraction using KeyBERT + KeyphraseVectorizers.

Pipeline:
  1. KeyphraseCountVectorizer extracts noun-phrase candidates from text
  2. KeyBERT (all-MiniLM-L6-v2) scores and ranks them
  3. Fallback to n-gram KeyBERT if vectorizer fails
"""
import logging

logger = logging.getLogger(__name__)

_kw_model = None
_vectorizer = None


def _get_model():
    global _kw_model
    if _kw_model is None:
        from config import settings
        from keybert import KeyBERT
        logger.info(f"Loading KeyBERT model: {settings.KEYWORD_MODEL}")
        _kw_model = KeyBERT(model=settings.KEYWORD_MODEL)
        logger.info("KeyBERT model ready.")
    return _kw_model


def _get_vectorizer():
    global _vectorizer
    if _vectorizer is None:
        from keyphrase_vectorizers import KeyphraseCountVectorizer
        _vectorizer = KeyphraseCountVectorizer(stop_words="english")
    return _vectorizer


def extract_keywords(text: str, top_n: int = 10) -> list[str]:
    """
    Extract top-N keywords from text.
    Uses noun-phrase candidates (KeyphraseVectorizers) ranked by KeyBERT.
    Falls back to n-gram extraction if vectorizer fails.
    """
    if not text or len(text.strip()) < 20:
        return []

    model = _get_model()

    # Primary: KeyphraseVectorizers candidate extraction
    try:
        vectorizer = _get_vectorizer()
        results = model.extract_keywords(
            text,
            vectorizer=vectorizer,
            top_n=top_n,
            use_maxsum=True,
            nr_candidates=min(20, max(top_n * 2, 10)),
        )
        keywords = [kw for kw, _ in results]
        if keywords:
            return keywords
    except Exception as e:
        logger.debug(f"KeyphraseVectorizer failed ({e}), using n-gram fallback")

    # Fallback: n-gram KeyBERT
    try:
        results = model.extract_keywords(
            text,
            keyphrase_ngram_range=(1, 3),
            stop_words="english",
            top_n=top_n,
            use_maxsum=True,
            nr_candidates=min(20, max(top_n * 2, 10)),
        )
        return [kw for kw, _ in results]
    except Exception as e:
        logger.warning(f"Keyword extraction failed entirely: {e}")
        return []
