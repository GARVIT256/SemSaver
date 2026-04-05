# SemSaver API Documentation

**Base URL:** `http://localhost:8000`  
**Version:** 2.1.0

---

## Authentication

All endpoints except `/health` require an API key in the request header.

```
X-Api-Key: <your API key>
```

Set the key in `.env` → `API_KEY=your-secret-key`. Leave blank to disable auth (dev only).

---

## Endpoints

### `GET /health`

Health check. No authentication required.

**Response `200`:**
```json
{
  "status": "ok",
  "total_chunks": 42,
  "embedding_model": "BAAI/bge-small-en-v1.5",
  "generation_model": "llama-3.3-70b-versatile",
  "auth_enabled": true
}
```

---

### `POST /upload`

Upload one or more PDF or PPTX files for ingestion.

**Rate limit:** 5 requests / minute per IP  
**Max file size:** 10 MB (configurable via `MAX_FILE_SIZE`)

**Request:** `multipart/form-data`

| Field  | Type         | Description               |
|--------|--------------|---------------------------|
| files  | file[]       | PDF or PPTX files         |

**Headers:**
```
X-Api-Key: <key>
Content-Type: multipart/form-data
```

**Response `200`:**
```json
{
  "message": "Ingested 2 file(s).",
  "files": [
    "abc123_lecture1.pdf",
    "def456_chapter2.pptx"
  ],
  "summaries": [
    { "file": "abc123_lecture1.pdf", "chunks": 18, "keywords": 132 },
    { "file": "def456_chapter2.pptx", "chunks": 11, "keywords": 87 }
  ]
}
```

**Error responses:**

| Code | Reason |
|------|--------|
| 400  | Unsupported file type / empty file / no files provided |
| 403  | Missing or invalid API key |
| 413  | File exceeds size limit |
| 429  | Rate limit exceeded |
| 500  | Internal ingestion error |

---

### `POST /chat`

Send a question and receive an answer grounded in uploaded materials.

**Rate limit:** 30 requests / minute per IP

**Request body (JSON):**
```json
{
  "query": "What are the main types of machine learning?"
}
```

**Headers:**
```
X-Api-Key: <key>
Content-Type: application/json
```

**Response `200`:**
```json
{
  "answer": "According to the uploaded material, the three main types of machine learning are...",
  "sources": ["abc123_lecture1.pdf"],
  "confidence": 0.8312,
  "graph_path": ["supervised learning", "classification", "regression"]
}
```

**Response fields:**

| Field       | Type     | Description |
|-------------|----------|-------------|
| answer      | string   | LLM-generated answer from retrieved context |
| sources     | string[] | Source file names referenced in the answer |
| confidence  | float    | Mean cosine similarity of retrieved chunks (0–1) |
| graph_path  | string[] | Prerequisite concept chain from Neo4j (may be empty) |

**Error responses:**

| Code | Reason |
|------|--------|
| 400  | Empty query |
| 403  | Invalid API key |
| 429  | Rate limit exceeded |
| 500  | Retrieval or generation error |

---

## Security Notes

- Filenames are stored with a `uuid4` prefix — original names are never used on disk
- Prompt injection patterns are stripped from queries before reaching the LLM
- Error responses never include raw stack traces
- All requests and errors are logged (query content is NOT logged)
