#!/usr/bin/env python3
"""
run_pipeline.py  ─  One-command SemSaver Fine-Tuning Pipeline
═══════════════════════════════════════════════════════════════

Runs all four stages in sequence:

  Stage 1 │ prepare_triplets.py  ─ Build (Q, P, N) triplets
  Stage 2 │ train.py             ─ Fine-tune embedding model
  Stage 3 │ evaluate.py          ─ Compare base vs fine-tuned
  Stage 4 │ reindex.py           ─ Re-encode FAISS index

Usage:
    python finetuning/run_pipeline.py [--skip-reindex] [--epochs 3]

Flags:
    --skip-reindex   Skip the FAISS re-indexing step (useful for dry evaluation)
    --epochs N       Number of training epochs (default 3)
    --loss {mnrl,triplet}  Loss function (default mnrl)
"""

import argparse
import subprocess
import sys
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

FT_DIR = Path(__file__).resolve().parent


def run(cmd: list[str], label: str):
    logger.info(f"\n{'━' * 55}")
    logger.info(f"  {label}")
    logger.info(f"{'━' * 55}")
    logger.info(f"CMD: {' '.join(cmd)}\n")
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        logger.error(f"[FAILED] {label} exited with code {result.returncode}")
        sys.exit(result.returncode)
    logger.info(f"[OK] {label} completed\n")


def main():
    p = argparse.ArgumentParser(description="SemSaver fine-tuning pipeline")
    p.add_argument("--skip-reindex", action="store_true")
    p.add_argument("--epochs",  type=int, default=3)
    p.add_argument("--batch",   type=int, default=8)
    p.add_argument("--loss",    type=str, default="mnrl", choices=["mnrl", "triplet"])
    args = p.parse_args()

    py = sys.executable

    # ── Stage 1: Prepare triplets ─────────────────────────────────────────────
    run(
        [py, str(FT_DIR / "prepare_triplets.py")],
        "STAGE 1/4 │ Prepare Triplets"
    )

    # ── Stage 2: Train ────────────────────────────────────────────────────────
    run(
        [py, str(FT_DIR / "train.py"),
         "--epochs", str(args.epochs),
         "--batch",  str(args.batch),
         "--loss",   args.loss],
        "STAGE 2/4 │ Fine-Tune Embedding Model"
    )

    # ── Stage 3: Evaluate ─────────────────────────────────────────────────────
    run(
        [py, str(FT_DIR / "evaluate.py")],
        "STAGE 3/4 │ Evaluate: Base vs Fine-Tuned"
    )

    # ── Stage 4: Re-index ─────────────────────────────────────────────────────
    if args.skip_reindex:
        logger.info("STAGE 4/4 │ Re-index FAISS — SKIPPED (--skip-reindex)")
    else:
        run(
            [py, str(FT_DIR / "reindex.py")],
            "STAGE 4/4 │ Re-index FAISS with Fine-Tuned Embeddings"
        )

    logger.info("=" * 55)
    logger.info("  ✅ PIPELINE COMPLETE")
    logger.info("=" * 55)
    logger.info("Results → finetuning/eval_results.json")
    logger.info("Model   → finetuning/semsaver-ft-model/")
    logger.info("")
    logger.info("To activate the model, add this to backend/.env:")
    logger.info("  EMBEDDING_MODEL=../finetuning/semsaver-ft-model")
    logger.info("Then restart the backend server.")


if __name__ == "__main__":
    main()
