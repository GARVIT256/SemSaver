"""
extract_chapter9_questions.py
═════════════════════════════
Reads ALL PDFs from the Chapter9/ folder, extracts text with PyMuPDF,
then uses Groq (Llama-3.3-70b) to generate high-quality Q&A pairs.

The generated pairs cover:
  - Factual recall questions
  - Conceptual understanding questions
  - Application / scenario questions
  - Multi-hop prerequisite questions (e.g. "What must you know before X?")
  - Comparison questions

Output:
  evaluation/chapter9_dataset.json   — new QA pairs
  evaluation/dataset_combined.json   — merged with existing dataset.json

Usage:
  python evaluation/extract_chapter9_questions.py
"""

import json
import logging
import os
import sys
import time
from pathlib import Path

import fitz  # PyMuPDF

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT         = Path(__file__).resolve().parent.parent
CHAPTER_DIR  = ROOT / "Chapter9"
EVAL_DIR     = ROOT / "evaluation"
OUT_NEW      = EVAL_DIR / "chapter9_dataset.json"
OUT_COMBINED = EVAL_DIR / "dataset_combined.json"
EXISTING     = EVAL_DIR / "dataset.json"

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ── Load env ──────────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=ROOT / "backend" / ".env")
except ImportError:
    pass

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
if not GROQ_API_KEY:
    logger.error("GROQ_API_KEY not set. Cannot generate questions.")
    sys.exit(1)


# ══════════════════════════════════════════════════════════════════════════════
# 1. PDF TEXT EXTRACTION
# ══════════════════════════════════════════════════════════════════════════════

def extract_pdf_text(pdf_path: Path, max_chars: int = 8000) -> str:
    """Extract and clean text from a PDF, truncated to max_chars."""
    doc = fitz.open(str(pdf_path))
    pages_text = []
    total = 0
    for page in doc:
        txt = page.get_text("text").strip()
        if txt:
            pages_text.append(txt)
            total += len(txt)
            if total >= max_chars:
                break
    doc.close()
    raw = "\n\n".join(pages_text)
    return raw[:max_chars]


# ══════════════════════════════════════════════════════════════════════════════
# 2. LLM QUESTION GENERATION
# ══════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """You are an expert computer science educator creating evaluation questions for a RAG (Retrieval-Augmented Generation) system.

Given a passage from a textbook, generate exactly 8 diverse Q&A pairs:
- 2 factual recall questions (specific facts, definitions, values)
- 2 conceptual understanding questions (explain concepts, differences)
- 1 application/scenario question (how/when to use something)
- 1 comparison question (compare two related concepts)
- 1 multi-hop question (requires combining 2+ concepts, use words like "prerequisite", "before", "depends on")
- 1 definition/syntax question (specific syntax, keywords, rules)

RULES:
- Each answer must be concise (1-3 sentences max)
- Answers must be directly answerable from the passage
- Questions must be specific and unambiguous
- Do NOT include question numbers in questions
- Return ONLY valid JSON, no markdown, no extra text

Return format (strict JSON array):
[
  {"question": "...", "answer": "..."},
  ...
]"""


def generate_questions(text: str, chapter_name: str, client) -> list[dict]:
    """Call Groq to generate Q&A pairs from chapter text."""
    prompt = f"""Chapter: {chapter_name}

Passage:
{text}

Generate 8 Q&A pairs as specified."""

    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            temperature=0.3,
            max_tokens=2048,
        )
        raw = resp.choices[0].message.content.strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        pairs = json.loads(raw)
        if not isinstance(pairs, list):
            logger.warning(f"Unexpected format from LLM for {chapter_name}")
            return []

        # Validate structure
        valid = []
        for p in pairs:
            if isinstance(p, dict) and "question" in p and "answer" in p:
                valid.append({
                    "question": str(p["question"]).strip(),
                    "answer":   str(p["answer"]).strip(),
                    "source":   chapter_name,
                })
        logger.info(f"  ✓ {len(valid)} Q&A pairs from {chapter_name}")
        return valid

    except json.JSONDecodeError as e:
        logger.warning(f"  JSON parse error for {chapter_name}: {e}")
        return []
    except Exception as e:
        logger.warning(f"  LLM error for {chapter_name}: {e}")
        return []


# ══════════════════════════════════════════════════════════════════════════════
# 3. MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    from groq import Groq
    client = Groq(api_key=GROQ_API_KEY)

    pdfs = sorted(CHAPTER_DIR.glob("*.pdf"))
    if not pdfs:
        logger.error(f"No PDFs found in {CHAPTER_DIR}")
        sys.exit(1)

    logger.info(f"Found {len(pdfs)} PDFs in {CHAPTER_DIR.name}: {[p.name for p in pdfs]}")

    all_pairs = []

    for pdf_path in pdfs:
        logger.info(f"\nProcessing: {pdf_path.name}")
        text = extract_pdf_text(pdf_path, max_chars=7000)

        if len(text.strip()) < 200:
            logger.warning(f"  Skipping — too little text ({len(text)} chars)")
            continue

        logger.info(f"  Extracted {len(text)} chars. Generating questions…")
        pairs = generate_questions(text, pdf_path.stem, client)
        all_pairs.extend(pairs)

        # Rate-limit courtesy delay
        time.sleep(2)

    logger.info(f"\nTotal generated: {len(all_pairs)} Q&A pairs")

    # Save chapter9-specific dataset (without "source" field for eval compat)
    chapter9_clean = [{"question": p["question"], "answer": p["answer"]} for p in all_pairs]

    with open(OUT_NEW, "w", encoding="utf-8") as f:
        json.dump(chapter9_clean, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved chapter9 dataset → {OUT_NEW} ({len(chapter9_clean)} pairs)")

    # Merge with existing dataset
    existing_pairs = []
    if EXISTING.exists():
        with open(EXISTING, encoding="utf-8") as f:
            existing_pairs = json.load(f)
        logger.info(f"Existing dataset: {len(existing_pairs)} pairs")

    combined = existing_pairs + chapter9_clean
    with open(OUT_COMBINED, "w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved combined dataset → {OUT_COMBINED} ({len(combined)} pairs)")

    print(f"\n✅ Done! {len(chapter9_clean)} new Q&A pairs from Chapter9 PDFs")
    print(f"   New dataset:      {OUT_NEW}")
    print(f"   Combined dataset: {OUT_COMBINED} ({len(combined)} total pairs)")


if __name__ == "__main__":
    main()
