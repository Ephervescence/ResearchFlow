# ResearchFlow Architecture

ResearchFlow is an LLM Agent research assistant. The MVP focuses on one clear loop:

```text
User query
  -> FastAPI task API
  -> LangGraph research workflow
  -> PostgreSQL persistence
  -> React execution dashboard
```

## Backend

- `app/api`: HTTP routes.
- `app/services`: business logic around tasks, steps, sources, notes, and reports.
- `app/agent`: LangGraph state and workflow nodes.
- `app/db`: SQLAlchemy models and database session setup.
- `app/schemas`: Pydantic response/request models.

## Agent Workflow

The current graph is intentionally small:

```text
planner -> search -> reader -> extractor -> reflection -> report
```

Search is implemented behind `app/tools/search.py`. The workflow calls a stable `SearchTool`
interface, so providers can be changed through environment variables instead of rewriting the
LangGraph node.

Reader is implemented behind `app/tools/reader.py`. It downloads HTML, uses Trafilatura to extract
main text, falls back to the search snippet when a page cannot be read, and records readable status
in the agent step output.

Search providers:

- `mock`: deterministic local results for development without network access.
- `ddgs`: live metasearch through the `ddgs` Python package.

Reader behavior:

- Stores compact source summaries in PostgreSQL.
- Keeps full extracted text in LangGraph state for downstream extraction/report generation.
- Limits page text with `READER_MAX_CHARS` to keep future LLM and embedding calls bounded.

Local document uploads:

- Files are uploaded through `/api/tasks/{task_id}/files`.
- Supported formats are PDF, Markdown, and TXT.
- Parsed text is stored in `uploaded_files.parsed_text`.
- During the Reader node, uploaded documents are merged with web documents as normal sources.

## RAG Knowledge Base

Readable web pages and uploaded documents are converted into chunks after the Reader node:

```text
source content -> chunk_text -> EmbeddingClient -> document_chunks.embedding
```

The first implementation uses deterministic mock embeddings so the full pipeline works without an
external embedding API. The database schema uses `pgvector.sqlalchemy.Vector(384)`, and retrieval
orders chunks by cosine distance.

The Agent graph includes a dedicated RAG node:

```text
planner -> memory_recall -> search -> reader -> extractor -> rag -> memory_save -> reflection -> report
```

The report generator receives retrieved chunks first, with raw source snippets as fallback evidence.

## Long-Term Memory

ResearchFlow stores cross-task memories in `memories`.

Memory flow:

```text
new task query -> memory_recall -> search context
task notes + retrieved chunks -> memory_save -> memories.embedding
```

The first implementation stores automatic task summaries as `long_term_memory`. Memory retrieval
uses the same embedding client as RAG and orders results by pgvector cosine distance.

API endpoints:

- `GET /api/memories`
- `POST /api/memories/search`

## Citation Tracking

Report generation converts retrieved RAG chunks into numbered citation items:

```text
retrieved_chunks -> citation_items -> report markdown [1] [2] -> report_citations
```

The report keeps visible references in Markdown, while `report_citations` stores structured evidence
for later UI rendering and audit.

API endpoint:

- `GET /api/tasks/{task_id}/citations`

## Storage

PostgreSQL is used for structured records. The Docker image includes `pgvector`, so the next RAG
milestone can add an embeddings table without introducing Chroma or FAISS.

## LLM Provider

`app/agent/llm.py` uses an OpenAI-compatible wrapper. It can call domestic providers such as
DeepSeek or Qwen by setting `LLM_BASE_URL`, `LLM_API_KEY`, and `LLM_MODEL`.
