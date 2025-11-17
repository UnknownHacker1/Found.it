"""
Foundit Backend - AI-Powered Conversational File Search
Uses RAG (Retrieval-Augmented Generation) with local LLM for intelligent file discovery
"""

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from pathlib import Path
import json
import logging

from indexer import FileIndexer
from search_engine import SearchEngine
from rag_engine import RAGEngine
from llm_provider import LLMFactory, OpenRouterProvider
import config
from auth import oauth, create_access_token, get_current_user, is_oauth_configured

logger = logging.getLogger(__name__)

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


# ===== OAuth Authentication Endpoints =====

@app.get("/auth/status")
async def auth_status():
    """Check if OAuth is configured and available"""
    return {
        "oauth_enabled": is_oauth_configured(),
        "provider": "google" if is_oauth_configured() else None
    }


@app.get("/auth/login")
async def login(request: Request):
    """
    Initiate Google OAuth login flow
    Redirects user to Google's consent screen
    """
    if not is_oauth_configured():
        raise HTTPException(
            status_code=503,
            detail="OAuth not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in config.py"
        )

    redirect_uri = config.GOOGLE_REDIRECT_URI
    return await oauth.google.authorize_redirect(request, redirect_uri)


@app.get("/auth/callback")
async def auth_callback(request: Request):
    """
    OAuth callback endpoint - Google redirects here after user consent
    Exchanges authorization code for user info and creates JWT token
    """
    if not is_oauth_configured():
        raise HTTPException(status_code=503, detail="OAuth not configured")

    try:
        # Exchange authorization code for access token
        token = await oauth.google.authorize_access_token(request)

        # Get user info from Google
        user_info = token.get('userinfo')
        if not user_info:
            raise HTTPException(status_code=400, detail="Failed to get user info")

        # Create JWT token for session
        access_token = create_access_token(
            data={
                "email": user_info.get("email"),
                "name": user_info.get("name"),
                "picture": user_info.get("picture"),
                "sub": user_info.get("sub")  # Google user ID
            }
        )

        # Redirect to frontend with token
        # Frontend will capture this and store the token
        return RedirectResponse(
            url=f"http://localhost:8001/auth/success?token={access_token}"
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Authentication failed: {str(e)}")


@app.get("/auth/success")
async def auth_success(token: str):
    """
    Success page that displays the token
    Frontend JavaScript will capture this token
    """
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Login Successful</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            }}
            .container {{
                background: white;
                padding: 40px;
                border-radius: 12px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                text-align: center;
            }}
            h1 {{
                color: #333;
                margin-bottom: 20px;
            }}
            .checkmark {{
                width: 80px;
                height: 80px;
                margin: 0 auto 20px;
                border-radius: 50%;
                background: #4CAF50;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            .checkmark::after {{
                content: '✓';
                color: white;
                font-size: 50px;
            }}
            p {{
                color: #666;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="checkmark"></div>
            <h1>Login Successful!</h1>
            <p>You can close this window.</p>
        </div>
        <script>
            // Send token to Electron app
            window.location.hash = '#token={token}';

            // Auto-close after 2 seconds
            setTimeout(() => {{
                window.close();
            }}, 2000);
        </script>
    </body>
    </html>
    """
    return JSONResponse(content={"token": token, "html": html_content})


@app.get("/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """
    Get current authenticated user info
    Protected endpoint - requires valid JWT token
    """
    return current_user


@app.post("/auth/logout")
async def logout(current_user: dict = Depends(get_current_user)):
    """
    Logout endpoint (token invalidation happens client-side)
    """
    return {"message": "Logged out successfully"}


# Global progress storage for polling
indexing_progress = {
    "percentage": 0,
    "current": 0,
    "total": 0,
    "status": "idle",
    "cancelled": False
}

@app.post("/index")
async def index_files(request: IndexRequest):
    """
    Index files from the specified directory
    Extracts content and generates AI embeddings
    """
    global indexing_progress

    try:
        path = Path(request.path)
        if not path.exists():
            raise HTTPException(status_code=400, detail="Path does not exist")

        # Reset progress
        indexing_progress = {
            "percentage": 0,
            "current": 0,
            "total": 0,
            "status": "indexing",
            "cancelled": False
        }

        def progress_callback(current, total, percentage):
            global indexing_progress
            # Check if cancelled
            if indexing_progress.get('cancelled'):
                raise Exception("Indexing cancelled by user")

            indexing_progress = {
                'current': current,
                'total': total,
                'percentage': percentage,
                'status': 'indexing',
                'cancelled': False
            }

        # Index files with progress tracking (0-90%)
        result = indexer.index_directory(
            str(path),
            force_reindex=request.force_reindex,
            progress_callback=progress_callback
        )

        # Check if cancelled before building embeddings
        if indexing_progress.get('cancelled'):
            indexing_progress['status'] = 'cancelled'
            return {
                "status": "cancelled",
                "files_indexed": 0,
                "total_files": 0,
                "skipped": 0,
                "progress": 0
            }

        # Build vector index (90-100%)
        indexing_progress['percentage'] = 95
        indexing_progress['status'] = 'building_embeddings'
        logger.info("Building embeddings...")
        search_engine.build_index(indexer.get_documents())

        # Complete
        indexing_progress['percentage'] = 100
        indexing_progress['status'] = 'complete'

        return {
            "status": "success",
            "files_indexed": result["files_indexed"],
            "total_files": result["total_files"],
            "skipped": result["skipped"],
            "progress": 100
        }

    except Exception as e:
        if "cancelled" in str(e).lower():
            indexing_progress['status'] = 'cancelled'
            return {
                "status": "cancelled",
                "files_indexed": 0,
                "total_files": 0,
                "skipped": 0,
                "progress": 0
            }
        indexing_progress['status'] = 'error'
        indexing_progress['error'] = str(e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/index-progress")
async def get_index_progress():
    """Get current indexing progress"""
    return indexing_progress


@app.post("/cancel-index")
async def cancel_index():
    """Cancel ongoing indexing operation"""
    global indexing_progress
    indexing_progress['cancelled'] = True
    indexing_progress['status'] = 'cancelled'
    return {"status": "cancelled"}


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


@app.post("/summarize-file")
async def summarize_file(request: dict):
    """
    Summarize a specific file
    """
    try:
        file_path = request.get("file_path")
        if not file_path:
            raise HTTPException(status_code=400, detail="file_path is required")

        from pathlib import Path
        from document_parser import DocumentParser

        path = Path(file_path)
        if not path.exists():
            raise HTTPException(status_code=404, detail="File not found")

        # Parse file content
        parser = DocumentParser()
        content = parser.parse(path)

        if not content:
            return {
                "summary": "Unable to extract text content from this file.",
                "file_name": path.name,
                "file_type": path.suffix
            }

        # Truncate if too long
        max_content_length = 8000
        truncated_content = content[:max_content_length]
        if len(content) > max_content_length:
            truncated_content += "\n\n[Content truncated...]"

        # Use LLM to summarize
        if not rag_engine or not rag_engine.is_available():
            # Fallback: return first 500 chars
            return {
                "summary": f"Preview: {content[:500]}..." if len(content) > 500 else content,
                "file_name": path.name,
                "file_type": path.suffix
            }

        summary_prompt = f"""You are a document summarization expert. Provide a clear, concise summary of this file.

File name: {path.name}
File type: {path.suffix}

Content:
{truncated_content}

IMPORTANT:
- If the file is SHORT (< 100 words), provide a 1-2 sentence summary
- If the file is MEDIUM (100-500 words), provide a 3-4 sentence summary
- If the file is LONG (500+ words), provide a detailed paragraph summary
- Focus on the KEY points, PURPOSE, and MAIN content
- Be clear and informative
- If it's a resume/CV: mention name, experience, education
- If it's a report: mention topic, findings, conclusions
- If it's code: mention language, purpose, main functions

Summary:"""

        summary = rag_engine.llm.generate(summary_prompt, max_tokens=500)

        return {
            "summary": summary.strip(),
            "file_name": path.name,
            "file_type": path.suffix,
            "content_length": len(content)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
                print("[OK] OpenRouter provider initialized")
            else:
                print("[ERROR] OpenRouter provider not available (check API key)")

            rag_engine = RAGEngine(search_engine, llm_provider=llm_provider)
        else:
            # Fall back to auto-detect (tries OpenRouter, Ollama, OpenAI, Anthropic)
            print("No OpenRouter API key found. Trying other providers...")
            rag_engine = RAGEngine(search_engine)

        if rag_engine and rag_engine.is_available():
            print("[OK] RAG engine ready! You can now chat with your files.")
        else:
            print("[WARNING] RAG engine not fully available.")
            print("  Please set OPENROUTER_API_KEY in config.py")
            print("  Or install Ollama: https://ollama.com")
    except Exception as e:
        print(f"[ERROR] Could not initialize RAG engine: {e}")
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
