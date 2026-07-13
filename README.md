# rag-kit

Agentic RAG system for Hermes Agent — watch a folder, auto-ingest documents (PDF, DOCX, TXT, MD), embed with multilingual sentence-transformers, store in LanceDB, and query via a CLI designed for LLM agent consumption.

## Quickstart (one-liner per platform)

```bash
# Windows
scripts\install-windows.bat

# Linux / DGX Spark
chmod +x scripts/install-dgx-spark.sh && ./scripts/install-dgx-spark.sh
```

That's it. The installer creates a venv at `~/rag-kit-venv/`, installs everything, starts the watcher, and optionally sets up autostart.

## Offline Installation

1. Download models first (on a machine with internet):
   ```bash
   # Windows
   scripts\download-models.bat

   # Linux
   chmod +x scripts/download-models.sh && ./scripts/download-models.sh
   ```

2. Copy `~/models/` to the target machine, then run the install script — it works fully offline.

## Features

- **Auto-ingest**: Watches a folder, processes new/changed/deleted files automatically
- **Multilingual**: Chinese + English text extraction, chunking, and embeddings
- **OCR fallback**: EasyOCR for scanned PDFs and image-based documents
- **VLM captioning**: SmolVLM-256M for charts and diagrams (optional, configurable)
- **Hybrid search**: Semantic (vector similarity) + keyword (FTS) scoring via LanceDB
- **Local vector DB**: LanceDB — no server, no external dependencies
- **Agent-friendly**: All CLI commands support `--json` output for Hermes Agent
- **2 GB budget**: Total model memory (embedding + OCR + VLM) fits within 2 GB
- **Cross-platform**: Windows + Linux (DGX Spark ARM64)
- **Autostart**: Windows Scheduled Task or Linux systemd user service on boot

## CLI Reference

| Command | Description | JSON flag |
|---|---|---|
| `rag ingest <path>` | Ingest a file or folder | `--json` |
| `rag query "<text>"` | Hybrid search (vector + keyword) | `--json` |
| `rag list-files` | List all ingested files | `--json` |
| `rag delete <path>` | Remove a file's chunks from DB | `--json` |
| `rag status` | Show system status and model info | `--json` |
| `rag watch <folder>` | Start real-time folder watcher | `--json` |
| `rag setup-autostart` | Configure autostart (boot) | `--json` |
| `rag config` | Print or update configuration | — |
| `rag config init` | Create default config file | — |
| `rag config path` | Show config file location | — |
| `rag config set <key> <value>` | Update a config value | — |
| `rag --version` | Show version | — |

### JSON output examples

```bash
# Search (agent consumption)
rag query --json "机器学习是什么" --top-k 5

# System status
rag status --json

# List files
rag list-files --json

# Setup autostart
rag setup-autostart --json
```

## Configuration

rag-kit loads config from (in order of precedence):

1. `RAG_KIT_CONFIG` environment variable (path to a YAML file)
2. `./rag-kit.yaml` (current directory)
3. `~/.rag-kit.yaml` (user home)

Every config key can be overridden via environment variable `RAG_KIT_<KEY>`:

```bash
export RAG_KIT_WATCH_FOLDER=~/my-documents
export RAG_KIT_DB_PATH=~/my-lancedb
export RAG_KIT_VLM_ENABLED=false
export RAG_KIT_HF_ENDPOINT=https://hf-mirror.com   # China mirror
```

### Config file reference

| Key | Type | Default | Description |
|---|---|---|---|
| `watch_folder` | path | `~/Documents/rag-ingest` | Folder the watcher monitors |
| `db_path` | path | `~/lancedb` | LanceDB storage directory |
| `model_dir` | path | `~/models` | Model cache directory |
| `embedding_model` | str | `paraphrase-multilingual-MiniLM-L12-v2` | Sentence-transformers model |
| `vlm_model` | str | `HuggingFaceTB/SmolVLM-256M-Instruct` | VLM model for captions |
| `vlm_enabled` | bool | `true` | Enable VLM captioning |
| `supported_extensions` | list | `[.pdf, .docx, .txt, .md]` | File types to ingest |
| `languages` | list | `[zh, en]` | OCR languages |
| `chunk_size` | int | `512` | Target chunk length (chars) |
| `chunk_overlap` | int | `64` | Overlap between chunks |
| `watch_interval` | int | `30` | Polling interval (seconds) |
| `search_alpha` | float | `0.5` | Semantic vs keyword blend |
| `max_memory_mb` | int | `2048` | Memory budget guard |
| `hf_endpoint` | str | `""` | HF endpoint (set for China) |

## Architecture

```
┌──────────────┐    ┌───────────────┐    ┌───────────┐    ┌─────────┐
│ Watch Folder │───▶│ Ingest Engine │───▶│ Embedding │───▶│ LanceDB │
│ (watchdog +  │    │ (OCR + VLM)   │    │ (384-dim) │    │ (local) │
│  poll-based) │    └───────────────┘    └───────────┘    └────┬────┘
└──────────────┘                                               │
                                                               ▼
                                                        ┌──────────┐
                                                        │  Query   │
                                                        │ (hybrid) │
                                                        └──────────┘
```

### Models

| Component | Model | Disk | Runtime RAM |
|---|---|---|---|
| Embedding | paraphrase-multilingual-MiniLM-L12-v2 | ~470 MB | ~500 MB |
| OCR | EasyOCR (zh+en) | ~100 MB download | ~500 MB |
| VLM | SmolVLM-256M-Instruct | ~500 MB | ~500 MB |
| **Total** | | **~1.1 GB** | **~1.5 GB (< 2 GB)** |

### Package structure

```
rag-kit/
├── rag_kit/
│   ├── __init__.py          # Version, package metadata
│   ├── config.py            # YAML config, env overrides, validation
│   ├── autostart.py         # schtasks (Win) / systemd (Linux)
│   ├── watcher.py           # Poll-based folder monitor with MD5 tracking
│   ├── cli/
│   │   ├── __init__.py
│   │   └── main.py          # Typer CLI: 7 commands + --json
│   ├── embed/
│   │   └── __init__.py      # EmbeddingEngine, chunk_text, Chunk dataclass
│   ├── store/
│   │   └── __init__.py      # VectorStore: LanceDB CRUD + search
│   ├── ingest/
│   │   ├── __init__.py
│   │   ├── pipeline.py      # File ingestion: PDF/DOCX/TXT/MD
│   │   ├── ocr.py           # EasyOCR wrapper
│   │   └── language.py      # Language detection
│   └── vlm/
│       ├── __init__.py
│       ├── captioner.py     # SmolVLM captioner
│       ├── extractor.py     # Image extraction from docs
│       └── language.py      # VLM prompt language
├── scripts/
│   ├── install-windows.bat
│   ├── install-dgx-spark.sh
│   ├── download-models.bat
│   └── download-models.sh
├── tests/
│   ├── test_rag_pipeline.py    # 27 comprehensive tests
│   ├── test_cli.py             # CLI integration tests
│   ├── test_embed_store.py     # Embed + store smoke test
│   ├── test_ingest_pipeline.py # Document ingestion tests
│   └── test_vlm.py             # VLM component tests
├── SKILL.md                    # Hermes Agent skill
├── pyproject.toml
└── README.md
```

## Hermes Agent Integration

rag-kit includes a SKILL.md that teaches Hermes Agent to use `rag query --json` instead of `web_search` when the user asks about "my documents", "search my data", or "the database".

The installer copies the skill to `~/.hermes/skills/research/rag-kit/SKILL.md`. After installation, Hermes Agent will:
- Detect queries about local documents
- Run `rag query --json --top-k 5 "query"`
- Present results with source attribution

## Testing

```bash
cd rag-kit

# Run the comprehensive pipeline tests (27 tests, no model download needed)
python -m pytest tests/test_rag_pipeline.py -v

# Run all tests
python -m pytest tests/ -v

# Run specific test modules
python -m pytest tests/test_cli.py -v
python -m pytest tests/test_embed_store.py -v
python -m pytest tests/test_vlm.py -v
```

## Troubleshooting

### "ModuleNotFoundError" or import errors
```bash
# Ensure you're in the right venv
source ~/rag-kit-venv/bin/activate       # Linux
~\rag-kit-venv\Scripts\activate.bat      # Windows
```

### "HF_HUB_OFFLINE=1 but model not cached"
```bash
# Pre-download models first
scripts/download-models.bat   # Windows
# or
# Set China mirror
export HF_ENDPOINT=https://hf-mirror.com
```

### "Permission denied" on setup-autostart (Windows)
Run as Administrator or skip autostart — the watcher can be started manually:
```bash
rag watch ~\Documents\rag-ingest
```

### Watcher not running
```bash
# Check watcher status
rag status

# Start manually
rag watch ~/Documents/rag-ingest &

# Check autostart
rag setup-autostart --json
```

### Empty query results
```bash
# Check if documents were ingested
rag list-files --json

# Re-ingest
rag ingest ~/Documents/rag-ingest
```

## Requirements

- Python 3.10+
- 4 GB RAM recommended (2 GB minimum for models)
- ~2 GB disk for models + documents
- NVIDIA GPU optional (CPU-only supported)

## Platforms

| Platform | Install Script | Autostart |
|---|---|---|
| Windows 10/11 | `scripts\install-windows.bat` | schtasks |
| Linux (x86_64) | `scripts/install-dgx-spark.sh` | systemd user service |
| Linux (DGX Spark ARM64) | `scripts/install-dgx-spark.sh` | systemd user service |

## License

MIT