"""
SemSaver Evaluation Pipeline v3
================================
Compares:
  - Baseline  : Groq/Llama-3.3-70b direct call (no retrieval, no context)
  - SemSaver  : Hybrid RAG via POST /chat (FAISS + Neo4j + Groq)

Using the SAME underlying LLM makes this a clean ablation study:
  "Does the RAG pipeline actually help?"

Falls back to Gemini for baseline if GROQ_API_KEY is not available.

Robust features:
  - Exponential back-off on 429 / rate-limit errors (max 3 retries)
  - SemSaver connection retries (max 2)
  - Per-question delay to stay within API quotas
  - Invalid-response detection + logging
  - Sanity check at the end

Usage:
  python evaluation/evaluation.py            # full 30 questions
  python evaluation/evaluation.py --limit 10 # first N questions
  python evaluation/evaluation.py --dry-run  # first 5 (smoke test)
"""

import argparse
import csv
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

# ── Optional: google-genai fallback ──────────────────────────────────────────
try:
    from google import genai
    from google.genai import types as genai_types
    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False

# ── Load .env from backend folder ─────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    _env_path = Path(__file__).parent.parent / "backend" / ".env"
    load_dotenv(dotenv_path=_env_path)
except ImportError:
    pass

# ── Paths ─────────────────────────────────────────────────────────────────────
EVAL_DIR     = Path(__file__).parent
DATASET_PATH = EVAL_DIR / "dataset.json"
RESULTS_JSON = EVAL_DIR / "results.json"
RESULTS_CSV  = EVAL_DIR / "results.csv"
LOG_PATH     = EVAL_DIR / "eval.log"

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("semsaver_eval")

# ── Tuneables ─────────────────────────────────────────────────────────────────
INTER_QUESTION_DELAY = 2          # seconds between questions
RETRY_DELAYS         = [5, 15, 30]  # back-off on rate-limit
SEMSAVER_RETRIES     = 2          # connection retries for /chat


# ══════════════════════════════════════════════════════════════════════════════
# 1. DATASET
# ══════════════════════════════════════════════════════════════════════════════

def load_dataset(path: Path) -> list:
    if not path.exists():
        logger.error(f"Dataset not found: {path}")
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    logger.info(f"Loaded {len(data)} questions from {path.name}")
    return data


# ══════════════════════════════════════════════════════════════════════════════
# 2. SYSTEM CONNECTORS
# ══════════════════════════════════════════════════════════════════════════════

# ── Groq singleton ────────────────────────────────────────────────────────────
_groq_client = None

def _get_groq(api_key: str):
    global _groq_client
    if _groq_client is None:
        from groq import Groq
        _groq_client = Groq(api_key=api_key)
    return _groq_client


# ── Gemini singleton ──────────────────────────────────────────────────────────
_gemini_client = None

def _get_gemini(api_key: str):
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = genai.Client(api_key=api_key)
    return _gemini_client


def _call_with_retry(call_fn, label: str) -> str:
    """
    Execute call_fn(); retry up to len(RETRY_DELAYS) times on rate-limit errors.
    Returns answer string (may be "ERROR: …" on failure).
    """
    for attempt, wait in enumerate(RETRY_DELAYS, 1):
        try:
            return call_fn()
        except Exception as exc:
            err = str(exc)
            is_quota = any(kw in err for kw in
                           ["429", "RESOURCE_EXHAUSTED", "rate_limit",
                            "RateLimitError", "quota"])
            if is_quota and attempt < len(RETRY_DELAYS):
                logger.warning(
                    f"  {label} rate-limit on attempt {attempt}. "
                    f"Waiting {wait}s…"
                )
                time.sleep(wait)
                continue
            logger.warning(f"  {label} error (attempt {attempt}): {exc}")
            return f"ERROR: {exc}"
    return f"ERROR: {label} rate-limit — all retries exhausted"


def groq_baseline(query: str, groq_api_key: str,
                  model: str = "llama-3.3-70b-versatile") -> dict:
    """
    Direct Groq (Llama) call — NO retrieval context.
    Same LLM as SemSaver, but without any RAG pipeline.
    Returns: { answer, response_time, attempts }
    """
    prompt = (
        "You are a helpful assistant. Answer the following question "
        "concisely and accurately in 1-3 sentences. "
        "Do not say you don't know; give the best answer you can.\n\n"
        f"Question: {query}"
    )

    client = _get_groq(groq_api_key)
    t0 = time.perf_counter()

    def call():
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=512,
        )
        return resp.choices[0].message.content.strip()

    answer = _call_with_retry(call, "Groq-baseline")
    elapsed = round(time.perf_counter() - t0, 3)
    return {"answer": answer, "response_time": elapsed}


def gemini_baseline(query: str, gemini_api_key: str,
                    model: str = "gemini-2.0-flash") -> dict:
    """
    Direct Gemini call — NO retrieval context (fallback baseline).
    Returns: { answer, response_time }
    """
    if not _GENAI_AVAILABLE:
        return {"answer": "ERROR: google-genai not installed",
                "response_time": 0.0}

    prompt = (
        "You are a helpful assistant. Answer the following question "
        "concisely and accurately in 1-3 sentences.\n\n"
        f"Question: {query}"
    )

    client = _get_gemini(gemini_api_key)
    t0 = time.perf_counter()

    def call():
        resp = client.models.generate_content(
            model=model,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=512,
            ),
        )
        return resp.text.strip() if resp.text else "ERROR: Empty response"

    answer = _call_with_retry(call, "Gemini-baseline")
    elapsed = round(time.perf_counter() - t0, 3)
    return {"answer": answer, "response_time": elapsed}


def semsaver_system(query: str, base_url: str, api_key: str = "") -> dict:
    """
    SemSaver POST /chat — Hybrid RAG (FAISS + Neo4j + Groq).
    Retries SEMSAVER_RETRIES times on connection errors.
    Returns: { answer, sources, confidence, graph_path, response_time }
    """
    url = f"{base_url.rstrip('/')}/chat"
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-Api-Key"] = api_key

    t0 = time.perf_counter()

    for attempt in range(1, SEMSAVER_RETRIES + 2):
        try:
            resp = requests.post(
                url, json={"query": query},
                headers=headers, timeout=60,
            )
            resp.raise_for_status()
            data       = resp.json()
            answer     = data.get("answer",     "ERROR: No answer field")
            sources    = data.get("sources",    [])
            confidence = data.get("confidence", 0.0)
            graph_path = data.get("graph_path", [])
            elapsed    = round(time.perf_counter() - t0, 3)
            return {
                "answer": answer, "sources": sources,
                "confidence": confidence, "graph_path": graph_path,
                "response_time": elapsed,
            }
        except requests.exceptions.ConnectionError:
            if attempt <= SEMSAVER_RETRIES:
                logger.warning(
                    f"  SemSaver connection refused (attempt {attempt}). "
                    "Retrying in 3s…"
                )
                time.sleep(3)
                continue
            logger.error("  SemSaver unreachable — backend may be down.")
            elapsed = round(time.perf_counter() - t0, 3)
            return {
                "answer": "ERROR: Backend not reachable",
                "sources": [], "confidence": 0.0,
                "graph_path": [], "response_time": elapsed,
            }
        except Exception as exc:
            logger.warning(f"  SemSaver error: {exc}")
            elapsed = round(time.perf_counter() - t0, 3)
            return {
                "answer": f"ERROR: {exc}",
                "sources": [], "confidence": 0.0,
                "graph_path": [], "response_time": elapsed,
            }

    elapsed = round(time.perf_counter() - t0, 3)
    return {"answer": "ERROR: exhausted retries", "sources": [],
            "confidence": 0.0, "graph_path": [], "response_time": elapsed}


# ══════════════════════════════════════════════════════════════════════════════
# 3. SCORING
# ══════════════════════════════════════════════════════════════════════════════

def score_answer(predicted: str, ground_truth: str) -> float:
    """
    Graded scoring:
      1.0  — exact / token-set / substring match (case-insensitive)
      0.5  — ≥60% key-term (>3 chars) overlap
      0.25 — ≥30% key-term overlap
      0.0  — no meaningful match or ERROR
    """
    if predicted.upper().startswith("ERROR"):
        return 0.0

    pred = predicted.lower().strip()
    gt   = ground_truth.lower().strip()

    if pred == gt:
        return 1.0
    if set(pred.split()) == set(gt.split()):
        return 1.0
    if gt in pred or pred in gt:
        return 1.0

    key_terms = [t for t in gt.split() if len(t) > 3]
    if key_terms:
        hit   = sum(1 for t in key_terms if t in pred)
        ratio = hit / len(key_terms)
        if ratio >= 0.6:
            return 0.5
        if ratio >= 0.3:
            return 0.25

    return 0.0


def is_valid_answer(answer: str) -> bool:
    if answer.upper().startswith("ERROR"):
        return False
    return len(answer.strip()) >= 10


# ══════════════════════════════════════════════════════════════════════════════
# 4. MULTI-HOP DETECTION
# ══════════════════════════════════════════════════════════════════════════════

_MULTI_HOP_KW = {"before", "prerequisite", "relation",
                 "after", "depend", "order", "chain", "prior"}


def is_multi_hop(question: str) -> bool:
    q = question.lower()
    return any(kw in q for kw in _MULTI_HOP_KW)


def check_multi_hop_success(ss_data: dict, ss_score: float) -> bool:
    graph_path = ss_data.get("graph_path", [])
    sources    = ss_data.get("sources",    [])
    confidence = ss_data.get("confidence", 0.0)
    if len(graph_path) >= 2 and ss_score > 0:
        return True
    if sources and confidence > 0.15 and ss_score >= 0.25:
        return True
    return False


# ══════════════════════════════════════════════════════════════════════════════
# 5. EVALUATION LOOP
# ══════════════════════════════════════════════════════════════════════════════

def run_evaluation(
    dataset: list,
    base_url: str,
    groq_api_key: str,
    gemini_api_key: str,
    semsaver_api_key: str,
    baseline_model: str,
    use_groq_baseline: bool,
) -> list:
    results   = []
    invalid_q = []

    for idx, item in enumerate(dataset, 1):
        question    = item["question"]
        ground_truth = item["answer"]

        logger.info("─" * 64)
        logger.info(f"[{idx}/{len(dataset)}] {question}")

        # ── Baseline call ──────────────────────────────────────────────────
        if use_groq_baseline:
            logger.info("  → Groq baseline (no retrieval)…")
            b_data   = groq_baseline(question, groq_api_key,
                                     model=baseline_model)
            b_label  = "groq_no_rag"
        else:
            logger.info("  → Gemini baseline (no retrieval)…")
            b_data   = gemini_baseline(question, gemini_api_key,
                                       model=baseline_model)
            b_label  = "gemini_no_rag"

        b_answer = b_data["answer"]
        b_score  = score_answer(b_answer, ground_truth)
        b_valid  = is_valid_answer(b_answer)
        logger.info(
            f"  ← Baseline ({b_data['response_time']}s): "
            f"{b_answer[:90]}  [score={b_score}]"
        )

        # ── SemSaver RAG ───────────────────────────────────────────────────
        logger.info("  → SemSaver RAG…")
        ss_data   = semsaver_system(question, base_url, semsaver_api_key)
        ss_answer = ss_data["answer"]
        ss_score  = score_answer(ss_answer, ground_truth)
        ss_valid  = is_valid_answer(ss_answer)
        logger.info(
            f"  ← SemSaver ({ss_data['response_time']}s, "
            f"conf={ss_data['confidence']:.3f}, "
            f"sources={ss_data['sources']}): "
            f"{ss_answer[:90]}  [score={ss_score}]"
        )

        if not b_valid or not ss_valid:
            invalid_q.append(idx)
            logger.warning(
                f"  ⚠ Invalid response — "
                f"baseline_valid={b_valid}, semsaver_valid={ss_valid}"
            )

        mh        = is_multi_hop(question)
        mh_ok     = check_multi_hop_success(ss_data, ss_score) if mh else None

        results.append({
            "id":                      idx,
            "question":                question,
            "ground_truth":            ground_truth,
            "baseline_label":          b_label,
            # Baseline
            "gemini_answer":           b_answer,
            "gemini_score":            b_score,
            "gemini_valid":            b_valid,
            "gemini_response_time":    b_data["response_time"],
            # SemSaver
            "semsaver_answer":         ss_answer,
            "semsaver_score":          ss_score,
            "semsaver_valid":          ss_valid,
            "semsaver_response_time":  ss_data["response_time"],
            "semsaver_sources":        ss_data["sources"],
            "semsaver_confidence":     ss_data["confidence"],
            "semsaver_graph_path":     ss_data["graph_path"],
            # Multi-hop
            "multi_hop_question":      mh,
            "multi_hop_success":       mh_ok,
        })

        if idx < len(dataset):
            time.sleep(INTER_QUESTION_DELAY)

    if invalid_q:
        logger.warning(f"\n⚠ Questions with invalid answers: {invalid_q}")

    return results


# ══════════════════════════════════════════════════════════════════════════════
# 6. METRICS
# ══════════════════════════════════════════════════════════════════════════════

def compute_metrics(results: list) -> dict:
    n = len(results)
    if n == 0:
        return {}

    g_scores  = [r["gemini_score"]   for r in results]
    ss_scores = [r["semsaver_score"] for r in results]

    def breakdown(scores, valid_flags):
        return {
            "average_accuracy": round(sum(scores) / len(scores), 4) if scores else 0.0,
            "exact_match":   sum(1 for s in scores if s == 1.0),
            "partial_match": sum(1 for s in scores if s == 0.5),
            "quarter_match": sum(1 for s in scores if s == 0.25),
            "wrong":         sum(1 for s in scores if s == 0.0),
            "invalid":       sum(1 for v in valid_flags if not v),
            "total":         n,
        }

    mh_results = [r for r in results if r["multi_hop_question"]]
    mh_correct = sum(1 for r in mh_results if r["multi_hop_success"] is True)

    return {
        "total_questions": n,
        "baseline_label":  results[0]["baseline_label"] if results else "unknown",
        "gemini":   breakdown(g_scores,  [r["gemini_valid"]   for r in results]),
        "semsaver": breakdown(ss_scores, [r["semsaver_valid"] for r in results]),
        "multi_hop": {
            "total":            len(mh_results),
            "semsaver_correct": mh_correct,
        },
    }


# ══════════════════════════════════════════════════════════════════════════════
# 7. OUTPUT
# ══════════════════════════════════════════════════════════════════════════════

def save_json(results: list, metrics: dict, path: Path) -> None:
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "metrics":      metrics,
        "results":      results,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    logger.info(f"Results JSON → {path}")


def save_csv(results: list, path: Path) -> None:
    if not results:
        return
    fields = [
        "id", "question", "ground_truth",
        "baseline_label",
        "gemini_answer", "gemini_score", "gemini_valid", "gemini_response_time",
        "semsaver_answer", "semsaver_score", "semsaver_valid",
        "semsaver_response_time", "semsaver_confidence",
        "multi_hop_question", "multi_hop_success",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(results)
    logger.info(f"Results CSV  → {path}")


def print_summary(metrics: dict, results: list) -> None:
    sep   = "═" * 68
    g     = metrics.get("gemini",   {})
    s     = metrics.get("semsaver", {})
    mh    = metrics.get("multi_hop", {})
    g_acc = g.get("average_accuracy", 0)
    s_acc = s.get("average_accuracy", 0)
    blbl  = metrics.get("baseline_label", "Baseline (no RAG)")

    print(f"\n{sep}")
    print("  SEMSAVER EVALUATION RESULTS")
    print(f"  Baseline: {blbl}")
    print(sep)
    print(f"\n{'Metric':<34} {'Baseline':>10} {'SemSaver':>10}")
    print("-" * 56)
    print(f"{'Average Accuracy':<34} {g_acc:>10.4f} {s_acc:>10.4f}")
    print(f"{'Exact Match (1.0)':<34} {g.get('exact_match',0):>10} {s.get('exact_match',0):>10}")
    print(f"{'Partial Match (0.5)':<34} {g.get('partial_match',0):>10} {s.get('partial_match',0):>10}")
    print(f"{'Quarter Match (0.25)':<34} {g.get('quarter_match',0):>10} {s.get('quarter_match',0):>10}")
    print(f"{'Wrong (0.0)':<34} {g.get('wrong',0):>10} {s.get('wrong',0):>10}")
    print(f"{'Invalid Responses':<34} {g.get('invalid',0):>10} {s.get('invalid',0):>10}")
    print(f"{'Total Questions':<34} {g.get('total',0):>10} {s.get('total',0):>10}")

    if mh.get("total", 0) > 0:
        print(f"\n{'Multi-hop Qs (total)':<34} {mh['total']:>10}")
        print(f"{'SemSaver multi-hop correct':<34} {mh['semsaver_correct']:>10}")

    diff = round(s_acc - g_acc, 4)
    print(f"\n{sep}")
    if diff > 0:
        pct = round(diff * 100, 1)
        print(f"  🏆  SemSaver WINS  |  +{diff:.4f} ({pct}%) accuracy improvement over {blbl}")
    elif diff < 0:
        print(f"  📊  Baseline leads by +{abs(diff):.4f} accuracy points")
    else:
        print("  📊  Tied performance")
    print(sep)

    # ── Top 3: SemSaver beat baseline ─────────────────────────────────────
    wins = sorted(
        [r for r in results if r["semsaver_score"] > r["gemini_score"]],
        key=lambda r: r["semsaver_score"] - r["gemini_score"],
        reverse=True,
    )
    if wins:
        print(f"\n📌  Top cases where SemSaver beat baseline ({len(wins)} total):\n")
        for i, r in enumerate(wins[:3], 1):
            print(f"  [{i}] Q: {r['question']}")
            print(f"       GT      : {r['ground_truth']}")
            ba = r['gemini_answer']
            sa = r['semsaver_answer']
            print(f"       Baseline: {ba[:110]}  (score={r['gemini_score']})")
            print(f"       SemSaver: {sa[:110]}  (score={r['semsaver_score']})")
            if r["semsaver_sources"]:
                print(f"       Sources : {r['semsaver_sources']}")
            print()
    else:
        print("\n  No cases where SemSaver outscored baseline detected.")

    print(f"{sep}\n")


# ══════════════════════════════════════════════════════════════════════════════
# 8. SANITY CHECK
# ══════════════════════════════════════════════════════════════════════════════

def sanity_check(metrics: dict, results: list) -> None:
    issues = []
    g  = metrics.get("gemini",   {})
    s  = metrics.get("semsaver", {})

    s_correct = s.get("exact_match", 0) + s.get("partial_match", 0)
    g_correct = g.get("exact_match", 0) + g.get("partial_match", 0)

    if s_correct < 5:
        issues.append(
            f"SemSaver has only {s_correct} correct answers (exact+partial ≥ 0.5). "
            "Ensure documents are ingested — backend shows "
            f"{results[0].get('semsaver_sources', 'unknown sources')}."
        )
    if s.get("average_accuracy", 0) <= g.get("average_accuracy", 0):
        issues.append(
            f"SemSaver accuracy ({s.get('average_accuracy',0):.4f}) is NOT above "
            f"baseline ({g.get('average_accuracy',0):.4f}). "
            "Consider: (1) uploading more/better documents, "
            "(2) checking FAISS index has enough chunks."
        )
    if s.get("invalid", 0) > 5:
        issues.append(
            f"{s.get('invalid',0)} SemSaver responses were ERRORs — "
            "backend may have crashed."
        )
    if g.get("invalid", 0) > 5:
        issues.append(
            f"{g.get('invalid',0)} baseline responses were ERRORs — "
            "API quota may be exhausted."
        )

    print()
    if issues:
        print("⚠️  SANITY CHECK WARNINGS:")
        for w in issues:
            print(f"   • {w}")
    else:
        bbl  = metrics.get("baseline_label", "baseline")
        diff = round(
            s.get("average_accuracy", 0) - g.get("average_accuracy", 0), 4
        )
        print(
            f"✅  Sanity check PASSED\n"
            f"   SemSaver accuracy:  {s.get('average_accuracy',0):.4f}\n"
            f"   {bbl} accuracy: {g.get('average_accuracy',0):.4f}\n"
            f"   Delta:              +{diff:.4f}"
        )
    print()


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="SemSaver Evaluation Pipeline v3")
    parser.add_argument("--base-url",      default="http://localhost:8000")
    parser.add_argument("--api-key",       default=os.getenv("API_KEY", ""))
    parser.add_argument("--groq-key",      default=os.getenv("GROQ_API_KEY", ""))
    parser.add_argument("--gemini-key",    default=os.getenv("GEMINI_API_KEY", ""))
    parser.add_argument("--groq-model",    default=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"))
    parser.add_argument("--gemini-model",  default="gemini-2.0-flash")
    parser.add_argument("--force-gemini",  action="store_true",
                        help="Use Gemini as baseline even if Groq key is available")
    parser.add_argument("--limit",         type=int, default=None)
    parser.add_argument("--dry-run",       action="store_true",
                        help="Evaluate first 5 questions only")
    args = parser.parse_args()

    # ── Choose baseline ───────────────────────────────────────────────────
    use_groq_baseline = bool(args.groq_key) and not args.force_gemini
    if use_groq_baseline:
        baseline_model = args.groq_model
        logger.info(f"Baseline: Groq/{baseline_model} (no RAG context)")
    else:
        if not args.gemini_key:
            logger.error(
                "No GROQ_API_KEY or GEMINI_API_KEY found. "
                "Set one in backend/.env or pass --groq-key / --gemini-key."
            )
            sys.exit(1)
        if not _GENAI_AVAILABLE:
            logger.error(
                "google-genai package not found. "
                "Run: pip install google-genai"
            )
            sys.exit(1)
        baseline_model = args.gemini_model
        logger.info(f"Baseline: Gemini/{baseline_model} (no RAG context)")

    # ── Verify backend ────────────────────────────────────────────────────
    health_url = f"{args.base_url.rstrip('/')}/health"
    try:
        hr     = requests.get(health_url, timeout=5)
        hr.raise_for_status()
        health = hr.json()
        chunks = health.get("total_chunks", 0)
        gen    = health.get("generation_model", "?")
        logger.info(
            f"Backend online — chunks={chunks}, "
            f"generation_model={gen}, auth={health.get('auth_enabled')}"
        )
        if chunks == 0:
            logger.warning(
                "⚠ Backend reports 0 indexed chunks. "
                "Upload documents via /upload before running evaluation."
            )
    except Exception as exc:
        logger.error(
            f"Cannot reach backend at {health_url}: {exc}\n"
            "Start it with:\n"
            "  cd backend\n"
            "  venv\\Scripts\\python.exe -m uvicorn main:app --port 8000"
        )
        sys.exit(1)

    # ── Load dataset ──────────────────────────────────────────────────────
    dataset = load_dataset(DATASET_PATH)
    limit   = 5 if args.dry_run else args.limit
    if limit:
        dataset = dataset[:limit]
        logger.info(f"Using first {limit} questions.")

    logger.info(
        f"\nEvaluation start — {len(dataset)} questions | "
        f"baseline={baseline_model} | delay={INTER_QUESTION_DELAY}s"
    )

    # ── Run evaluation ────────────────────────────────────────────────────
    results = run_evaluation(
        dataset,
        base_url=args.base_url,
        groq_api_key=args.groq_key,
        gemini_api_key=args.gemini_key,
        semsaver_api_key=args.api_key,
        baseline_model=baseline_model,
        use_groq_baseline=use_groq_baseline,
    )

    # ── Metrics + outputs ─────────────────────────────────────────────────
    metrics = compute_metrics(results)
    save_json(results, metrics, RESULTS_JSON)
    save_csv(results, RESULTS_CSV)
    print_summary(metrics, results)
    sanity_check(metrics, results)

    logger.info("Evaluation complete.")


if __name__ == "__main__":
    main()
