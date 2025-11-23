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

    def __init__(self, model_name: str = 'all-MiniLM-L6-v2', llm_provider=None):
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
        self.llm_provider = llm_provider  # Optional LLM for intelligent query expansion
        self.expansion_cache = {}  # Cache AI expansions for speed

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
        # Combine filename, file type, content, AND document type classification
        texts = []
        for doc in documents:
            # Classify document type based on content
            doc_type = self._classify_document_type(doc['content'], doc['file_name'])

            # Build RICH enriched text with document type semantics
            enriched = f"Document Type: {doc_type}. "
            enriched += f"Filename: {doc['file_name']}. "
            enriched += f"File Format: {doc['file_type']}. "
            enriched += f"Content: {doc['content']}"

            # Store document type in metadata for later use
            doc['document_type'] = doc_type

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

    def search(self, query: str, top_k: int = 10, use_ai_expansion: bool = False) -> List[Dict]:
        """
        Search for documents similar to the query
        Uses AI to understand semantic meaning with intelligent query expansion

        Args:
            query: User's search query
            top_k: Number of results to return
            use_ai_expansion: If True, uses AI to expand query (slower but smarter)
                             If False, uses fast fallback expansion (default for speed)
        """
        if self.index is None or self.model is None:
            raise ValueError("Index not built. Call build_index() first")

        # SPEED OPTIMIZATION: Skip AI expansion by default, use fast fallback
        # AI expansion adds 1-2 seconds, fallback is instant
        if use_ai_expansion:
            expanded_query = self._expand_query_with_ai(query)
        else:
            # Use fast fallback for instant results
            expanded_query = self._expand_query_fallback(query)

        # Generate query embedding using expanded query
        query_embedding = self.model.encode([expanded_query])

        # Normalize for cosine similarity
        faiss.normalize_L2(query_embedding)

        # Search for more results than needed (we'll re-rank)
        search_k = min(top_k * 3, len(self.documents))
        scores, indices = self.index.search(query_embedding, search_k)

        # Prepare results with ENHANCED hybrid scoring
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

                # NEW: Document type matching boost - CRITICAL for intent understanding
                doc_type_boost = 0.0
                doc_type = doc.get('document_type', '').lower()

                # Strong boost if document type matches query intent
                if 'resume' in query_lower or 'cv' in query_lower:
                    if 'resume' in doc_type or 'curriculum vitae' in doc_type or 'professional profile' in doc_type:
                        doc_type_boost = 0.4  # Strong boost for resume queries matching resume documents
                    elif 'transcript' in doc_type or 'tax' in doc_type or 'immigration' in doc_type:
                        doc_type_boost = -0.3  # Penalize clearly wrong document types

                elif 'transcript' in query_lower or 'grade' in query_lower:
                    if 'transcript' in doc_type:
                        doc_type_boost = 0.4
                    elif 'resume' in doc_type:
                        doc_type_boost = -0.2

                elif 'travel' in query_lower or 'passport' in query_lower or 'visa' in query_lower:
                    if 'immigration' in doc_type or 'passport' in doc_type or 'travel' in doc_type:
                        doc_type_boost = 0.4
                    elif 'resume' in doc_type or 'tax' in doc_type:
                        doc_type_boost = -0.2

                elif 'homework' in query_lower or 'assignment' in query_lower or 'math' in query_lower or 'calculus' in query_lower:
                    if 'homework' in doc_type or 'assignment' in doc_type or 'math' in doc_type or 'calculus' in doc_type:
                        doc_type_boost = 0.4
                    elif 'resume' in doc_type or 'tax' in doc_type or 'immigration' in doc_type:
                        doc_type_boost = -0.2

                # Combined hybrid score with document type intelligence
                final_score = max(0.0, min(1.0, semantic_score + filename_boost + doc_type_boost))

                doc['score'] = final_score
                doc['semantic_score'] = semantic_score
                doc['filename_boost'] = filename_boost
                doc['doc_type_boost'] = doc_type_boost

                # Don't include full content in results (too large)
                doc.pop('content', None)
                results.append(doc)

        # Sort by final score and return top_k
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:top_k]

    def _classify_document_type(self, content: str, filename: str) -> str:
        """
        Classify document type based on content patterns for better semantic understanding
        This helps the embeddings understand what KIND of document it is
        """
        content_lower = content.lower()
        filename_lower = filename.lower()

        # Resume/CV detection - look for career-related patterns
        resume_indicators = [
            'education', 'work experience', 'skills', 'professional experience',
            'employment history', 'curriculum vitae', 'linkedin', 'github',
            'bachelor', 'master', 'university', 'degree', 'gpa',
            'projects', 'certifications', 'references'
        ]
        resume_score = sum(1 for indicator in resume_indicators if indicator in content_lower)

        # Check for resume structure (contact info + education + experience)
        has_contact = any(x in content_lower for x in ['email', 'phone', '@', 'linkedin', 'github'])
        has_education = any(x in content_lower for x in ['education', 'university', 'bachelor', 'master', 'degree', 'gpa'])
        has_experience = any(x in content_lower for x in ['experience', 'work', 'employment', 'skills', 'projects'])

        if (resume_score >= 3) or (has_contact and has_education and has_experience):
            return "Resume CV Curriculum Vitae Professional Profile Career Document"

        # Cover letter detection
        if any(x in content_lower for x in ['dear hiring', 'i am writing to apply', 'cover letter', 'sincerely', 'application for']):
            return "Cover Letter Job Application"

        # Academic transcript detection
        if any(x in content_lower for x in ['transcript', 'course', 'grade', 'credit hours', 'semester', 'gpa']) and \
           any(x in content_lower for x in ['official', 'university', 'college', 'registrar']):
            return "Academic Transcript Grade Report Educational Record"

        # Immigration/Travel documents
        if any(x in content_lower for x in ['i-20', 'i20', 'sevis', 'homeland security', 'nonimmigrant student']):
            return "Immigration Document I-20 Student Visa Travel Authorization"

        if any(x in content_lower for x in ['i-94', 'i94', 'arrival', 'departure', 'admission number']):
            return "Immigration Document I-94 Travel Record Arrival Departure"

        if any(x in content_lower for x in ['passport', 'nationality', 'passport number', 'place of birth']):
            return "Passport Travel Document Identification"

        # Tax documents
        if any(x in content_lower for x in ['w-2', 'w2', 'wage and tax', 'employer identification', 'social security']) and \
           any(x in content_lower for x in ['wages', 'federal', 'income tax']):
            return "Tax Document W-2 Form Wage Statement"

        # Financial documents
        if any(x in content_lower for x in ['budget', 'expenses', 'revenue', 'financial report', 'quarterly']):
            return "Financial Document Budget Report Expense Revenue"

        if any(x in content_lower for x in ['invoice', 'payment', 'bill', 'amount due']):
            return "Invoice Bill Payment Receipt"

        # Meeting notes/workflow
        if any(x in content_lower for x in ['meeting minutes', 'agenda', 'action items', 'attendees']):
            return "Meeting Notes Minutes Documentation"

        if any(x in content_lower for x in ['workflow', 'process', 'procedure', 'steps']):
            return "Workflow Document Process Guide Procedure"

        # Academic/homework - check for calculus/math homework patterns
        if any(x in content_lower for x in ['homework', 'assignment', 'problem set', 'due date', 'calculus', 'derivative', 'integral', 'solve for', 'find the value', 'exercise']) or \
           'hw' in filename_lower or 'homework' in filename_lower or 'not_hw' in filename_lower:
            # Additional check for math/calculus content
            math_indicators = ['∫', 'derivative', 'integral', 'calculus', 'equation', 'solve', 'find x', 'problem']
            if any(indicator in content_lower for indicator in math_indicators):
                return "Academic Assignment Homework Problem Set Math Calculus Exercise"
            return "Academic Assignment Homework Problem Set"

        # Lab reports
        if any(x in content_lower for x in ['lab report', 'experiment', 'procedure', 'results', 'conclusion', 'hypothesis']):
            return "Lab Report Scientific Experiment Academic"

        # Default: Generic document
        return "General Document File"

    def _expand_query_with_ai(self, query: str) -> str:
        """
        Use AI (LLM) to intelligently expand the query with semantic alternatives
        OPTIMIZED for speed with caching and shorter prompts
        """
        # Check cache first - HUGE speed improvement!
        cache_key = query.lower().strip()
        if cache_key in self.expansion_cache:
            logger.info(f"Using cached expansion for: '{query}'")
            return self.expansion_cache[cache_key]

        if not self.llm_provider or not self.llm_provider.is_available():
            # Fallback to basic expansion if LLM unavailable
            return self._expand_query_fallback(query)

        try:
            # OPTIMIZED: Much shorter prompt for faster response
            prompt = f"""Expand this search query with synonyms and related terms (keywords only):

Query: "{query}"

Examples:
"resume" → resume CV curriculum vitae employment work experience education
"homework" → homework assignment problem set exercise
"travel docs" → travel passport visa immigration i94

Output (keywords):"""

            # Get AI expansion with REDUCED tokens for speed
            expanded_terms = self.llm_provider.generate(prompt, max_tokens=50)
            expanded_terms = expanded_terms.strip()

            # Clean up the response
            expanded_terms = expanded_terms.replace('\n', ' ').replace('  ', ' ')

            # Combine original query with AI-generated terms
            final_query = f"{query} {expanded_terms}"

            # Cache the result for future use
            self.expansion_cache[cache_key] = final_query

            logger.info(f"AI-expanded: '{query}' -> '{expanded_terms[:50]}...'")
            return final_query

        except Exception as e:
            logger.warning(f"AI expansion failed: {e}. Using fallback.")
            return self._expand_query_fallback(query)

    def _expand_query_fallback(self, query: str) -> str:
        """
        Fast fallback query expansion - instant results
        Uses smart keyword matching for common document types
        """
        query_lower = query.lower()

        # Comprehensive but instant expansions for common queries
        fast_expansions = {
            # Career documents
            'resume': 'resume CV curriculum vitae professional profile employment work experience education skills',
            'cv': 'CV resume curriculum vitae professional profile employment work experience education',

            # Academic
            'homework': 'homework assignment problem set exercise math calculus',
            'assignment': 'assignment homework problem set exercise',
            'math': 'math mathematics calculus algebra geometry homework',
            'calculus': 'calculus math mathematics derivative integral homework',

            # Travel/Immigration
            'travel': 'travel passport visa immigration i94 i-94',
            'passport': 'passport travel visa immigration',
            'visa': 'visa passport travel immigration',
            'i94': 'i94 i-94 immigration travel arrival departure',

            # Financial
            'tax': 'tax w-2 w2 form income federal IRS',
            'budget': 'budget financial expenses revenue costs',
            'invoice': 'invoice bill receipt payment',

            # Academic records
            'transcript': 'transcript grades academic course gpa',
            'grade': 'grade transcript academic course gpa',
        }

        # Apply expansion for matching keywords
        for key, expansion in fast_expansions.items():
            if key in query_lower:
                return f"{query} {expansion}"

        # No expansion needed
        return query

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
