"""
Application configuration.
All values are read from environment variables (with sensible defaults).
Copy .env.template → .env and fill in secrets before running.
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # ── LLM: Groq (primary — fast, generous free tier) ───────────────────
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    # ── LLM: Gemini (fallback if GROQ_API_KEY is not set) ────────────────
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GENERATION_MODEL: str = os.getenv("GENERATION_MODEL", "gemini-2.0-flash")

    # ── Neo4j ─────────────────────────────────────────────────────────────
    NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "password")

    # ── Storage paths ─────────────────────────────────────────────────────
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "../uploads")
    FAISS_INDEX_PATH: str = os.getenv("FAISS_INDEX_PATH", "faiss_index.bin")
    FAISS_META_PATH: str = os.getenv("FAISS_META_PATH", "faiss_meta.json")

    # ── Local models (no API calls for embeddings / keywords) ────────────
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
    KEYWORD_MODEL: str = os.getenv("KEYWORD_MODEL", "all-MiniLM-L6-v2")

    # ── Pipeline tuning ───────────────────────────────────────────────────
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "600"))      # words per chunk
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "100"))  # words overlap
    TOP_K_KEYWORDS: int = int(os.getenv("TOP_K_KEYWORDS", "10"))
    TOP_K_VECTOR: int = int(os.getenv("TOP_K_VECTOR", "5"))

    # ── Security ──────────────────────────────────────────────────────────
    # X-Api-Key header value required on /upload and /chat.
    # Leave blank to disable auth (development only).
    API_KEY: str = os.getenv("API_KEY", "")

    # JWT secret — reserved for future stateful session support.
    JWT_SECRET: str = os.getenv("JWT_SECRET", "change-me-in-production")

    # Maximum upload file size in bytes (default: 10 MB).
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", str(10 * 1024 * 1024)))

    # slowapi rate-limit strings (requests / period).
    RATE_LIMIT_UPLOAD: str = os.getenv("RATE_LIMIT_UPLOAD", "5/minute")
    RATE_LIMIT_CHAT: str = os.getenv("RATE_LIMIT_CHAT", "30/minute")

    # Comma-separated allowed CORS origins.
    ALLOWED_ORIGINS: list[str] = [
        o.strip()
        for o in os.getenv(
            "ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
        ).split(",")
        if o.strip()
    ]


settings = Settings()
