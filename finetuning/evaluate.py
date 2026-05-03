"""
evaluate.py  ─  SemSaver Retrieval Evaluation  (Before vs After)
═════════════════════════════════════════════════════════════════

Compares the BASE model vs the FINE-TUNED model on three metrics:

  1. Top-1 / Top-3 / Top-5 Recall@K
       For each query, we check whether the correct positive answer
       appears in the top-K retrieved items from a candidate pool.

  2. Mean Reciprocal Rank (MRR)
       Average of 1/rank_of_first_correct_hit across all queries.

  3. Mean Cosine Similarity (query ↔ positive vs query ↔ negative)
       Measures how well positive and negative chunks are separated
       in embedding space.

Usage:
    python finetuning/evaluate.py [--pool 30]

The --pool argument controls how many candidates are in the retrieval
pool.  Default 30 = the full dataset, which is the hardest setting.
"""

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT          = Path(__file__).resolve().parent.parent
FT_DIR        = ROOT / "finetuning"
DATASET_PATH  = ROOT / "evaluation" / "dataset.json"
OUTPUT_MODEL  = FT_DIR / "semsaver-ft-model"
RESULTS_PATH  = FT_DIR / "eval_results.json"

BASE_MODEL    = "all-MiniLM-L6-v2"


def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    a = a / (np.linalg.norm(a) + 1e-9)
    b = b / (np.linalg.norm(b) + 1e-9)
    return float(np.dot(a, b))


def encode_all(model, texts: list[str]) -> np.ndarray:
    vecs = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return np.array(vecs, dtype=np.float32)


def recall_at_k(
    query_vecs: np.ndarray,
    corpus_vecs: np.ndarray,
    correct_indices: list[int],
    k: int,
) -> float:
    """Fraction of queries whose correct chunk is in top-K."""
    hits = 0
    for q_vec, correct_idx in zip(query_vecs, correct_indices):
        sims = corpus_vecs @ q_vec          # cosine similarity (already normalised)
        top_k = np.argsort(sims)[::-1][:k]
        if correct_idx in top_k:
            hits += 1
    return hits / len(correct_indices)


def mean_reciprocal_rank(
    query_vecs: np.ndarray,
    corpus_vecs: np.ndarray,
    correct_indices: list[int],
) -> float:
    rrs = []
    for q_vec, correct_idx in zip(query_vecs, correct_indices):
        sims  = corpus_vecs @ q_vec
        ranks = np.argsort(sims)[::-1]
        rank  = np.where(ranks == correct_idx)[0][0] + 1   # 1-indexed
        rrs.append(1.0 / rank)
    return float(np.mean(rrs))


def pos_neg_separation(
    model,
    triplets: list[dict],
) -> dict:
    """
    Average cosine similarity of (query, positive) vs (query, negative).
    Higher gap = better embedding quality.
    """
    queries   = [t["query"]    for t in triplets]
    positives = [t["positive"] for t in triplets]
    negatives = [t["negative"] for t in triplets]

    q_vecs = encode_all(model, queries)
    p_vecs = encode_all(model, positives)
    n_vecs = encode_all(model, negatives)

    pos_sims = [cosine_sim(q, p) for q, p in zip(q_vecs, p_vecs)]
    neg_sims = [cosine_sim(q, n) for q, n in zip(q_vecs, n_vecs)]

    return {
        "mean_pos_similarity": float(np.mean(pos_sims)),
        "mean_neg_similarity": float(np.mean(neg_sims)),
        "separation_gap":      float(np.mean(pos_sims) - np.mean(neg_sims)),
    }


def evaluate_model(model_name_or_path, label: str, dataset: list[dict], triplets: list[dict]):
    from sentence_transformers import SentenceTransformer

    logger.info(f"Loading model [{label}]: {model_name_or_path}")
    model = SentenceTransformer(str(model_name_or_path))

    # Build corpus = all answers in the dataset
    corpus   = [item["answer"]   for item in dataset]
    queries  = [item["question"] for item in dataset]
    # Each query's "ground truth" is its own answer (same index)
    correct_indices = list(range(len(dataset)))

    logger.info(f"Encoding {len(corpus)} corpus items and {len(queries)} queries …")
    corpus_vecs = encode_all(model, corpus)
    query_vecs  = encode_all(model, queries)

    r1  = recall_at_k(query_vecs, corpus_vecs, correct_indices, k=1)
    r3  = recall_at_k(query_vecs, corpus_vecs, correct_indices, k=3)
    r5  = recall_at_k(query_vecs, corpus_vecs, correct_indices, k=5)
    mrr = mean_reciprocal_rank(query_vecs, corpus_vecs, correct_indices)
    sep = pos_neg_separation(model, triplets)

    metrics = {
        "Recall@1":  round(r1,  4),
        "Recall@3":  round(r3,  4),
        "Recall@5":  round(r5,  4),
        "MRR":       round(mrr, 4),
        **{k: round(v, 4) for k, v in sep.items()},
    }

    logger.info(f"[{label}] Results:")
    for k, v in metrics.items():
        logger.info(f"  {k:30s} = {v}")

    return metrics


def print_comparison(before: dict, after: dict):
    print("\n" + "═" * 60)
    print(f"  {'Metric':<28} {'BASE':>8}  {'FINE-TUNED':>10}  {'Δ':>8}")
    print("═" * 60)
    for key in before:
        b = before[key]
        a = after[key]
        delta = a - b
        delta_str = f"{delta:+.4f}"
        indicator = "✅" if delta > 0.005 else ("⬇" if delta < -0.005 else "≈")
        print(f"  {key:<28} {b:8.4f}  {a:10.4f}  {delta_str:>8}  {indicator}")
    print("═" * 60 + "\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--base",  type=str, default=BASE_MODEL, help="Base model name/path")
    args = p.parse_args()

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        logger.error("Run: pip install sentence-transformers")
        sys.exit(1)

    if not DATASET_PATH.exists():
        logger.error(f"Dataset not found: {DATASET_PATH}")
        sys.exit(1)

    with open(DATASET_PATH, encoding="utf-8") as f:
        dataset = json.load(f)

    # Load all available triplets for pos/neg separation metric
    all_triplets = []
    for fp in [FT_DIR / "triplets.json", FT_DIR / "triplets_eval.json"]:
        if fp.exists():
            with open(fp, encoding="utf-8") as f:
                all_triplets.extend(json.load(f))

    if not all_triplets:
        logger.warning("No triplets found — separation gap metric will be skipped")
        # Build minimal triplets from dataset for separation metric
        import random
        random.seed(0)
        for i, item in enumerate(dataset):
            neg_idx = (i + 1) % len(dataset)
            all_triplets.append({
                "query": item["question"],
                "positive": item["answer"],
                "negative": dataset[neg_idx]["answer"],
            })

    logger.info(f"Dataset: {len(dataset)} QA pairs, {len(all_triplets)} triplets")

    # ── Baseline ──────────────────────────────────────────────────────────────
    before_metrics = evaluate_model(args.base, "BASE", dataset, all_triplets)

    # ── Fine-tuned ────────────────────────────────────────────────────────────
    if not OUTPUT_MODEL.exists():
        logger.error(f"Fine-tuned model not found at {OUTPUT_MODEL}")
        logger.error("Run:  python finetuning/train.py  first")
        sys.exit(1)

    after_metrics = evaluate_model(OUTPUT_MODEL, "FINE-TUNED", dataset, all_triplets)

    # ── Comparison ────────────────────────────────────────────────────────────
    print_comparison(before_metrics, after_metrics)

    results = {
        "base_model":      args.base,
        "finetuned_model": str(OUTPUT_MODEL),
        "before":          before_metrics,
        "after":           after_metrics,
        "delta":           {k: round(after_metrics[k] - before_metrics[k], 4) for k in before_metrics},
    }
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    logger.info(f"Results saved → {RESULTS_PATH}")
    logger.info("To integrate: set EMBEDDING_MODEL=finetuning/semsaver-ft-model in backend/.env")


if __name__ == "__main__":
    main()
