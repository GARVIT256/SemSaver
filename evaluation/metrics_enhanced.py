"""
metrics_enhanced.py  -  SemSaver Enhanced Evaluation Metrics
=============================================================
New metrics beyond the original keyword-overlap scoring:

  1. Semantic Similarity Score  (sentence-transformers cosine)
  2. Token-level F1             (precision/recall on token overlap)
  3. BLEU-1                     (unigram precision)
  4. Source Coverage Rate       (did SemSaver cite sources?)
  5. Confidence Calibration     (does high confidence => higher score?)
  6. Latency Comparison         (average response times)
  7. Per-category Accuracy      (factual / conceptual / multi-hop / comparison)
  8. Retrieval Precision@K      (embedding model: base vs fine-tuned)
  9. Answer Length Adequacy     (not too short, not too verbose)
 10. Failure Mode Analysis      (ERROR rate, "insufficient info" rate)

Usage:
    python evaluation/metrics_enhanced.py
    python evaluation/metrics_enhanced.py --dataset evaluation/dataset_combined.json
    python evaluation/metrics_enhanced.py --dataset evaluation/chapter9_dataset.json

Outputs:
    evaluation/enhanced_results.json
"""

import argparse
import json
import logging
import math
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("enhanced_eval")

ROOT         = Path(__file__).resolve().parent.parent
EVAL_DIR     = ROOT / "evaluation"
FT_DIR       = ROOT / "finetuning"
RESULTS_PATH = EVAL_DIR / "enhanced_results.json"
BASE_MODEL   = "all-MiniLM-L6-v2"
FT_MODEL     = FT_DIR / "semsaver-ft-model"

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=ROOT / "backend" / ".env")
except ImportError:
    pass

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
SEMSAVER_URL = "http://localhost:8000"
INTER_DELAY  = 5.0


# ══════════════════════════════════════════════════════════════════════════════
# TOKENIZER
# ══════════════════════════════════════════════════════════════════════════════

def tokenize(text: str) -> list[str]:
    return re.findall(r"\b\w+\b", text.lower())


# ══════════════════════════════════════════════════════════════════════════════
# METRIC FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def token_f1(pred: str, ref: str) -> float:
    p_toks = tokenize(pred)
    r_toks = tokenize(ref)
    if not p_toks or not r_toks:
        return 0.0
    common = set(p_toks) & set(r_toks)
    if not common:
        return 0.0
    prec = len([t for t in p_toks if t in common]) / len(p_toks)
    rec  = len([t for t in r_toks if t in common]) / len(r_toks)
    if prec + rec == 0:
        return 0.0
    return 2 * prec * rec / (prec + rec)


def bleu1(pred: str, ref: str) -> float:
    p_toks = tokenize(pred)
    r_toks = set(tokenize(ref))
    if not p_toks:
        return 0.0
    hits = sum(1 for t in p_toks if t in r_toks)
    prec = hits / len(p_toks)
    # Brevity penalty
    bp = 1.0 if len(p_toks) >= len(tokenize(ref)) else math.exp(1 - len(tokenize(ref)) / max(len(p_toks), 1))
    return round(prec * bp, 4)


def answer_length_score(pred: str, ref: str) -> float:
    """Score 1.0 if answer length is within 0.3x-3x of reference length."""
    pl, rl = len(pred.split()), len(ref.split())
    if rl == 0:
        return 0.0
    ratio = pl / rl
    if 0.3 <= ratio <= 3.0:
        return 1.0
    elif ratio < 0.3:
        return ratio / 0.3
    else:
        return max(0.0, 1.0 - (ratio - 3.0) / 3.0)


def is_insufficient(answer: str) -> bool:
    phrases = ["insufficient information", "not found", "not provided",
               "no information", "cannot answer", "unable to find"]
    a = answer.lower()
    return any(p in a for p in phrases)


def detect_category(question: str) -> str:
    q = question.lower()
    if any(w in q for w in ["before", "prerequisite", "depends", "prior", "order", "chain", "need to know"]):
        return "multi_hop"
    if any(w in q for w in ["difference", "compare", "versus", "vs", "contrast", "between"]):
        return "comparison"
    if any(w in q for w in ["what is", "define", "definition", "mean"]):
        return "factual"
    if any(w in q for w in ["how", "why", "when", "explain", "describe", "purpose"]):
        return "conceptual"
    return "factual"


# ══════════════════════════════════════════════════════════════════════════════
# SYSTEM CALLS
# ══════════════════════════════════════════════════════════════════════════════

def call_llm(question: str) -> dict:
    """Primary LLM call for baseline. Tries Groq, falls back to Gemini."""
    t0 = time.perf_counter()
    answer = None
    
    # 1. Groq
    if GROQ_API_KEY:
        try:
            from groq import Groq
            client = Groq(api_key=GROQ_API_KEY)
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": f"Answer concisely (1-3 sentences): {question}"}],
                temperature=0.1,
                max_tokens=256,
            )
            answer = resp.choices[0].message.content.strip()
        except Exception as e:
            logger.debug(f"Baseline Groq failed: {e}")

    # 2. Gemini fallback
    if answer is None:
        try:
            import google.generativeai as genai
            api_key = os.getenv("GEMINI_API_KEY", "")
            if api_key:
                genai.configure(api_key=api_key)
                model_obj = genai.GenerativeModel("gemini-2.0-flash")
                resp = model_obj.generate_content(f"Answer concisely (1-3 sentences): {question}")
                answer = resp.text.strip()
        except Exception as e:
            logger.debug(f"Baseline Gemini failed: {e}")

    if answer is None:
        answer = "ERROR: No LLM available for baseline."

    elapsed = round(time.perf_counter() - t0, 3)
    return {"answer": answer, "response_time": elapsed}


def call_semsaver(question: str) -> dict:
    t0 = time.perf_counter()
    try:
        resp = requests.post(
            f"{SEMSAVER_URL}/chat",
            json={"query": question},
            headers={"Content-Type": "application/json"},
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        return {
            "answer":      data.get("answer", "ERROR: no answer"),
            "sources":     data.get("sources", []),
            "confidence":  data.get("confidence", 0.0),
            "graph_path":  data.get("graph_path", []),
            "response_time": round(time.perf_counter() - t0, 3),
        }
    except Exception as e:
        return {
            "answer": f"ERROR: {e}", "sources": [], "confidence": 0.0,
            "graph_path": [], "response_time": round(time.perf_counter() - t0, 3),
        }


# ══════════════════════════════════════════════════════════════════════════════
# EMBEDDING METRICS  (base vs fine-tuned)
# ══════════════════════════════════════════════════════════════════════════════

def compute_retrieval_metrics(dataset: list) -> dict:
    """Recall@K and MRR for base and fine-tuned models."""
    try:
        from sentence_transformers import SentenceTransformer
        import numpy as np
    except ImportError:
        logger.warning("sentence-transformers not installed — skipping embedding metrics")
        return {}

    corpus  = [item["answer"]   for item in dataset]
    queries = [item["question"] for item in dataset]
    correct = list(range(len(dataset)))

    results = {}
    models = {"base_model": BASE_MODEL}
    if FT_MODEL.exists():
        models["finetuned_model"] = str(FT_MODEL)
    else:
        logger.warning("Fine-tuned model not found — only base model evaluated")

    for label, model_path in models.items():
        logger.info(f"Loading embedding model [{label}]: {model_path}")
        try:
            m = SentenceTransformer(str(model_path))
            c_vecs = np.array(m.encode(corpus,  normalize_embeddings=True, show_progress_bar=False), dtype=np.float32)
            q_vecs = np.array(m.encode(queries, normalize_embeddings=True, show_progress_bar=False), dtype=np.float32)

            def recall_at(k):
                hits = sum(1 for q, ci in zip(q_vecs, correct)
                           if ci in np.argsort(c_vecs @ q)[::-1][:k])
                return round(hits / len(correct), 4)

            def mrr():
                rrs = []
                for q, ci in zip(q_vecs, correct):
                    rank = int(np.where(np.argsort(c_vecs @ q)[::-1] == ci)[0][0]) + 1
                    rrs.append(1.0 / rank)
                return round(float(np.mean(rrs)), 4)

            # Positive-negative separation
            sep_gaps = []
            for i, (q, ci) in enumerate(zip(q_vecs, correct)):
                pos_sim = float(c_vecs[ci] @ q)
                neg_idx = (i + 1) % len(corpus)
                neg_sim = float(c_vecs[neg_idx] @ q)
                sep_gaps.append(pos_sim - neg_sim)

            results[label] = {
                "Recall@1":       recall_at(1),
                "Recall@3":       recall_at(3),
                "Recall@5":       recall_at(5),
                "MRR":            mrr(),
                "separation_gap": round(float(np.mean(sep_gaps)), 4),
            }
            logger.info(f"  [{label}] {results[label]}")
        except Exception as e:
            logger.warning(f"  [{label}] error: {e}")
            results[label] = {}

    # Compute deltas if both exist
    if "base_model" in results and "finetuned_model" in results:
        b, ft = results["base_model"], results["finetuned_model"]
        results["delta"] = {k: round(ft.get(k, 0) - b.get(k, 0), 4) for k in b}

    return results


# ══════════════════════════════════════════════════════════════════════════════
# SEMANTIC SIMILARITY
# ══════════════════════════════════════════════════════════════════════════════

def compute_semantic_sim(pred: str, ref: str, model) -> float:
    import numpy as np
    vecs = model.encode([pred, ref], normalize_embeddings=True, show_progress_bar=False)
    return float(np.dot(vecs[0], vecs[1]))


# ══════════════════════════════════════════════════════════════════════════════
# MAIN EVALUATION LOOP
# ══════════════════════════════════════════════════════════════════════════════

def run_enhanced_evaluation(dataset: list, use_semsaver: bool) -> list:
    results = []
    sem_model = None

    try:
        from sentence_transformers import SentenceTransformer
        sem_model = SentenceTransformer(BASE_MODEL)
        logger.info("Semantic similarity model loaded.")
    except Exception:
        logger.warning("Could not load SentenceTransformer — skipping semantic sim.")

    for idx, item in enumerate(dataset, 1):
        question    = item["question"]
        ground_truth = item["answer"]
        category    = detect_category(question)

        logger.info(f"[{idx}/{len(dataset)}] [{category}] {question[:80]}")

        # LLM baseline (Groq/Gemini)
        llm = call_llm(question)
        time.sleep(0.5)

        # SemSaver RAG
        ss = call_semsaver(question) if use_semsaver else {
            "answer": "SKIPPED", "sources": [], "confidence": 0.0,
            "graph_path": [], "response_time": 0.0
        }

        # Scores
        for system, answer in [("llm", llm["answer"]), ("semsaver", ss["answer"])]:
            pass  # computed below

        llm_tf1  = token_f1(llm["answer"],  ground_truth)
        ss_tf1   = token_f1(ss["answer"],   ground_truth)
        llm_b1   = bleu1(llm["answer"],     ground_truth)
        ss_b1    = bleu1(ss["answer"],      ground_truth)
        llm_len  = answer_length_score(llm["answer"],  ground_truth)
        ss_len   = answer_length_score(ss["answer"],   ground_truth)
        llm_insuf = is_insufficient(llm["answer"])
        ss_insuf  = is_insufficient(ss["answer"])

        llm_sem = ss_sem = 0.0
        if sem_model and not llm["answer"].startswith("ERROR") and not ss["answer"].startswith("ERROR"):
            llm_sem = compute_semantic_sim(llm["answer"], ground_truth, sem_model)
            ss_sem  = compute_semantic_sim(ss["answer"],  ground_truth, sem_model)

        row = {
            "id":            idx,
            "question":      question,
            "ground_truth":  ground_truth,
            "category":      category,
            # LLM
            "llm_answer":          llm["answer"],
            "llm_response_time":   llm["response_time"],
            "llm_token_f1":        round(llm_tf1, 4),
            "llm_bleu1":           llm_b1,
            "llm_semantic_sim":    round(llm_sem, 4),
            "llm_length_score":    round(llm_len, 4),
            "llm_insufficient":    llm_insuf,
            # SemSaver
            "ss_answer":           ss["answer"],
            "ss_response_time":    ss["response_time"],
            "ss_token_f1":         round(ss_tf1, 4),
            "ss_bleu1":            ss_b1,
            "ss_semantic_sim":     round(ss_sem, 4),
            "ss_length_score":     round(ss_len, 4),
            "ss_insufficient":     ss_insuf,
            "ss_sources":          ss["sources"],
            "ss_confidence":       ss["confidence"],
            "ss_has_sources":      len(ss["sources"]) > 0,
        }
        results.append(row)

        if idx < len(dataset):
            time.sleep(INTER_DELAY)

    return results


# ══════════════════════════════════════════════════════════════════════════════
# AGGREGATE METRICS
# ══════════════════════════════════════════════════════════════════════════════

def aggregate_metrics(results: list, retrieval: dict) -> dict:
    n = len(results)
    if n == 0:
        return {}

    def avg(key): return round(sum(r[key] for r in results) / n, 4)
    def count(key, val=True): return sum(1 for r in results if r[key] == val)

    # Per-category breakdown
    cats = defaultdict(lambda: defaultdict(list))
    for r in results:
        c = r["category"]
        cats[c]["llm_token_f1"].append(r["llm_token_f1"])
        cats[c]["ss_token_f1"].append(r["ss_token_f1"])
        cats[c]["llm_semantic_sim"].append(r["llm_semantic_sim"])
        cats[c]["ss_semantic_sim"].append(r["ss_semantic_sim"])

    cat_summary = {}
    for cat, metrics in cats.items():
        cat_summary[cat] = {
            k: round(sum(v) / len(v), 4) if v else 0.0
            for k, v in metrics.items()
        }
        cat_summary[cat]["count"] = len(metrics["llm_token_f1"])

    # Confidence calibration: does high confidence correlate with higher score?
    conf_buckets = {"low": [], "mid": [], "high": []}
    for r in results:
        c = r["ss_confidence"]
        score = r["ss_token_f1"]
        if c < 0.5:
            conf_buckets["low"].append(score)
        elif c < 0.75:
            conf_buckets["mid"].append(score)
        else:
            conf_buckets["high"].append(score)
    calibration = {
        k: round(sum(v) / len(v), 4) if v else 0.0
        for k, v in conf_buckets.items()
    }

    return {
        "total_questions": n,
        "overall": {
            "llm_avg_token_f1":      avg("llm_token_f1"),
            "ss_avg_token_f1":       avg("ss_token_f1"),
            "llm_avg_bleu1":         avg("llm_bleu1"),
            "ss_avg_bleu1":          avg("ss_bleu1"),
            "llm_avg_semantic_sim":  avg("llm_semantic_sim"),
            "ss_avg_semantic_sim":   avg("ss_semantic_sim"),
            "llm_avg_length_score":  avg("llm_length_score"),
            "ss_avg_length_score":   avg("ss_length_score"),
            "llm_avg_latency_s":     avg("llm_response_time"),
            "ss_avg_latency_s":      avg("ss_response_time"),
            "ss_source_coverage":    round(count("ss_has_sources") / n, 4),
            "llm_insufficient_rate": round(count("llm_insufficient") / n, 4),
            "ss_insufficient_rate":  round(count("ss_insufficient") / n, 4),
        },
        "delta": {
            "token_f1":      round(avg("ss_token_f1")      - avg("llm_token_f1"), 4),
            "bleu1":         round(avg("ss_bleu1")         - avg("llm_bleu1"), 4),
            "semantic_sim":  round(avg("ss_semantic_sim")  - avg("llm_semantic_sim"), 4),
            "latency_s":     round(avg("ss_response_time") - avg("llm_response_time"), 4),
        },
        "per_category":          cat_summary,
        "confidence_calibration": calibration,
        "retrieval_metrics":      retrieval,
    }


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dataset",      default=str(EVAL_DIR / "dataset_combined.json"))
    p.add_argument("--no-semsaver",  action="store_true", help="Skip live SemSaver calls")
    p.add_argument("--limit",        type=int, default=None)
    args = p.parse_args()

    if not GROQ_API_KEY and not os.getenv("GEMINI_API_KEY", ""):
        logger.error("Neither GROQ_API_KEY nor GEMINI_API_KEY found"); sys.exit(1)
    try:
        from groq import Groq  # noqa
    except ImportError:
        logger.error("pip install groq"); sys.exit(1)

    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        logger.error(f"Dataset not found: {dataset_path}"); sys.exit(1)

    with open(dataset_path, encoding="utf-8") as f:
        dataset = json.load(f)

    if args.limit:
        dataset = dataset[:args.limit]
    logger.info(f"Dataset: {len(dataset)} questions from {dataset_path.name}")

    # Check SemSaver
    use_semsaver = not args.no_semsaver
    if use_semsaver:
        try:
            r = requests.get(f"{SEMSAVER_URL}/health", timeout=30)
            r.raise_for_status()
            logger.info(f"SemSaver online: {r.json()}")
        except Exception as e:
            logger.warning(f"SemSaver not reachable: {e} -- skipping live calls")
            use_semsaver = False

    logger.info("Computing retrieval metrics (embedding models)...")
    retrieval = compute_retrieval_metrics(dataset)

    logger.info("Running enhanced evaluation loop...")
    results = run_enhanced_evaluation(dataset, use_semsaver)

    metrics = aggregate_metrics(results, retrieval)

    output = {
        "dataset":  str(dataset_path),
        "metrics":  metrics,
        "results":  results,
    }
    with open(RESULTS_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved enhanced results -> {RESULTS_PATH}")

    # Print summary
    ov = metrics.get("overall", {})
    dl = metrics.get("delta", {})
    print("\n" + "="*65)
    print("  ENHANCED EVALUATION SUMMARY")
    print("="*65)
    print(f"  {'Metric':<35} {'LLM':>8}  {'SemSaver':>9}  {'Delta':>7}")
    print("-"*65)
    rows = [
        ("Token F1",          "llm_avg_token_f1",     "ss_avg_token_f1",     "token_f1"),
        ("BLEU-1",            "llm_avg_bleu1",         "ss_avg_bleu1",         "bleu1"),
        ("Semantic Sim",      "llm_avg_semantic_sim",  "ss_avg_semantic_sim",  "semantic_sim"),
        ("Avg Latency (s)",   "llm_avg_latency_s",     "ss_avg_latency_s",     "latency_s"),
    ]
    for label, lk, sk, dk in rows:
        lv = ov.get(lk, 0); sv = ov.get(sk, 0); dv = dl.get(dk, 0)
        print(f"  {label:<35} {lv:>8.4f}  {sv:>9.4f}  {dv:>+7.4f}")
    print(f"\n  Source Coverage:   {ov.get('ss_source_coverage', 0):.1%}")
    print(f"  LLM Insuff Rate:   {ov.get('llm_insufficient_rate', 0):.1%}")
    print(f"  SS  Insuff Rate:   {ov.get('ss_insufficient_rate',  0):.1%}")
    print("="*65)

    if retrieval:
        print("\n  RETRIEVAL METRICS (Embedding Models)")
        print("-"*65)
        for model_label, mdata in retrieval.items():
            if model_label == "delta" or not isinstance(mdata, dict):
                continue
            print(f"  [{model_label}]")
            for k, v in mdata.items():
                print(f"    {k:<20} = {v}")
        if "delta" in retrieval:
            print(f"  [delta (ft - base)]")
            for k, v in retrieval["delta"].items():
                arrow = "^" if v > 0 else ("v" if v < 0 else "~")
                print(f"    {k:<20} {v:+.4f}  {arrow}")
    print()


if __name__ == "__main__":
    main()
