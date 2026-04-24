# ResearchAI — Multi-Agent Research System

> **CrewAI + RAG + FastAPI + React** — 3 AI agents that search, analyse, and summarise any topic in minutes.

---

## Architecture

```
User (React UI)
      │
      ▼  POST /query
FastAPI (api.py)
      │
      ├── RAG Pipeline (rag_pipeline.py)
      │     └── FAISS vector store ← /data documents
      │
      └── CrewAI Crew (crew.py)
            ├── Research Agent  (RAG + DuckDuckGo)
            ├── Analysis Agent  (trends & insights)
            └── Summary Agent   (structured JSON output)
```

---

## Folder Structure

```
multi research agent/
├── agents.py          # 3 CrewAI agents
├── tasks.py           # Sequential pipeline tasks
├── crew.py            # Orchestrator → returns {summary, insights, sources}
├── tools.py           # search_tool + rag_tool
├── rag_pipeline.py    # FAISS RAG: load → chunk → embed → retrieve
├── llm_config.py      # Centralised LLM config (Groq/OpenAI/Ollama)
├── api.py             # FastAPI: POST /query, GET /history, etc.
├── app.py             # Original Streamlit UI (still works independently)
├── requirements.txt
├── .env               # API keys & config
├── data/              # Drop .txt / .md files here for RAG ingestion
│   └── sample.txt
├── research_history.json
└── frontend/
    ├── package.json
    └── src/
        ├── App.js
        ├── App.css
        ├── index.js
        ├── components/
        │   ├── ChatBox.js
        │   └── ChatBox.css
        └── services/
            └── api.js
```

---

## Quick Start

### 1 — Clone & set up environment

```bash
cd "multi research agent"
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

### 2 — Install backend dependencies

```bash
pip install -r requirements.txt
```

### 3 — Configure API keys

Edit `.env`:

```env
# Groq (default — free, fast)
LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_api_key_here

# OR switch to OpenAI:
# LLM_PROVIDER=openai
# OPENAI_API_KEY=your_openai_api_key_here

# OR use local Ollama (no API key needed):
# LLM_PROVIDER=ollama
# OLLAMA_MODEL=llama3
```

Get a **free Groq API key** at → https://console.groq.com

### 4 — Start the FastAPI backend

```bash
uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

API docs are available at → http://127.0.0.1:8000/docs

### 5 — Start the React frontend

```bash
cd frontend
npm install
npm start
```

Open → http://localhost:3000

---

## API Endpoints

| Method | Endpoint        | Description                              |
|--------|-----------------|------------------------------------------|
| POST   | `/query`        | Run the research pipeline                |
| GET    | `/history`      | Fetch all past queries (newest first)    |
| DELETE | `/history`      | Wipe research history                    |
| GET    | `/health`       | Liveness check                           |
| GET    | `/rebuild-index`| Re-index `/data` documents into FAISS    |

### POST `/query` — Request

```json
{ "query": "How is AI transforming healthcare in 2026?" }
```

### POST `/query` — Response

```json
{
  "query": "How is AI transforming healthcare in 2026?",
  "summary": "AI is revolutionising healthcare through ...",
  "insights": [
    "Diagnostic AI models now match specialist accuracy in radiology ...",
    "Drug discovery timelines have been cut by 40% ...",
    ...
  ],
  "sources": [
    "https://www.nature.com/articles/...",
    "https://techcrunch.com/2026/..."
  ],
  "timestamp": "2026-04-20T14:30:00Z",
  "duration_seconds": 87.4
}
```

---

## RAG — Adding Your Own Documents

1. Drop `.txt` or `.md` files into the `data/` folder.
2. Call `GET http://127.0.0.1:8000/rebuild-index` to re-index.
3. The Research Agent will now use your documents as background context.

---

## LLM Provider Switching

| Provider | Speed  | Cost     | Setup                      |
|----------|--------|----------|----------------------------|
| Groq     | Fast   | Free     | `GROQ_API_KEY` in `.env`   |
| OpenAI   | Fast   | Paid     | `OPENAI_API_KEY` in `.env` |
| Ollama   | Medium | Free     | Run Ollama locally          |

---

## Streamlit UI (original)

The original Streamlit interface still works independently:

```bash
streamlit run app.py
```

---

## Environment Variables Reference

| Variable          | Default              | Description                        |
|-------------------|----------------------|------------------------------------|
| `LLM_PROVIDER`    | `groq`               | `groq` / `openai` / `ollama`      |
| `GROQ_API_KEY`    | —                    | Groq API key                       |
| `OPENAI_API_KEY`  | —                    | OpenAI API key                     |
| `GROQ_MODEL`      | `llama3-70b-8192`    | Groq model name                    |
| `OPENAI_MODEL`    | `gpt-4o`             | OpenAI model name                  |
| `OLLAMA_MODEL`    | `llama3`             | Ollama model name                  |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL              |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2`  | HuggingFace sentence-transformer   |
| `DATA_DIR`        | `./data`             | Document directory for RAG         |
| `FAISS_INDEX_DIR` | `./data/faiss_index` | Where FAISS index is persisted     |
| `HISTORY_FILE`    | `research_history.json` | Chat history persistence        |
