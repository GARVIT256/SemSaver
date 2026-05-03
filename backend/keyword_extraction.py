"""
Keyword extraction using TF-IDF (Sklearn) as a robust fallback.
Replaces KeyBERT to avoid heavy dependencies and build issues on Windows.
"""
import logging
import re
from sklearn.feature_extraction.text import TfidfVectorizer

logger = logging.getLogger(__name__)

# Basic stopwords to keep results clean
STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "as", "at",
    "be", "because", "been", "before", "being", "below", "between", "both", "but", "by",
    "can", "could", "did", "do", "does", "doing", "down", "during", "each", "few", "for", "from", "further",
    "had", "has", "have", "having", "here", "how", "if", "in", "into", "is", "it", "its", "itself",
    "just", "me", "more", "most", "my", "myself", "no", "nor", "not", "now", "of", "off", "on", "once", "only",
    "or", "other", "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "she", "should", "so",
    "some", "such", "than", "that", "the", "their", "theirs", "them", "themselves", "then", "there", "these",
    "they", "this", "those", "through", "to", "too", "under", "until", "up", "very", "was", "we", "were",
    "what", "when", "where", "which", "while", "who", "whom", "why", "with", "would", "you", "your", "yours",
    "yourself", "yourselves"
}

def extract_keywords(text: str, top_n: int = 10) -> list[str]:
    """
    Extract top-N keywords using TF-IDF from Sklearn.
    Very fast, local, and requires only scikit-learn.
    """
    if not text or len(text.strip()) < 20:
        return []

    try:
        # We treat the text as a single document and find the most important words
        # This isn't "global" TF-IDF but it acts as a good importance ranker for single chunks
        # when we use a custom tokenizer and lowercase everything.
        
        # Clean text slightly
        text = re.sub(r'[^a-zA-Z\s]', ' ', text.lower())
        
        vectorizer = TfidfVectorizer(
            stop_words=list(STOPWORDS),
            ngram_range=(1, 2), # Unigrams and bigrams
            max_features=100
        )
        
        # Fit on the single text (will basically rank by frequency but handle stopwords/ngrams)
        # Note: In a single doc, TF-IDF is basically just normalized frequency.
        tfidf_matrix = vectorizer.fit_transform([text])
        feature_names = vectorizer.get_feature_names_out()
        scores = tfidf_matrix.toarray()[0]
        
        # Sort by score descending
        sorted_indices = scores.argsort()[::-1]
        keywords = [feature_names[i] for i in sorted_indices[:top_n] if scores[i] > 0]
        
        return keywords
    except Exception as e:
        logger.warning(f"Keyword extraction failed (Sklearn): {e}")
        return []
