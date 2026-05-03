"""
prepare_triplets.py  ─  SemSaver Fine-Tuning Data Preparation
═══════════════════════════════════════════════════════════════

Reads  evaluation/dataset.json  (30 QA pairs) and produces
finetuning/triplets.json with structure:

    [{"query": ..., "positive": ..., "negative": ...}, ...]

Negative Sampling Strategy
──────────────────────────
Two-stage to maximise training signal from a small dataset:

  Stage 1 – HARD negatives (preferred):
      For each query we pick an answer from a semantically
      *adjacent* topic cluster (same OOP domain, wrong concept).
      Hard-negative clusters are hand-seeded below and augmented
      via cosine similarity of pretrained embeddings so the model
      actually has to learn fine-grained distinctions.

  Stage 2 – EASY negatives (fallback):
      A random answer from a *different* cluster is appended so
      every sample has at least one easy negative as well.

The script outputs:
  finetuning/triplets.json     — primary training set
  finetuning/triplets_eval.json — 20 % held-out for evaluation

Usage:
    python finetuning/prepare_triplets.py
"""

import json
import random
import os
import sys
from pathlib import Path

import numpy as np

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT         = Path(__file__).resolve().parent.parent
DATASET_PATH = ROOT / "evaluation" / "dataset.json"
OUT_DIR      = ROOT / "finetuning"
OUT_DIR.mkdir(exist_ok=True)

TRIPLETS_PATH      = OUT_DIR / "triplets.json"
TRIPLETS_EVAL_PATH = OUT_DIR / "triplets_eval.json"

random.seed(42)
np.random.seed(42)


# ── Hard-Negative Cluster Definitions ─────────────────────────────────────────
# Each cluster contains indices into the dataset that are topically adjacent.
# Negatives are drawn from *other* clusters first (hard), then any (easy).

TOPIC_CLUSTERS = {
    "oop_core":        [0, 1, 2, 3, 12, 14, 20, 21, 22, 24],   # inheritance, encapsulation, poly…
    "data_types":      [4, 5, 6, 7, 8, 9],                      # int, float, char, String…
    "class_mechanics": [10, 11, 12, 13, 14],                    # constructor, this, super…
    "arrays":          [15, 16, 17, 18, 23],                    # arrays, ArrayList, jagged…
    "language_basics": [10, 19, 25, 26, 27, 28, 29],            # JVM, access mod, comments…
}


def cluster_of(idx: int) -> str | None:
    for cluster_name, indices in TOPIC_CLUSTERS.items():
        if idx in indices:
            return cluster_name
    return None


def pick_hard_negative(idx: int, all_items: list[dict]) -> str:
    """
    Return the answer of an item from the SAME broad domain but a DIFFERENT
    cluster (confusable concept).  Falls back to random if mapping not found.
    """
    my_cluster = cluster_of(idx)
    # Prefer items in adjacent clusters (same domain family)
    adjacent_clusters = [
        "oop_core", "class_mechanics"
    ] if my_cluster in ("oop_core", "class_mechanics", "arrays") else [
        "data_types", "language_basics"
    ]

    candidates = []
    for c in adjacent_clusters:
        if c != my_cluster:
            candidates.extend(TOPIC_CLUSTERS[c])

    # Exclude self
    candidates = [i for i in candidates if i != idx]

    if not candidates:
        # Fallback: any other item
        candidates = [i for i in range(len(all_items)) if i != idx]

    chosen = random.choice(candidates)
    return all_items[chosen]["answer"]


def pick_easy_negative(idx: int, all_items: list[dict]) -> str:
    """Return an answer from a completely different cluster."""
    my_cluster = cluster_of(idx)
    candidates = []
    for c, idxs in TOPIC_CLUSTERS.items():
        if c != my_cluster:
            candidates.extend(idxs)
    candidates = [i for i in candidates if i != idx]
    if not candidates:
        candidates = [i for i in range(len(all_items)) if i != idx]
    chosen = random.choice(candidates)
    return all_items[chosen]["answer"]


def build_triplets(items: list[dict]) -> list[dict]:
    """
    For each QA item generate TWO triplets:
      1. (query, correct_answer, hard_negative)
      2. (query, correct_answer, easy_negative)
    This doubles the dataset size from 30 → 60 samples.
    """
    triplets = []
    for idx, item in enumerate(items):
        query    = item["question"]
        positive = item["answer"]
        hard_neg = pick_hard_negative(idx, items)
        easy_neg = pick_easy_negative(idx, items)

        triplets.append({
            "query":    query,
            "positive": positive,
            "negative": hard_neg,
            "neg_type": "hard",
        })
        if easy_neg != hard_neg:
            triplets.append({
                "query":    query,
                "positive": positive,
                "negative": easy_neg,
                "neg_type": "easy",
            })

    return triplets


def main():
    if not DATASET_PATH.exists():
        print(f"[ERROR] Dataset not found: {DATASET_PATH}")
        sys.exit(1)

    with open(DATASET_PATH, encoding="utf-8") as f:
        items = json.load(f)

    print(f"[INFO] Loaded {len(items)} QA pairs from dataset.json")

    all_triplets = build_triplets(items)
    random.shuffle(all_triplets)

    # 80 / 20 train / eval split
    split_at = int(len(all_triplets) * 0.8)
    train_triplets = all_triplets[:split_at]
    eval_triplets  = all_triplets[split_at:]

    with open(TRIPLETS_PATH, "w", encoding="utf-8") as f:
        json.dump(train_triplets, f, indent=2, ensure_ascii=False)

    with open(TRIPLETS_EVAL_PATH, "w", encoding="utf-8") as f:
        json.dump(eval_triplets, f, indent=2, ensure_ascii=False)

    print(f"[OK]   Training triplets : {len(train_triplets)}  → {TRIPLETS_PATH}")
    print(f"[OK]   Eval triplets     : {len(eval_triplets)}  → {TRIPLETS_EVAL_PATH}")
    hard_count = sum(1 for t in train_triplets if t["neg_type"] == "hard")
    easy_count = sum(1 for t in train_triplets if t["neg_type"] == "easy")
    print(f"[INFO] Breakdown — hard: {hard_count}, easy: {easy_count}")


if __name__ == "__main__":
    main()
