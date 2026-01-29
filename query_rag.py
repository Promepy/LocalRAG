#!/usr/bin/env python3
"""
Chat/Query Script for Local RAG System
Takes a user query, retrieves relevant context from Chroma, and generates response with citations.
"""

import os
import json
import subprocess
import sys
import chromadb

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_PATH = os.path.join(BASE_DIR, "rag", "vectorstore", "chroma")
TOP_K = 5  # Number of chunks to retrieve

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
        print(f"Error getting embedding: {e}")
    return None

def retrieve_context(query, collection, top_k=TOP_K):
    """Retrieve relevant document chunks."""
    # Get query embedding
    query_embedding = get_embedding(query)
    if not query_embedding:
        return []
    
    # Search Chroma
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )
    
    contexts = []
    if results['documents'] and results['documents'][0]:
        for i, doc in enumerate(results['documents'][0]):
            metadata = results['metadatas'][0][i] if results['metadatas'] else {}
            distance = results['distances'][0][i] if results['distances'] else None
            contexts.append({
                "content": doc,
                "source": metadata.get("source", "unknown"),
                "chunk_index": metadata.get("chunk_index", 0),
                "distance": distance
            })
    
    return contexts

def generate_response(query, contexts):
    """Generate response using Ollama LLM with retrieved context."""
    
    # Build context string
    context_text = "\n\n".join([
        f"[Source: {ctx['source']}]\n{ctx['content']}"
        for ctx in contexts
    ])
    
    # Build prompt
    system_prompt = """You are a helpful assistant that answers questions based on the provided context.
Always cite your sources by mentioning the source file name when you use information from it.
If the context doesn't contain relevant information to answer the question, say so.
Be concise but thorough in your answers."""

    user_prompt = f"""Context documents:
{context_text}

Question: {query}

Based on the context above, please answer the question. Include source citations."""

    # Call Ollama
    payload = {
        "model": "llama3.1:8b-instruct-q4_0",
        "prompt": f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n{system_prompt}<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n{user_prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n",
        "stream": False
    }
    
    try:
        result = subprocess.run(
            ['curl', '-s', 'http://localhost:11434/api/generate',
             '-d', json.dumps(payload)],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            response = json.loads(result.stdout)
            return response.get("response", "")
    except Exception as e:
        print(f"Error generating response: {e}")
    
    return None

def format_sources(contexts):
    """Format source citations."""
    seen_sources = {}
    for ctx in contexts:
        source = ctx['source']
        if source not in seen_sources:
            seen_sources[source] = []
        seen_sources[source].append(ctx['chunk_index'])
    
    sources_text = "\n\nSources:\n"
    for source, chunks in seen_sources.items():
        chunk_str = ", ".join([f"chunk_{c:03d}" for c in sorted(chunks)])
        sources_text += f"- {source} ({chunk_str})\n"
    
    return sources_text

def query_rag(query):
    """Main query function."""
    # Initialize Chroma
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_or_create_collection(name="local_rag")
    
    if collection.count() == 0:
        return {
            "answer": "No documents in the knowledge base. Please run ingestion first.",
            "sources": [],
            "context_count": 0
        }
    
    # Retrieve context
    contexts = retrieve_context(query, collection)
    
    if not contexts:
        return {
            "answer": "Could not retrieve relevant context for your query.",
            "sources": [],
            "context_count": 0
        }
    
    # Generate response
    answer = generate_response(query, contexts)
    
    if not answer:
        return {
            "answer": "Error generating response. Please check if Ollama is running.",
            "sources": [],
            "context_count": 0
        }
    
    # Format sources
    sources = [{"source": ctx["source"], "chunk": ctx["chunk_index"]} for ctx in contexts]
    
    return {
        "answer": answer,
        "sources": sources,
        "context_count": len(contexts)
    }

def interactive_mode():
    """Run in interactive chat mode."""
    print("=" * 60)
    print("Local RAG Chat")
    print("Type 'quit' or 'exit' to end the session")
    print("=" * 60)
    print()
    
    # Check collection
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client.get_or_create_collection(name="local_rag")
    print(f"📚 Knowledge base: {collection.count()} document chunks\n")
    
    while True:
        try:
            query = input("You: ").strip()
            
            if not query:
                continue
            
            if query.lower() in ['quit', 'exit', 'q']:
                print("\nGoodbye!")
                break
            
            print("\n🔍 Searching...\n")
            result = query_rag(query)
            
            print(f"Assistant: {result['answer']}")
            
            if result['sources']:
                print("\n📎 Sources:")
                for src in result['sources']:
                    print(f"   - {src['source']} (chunk {src['chunk']})")
            
            print()
            
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Single query mode
        query = " ".join(sys.argv[1:])
        result = query_rag(query)
        print(json.dumps(result, indent=2))
    else:
        # Interactive mode
        interactive_mode()
