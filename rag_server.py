#!/usr/bin/env python3
"""
RAG API Server - OpenAI-Compatible API for LocalRAG
Provides an OpenAI-compatible endpoint that integrates with Open WebUI.
Automatically retrieves relevant context from Chroma before generating responses.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os
import subprocess
import chromadb

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_PATH = os.path.join(BASE_DIR, "rag", "vectorstore", "chroma")
TOP_K = 5
MODEL_NAME = "localrag"  # Virtual model name shown in Open WebUI
OLLAMA_MODEL = "llama3.1:8b-instruct-q4_0"
PORT = 5001

# Initialize Chroma
client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = client.get_or_create_collection(name="local_rag")

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
        print(f"Embedding error: {e}")
    return None

def retrieve_context(query, top_k=TOP_K):
    """Retrieve relevant document chunks from Chroma."""
    if collection.count() == 0:
        return []
    
    query_embedding = get_embedding(query)
    if not query_embedding:
        return []
    
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas"]
    )
    
    contexts = []
    if results['documents'] and results['documents'][0]:
        for i, doc in enumerate(results['documents'][0]):
            metadata = results['metadatas'][0][i] if results['metadatas'] else {}
            contexts.append({
                "content": doc,
                "source": metadata.get("source", "unknown")
            })
    return contexts

def build_rag_prompt(messages, contexts):
    """Inject RAG context into the conversation."""
    if not contexts:
        return messages
    
    # Build context string
    context_text = "\n\n".join([
        f"[Source: {ctx['source']}]\n{ctx['content']}"
        for ctx in contexts
    ])
    
    # Create system message with RAG context
    rag_system = f"""You are a helpful assistant with access to a personal knowledge base.
Use the following context from the user's documents to answer questions.
Always cite sources when using information from the context.
If the context doesn't contain relevant info, say so and answer based on general knowledge.

--- RETRIEVED CONTEXT ---
{context_text}
--- END CONTEXT ---
"""
    
    # Prepend or merge with existing system message
    new_messages = []
    has_system = False
    
    for msg in messages:
        if msg.get("role") == "system":
            has_system = True
            new_messages.append({
                "role": "system",
                "content": rag_system + "\n\nAdditional instructions: " + msg.get("content", "")
            })
        else:
            new_messages.append(msg)
    
    if not has_system:
        new_messages.insert(0, {"role": "system", "content": rag_system})
    
    return new_messages

def call_ollama(messages, stream=False):
    """Call Ollama API with messages."""
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": stream
    }
    
    try:
        result = subprocess.run(
            ['curl', '-s', 'http://localhost:11434/api/chat',
             '-d', json.dumps(payload)],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception as e:
        print(f"Ollama error: {e}")
    return None

class RAGHandler(BaseHTTPRequestHandler):
    def _set_headers(self, status=200, content_type='application/json'):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()
    
    def do_OPTIONS(self):
        self._set_headers(200)
    
    def do_GET(self):
        if self.path == '/v1/models' or self.path == '/api/tags':
            # List available models (OpenAI format)
            self._set_headers()
            response = {
                "object": "list",
                "data": [
                    {
                        "id": MODEL_NAME,
                        "object": "model",
                        "created": 1700000000,
                        "owned_by": "local",
                        "name": MODEL_NAME
                    }
                ],
                "models": [
                    {
                        "name": MODEL_NAME,
                        "model": MODEL_NAME,
                        "modified_at": "2024-01-01T00:00:00Z",
                        "size": 0,
                        "digest": "localrag"
                    }
                ]
            }
            self.wfile.write(json.dumps(response).encode())
        
        elif self.path == '/health' or self.path == '/':
            self._set_headers()
            self.wfile.write(json.dumps({
                "status": "ok",
                "model": MODEL_NAME,
                "documents": collection.count()
            }).encode())
        
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Not found"}).encode())
    
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        
        try:
            data = json.loads(body) if body else {}
        except:
            self._set_headers(400)
            self.wfile.write(json.dumps({"error": "Invalid JSON"}).encode())
            return
        
        # Handle chat completions (OpenAI format)
        if self.path in ['/v1/chat/completions', '/api/chat']:
            messages = data.get('messages', [])
            
            if not messages:
                self._set_headers(400)
                self.wfile.write(json.dumps({"error": "No messages provided"}).encode())
                return
            
            # Get user's last message for RAG query
            user_query = ""
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    user_query = msg.get("content", "")
                    break
            
            # Retrieve RAG context
            print(f"📚 RAG Query: {user_query[:50]}...")
            contexts = retrieve_context(user_query)
            print(f"   Retrieved {len(contexts)} contexts")
            
            # Build RAG-enhanced messages
            rag_messages = build_rag_prompt(messages, contexts)
            
            # Call Ollama
            response = call_ollama(rag_messages, stream=False)
            
            if response:
                # Format as OpenAI response
                assistant_content = response.get('message', {}).get('content', '')
                
                # Add source citations if available
                if contexts:
                    sources = list(set([ctx['source'] for ctx in contexts]))
                    assistant_content += f"\n\n📎 Sources: {', '.join(sources)}"
                
                openai_response = {
                    "id": "chatcmpl-localrag",
                    "object": "chat.completion",
                    "created": 1700000000,
                    "model": MODEL_NAME,
                    "choices": [{
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": assistant_content
                        },
                        "finish_reason": "stop"
                    }],
                    "usage": {
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0
                    }
                }
                
                self._set_headers()
                self.wfile.write(json.dumps(openai_response).encode())
            else:
                self._set_headers(500)
                self.wfile.write(json.dumps({"error": "Failed to get response from Ollama"}).encode())
        
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Endpoint not found"}).encode())
    
    def log_message(self, format, *args):
        print(f"[RAG API] {args[0]}")

def run_server():
    print("=" * 60)
    print("LocalRAG API Server")
    print("=" * 60)
    print(f"📚 Knowledge base: {collection.count()} document chunks")
    print(f"🚀 Server running at: http://localhost:{PORT}")
    print(f"📡 OpenAI-compatible endpoint: http://localhost:{PORT}/v1/chat/completions")
    print()
    print("To connect Open WebUI:")
    print("  1. Go to Settings → Connections")
    print(f"  2. Add OpenAI API: http://localhost:{PORT}/v1")
    print("  3. API Key: any value (not validated)")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 60)
    
    server = HTTPServer(('localhost', PORT), RAGHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()

if __name__ == "__main__":
    run_server()
