#!/usr/bin/env python3
"""
Document Ingestion Script for Local RAG System
Processes documents from rag/data folder, generates embeddings, and stores in Chroma.
Called by n8n ingestion workflow or can run standalone.
"""

import os
import json
import hashlib
import subprocess
from datetime import datetime
from pathlib import Path
import chromadb

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "rag", "data")
CHROMA_PATH = os.path.join(BASE_DIR, "rag", "vectorstore", "chroma")
METADATA_PATH = os.path.join(BASE_DIR, "rag", "metadata", "file_index.json")

# Supported file types
SUPPORTED_EXTENSIONS = {'.pdf', '.md', '.txt', '.html', '.json'}

# Chunking config
CHUNK_SIZE = 1000  # characters (approx 250 tokens)
CHUNK_OVERLAP = 200

def load_file_index():
    """Load existing file index."""
    if os.path.exists(METADATA_PATH):
        with open(METADATA_PATH, 'r') as f:
            return json.load(f)
    return {"files": {}, "last_updated": None}

def save_file_index(index):
    """Save file index."""
    index["last_updated"] = datetime.now().isoformat()
    with open(METADATA_PATH, 'w') as f:
        json.dump(index, f, indent=2)

def get_file_hash(filepath):
    """Get MD5 hash of file content."""
    with open(filepath, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()

def read_file_content(filepath):
    """Read and extract text content from file."""
    ext = Path(filepath).suffix.lower()
    
    try:
        if ext == '.pdf':
            # For PDFs, we'd need PyPDF2 or similar
            # For simplicity, skip PDFs for now or use pdftotext
            result = subprocess.run(['pdftotext', filepath, '-'], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout
            return None
        elif ext in {'.md', '.txt', '.html'}:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
        elif ext == '.json':
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return json.dumps(data, indent=2)
    except Exception as e:
        print(f"  Error reading {filepath}: {e}")
        return None
    
    return None

def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        
        # Try to break at sentence boundary
        if end < len(text):
            last_period = chunk.rfind('.')
            last_newline = chunk.rfind('\n')
            break_point = max(last_period, last_newline)
            if break_point > chunk_size // 2:
                chunk = chunk[:break_point + 1]
                end = start + break_point + 1
        
        if chunk.strip():
            chunks.append(chunk.strip())
        
        start = end - overlap
        if start < 0:
            start = 0
        if end >= len(text):
            break
    
    return chunks

def get_embedding(text):
    """Get embedding from Ollama."""
    try:
        result = subprocess.run(
            ['curl', '-s', 'http://localhost:11434/api/embed',
             '-d', json.dumps({"model": "nomic-embed-text", "input": text})],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            response = json.loads(result.stdout)
            if 'embeddings' in response:
                return response['embeddings'][0]
    except Exception as e:
        print(f"  Error getting embedding: {e}")
    return None

def get_visibility(filepath):
    """Determine visibility based on folder structure."""
    if '/private/' in filepath:
        return 'private'
    elif '/public/' in filepath:
        return 'public'
    return 'mixed'

def scan_data_folder():
    """Scan data folder for files to process."""
    files_to_process = []
    
    for root, dirs, files in os.walk(DATA_DIR):
        for filename in files:
            filepath = os.path.join(root, filename)
            ext = Path(filepath).suffix.lower()
            
            if ext in SUPPORTED_EXTENSIONS:
                files_to_process.append(filepath)
    
    return files_to_process

def process_file(filepath, collection, file_index):
    """Process a single file: read, chunk, embed, store."""
    relative_path = os.path.relpath(filepath, DATA_DIR)
    file_hash = get_file_hash(filepath)
    
    # Check if file needs processing
    if relative_path in file_index["files"]:
        if file_index["files"][relative_path]["hash"] == file_hash:
            print(f"  ⏭️  Skipping (unchanged): {relative_path}")
            return 0
        else:
            # File changed - delete old chunks
            print(f"  🔄 File changed, re-processing: {relative_path}")
            old_ids = file_index["files"][relative_path].get("chunk_ids", [])
            if old_ids:
                try:
                    collection.delete(ids=old_ids)
                except:
                    pass
    
    # Read content
    content = read_file_content(filepath)
    if not content or len(content.strip()) < 50:
        print(f"  ⏭️  Skipping (empty/too short): {relative_path}")
        return 0
    
    # Chunk content
    chunks = chunk_text(content)
    if not chunks:
        return 0
    
    print(f"  📄 Processing: {relative_path} ({len(chunks)} chunks)")
    
    # Generate embeddings and store
    chunk_ids = []
    documents = []
    embeddings = []
    metadatas = []
    
    visibility = get_visibility(filepath)
    
    for i, chunk in enumerate(chunks):
        chunk_id = f"{hashlib.md5(relative_path.encode()).hexdigest()[:8]}_{i:04d}"
        
        embedding = get_embedding(chunk)
        if embedding:
            chunk_ids.append(chunk_id)
            documents.append(chunk)
            embeddings.append(embedding)
            metadatas.append({
                "source": relative_path,
                "chunk_index": i,
                "visibility": visibility,
                "filename": os.path.basename(filepath)
            })
    
    if chunk_ids:
        collection.add(
            ids=chunk_ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas
        )
        
        # Update file index
        file_index["files"][relative_path] = {
            "hash": file_hash,
            "chunk_ids": chunk_ids,
            "chunk_count": len(chunk_ids),
            "last_processed": datetime.now().isoformat()
        }
        
        return len(chunk_ids)
    
    return 0

def run_ingestion():
    """Main ingestion function."""
    print("=" * 60)
    print("Local RAG - Document Ingestion")
    print(f"Time: {datetime.now().isoformat()}")
    print("=" * 60)
    print()
    
    # Initialize Chroma
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_or_create_collection(name="local_rag")
    
    # Load file index
    file_index = load_file_index()
    
    # Scan for files
    files = scan_data_folder()
    print(f"Found {len(files)} files to check\n")
    
    # Process files
    total_chunks = 0
    processed_files = 0
    
    for filepath in files:
        chunks_added = process_file(filepath, collection, file_index)
        if chunks_added > 0:
            total_chunks += chunks_added
            processed_files += 1
    
    # Save index
    save_file_index(file_index)
    
    print()
    print("=" * 60)
    print(f"Ingestion Complete!")
    print(f"  Files processed: {processed_files}")
    print(f"  Chunks added: {total_chunks}")
    print(f"  Total docs in collection: {collection.count()}")
    print("=" * 60)
    
    return {"processed": processed_files, "chunks": total_chunks, "total": collection.count()}

if __name__ == "__main__":
    run_ingestion()
