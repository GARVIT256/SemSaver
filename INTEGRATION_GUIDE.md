# SemSaver — Frontend Integration Guide

This guide explains how to connect an existing frontend (React / Next.js / Vite) to the SemSaver backend.

---

## 1. Start the Backend

```powershell
cd "c:\Users\garvi\OneDrive\Documents\SemSaver new\backend"

# Activate virtual environment
.\.venv\Scripts\activate        # or .\venv\Scripts\activate

# Install dependencies (first time only)
pip install -r requirements.txt

# Start the server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API is now available at `http://localhost:8000`.  
Interactive docs: `http://localhost:8000/docs`

---

## 2. Environment Setup

Copy `.env.template` to `backend/.env` and fill in:

```bash
GROQ_API_KEY=gsk_...        # Required for LLM generation
API_KEY=your-secret-key    # Required for /upload and /chat
NEO4J_PASSWORD=...          # If using Neo4j
```

---

## 3. CORS Configuration

The backend already has CORS middleware configured.  
Update `ALLOWED_ORIGINS` in `.env` to match your frontend URL:

```bash
ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com
```

---

## 4. API Key Header

Every request to `/upload` and `/chat` must include:

```
X-Api-Key: your-secret-key
```

Store this securely — use an environment variable in your frontend:

```js
// .env.local (Next.js / Vite)
VITE_API_KEY=your-secret-key
// or
NEXT_PUBLIC_API_KEY=your-secret-key
```

> **Never commit API keys to version control.**

---

## 5. File Upload

```js
async function uploadFiles(files) {
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }

  const response = await fetch("http://localhost:8000/upload", {
    method: "POST",
    headers: {
      "X-Api-Key": import.meta.env.VITE_API_KEY,
      // Do NOT set Content-Type manually — browser sets it with boundary
    },
    body: formData,
  });

  if (!response.ok) {
    const err = await response.json();
    throw new Error(err.detail);
  }

  return response.json();
  // { message, files: [...], summaries: [...] }
}
```

**Accepted file types:** `.pdf`, `.pptx`, `.ppt`  
**Max file size:** 10 MB

---

## 6. Chat / Q&A

```js
async function askQuestion(query) {
  const response = await fetch("http://localhost:8000/chat", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Api-Key": import.meta.env.VITE_API_KEY,
    },
    body: JSON.stringify({ query }),
  });

  if (!response.ok) {
    const err = await response.json();
    throw new Error(err.detail);
  }

  return response.json();
  // { answer, sources, confidence, graph_path }
}
```

**Response shape:**

```ts
interface ChatResponse {
  answer: string;         // LLM-generated answer
  sources: string[];      // Filenames referenced
  confidence: number;     // 0.0 – 1.0 (vector similarity)
  graph_path: string[];   // Prerequisite concept chain (may be empty)
}
```

---

## 7. Health Check

```js
const res = await fetch("http://localhost:8000/health");
const { status, total_chunks, auth_enabled } = await res.json();
```

Use this to verify the backend is running before showing the UI.

---

## 8. Error Handling

All errors return:
```json
{ "detail": "Human-readable error message" }
```

| HTTP Code | Meaning |
|-----------|---------|
| 400       | Bad request (wrong file type, empty query, etc.) |
| 403       | Invalid or missing API key |
| 413       | File too large (> 10 MB) |
| 429       | Rate limit exceeded — back off and retry |
| 500       | Server error — check backend logs |

---

## 9. Rate Limits

| Endpoint  | Limit         |
|-----------|---------------|
| `/upload` | 5 / minute    |
| `/chat`   | 30 / minute   |

On `429`, show the user a message and retry after a short delay.

---

## 10. Displaying Results

```jsx
function AnswerCard({ response }) {
  return (
    <div>
      <p>{response.answer}</p>
      {response.confidence > 0 && (
        <small>Confidence: {(response.confidence * 100).toFixed(1)}%</small>
      )}
      {response.sources.length > 0 && (
        <p>Sources: {response.sources.join(", ")}</p>
      )}
      {response.graph_path.length > 1 && (
        <p>Concept path: {response.graph_path.join(" → ")}</p>
      )}
    </div>
  );
}
```
