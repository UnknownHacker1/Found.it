"""
Foundit Backend - AI-Powered Conversational File Search
Uses RAG (Retrieval-Augmented Generation) with local LLM for intelligent file discovery
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from pathlib import Path
import json

from indexer import FileIndexer
from search_engine import SearchEngine
from rag_engine import RAGEngine
from llm_provider import LLMFactory, OpenRouterProvider
import config

app = FastAPI(title="Foundit API")

# Enable CORS for Electron frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize search engine
indexer = FileIndexer()
search_engine = SearchEngine()
rag_engine = None  # Will be initialized after model loads


class IndexRequest(BaseModel):
    path: str
    force_reindex: bool = False


class SearchRequest(BaseModel):
    query: str
    top_k: int = 10


class SearchResult(BaseModel):
    file_path: str
    file_name: str
    file_type: str
    similarity_score: float
    preview: Optional[str] = None


@app.get("/")
async def root():
    return {"message": "Foundit API is running", "status": "ok"}


@app.post("/index")
async def index_files(request: IndexRequest):
    """
    Index files from the specified directory
    Extracts content and generates AI embeddings
    """
    try:
        path = Path(request.path)
        if not path.exists():
            raise HTTPException(status_code=400, detail="Path does not exist")

        # Index files
        result = indexer.index_directory(
            str(path),
            force_reindex=request.force_reindex
        )

        # Build vector index
        search_engine.build_index(indexer.get_documents())

        return {
            "status": "success",
            "files_indexed": result["files_indexed"],
            "total_files": result["total_files"],
            "skipped": result["skipped"]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search", response_model=List[SearchResult])
async def search_files(request: SearchRequest):
    """
    Search for files using AI semantic search
    Finds files with similar content to the query
    """
    try:
        if not search_engine.is_ready():
            raise HTTPException(
                status_code=400,
                detail="Index not built. Please index files first."
            )

        results = search_engine.search(request.query, top_k=request.top_k)

        return [
            SearchResult(
                file_path=r["file_path"],
                file_name=Path(r["file_path"]).name,
                file_type=Path(r["file_path"]).suffix,
                similarity_score=r["score"],
                preview=r.get("preview", "")
            )
            for r in results
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat")
async def chat(request: SearchRequest):
    """
    Chat with the AI assistant about files
    Uses RAG to understand intent and find relevant files
    """
    try:
        if not rag_engine or not rag_engine.is_available():
            raise HTTPException(
                status_code=400,
                detail="RAG engine not ready. Make sure Ollama is running and files are indexed."
            )

        result = rag_engine.chat(request.query, top_k=request.top_k)

        return {
            "response": result["response"],
            "reasoning": result.get("reasoning", ""),
            "files": [
                SearchResult(
                    file_path=f["file_path"],
                    file_name=f["file_name"],
                    file_type=f["file_type"],
                    similarity_score=f.get("score", 0.0),
                    preview=f.get("preview", "")
                )
                for f in result["files"]
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/conversation-history")
async def get_conversation_history():
    """Get conversation history"""
    if not rag_engine:
        return {"history": []}
    return {"history": rag_engine.get_conversation_history()}


@app.post("/clear-conversation")
async def clear_conversation():
    """Clear conversation history"""
    if rag_engine:
        rag_engine.clear_conversation()
    return {"status": "success", "message": "Conversation cleared"}


@app.get("/status")
async def get_status():
    """Get indexing and search engine status"""
    return {
        "indexed_files": indexer.get_document_count(),
        "index_ready": search_engine.is_ready(),
        "model_loaded": search_engine.model is not None,
        "rag_ready": rag_engine is not None and rag_engine.is_available()
    }


@app.post("/clear-index")
async def clear_index():
    """Clear the entire index"""
    try:
        indexer.clear()
        search_engine.clear()
        return {"status": "success", "message": "Index cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def initialize_models():
    """Initialize AI models - called on startup"""
    global rag_engine

    print("Loading AI models (this may take a moment)...")

    # Pre-load the embedding model
    search_engine.load_model()

    # Initialize RAG engine with LLM
    print("Initializing RAG engine...")
    print(f"OpenRouter API key present: {bool(config.OPENROUTER_API_KEY)}")
    try:
        # Try to use OpenRouter if API key is set
        if config.OPENROUTER_API_KEY:
            print(f"Using OpenRouter with model: {config.OPENROUTER_MODEL}")
            llm_provider = OpenRouterProvider(
                model=config.OPENROUTER_MODEL,
                api_key=config.OPENROUTER_API_KEY
            )

            # Test if provider is available
            if llm_provider.is_available():
                print("✓ OpenRouter provider initialized")
            else:
                print("✗ OpenRouter provider not available (check API key)")

            rag_engine = RAGEngine(search_engine, llm_provider=llm_provider)
        else:
            # Fall back to auto-detect (tries OpenRouter, Ollama, OpenAI, Anthropic)
            print("No OpenRouter API key found. Trying other providers...")
            rag_engine = RAGEngine(search_engine)

        if rag_engine and rag_engine.is_available():
            print("✓ RAG engine ready! You can now chat with your files.")
        else:
            print("✗ Warning: RAG engine not fully available.")
            print("  Please set OPENROUTER_API_KEY in config.py")
            print("  Or install Ollama: https://ollama.com")
    except Exception as e:
        print(f"✗ Error: Could not initialize RAG engine: {e}")
        print("  Set OPENROUTER_API_KEY in backend/config.py to use OpenRouter")
        print("  Get free API key: https://openrouter.ai/keys")
        import traceback
        traceback.print_exc()


# Initialize models when the module is loaded (not when main is run)
initialize_models()


if __name__ == "__main__":
    print("Starting Foundit Backend Server...")
    print("Server ready!")
    uvicorn.run(app, host="127.0.0.1", port=8001)
