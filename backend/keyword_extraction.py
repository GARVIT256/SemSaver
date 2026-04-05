"""
Keyword extraction using KeyBERT + KeyphraseVectorizers.

Pipeline:
  1. KeyphraseCountVectorizer extracts noun-phrase candidates from text (local NLP)
  2. KeyBERT (all-MiniLM-L6-v2) scores and ranks them via cosine similarity
  3. Fallback to n-gram KeyBERT if vectorizer fails

No external API calls are made — everything runs locally.
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
        try:
            from keyphrase_vectorizers import KeyphraseCountVectorizer
            _vectorizer = KeyphraseCountVectorizer(stop_words="english")
        except ImportError:
            logger.warning(
                "keyphrase-vectorizers not installed — noun-phrase mode unavailable. "
                "Run: pip install keyphrase-vectorizers"
            )
    return _vectorizer


def extract_keywords(text: str, top_n: int = 10) -> list[str]:
    """
    Extract top-N keywords from text.

    Uses noun-phrase candidates (KeyphraseVectorizers) ranked by KeyBERT similarity.
    Falls back to n-gram extraction if the vectorizer is unavailable or fails.

    Args:
        text:  Input text (at least 20 characters)
        top_n: Maximum number of keywords to return

    Returns:
        List of keyword strings (may be shorter than top_n).
    """
    if not text or len(text.strip()) < 20:
        return []

    model = _get_model()
    nr_candidates = min(20, max(top_n * 2, 10))

    # Primary: KeyphraseVectorizers noun-phrase candidates
    vectorizer = _get_vectorizer()
    if vectorizer is not None:
        try:
            results = model.extract_keywords(
                text,
                vectorizer=vectorizer,
                top_n=top_n,
                use_maxsum=True,
                nr_candidates=nr_candidates,
            )
            keywords = [kw for kw, _ in results]
            if keywords:
                return keywords
        except Exception as e:
            logger.debug(f"KeyphraseVectorizer failed ({e}), using n-gram fallback")

    # Fallback: standard n-gram KeyBERT
    try:
        results = model.extract_keywords(
            text,
            keyphrase_ngram_range=(1, 3),
            stop_words="english",
            top_n=top_n,
            use_maxsum=True,
            nr_candidates=nr_candidates,
        )
        return [kw for kw, _ in results]
    except Exception as e:
        logger.warning(f"Keyword extraction failed entirely: {e}")
        return []
