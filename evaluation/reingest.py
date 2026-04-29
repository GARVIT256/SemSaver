"""
Re-ingest all PPTX files from /uploads into the SemSaver backend.
Run this ONCE to populate the FAISS index with all course material.

Usage:
  python evaluation/reingest.py
"""
import sys
import time
from pathlib import Path

import requests

UPLOADS_DIR = Path(__file__).parent.parent / "uploads"
BASE_URL    = "http://localhost:8000"
EXTS        = {".pptx", ".ppt", ".pdf"}


def ingest_file(path: Path) -> dict:
    url = f"{BASE_URL}/upload"
    with open(path, "rb") as f:
        resp = requests.post(
            url,
            files=[("files", (path.name, f,
                    "application/vnd.openxmlformats-officedocument"
                    ".presentationml.presentation"))],
            timeout=120,
        )
    resp.raise_for_status()
    return resp.json()


def main():
    files = sorted(
        p for p in UPLOADS_DIR.iterdir()
        if p.suffix.lower() in EXTS
    )
    if not files:
        print(f"No PPTX/PDF files found in {UPLOADS_DIR}")
        sys.exit(1)

    print(f"Found {len(files)} file(s) to ingest:\n")
    for f in files:
        print(f"  {f.name}  ({f.stat().st_size // 1024} KB)")

    print("\nStarting ingestion…\n")

    for i, path in enumerate(files, 1):
        print(f"[{i}/{len(files)}] Ingesting {path.name}…", end=" ", flush=True)
        try:
            result = ingest_file(path)
            summaries = result.get("summaries", [])
            chunks = sum(s.get("chunks_stored", 0) for s in summaries
                         if isinstance(s, dict))
            print(f"✅  {chunks} chunks stored")
        except Exception as exc:
            print(f"❌  ERROR: {exc}")
        # Small pause between uploads to let embeddings settle
        time.sleep(1)

    # Confirm final index size
    try:
        h = requests.get(f"{BASE_URL}/health", timeout=5).json()
        print(f"\nFinal index size: {h.get('total_chunks')} chunks")
    except Exception:
        pass

    print("\nIngestion complete. Now run the evaluation:")
    print("  python evaluation/evaluation.py\n")


if __name__ == "__main__":
    main()
