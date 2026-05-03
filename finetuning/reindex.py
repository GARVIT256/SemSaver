"""
reindex.py  ─  Re-index FAISS with the fine-tuned model
═════════════════════════════════════════════════════════

After fine-tuning, this script:
  1. Reads existing FAISS metadata (chunk texts from faiss_meta.json)
  2. Re-encodes every chunk with the fine-tuned model
  3. Writes a new FAISS index that replaces the old one

Important: The fine-tuned model must be activated in backend/.env before
running the backend server (EMBEDDING_MODEL=../finetuning/semsaver-ft-model).
This script handles only the offline re-indexing step.

Usage:
    python finetuning/reindex.py [--dry-run]
"""

import argparse
import json
import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT         = Path(__file__).resolve().parent.parent
BACKEND_DIR  = ROOT / "backend"
FT_DIR       = ROOT / "finetuning"
FT_MODEL     = FT_DIR / "semsaver-ft-model"

FAISS_INDEX  = BACKEND_DIR / "faiss_index.bin"
FAISS_META   = BACKEND_DIR / "faiss_meta.json"


def backup(path: Path) -> Path:
    stamp  = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = path.with_suffix(f".backup_{stamp}{path.suffix}")
    shutil.copy2(path, backup)
    logger.info(f"Backed up {path.name} → {backup.name}")
    return backup


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true",
                   help="Show what would happen without writing anything")
    args = p.parse_args()

    # ── Guards ────────────────────────────────────────────────────────────────
    if not FT_MODEL.exists():
        logger.error(f"Fine-tuned model not found: {FT_MODEL}")
        logger.error("Run:  python finetuning/train.py  first")
        sys.exit(1)

    if not FAISS_META.exists():
        logger.error(f"faiss_meta.json not found at {FAISS_META}")
        logger.error("Upload at least one document via the /upload endpoint first.")
        sys.exit(1)

    # ── Load metadata ─────────────────────────────────────────────────────────
    with open(FAISS_META, encoding="utf-8") as f:
        metadata = json.load(f)

    if not metadata:
        logger.error("faiss_meta.json is empty — nothing to re-index.")
        sys.exit(1)

    texts = [m["text"] for m in metadata]
    logger.info(f"Loaded {len(texts)} chunks from faiss_meta.json")

    if args.dry_run:
        logger.info("[DRY RUN] Would re-encode and re-index these chunks:")
        for i, t in enumerate(texts[:5]):
            logger.info(f"  [{i}] {t[:80]}…")
        logger.info("[DRY RUN] No files were modified.")
        return

    # ── Load fine-tuned model ─────────────────────────────────────────────────
    try:
        from sentence_transformers import SentenceTransformer
        import faiss
    except ImportError as e:
        logger.error(f"Missing: {e}")
        sys.exit(1)

    logger.info(f"Loading fine-tuned model from: {FT_MODEL}")
    model = SentenceTransformer(str(FT_MODEL))
    dim   = model.get_sentence_embedding_dimension()
    logger.info(f"Embedding dimension: {dim}")

    # ── Encode all chunks ─────────────────────────────────────────────────────
    logger.info("Re-encoding all chunks (this may take a minute on CPU) …")
    vectors = model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=True,
        batch_size=32,
    )
    vectors = np.array(vectors, dtype=np.float32)
    logger.info(f"Encoded {len(vectors)} chunks, shape={vectors.shape}")

    # ── Build new FAISS index ─────────────────────────────────────────────────
    new_index = faiss.IndexFlatIP(dim)
    new_index.add(vectors)
    logger.info(f"New FAISS index: {new_index.ntotal} vectors, dim={new_index.d}")

    # ── Backup originals and save ─────────────────────────────────────────────
    if FAISS_INDEX.exists():
        backup(FAISS_INDEX)
    if FAISS_META.exists():
        backup(FAISS_META)

    faiss.write_index(new_index, str(FAISS_INDEX))
    with open(FAISS_META, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    logger.info(f"✅ New FAISS index saved → {FAISS_INDEX}")
    logger.info(f"✅ Metadata preserved   → {FAISS_META}")
    logger.info("")
    logger.info("Next: update backend/.env →  EMBEDDING_MODEL=../finetuning/semsaver-ft-model")
    logger.info("Then restart the backend server.")


if __name__ == "__main__":
    main()
