"""
Security module for SemSaver.

Provides:
  - API key authentication (FastAPI dependency)
  - Rate limiter instance (slowapi)
  - File upload validation (type, size, filename sanitisation)
  - Prompt injection guard
  - Safe error helper (no stack traces in responses)
  - Structured request logging
"""
import hashlib
import hmac
import logging
import re
import uuid
from pathlib import Path

from fastapi import Depends, Header, HTTPException, UploadFile, status

from config import settings

logger = logging.getLogger(__name__)

# ── Rate limiter ──────────────────────────────────────────────────────────────

_limiter = None


def get_limiter():
    """Return the singleton slowapi Limiter (lazy-init)."""
    global _limiter
    if _limiter is None:
        try:
            from slowapi import Limiter
            from slowapi.util import get_remote_address
            _limiter = Limiter(key_func=get_remote_address)
        except ImportError:
            logger.warning("slowapi not installed — rate limiting disabled.")
    return _limiter


# ── API-key authentication ────────────────────────────────────────────────────

async def verify_api_key(x_api_key: str = Header(default="")) -> None:
    """
    FastAPI dependency: validates X-Api-Key header.
    Uses constant-time comparison to prevent timing attacks.
    If API_KEY is not set in config, authentication is disabled (dev mode).
    """
    expected = settings.API_KEY
    if not expected:
        # No key configured → open access (warn once per startup)
        return

    # Constant-time comparison
    provided_hash = hashlib.sha256(x_api_key.encode()).digest()
    expected_hash = hashlib.sha256(expected.encode()).digest()

    if not hmac.compare_digest(provided_hash, expected_hash):
        logger.warning("Rejected request: invalid API key.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing API key.",
        )


# ── File upload validation ────────────────────────────────────────────────────

ALLOWED_EXTENSIONS = {".pdf", ".pptx", ".ppt"}
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.ms-powerpoint",
}


def sanitize_filename(original: str) -> str:
    """
    Return a safe filename: uuid4 prefix  stripped basename.
    Prevents directory traversal attacks.
    """
    basename = Path(original).name
    # Strip any path separators that slipped through
    safe = re.sub(r"[^\w\s\-.]", "_", basename)
    return f"{uuid.uuid4().hex}_{safe}"


async def validate_upload(file: UploadFile) -> bytes:
    """
    Read and validate an uploaded file.

    Checks:
      1. File extension is allowed (PDF / PPTX)
      2. File size ≤ MAX_FILE_SIZE bytes
      3. Returns the raw bytes for the caller to persist

    Raises HTTPException on any violation.
    """
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported file type '{suffix}'. "
                "Only PDF and PPTX files are accepted."
            ),
        )

    content = await file.read()

    if len(content) > settings.MAX_FILE_SIZE:
        size_mb = settings.MAX_FILE_SIZE / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of {size_mb:.0f} MB.",
        )

    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    return content


# ── Prompt injection guard ────────────────────────────────────────────────────

# Patterns that suggest prompt injection attempts
_INJECTION_PATTERNS = re.compile(
    r"("
    r"ignore\s+(?:all\s+)?(?:previous|prior|above)\s+instructions?"
    r"|forget\s+(?:your\s+)?(?:previous\s+)?instructions?"
    r"|act\s+as\s+(?:a\s+)?(?:system|admin|root|developer|jailbreak)"
    r"|you\s+are\s+now\s+(?:a\s+)?\w+"
    r"|disregard\s+(?:your\s+)?(?:previous\s+)?(?:instructions?|rules?|guidelines?)"
    r"|(?:new|different)\s+system\s+prompt"
    r"|jailbreak"
    r"|DAN\b"
    r"|SYSTEM\s*:"
    r")",
    re.IGNORECASE,
)


def sanitize_query(query: str) -> str:
    """
    Strip prompt-injection patterns from user query.
    Logs a warning (without the query content) when a match is found.
    """
    if _INJECTION_PATTERNS.search(query):
        logger.warning("Potential prompt injection attempt detected — patterns stripped.")
        query = _INJECTION_PATTERNS.sub("[REMOVED]", query)
    return query.strip()


# ── Safe error helper ─────────────────────────────────────────────────────────

def safe_error(msg: str, status_code: int = 500) -> HTTPException:
    """
    Return an HTTPException with a user-safe message.
    Call this instead of raising HTTPException with raw exception strings.
    """
    return HTTPException(status_code=status_code, detail=msg)


# ── Request logger ────────────────────────────────────────────────────────────

def log_request(endpoint: str, *, extra: dict | None = None) -> None:
    """
    Log a structured request entry.
    Never logs query content or file contents.
    """
    info: dict = {"endpoint": endpoint}
    if extra:
        # Only allow safe keys
        safe_keys = {"file_count", "file_names", "total_bytes", "graph_intent"}
        info.update({k: v for k, v in extra.items() if k in safe_keys})
    logger.info("REQUEST %s", info)
