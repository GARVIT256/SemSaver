"""
train.py  ─  SemSaver Contrastive Fine-Tuning Pipeline
═══════════════════════════════════════════════════════

Uses sentence-transformers MultipleNegativesRankingLoss (MNRL) with
TripletLoss as a secondary option.  MNRL is strongly preferred because:

  • It treats every OTHER positive in the batch as an in-batch negative,
    giving us N-1 negatives per sample for free — critical when N is small.
  • It is equivalent to InfoNCE / SimCSE loss and is proven for retrieval.

Training is designed to be lightweight:
  • Model : all-MiniLM-L6-v2  (22 M params, runs well on CPU)
  • Epochs: 3  (configurable, keeps overfitting low on tiny dataset)
  • Batch : 8  (fits in < 4 GB RAM on CPU)

Outputs
───────
  finetuning/semsaver-ft-model/   — fine-tuned SentenceTransformer

Usage:
    python finetuning/train.py [--epochs 3] [--batch 8] [--loss mnrl|triplet]
"""

import argparse
import json
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT          = Path(__file__).resolve().parent.parent
FT_DIR        = ROOT / "finetuning"
TRIPLETS_PATH = FT_DIR / "triplets.json"
OUTPUT_MODEL  = FT_DIR / "semsaver-ft-model"

BASE_MODEL    = "all-MiniLM-L6-v2"


# ── Args ──────────────────────────────────────────────────────────────────────
def parse_args():
    p = argparse.ArgumentParser(description="SemSaver embedding fine-tuning")
    p.add_argument("--epochs",    type=int,   default=3,      help="Training epochs")
    p.add_argument("--batch",     type=int,   default=8,      help="Batch size")
    p.add_argument("--warmup",    type=float, default=0.1,    help="Warmup ratio")
    p.add_argument("--loss",      type=str,   default="mnrl", choices=["mnrl", "triplet"],
                   help="Loss function: mnrl (recommended) | triplet")
    p.add_argument("--model",     type=str,   default=BASE_MODEL, help="Base model name")
    p.add_argument("--margin",    type=float, default=0.5,    help="Triplet loss margin")
    return p.parse_args()


def load_triplets(path: Path) -> list[dict]:
    if not path.exists():
        logger.error(f"Triplets file not found: {path}")
        logger.error("Run:  python finetuning/prepare_triplets.py  first.")
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        triplets = json.load(f)
    logger.info(f"Loaded {len(triplets)} triplets from {path.name}")
    return triplets


def build_mnrl_samples(triplets: list[dict]):
    """
    MNRL only needs (anchor, positive) pairs.
    Hard negatives are fed separately as InputExample negatives.
    We create one InputExample per triplet.
    """
    from sentence_transformers import InputExample
    samples = []
    for t in triplets:
        # MNRL with explicit hard negatives: [query, positive, negative]
        samples.append(InputExample(texts=[t["query"], t["positive"], t["negative"]]))
    return samples


def build_triplet_samples(triplets: list[dict]):
    """TripletLoss expects (anchor, positive, negative)."""
    from sentence_transformers import InputExample
    samples = []
    for t in triplets:
        samples.append(InputExample(texts=[t["query"], t["positive"], t["negative"]]))
    return samples


def main():
    args = parse_args()

    # Lazy-import heavy dependencies after arg parsing
    try:
        from sentence_transformers import SentenceTransformer, losses
        from sentence_transformers.evaluation import TripletEvaluator
        from torch.utils.data import DataLoader
    except ImportError as e:
        logger.error(f"Missing dependency: {e}")
        logger.error("Run:  pip install sentence-transformers torch")
        sys.exit(1)

    # ── 1. Load model ─────────────────────────────────────────────────────────
    logger.info(f"Loading base model: {args.model}")
    model = SentenceTransformer(args.model)
    logger.info(f"Embedding dim: {model.get_sentence_embedding_dimension()}")

    # ── 2. Load data ──────────────────────────────────────────────────────────
    triplets = load_triplets(TRIPLETS_PATH)

    # ── 3. Build loss ─────────────────────────────────────────────────────────
    if args.loss == "mnrl":
        logger.info("Using MultipleNegativesRankingLoss (MNRL) with hard negatives")
        train_samples = build_mnrl_samples(triplets)
        train_dataloader = DataLoader(train_samples, shuffle=True, batch_size=args.batch)
        # CachedMultipleNegativesRankingLoss = memory-efficient MNRL
        try:
            train_loss = losses.CachedMultipleNegativesRankingLoss(model)
            logger.info("Using CachedMultipleNegativesRankingLoss (memory-efficient)")
        except AttributeError:
            train_loss = losses.MultipleNegativesRankingLoss(model)
            logger.info("Using MultipleNegativesRankingLoss")
    else:
        logger.info(f"Using TripletLoss with margin={args.margin}")
        train_samples = build_triplet_samples(triplets)
        train_dataloader = DataLoader(train_samples, shuffle=True, batch_size=args.batch)
        train_loss = losses.TripletLoss(model=model, triplet_margin=args.margin)

    # ── 4. Evaluator (from held-out eval set) ─────────────────────────────────
    eval_path = FT_DIR / "triplets_eval.json"
    evaluator = None
    if eval_path.exists():
        with open(eval_path, encoding="utf-8") as f:
            eval_triplets = json.load(f)
        anchors   = [t["query"]    for t in eval_triplets]
        positives = [t["positive"] for t in eval_triplets]
        negatives = [t["negative"] for t in eval_triplets]
        evaluator = TripletEvaluator(
            anchors=anchors,
            positives=positives,
            negatives=negatives,
            name="semsaver-eval",
            show_progress_bar=False,
        )
        logger.info(f"Evaluator ready with {len(eval_triplets)} held-out triplets")
    else:
        logger.warning("No eval triplets found — training without evaluation callback")

    # ── 5. Compute training steps ──────────────────────────────────────────────
    steps_per_epoch = len(train_dataloader)
    total_steps     = steps_per_epoch * args.epochs
    warmup_steps    = max(1, int(total_steps * args.warmup))
    logger.info(
        f"Training: epochs={args.epochs}, steps_per_epoch={steps_per_epoch}, "
        f"total_steps={total_steps}, warmup={warmup_steps}"
    )

    # ── 6. Train ──────────────────────────────────────────────────────────────
    OUTPUT_MODEL.mkdir(parents=True, exist_ok=True)

    model.fit(
        train_objectives=[(train_dataloader, train_loss)],
        epochs=args.epochs,
        warmup_steps=warmup_steps,
        evaluator=evaluator,
        evaluation_steps=steps_per_epoch,   # evaluate once per epoch
        output_path=str(OUTPUT_MODEL),
        save_best_model=True,
        show_progress_bar=True,
    )

    logger.info(f"Fine-tuned model saved → {OUTPUT_MODEL}")
    logger.info("Next step: python finetuning/evaluate.py")


if __name__ == "__main__":
    main()
