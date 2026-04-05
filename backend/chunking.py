"""
Word-based text chunking with keyword annotation.
Each chunk is ~CHUNK_SIZE words with CHUNK_OVERLAP words of overlap.
"""
import uuid
import logging

from config import settings
from keyword_extraction import extract_keywords

logger = logging.getLogger(__name__)


def chunk_pages(pages: list[dict], file_name: str) -> list[dict]:
    """
    Split extracted pages into overlapping word-based chunks.
    Each chunk is annotated with KeyBERT-extracted keywords.

    Returns list of chunk dicts:
      chunk_id, text, source_file, page_number, keywords
    """
    chunks = []
    step = max(1, settings.CHUNK_SIZE - settings.CHUNK_OVERLAP)

    for page in pages:
        text = page["text"]
        page_num = page["page_number"]
        words = text.split()

        if not words:
            continue

        start = 0
        while start < len(words):
            end = min(start + settings.CHUNK_SIZE, len(words))
            chunk_text = " ".join(words[start:end])

            if chunk_text.strip():
                kws = extract_keywords(chunk_text, top_n=settings.TOP_K_KEYWORDS)
                chunks.append({
                    "chunk_id": str(uuid.uuid4()),
                    "text": chunk_text,
                    "source_file": file_name,
                    "page_number": page_num,
                    "keywords": kws,
                })
                logger.debug(
                    f"  Chunk p{page_num} words[{start}:{end}] → {len(kws)} keywords"
                )

            if end >= len(words):
                break
            start += step

    return chunks
