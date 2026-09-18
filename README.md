# Knowledge Assistant

A local-first personal knowledge base. Import PDFs and notes, search them by meaning and
keyword, and ask questions that are answered with citations — all from one SQLite file on
your machine. Indexing and search never touch the network; an LLM (local Ollama or a cloud
API) is only needed for answers and AI note tidying.

```
npx knowledge-assistant
```

That installs a private Python environment on first run, downloads a small embedding model
(~130 MB), and opens the app in your browser. Or install it globally with
`npm i -g knowledge-assistant` and run `ka`.

## Features

- **Import** — drop PDFs or paste text. Documents are split into passages, embedded locally,
  and indexed in the background with live progress.
- **Search** — hybrid retrieval: vector similarity (sqlite-vec) fused with BM25 keyword
  search (FTS5). Scope by category or topic.
- **Ask** — answers stream in with `[n]` citations that link to the exact passages used.
- **Library** — organise entries into categories and topics. Edits re-index automatically.
- **Notes** — write, tidy into a structured note (rule-based or AI), promote to the library.
- **Email** — sync a mailbox over IMAP; each message becomes a searchable entry, deduplicated by Message-ID, resumable by UID.
- **Templates** — five built-in structures plus your own.
- **Preferences** — describe how you like notes formatted in plain language.

## How answers are generated (RAG)

The **Ask** feature is a retrieval-augmented generation (RAG) pipeline, and it runs the same
retrieval stack as search. Every imported document is split into sentence-aware chunks of about
512 tokens with a 64-token overlap, and each chunk is embedded locally with a small ONNX model
(bge-small via fastembed). When you ask a question, the query is embedded and matched against
those vectors with sqlite-vec, in parallel with a BM25 keyword search over the same chunks in
FTS5. The two ranked lists are merged with reciprocal rank fusion, and the top six passages are
handed to the LLM as numbered context. The system prompt restricts the model to that context and
asks it to cite passages inline as `[n]`, so every claim in an answer links back to the exact
text it came from, and the model is told to say so rather than guess when the context has no
answer. Retrieval, embedding and indexing never leave your machine; only the final generation
step calls an LLM, which can itself be local via Ollama.

## Requirements

- Python 3.10+ (the npm launcher finds it; `pip` users install directly)
- Node 18+ only if using the npm launcher
- Optional: [Ollama](https://ollama.com) for fully offline answers, or an OpenAI/Anthropic key

## Install without npm

```bash
pip install knowledge-assistant[ollama]   # or [openai] / [anthropic] / [all]
ka serve --open
```

## Configuration

Environment variables (or a `.env` file in the working directory), all prefixed `KA_`:

| Variable | Default | Meaning |
|---|---|---|
| `KA_DATA_DIR` | `~/.knowledge-assistant` | Where the database, uploads and models live |
| `KA_PORT` | `8765` | HTTP port |
| `KA_LLM_PROVIDER` | `ollama` | `ollama`, `openai`, `anthropic`, or `none` |
| `KA_LLM_MODEL` | `llama3.2` | Model name for the chosen provider |
| `KA_OLLAMA_HOST` | `http://127.0.0.1:11434` | |
| `KA_OPENAI_API_KEY` / `KA_ANTHROPIC_API_KEY` | | Only for cloud providers |
| `KA_EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | Local embedding model (fastembed) |
| `KA_CHUNK_TOKENS` | `512` | Passage size |
| `KA_SEARCH_MAX_DISTANCE` | `0.45` | Vector cutoff (cosine distance); re-tune if you change the embedding model |
| `KA_WORKER_THREADS` | `2` | Background import workers |
| `KA_IMAP_HOST` / `KA_IMAP_USER` / `KA_IMAP_PASSWORD` | | Set all three to enable the email source (Gmail: use an app password) |
| `KA_IMAP_FOLDER` | `INBOX` | Folder to sync |
| `KA_IMAP_MAX_PER_SYNC` | `200` | Cap per sync run |

## CLI

```
ka serve [--open] [--port N]   start API, worker and web UI
ka ingest FILE                 import a PDF or text file without the server
ka search "query"              search from the terminal
ka db path | ka db reset       locate or wipe the database
```

## Architecture

One Python process: FastAPI serves the API and the built React app; a thread pool consumes a
job table in the same SQLite database; PDF parsing runs in a subprocess so a parser crash
fails one job instead of the server.

```
npm launcher ─► ka serve
                 ├─ FastAPI  /api/v1  + static SPA
                 ├─ Worker pool ◄── jobs table
                 │     └─ pdf_extract (subprocess)
                 ├─ Embedder: fastembed (ONNX, local)
                 ├─ LLM: ollama | openai | anthropic | none
                 └─ knowledge.db: tables + vec0 + fts5
```

The job queue is the producer/consumer seam: producers call `JobQueue.enqueue`, handlers are
registered by kind. Backing it with Redis or a separate worker process later means replacing
`jobs/queue.py` only. New sources (e.g. an email connector) are new job kinds.

```
src/knowledge_assistant/
  core/        models, repositories, chunking, embeddings, search, llm/, notes, preferences
  jobs/        queue, worker, handlers, pdf_extract
  api/         FastAPI routers and schemas
  cli.py       `ka`
web/           React 19 + Vite + Tailwind 4 (builds into src/knowledge_assistant/static)
launcher/      npm package: finds Python, creates a venv, runs `ka serve`
tests/         pytest (core, jobs, API) — no network, no model download
```

## Development

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev,all]"
pytest

cd web && npm install && npm run dev      # UI with API proxy to :8765
ka serve                                   # in another terminal
```

## Releasing

Bump `version` in both `pyproject.toml` and `launcher/package.json` (they must match: the
launcher installs the wheel whose version equals its own), then:

```bash
./scripts/build-launcher.sh      # builds the UI, the wheel, and stages it in launcher/
cd launcher && npm publish
```

The npm package bundles the wheel, so users never need PyPI.

## License

MIT
