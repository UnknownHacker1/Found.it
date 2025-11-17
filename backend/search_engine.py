"""
AI-Powered Search Engine
Uses sentence-transformers for embeddings and FAISS for vector similarity search
"""

from typing import List, Dict, Optional
import numpy as np
import logging
import json
import os
import sys
from pathlib import Path

# Sentence transformers for AI embeddings
try:
    from sentence_transformers import SentenceTransformer
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

# FAISS for vector similarity search
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SearchEngine:
    """
    AI-powered semantic search engine
    Converts text to embeddings and finds similar documents
    """

    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """
        Initialize search engine with AI model

        Default model: all-MiniLM-L6-v2
        - Fast and efficient
        - Good quality embeddings
        - Only ~80MB download
        - 384 dimensional vectors
        """
        self.model_name = model_name
        self.model = None
        self.index = None
        self.documents = []
        self.embeddings = None

        if not TRANSFORMERS_AVAILABLE:
            logger.error("sentence-transformers not installed!")
            logger.error("Install with: pip install sentence-transformers")

        if not FAISS_AVAILABLE:
            logger.error("faiss not installed!")
            logger.error("Install with: pip install faiss-cpu")

    def load_model(self):
        """Load the AI embedding model"""
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError("sentence-transformers not installed")

        if self.model is None:
            logger.info(f"Loading AI model: {self.model_name}...")
            logger.info("This may take a moment on first run (downloading model)...")

            self.model = SentenceTransformer(self.model_name)

            logger.info("Model loaded successfully!")

    def build_index(self, documents: List[Dict]):
        """
        Build vector index from documents
        Generates embeddings and creates FAISS index
        """
        if not TRANSFORMERS_AVAILABLE or not FAISS_AVAILABLE:
            raise ImportError("Required libraries not installed")

        if not documents:
            logger.warning("No documents to index")
            return

        # Load model if not already loaded
        if self.model is None:
            self.load_model()

        logger.info(f"Building index for {len(documents)} documents...")

        # Store documents
        self.documents = documents

        # Create enriched text for better semantic understanding
        # Combine filename, file type, and content
        texts = []
        for doc in documents:
            # Build enriched text: filename + file type + content
            enriched = f"Filename: {doc['file_name']}. "
            enriched += f"Type: {doc['file_type']}. "
            enriched += f"Content: {doc['content']}"
            texts.append(enriched)

        # Generate embeddings
        logger.info("Generating AI embeddings (this may take a while)...")
        self.embeddings = self.model.encode(
            texts,
            show_progress_bar=True,
            batch_size=32
        )

        # Build FAISS index
        logger.info("Building FAISS index...")
        dimension = self.embeddings.shape[1]

        # Use IndexFlatIP for cosine similarity (after normalization)
        self.index = faiss.IndexFlatIP(dimension)

        # Normalize embeddings for cosine similarity
        faiss.normalize_L2(self.embeddings)

        # Add to index
        self.index.add(self.embeddings)

        logger.info(f"Index built! Ready to search {len(documents)} documents")

    def search(self, query: str, top_k: int = 10) -> List[Dict]:
        """
        Search for documents similar to the query
        Uses AI to understand semantic meaning with query expansion
        """
        if self.index is None or self.model is None:
            raise ValueError("Index not built. Call build_index() first")

        # Expand query with related terms for better matching
        expanded_query = self._expand_query(query)

        # Generate query embedding using expanded query
        query_embedding = self.model.encode([expanded_query])

        # Normalize for cosine similarity
        faiss.normalize_L2(query_embedding)

        # Search for more results than needed (we'll re-rank)
        search_k = min(top_k * 3, len(self.documents))
        scores, indices = self.index.search(query_embedding, search_k)

        # Prepare results with hybrid scoring
        results = []
        query_lower = query.lower()
        query_terms = set(query_lower.split())

        for score, idx in zip(scores[0], indices[0]):
            if idx < len(self.documents):
                doc = self.documents[idx].copy()

                # Base semantic similarity score
                semantic_score = float(score)

                # Boost score if filename contains query terms
                filename_lower = doc['file_name'].lower()
                filename_boost = 0.0

                # Check for exact phrase match in filename
                if query_lower in filename_lower:
                    filename_boost = 0.3
                # Check for individual term matches
                elif any(term in filename_lower for term in query_terms):
                    filename_boost = 0.15

                # Combined hybrid score
                final_score = min(1.0, semantic_score + filename_boost)

                doc['score'] = final_score
                doc['semantic_score'] = semantic_score
                doc['filename_boost'] = filename_boost

                # Don't include full content in results (too large)
                doc.pop('content', None)
                results.append(doc)

        # Sort by final score and return top_k
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:top_k]

    def _expand_query(self, query: str) -> str:
        """
        Expand query with related terms for better semantic matching
        """
        query_lower = query.lower()

        # Define domain-specific expansions
        expansions = {
            'travel': 'travel passport visa immigration i94 i-94 flight ticket boarding',
            'travel documents': 'passport visa i94 i-94 immigration travel authorization boarding pass flight ticket',
            'passport': 'passport travel document identification visa',
            'visa': 'visa immigration travel authorization permit',
            'i94': 'i94 i-94 immigration arrival departure form travel',
            'flight': 'flight ticket boarding pass airline travel itinerary',
            'math': 'math mathematics calculus algebra geometry arithmetic equations',
            'homework': 'homework assignment problem set exercises coursework',
            'code': 'code programming source script implementation function',
            'python': 'python programming code script .py development',
            'java': 'java programming code class .java development',
            'meeting': 'meeting notes minutes discussion agenda action items',
            'budget': 'budget financial expenses costs spending money',
            'invoice': 'invoice bill receipt payment transaction',
            'contract': 'contract agreement legal document terms',
            'resume': 'resume cv curriculum vitae employment job career',
        }

        # Check if query matches any expansion categories
        expanded = query
        for key, expansion in expansions.items():
            if key in query_lower:
                expanded = f"{query} {expansion}"
                break

        return expanded

    def is_ready(self) -> bool:
        """Check if search engine is ready"""
        return self.index is not None and self.model is not None

    def clear(self):
        """Clear the index"""
        self.index = None
        self.documents = []
        self.embeddings = None
        logger.info("Search index cleared")

    def get_model_info(self) -> Dict:
        """Get information about the loaded model"""
        if self.model is None:
            return {"loaded": False}

        return {
            "loaded": True,
            "model_name": self.model_name,
            "embedding_dimension": self.model.get_sentence_embedding_dimension(),
            "max_sequence_length": self.model.max_seq_length
        }

    def get_cache_dir(self) -> Path:
        """Get persistent cache directory based on OS"""
        if os.name == 'nt':  # Windows
            base = Path(os.getenv('LOCALAPPDATA', os.path.expanduser('~\\AppData\\Local')))
        elif sys.platform == 'darwin':  # Mac
            base = Path.home() / 'Library' / 'Application Support'
        else:  # Linux
            base = Path.home() / '.local' / 'share'

        cache_dir = base / 'Foundit' / 'index'
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    def save_index(self):
        """Save index to disk for instant loading on restart"""
        if self.index is None or not self.documents:
            logger.warning("No index to save")
            return

        try:
            cache_dir = self.get_cache_dir()

            # Save FAISS index
            faiss.write_index(self.index, str(cache_dir / 'index.faiss'))

            # Save documents metadata (without content to reduce file size)
            docs_to_save = []
            for doc in self.documents:
                doc_copy = doc.copy()
                # Keep content but truncate if too large
                if 'content' in doc_copy and len(doc_copy['content']) > 5000:
                    doc_copy['content'] = doc_copy['content'][:5000] + '...[truncated]'
                docs_to_save.append(doc_copy)

            with open(cache_dir / 'documents.json', 'w', encoding='utf-8') as f:
                json.dump(docs_to_save, f, ensure_ascii=False, indent=2)

            # Save embeddings
            np.save(cache_dir / 'embeddings.npy', self.embeddings)

            # Save metadata (file count, last updated)
            metadata = {
                'file_count': len(self.documents),
                'model_name': self.model_name,
                'version': '1.0'
            }
            with open(cache_dir / 'metadata.json', 'w') as f:
                json.dump(metadata, f, indent=2)

            logger.info(f"✓ Index saved to {cache_dir} ({len(self.documents)} files)")

        except Exception as e:
            logger.error(f"Failed to save index: {e}")

    def load_index(self) -> bool:
        """Load index from disk (skip re-indexing!) - Returns True if successful"""
        try:
            cache_dir = self.get_cache_dir()

            index_file = cache_dir / 'index.faiss'
            docs_file = cache_dir / 'documents.json'
            emb_file = cache_dir / 'embeddings.npy'
            meta_file = cache_dir / 'metadata.json'

            # Check if all required files exist
            if not all([index_file.exists(), docs_file.exists(), emb_file.exists()]):
                logger.info("No cached index found - will need to index files")
                return False

            # Load model first (needed for search)
            if self.model is None:
                self.load_model()

            # Load FAISS index
            self.index = faiss.read_index(str(index_file))

            # Load documents
            with open(docs_file, 'r', encoding='utf-8') as f:
                self.documents = json.load(f)

            # Load embeddings
            self.embeddings = np.load(emb_file)

            # Load metadata if exists
            if meta_file.exists():
                with open(meta_file, 'r') as f:
                    metadata = json.load(f)
                    logger.info(f"✓ Loaded cached index: {metadata.get('file_count', len(self.documents))} files")
            else:
                logger.info(f"✓ Loaded cached index: {len(self.documents)} files")

            logger.info("Index loaded from cache (instant!) - ready to search")
            return True

        except Exception as e:
            logger.error(f"Failed to load cached index: {e}")
            logger.info("Will perform fresh indexing instead")
            # Clear any partial state
            self.index = None
            self.documents = []
            self.embeddings = None
            return False
