#!/usr/bin/env python3
"""
Chroma Vector Store Initialization Script
Initializes and validates the local Chroma database for the RAG system.
"""

import chromadb
from chromadb.config import Settings
import os
import json

# Paths
RAG_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_PATH = os.path.join(RAG_DIR, "rag", "vectorstore", "chroma")
METADATA_PATH = os.path.join(RAG_DIR, "rag", "metadata", "file_index.json")

def init_chroma():
    """Initialize Chroma with persistence."""
    print(f"Initializing Chroma at: {CHROMA_PATH}")
    
    # Create Chroma client with persistence
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    
    # Create or get the main collection
    collection = client.get_or_create_collection(
        name="local_rag",
        metadata={"description": "Local RAG document embeddings"}
    )
    
    print(f"✅ Collection 'local_rag' ready")
    print(f"   Current document count: {collection.count()}")
    
    return client, collection

def init_metadata():
    """Initialize the file index metadata file."""
    if not os.path.exists(METADATA_PATH):
        with open(METADATA_PATH, 'w') as f:
            json.dump({"files": {}, "last_updated": None}, f, indent=2)
        print(f"✅ Created file index at: {METADATA_PATH}")
    else:
        print(f"✅ File index exists at: {METADATA_PATH}")

def test_embedding():
    """Test embedding generation via Ollama."""
    import subprocess
    import json as json_module
    
    print("\nTesting embedding generation...")
    
    result = subprocess.run(
        ['curl', '-s', 'http://localhost:11434/api/embed', 
         '-d', '{"model":"nomic-embed-text","input":"test document for RAG system"}'],
        capture_output=True, text=True
    )
    
    if result.returncode == 0:
        response = json_module.loads(result.stdout)
        if 'embeddings' in response:
            embedding_dim = len(response['embeddings'][0])
            print(f"✅ Embedding generated successfully")
            print(f"   Dimension: {embedding_dim}")
            return True
    
    print("❌ Embedding generation failed")
    return False

if __name__ == "__main__":
    print("=" * 50)
    print("Local RAG System - Chroma Initialization")
    print("=" * 50)
    print()
    
    # Initialize Chroma
    client, collection = init_chroma()
    
    # Initialize metadata
    init_metadata()
    
    # Test embeddings
    test_embedding()
    
    print()
    print("=" * 50)
    print("Initialization complete!")
    print("=" * 50)
