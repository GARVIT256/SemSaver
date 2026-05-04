"""
FastAPI application — SemSaver Backend

Endpoints:
  POST /upload  — ingest PDF/PPTX files (fully local pipeline)
  POST /chat    — hybrid RAG query (local retrieval + Groq/Gemini generation)
  GET  /health  — health check

Security:
  - API key authentication (X-Api-Key header) via security.verify_api_key
  - Rate limiting via slowapi decorators (5/min upload, 30/min chat)
  - File validation (type, size, filename sanitation) via security.validate_upload
  - Prompt injection guard via security.sanitize_query
  - Safe error responses (no raw stack traces)
"""
import logging
import uuid
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import List

from fastapi import Depends, FastAPI, File, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import settings
import graph_store
import ingestion
import retrieval
import chat
import vector_store
import security

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── Rate limiter (optional — disabled if slowapi not installed) ───────────────
_limiter = security.get_limiter()


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    try:
        graph_store.create_indexes()
        logger.info("Neo4j indexes ready.")
    except Exception as e:
        logger.warning(f"Neo4j not available (graph features disabled): {e}")

    if not settings.API_KEY:
        logger.warning(
            "API_KEY is not set — authentication is DISABLED. "
            "Set API_KEY in .env before deploying to production."
        )

    # Pre-load embedding model to avoid first-request latency (~40s cold start)
    try:
        import embeddings
        embeddings._get_model()
        logger.info("Embedding model pre-loaded successfully.")
    except Exception as e:
        logger.warning(f"Failed to pre-load embedding model: {e}")

    # Pre-load reranker to avoid first-request latency (only if enabled)
    if settings.RERANKER_ENABLED:
        try:
            import reranker
            reranker._get_reranker()
        except Exception as e:
            logger.warning(f"Failed to pre-load reranker: {e}")
    else:
        logger.info("Reranker disabled — skipping pre-load.")

    yield
    graph_store.close_driver()


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="SemSaver API",
    description="Syllabus-specific AI study assistant — Hybrid Graph + Vector RAG",
    version="2.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if _limiter is not None:
    try:
        from slowapi import _rate_limit_exceeded_handler
        from slowapi.errors import RateLimitExceeded
        app.state.limiter = _limiter
        app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    except ImportError:
        pass


# ── Pydantic models ───────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    query: str


class ChatResponse(BaseModel):
    answer: str
    sources: List[str]
    confidence: float
    graph_path: List[str]


class UploadResponse(BaseModel):
    message: str
    files: List[str]
    summaries: List[dict]


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    token: str
    role: str


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "total_chunks": vector_store.get_total_chunks(),
        "embedding_model": settings.EMBEDDING_MODEL,
        "generation_model": (
            settings.GROQ_MODEL if settings.GROQ_API_KEY else settings.GENERATION_MODEL
        ),
        "auth_enabled": bool(settings.API_KEY),
    }


@app.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest):
    """
    Mock login endpoint for demo purposes.
    """
    logger.info(f"Login attempt for: {req.email}")
    email = req.email.lower().strip()
    password = req.password.strip()

    # Simple mock authentication
    users = {
        "student@semsaver.com": {"password": "student123", "role": "student"},
        "professor@semsaver.com": {"password": "prof123", "role": "professor"},
        "admin@semsaver.com": {"password": "admin123", "role": "admin"},
    }

    if email in users and users[email]["password"] == password:
        # For demo, the token is just a base64-like string
        token = f"demo_token_{users[email]['role']}_{uuid.uuid4().hex}"
        return LoginResponse(token=token, role=users[email]["role"])
    
    raise security.safe_error("Invalid email or password.", 401)


@app.post("/upload", response_model=UploadResponse)
async def upload_files(
    request: Request,
    files: List[UploadFile] = File(...),
    _auth: None = Depends(security.verify_api_key),
):
    if not files:
        raise security.safe_error("No files provided.", 400)

    security.log_request(
        "/upload",
        extra={"file_count": len(files), "file_names": [f.filename for f in files]},
    )

    summaries: list[dict] = []
    saved_names: list[str] = []

    for file in files:
        # Validates extension + size; returns raw bytes
        content: bytes = await security.validate_upload(file)

        # UUID-prefix filename prevents path traversal
        safe_name = security.sanitize_filename(file.filename or "upload")
        dest = Path(settings.UPLOAD_DIR) / safe_name
        dest.write_bytes(content)
        saved_names.append(safe_name)
        logger.info(f"Saved upload: {safe_name} ({len(content)} bytes)")

        try:
            summary = ingestion.ingest_file(str(dest))
            summaries.append(summary)
        except Exception as e:
            logger.error(f"Ingestion failed for {safe_name}: {e}")
            summaries.append({
                "file": safe_name,
                "error": "Ingestion failed. Check server logs.",
            })

    return UploadResponse(
        message=f"Ingested {len(saved_names)} file(s).",
        files=saved_names,
        summaries=summaries,
    )


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: Request,
    req: ChatRequest,
    _auth: None = Depends(security.verify_api_key),
):
    query = req.query.strip()
    if not query:
        raise security.safe_error("Query cannot be empty.", 400)

    # Strip prompt injection patterns before any downstream processing
    query = security.sanitize_query(query)

    security.log_request("/chat")

    try:
        # OFF-LOAD TO THREAD: prevent blocking the event loop
        result = await asyncio.to_thread(retrieval.retrieve, query)
    except Exception as e:
        logger.error(f"Retrieval error: {e}")
        raise security.safe_error("Retrieval failed. Please try again.", 500)

    try:
        # OFF-LOAD TO THREAD: prevent blocking the event loop
        response = await asyncio.to_thread(chat.generate_answer, query, result)
    except Exception as e:
        logger.error(f"Generation error: {e}")
        raise security.safe_error("Answer generation failed. Please try again.", 500)

    return ChatResponse(**response)
