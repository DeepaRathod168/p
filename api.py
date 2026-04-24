"""
api.py
──────
FastAPI application — the backend entry point.

Endpoints
---------
POST /query         Run the CrewAI research pipeline.
GET  /history       Return the persisted chat/research history.
DELETE /history     Clear all history.
GET  /health        Simple liveness check.
GET  /rebuild-index Force-rebuild the FAISS RAG index.

Run with:
    uvicorn api:app --reload --host 0.0.0.0 --port 8000

CORS is open to localhost:3000 (React dev server).
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("api")

# ── History file ──────────────────────────────────────────────────────────────
HISTORY_FILE = Path(os.getenv("HISTORY_FILE", "research_history.json"))


def _load_history() -> list[dict]:
    """Load research history from disk."""
    try:
        if HISTORY_FILE.exists():
            return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Could not load history: %s", exc)
    return []


def _save_history(history: list[dict]) -> None:
    """Persist research history to disk."""
    try:
        HISTORY_FILE.write_text(
            json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as exc:
        logger.warning("Could not save history: %s", exc)


# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="Multi-Agent Research System API",
    description=(
        "FastAPI backend for a CrewAI + RAG powered research pipeline. "
        "Submit a natural-language query and receive a structured research report."
    ),
    version="2.0.0",
)

# CORS — allow the React dev server and any local origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    """Incoming research query."""
    query: str = Field(
        ...,
        min_length=3,
        max_length=500,
        example="How is AI transforming healthcare in 2026?",
    )


class QueryResponse(BaseModel):
    """Structured research response."""
    summary: str
    insights: list[str]
    sources: list[str]
    query: str
    timestamp: str
    duration_seconds: float


class HistoryEntry(BaseModel):
    query: str
    summary: str
    insights: list[str]
    sources: list[str]
    timestamp: str
    duration_seconds: float


class StatusResponse(BaseModel):
    status: str
    message: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health", response_model=StatusResponse, tags=["System"])
def health_check() -> dict[str, str]:
    """Liveness probe — returns 200 OK if the server is running."""
    return {"status": "ok", "message": "Multi-Agent Research API is running."}


@app.post("/query", response_model=QueryResponse, tags=["Research"])
async def run_query(request: QueryRequest) -> dict[str, Any]:
    """
    Execute the full CrewAI + RAG research pipeline.

    1. RAG retrieves background context from /data documents.
    2. Research Agent searches the web for latest information.
    3. Analysis Agent identifies trends and insights.
    4. Summary Agent returns a structured JSON report.

    Returns a structured response with summary, insights, and sources.
    """
    from time import perf_counter
    from crew import run_research  # lazy import keeps startup fast

    query = request.query.strip()
    logger.info("Received query: %s", query)
    print(f"DEBUG: Incoming query POST /query - {query}")

    start = perf_counter()
    try:
        result = run_research(query)
        print(f"DEBUG: Successfully executed query: {query}")
    except Exception as exc:
        print(f"DEBUG: Failed to execute query - Error: {str(exc)}")
        logger.error("Crew execution failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Research pipeline error: {str(exc)}",
        )

    duration = round(perf_counter() - start, 2)
    timestamp = datetime.utcnow().isoformat() + "Z"

    response = {
        "query": query,
        "summary": result.get("summary", ""),
        "insights": result.get("insights", []),
        "sources": result.get("sources", []),
        "timestamp": timestamp,
        "duration_seconds": duration,
    }

    # Persist to history
    history = _load_history()
    history.append(response)
    _save_history(history)
    logger.info("Query complete in %.2fs. History now has %d entries.", duration, len(history))

    return response


@app.get("/history", response_model=list[HistoryEntry], tags=["History"])
def get_history() -> list[dict]:
    """Return the full persisted research history (newest first)."""
    history = _load_history()
    return list(reversed(history))


@app.delete("/history", response_model=StatusResponse, tags=["History"])
def clear_history() -> dict[str, str]:
    """Wipe all research history from disk."""
    _save_history([])
    return {"status": "ok", "message": "History cleared."}


@app.get("/rebuild-index", response_model=StatusResponse, tags=["System"])
def rebuild_rag_index() -> dict[str, str]:
    """
    Force a rebuild of the FAISS RAG index.
    Call this after adding new documents to the /data directory.
    """
    try:
        from rag_pipeline import rebuild_index
        rebuild_index()
        return {"status": "ok", "message": "FAISS index rebuilt successfully."}
    except Exception as exc:
        logger.error("Index rebuild failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ── Dev entry point ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
