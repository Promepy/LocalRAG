# LocalRAG - Fully Offline RAG System

A **100% local, privacy-first Retrieval-Augmented Generation (RAG) system** that runs entirely on your machine. Chat with your personal documents using local LLMs — no cloud, no API costs, no data leaving your device.

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![Ollama](https://img.shields.io/badge/Ollama-Local%20LLM-green.svg)
![Chroma](https://img.shields.io/badge/Chroma-Vector%20DB-purple.svg)
![Open WebUI](https://img.shields.io/badge/Open%20WebUI-Compatible-orange.svg)

---

## ✨ Features

- **Fully Offline** — No internet required after initial setup
- **Document Ingestion** — Supports Markdown, TXT, HTML, JSON, and PDF
- **Incremental Updates** — Only processes new/modified files
- **Source Citations** — Every answer includes document references
- **Fast Retrieval** — 768-dimensional embeddings with Chroma
- **Cross-Platform** — Works on macOS and Windows
- **Open WebUI Integration** — Use with a beautiful chat interface via OpenAI-compatible API

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    LocalRAG System                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  Documents   │───▶│   Chunking   │───▶│  Embeddings  │  │
│  │  (rag/data/) │    │  (1000 char) │    │ (nomic-text) │  │
│  └──────────────┘    └──────────────┘    └──────┬───────┘  │
│                                                  │          │
│                                                  ▼          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Response   │◀───│   Ollama     │◀───│    Chroma    │  │
│  │ + Citations  │    │   LLM 8B     │    │ Vector Store │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Flow:**
1. **Ingestion**: Documents → Chunk → Embed → Store in Chroma
2. **Query**: User question → Embed → Search Chroma → Retrieve context → Generate answer with LLM

---

## 🔒 Privacy Benefits

| Benefit | Description |
|---------|-------------|
| **Zero Cloud Dependency** | All processing happens on your machine |
| **No API Keys Needed** | No OpenAI, no Anthropic, no costs |
| **Data Never Leaves** | Documents stay on your local disk |
| **No Telemetry** | Ollama and Chroma don't phone home |
| **Full Control** | You own the models, data, and infrastructure |

**Use Cases:**
- Personal knowledge management with private notes
- Sensitive document Q&A (legal, medical, financial)
- Offline research assistant
- Corporate environments with strict data policies

---

## 💻 Setup Instructions

### macOS (Apple Silicon)

**Tested Configuration:**
| Component | Specification |
|-----------|---------------|
| Device | Mac mini |
| Chip | Apple M4 |
| CPU | 10 cores (4P + 6E) |
| Memory | 16 GB RAM |
| OS | macOS Sequoia |

**Compatible Macs:**
- Mac mini M1/M2/M3/M4 (8GB+ RAM)
- MacBook Air M1/M2/M3 (8GB+ RAM recommended, 16GB ideal)
- MacBook Pro M1/M2/M3/M4 (all configurations)
- Mac Studio M1/M2 Max/Ultra
- iMac M1/M3

**Installation:**

```bash
# 1. Install Ollama (download from https://ollama.com/download)
brew install ollama

# 2. Pull required models
ollama pull llama3.1:8b-instruct-q4_0
ollama pull nomic-embed-text

# 3. Install Python dependencies
pip3 install chromadb

# 4. Clone and setup
git clone <your-repo-url>
cd LocalRAG

# 5. Initialize Chroma
python3 init_chroma.py

# 6. Add your documents to rag/data/ folder

# 7. Run ingestion
python3 ingest_documents.py

# 8. Start chatting (Terminal)
python3 query_rag.py

# 9. OR start API server (for Open WebUI)
python3 rag_server.py
```

---

### Windows

**Requirements:**
- Windows 10/11
- Python 3.9+
- 8GB+ RAM (16GB recommended)

**Installation:**

```powershell
# 1. Install Ollama from https://ollama.com/download/windows

# 2. Pull required models
ollama pull llama3.1:8b-instruct-q4_0
ollama pull nomic-embed-text

# 3. Install Python dependencies
pip install chromadb

# 4. Clone and setup
git clone <your-repo-url>
cd LocalRAG

# 5. Initialize Chroma
python init_chroma.py

# 6. Add documents to rag\data\ folder

# 7. Run ingestion
python ingest_documents.py

# 8. Start chatting (Terminal)
python query_rag.py

# 9. OR start API server (for Open WebUI)
python rag_server.py
```

> **Note:** For PDF support on Windows, install [Xpdf tools](https://www.xpdfreader.com/download.html) and add to PATH.

---

## 📁 Project Structure

```
LocalRAG/
├── rag/
│   ├── data/
│   │   ├── private/      # Personal, sensitive docs
│   │   ├── public/       # Shareable content
│   │   └── mixed/        # Other files
│   ├── vectorstore/
│   │   └── chroma/       # Persistent vector DB
│   └── metadata/
│       └── file_index.json
├── init_chroma.py        # Initialize vector store
├── ingest_documents.py   # Document ingestion script
├── query_rag.py          # Interactive terminal chat
├── rag_server.py         # OpenAI-compatible API server
└── README.md
```

---

## 📊 Sample Output

```
============================================================
Local RAG Chat
Type 'quit' or 'exit' to end the session
============================================================

📚 Knowledge base: 20 document chunks

You: What are the advantages of local AI?

🔍 Searching...

Assistant: According to the context (public/linkedin_posts.md), 
the key advantages of local AI are:

* Complete privacy control
* No API costs
* No internet dependency
* Lower latency for some use cases

📎 Sources:
   - public/linkedin_posts.md (chunk 0)
   - public/linkedin_posts.md (chunk 1)
   - private/notes.md (chunk 0)
```

---

## 🌐 Open WebUI Integration

Use LocalRAG with [Open WebUI](https://github.com/open-webui/open-webui) for a beautiful chat interface:

### Setup

1. **Start the RAG API server:**
   ```bash
   python3 rag_server.py
   ```
   Server runs at `http://localhost:5001`

2. **Configure Open WebUI:**
   - Go to **Settings** → **Connections**
   - Add OpenAI API connection:
     - **URL**: `http://localhost:5001/v1`
     - **API Key**: `any-value` (not validated)

3. **Select `localrag` model** in the chat dropdown

Now all your chats in Open WebUI will use RAG with your local documents!

---

## 🚀 Future Extensions

| Extension | Description |
|-----------|-------------|
| **Scheduled Ingestion** | Use cron or Task Scheduler for automatic updates |
| **Multiple Collections** | Separate vector stores for different knowledge domains |
| **Hybrid Search** | Combine semantic search with keyword matching (BM25) |
| **Conversation Memory** | Add chat history for multi-turn conversations |
| **Larger Models** | Use Llama 70B or Mixtral for improved reasoning |

---

## 📄 License

MIT License - Feel free to use, modify, and distribute.

---

## 🙏 Acknowledgments

- [Ollama](https://ollama.com) - Local LLM runtime
- [Chroma](https://www.trychroma.com) - Vector database
- [Meta Llama](https://llama.meta.com) - Language model
- [Nomic](https://www.nomic.ai) - Embedding model
