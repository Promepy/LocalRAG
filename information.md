# Local RAG System (Ollama + Chroma)

## 1. Project Overview

The goal of this project is to design and implement a **fully local, offline Retrieval-Augmented Generation (RAG) system** running on a Mac mini (Apple Silicon). The system will ingest personal documents from a local folder, generate embeddings, store them in a local vector database, and answer user queries via a chat interface with **source citations**.

---

## 2. Scope (In-Scope vs Out-of-Scope)

### In Scope

* Fully offline local RAG system
* Local document ingestion (PDF, Markdown, TXT, HTML, JSON)
* Incremental updates of document embeddings
* Local vector store with persistence
* Local LLM inference using Ollama
* Single-user chat interface
* Source citations in responses
* Low-latency responses optimized for Apple Silicon

### Out of Scope (for this phase)

* Cloud workflows
* Tool calling / agents
* Multi-user access
* External APIs or internet access
* Messaging platforms (WhatsApp, X, website embeds)

---

## 3. Hardware & Environment

* Device: Mac mini
* Chip: Apple M4
* CPU: 10 cores (4 performance + 6 efficiency)
* Memory: 16 GB RAM
* OS: macOS
* Network: Offline / Localhost only

---

## 4. Core Design Principles

* **100% Offline** – No external API calls or internet dependency
* **Low Latency** – Fast embeddings and inference
* **Incremental Updates** – Only new/modified files are reprocessed
* **Modular Architecture** – Clean separation between ingestion, storage, and query
* **Future-Ready** – Clear boundaries for later cloud/agent expansion

---

## 5. High-Level Architecture

```
[ Local Data Folder ]
        ↓
[ Document Ingestion Script ]
        ↓
[ Embeddings via Ollama ]
        ↓
[ Local Vector Store (Chroma) ]
        ↓
[ Query Script ]
        ↓
[ Ollama LLM ]
        ↓
[ Chat UI + Citations ]
```

All components run locally on the same machine.

---

## 6. Model Selection

### Language Model (Generation)

* Primary: `llama3.1:8b-instruct-q4_0`
* Fallback: `mistral:7b-instruct`

Rationale:

* Fits comfortably within 16 GB RAM
* Strong reasoning and summarization
* Good RAG performance on Apple Silicon

### Embedding Model

* `nomic-embed-text` (via Ollama)

Rationale:

* Fast embedding generation
* High-quality semantic retrieval (768 dimensions)
* Low memory usage

---

## 7. Vector Store

* Technology: Chroma (local, file-based)
* Persistence: Enabled
* Storage Path: `rag/vectorstore/chroma/`

Each embedded chunk stores metadata including:

* Source filename
* File path
* Chunk ID
* Visibility tag (public/private)

---

## 8. Data Organization & Folder Structure

```
rag/
├── data/
│   ├── private/      # Personal, sensitive docs
│   ├── public/       # Shareable content
│   └── mixed/        # Other files
├── vectorstore/
│   └── chroma/
└── metadata/
    └── file_index.json
```

### Public vs Private Content

* `public/`: Content intended for future external or cloud access
* `private/`: Strictly personal data

This separation enables future policy-based access without re-indexing.

---

## 9. Chunking Strategy

* Chunk size: ~1000 characters
* Overlap: ~200 characters

This balances:

* Retrieval accuracy
* Citation correctness
* LLM context efficiency

---

## 10. Update & Sync Strategy

* Mechanism:

  * Track filename + MD5 hash
  * Compare against `metadata/file_index.json`
  * Only process new or changed files

This ensures minimal compute usage and low latency.

---

## 11. Scripts

### ingest_documents.py

1. Scan data directory
2. Detect new/modified files
3. Load file content
4. Chunk text
5. Generate embeddings via Ollama
6. Upsert into Chroma
7. Update file index metadata

### query_rag.py

1. Accept user query
2. Embed user query
3. Similarity search (Top-K) in Chroma
4. Construct prompt with retrieved context
5. Call Ollama LLM
6. Format response with citations
7. Return answer

---

## 12. Citation Format

Responses include a source section:

```
Sources:
- linkedin_posts.md (chunk 0)
- notes.md (chunk 1)
```

This ensures transparency and traceability.

---

## 13. Performance Expectations

* Embedding generation: Near-instant
* Vector search: Instant
* LLM response time:

  * Short answers: ~1-2 seconds
  * Long answers: ~2-4 seconds

---

## 14. Security & Privacy

* No internet connectivity required
* All data remains on local disk
* No external telemetry
* Single-user access

---

## 15. Future Extensions (Not Implemented Now)

* Web chat interface
* Scheduled automatic ingestion
* Tool calling and agent layers
* Multi-knowledge-base routing
* Personal memory and preference modeling

---

## 16. Definition of Done

* System runs fully offline
* Documents update into RAG on demand
* Queries return accurate answers
* Responses include correct citations
* Latency is acceptable for daily use

---

This document serves as the authoritative requirements and execution blueprint for the local RAG system.
