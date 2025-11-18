"""
RAG (Retrieval-Augmented Generation) Engine
Combines vector search with LLM reasoning for intelligent file discovery
"""

from typing import List, Dict, Optional
import logging
from datetime import datetime

from search_engine import SearchEngine
from llm_provider import LLMFactory, LLMProvider
from document_parser import DocumentParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RAGEngine:
    """
    Conversational RAG system for intelligent file search
    Uses vector search + LLM to understand user intent and reason about files
    """

    def __init__(
        self,
        search_engine: SearchEngine,
        llm_provider: Optional[LLMProvider] = None,
        provider_type: str = "ollama"
    ):
        """
        Initialize RAG engine

        Args:
            search_engine: Vector search engine
            llm_provider: Optional pre-configured LLM provider
            provider_type: Type of LLM provider to use if llm_provider not provided
        """
        self.search_engine = search_engine
        self.conversation_history = []
        self.document_parser = DocumentParser()

        # Initialize LLM provider
        if llm_provider:
            self.llm = llm_provider
        else:
            try:
                self.llm = LLMFactory.create_best_available(
                    ollama={"model": "llama3.1:8b"}
                )
                logger.info(f"Initialized LLM provider: {type(self.llm).__name__}")
            except Exception as e:
                logger.error(f"Failed to initialize LLM: {e}")
                self.llm = None

    def chat(self, user_message: str, top_k: int = 5) -> Dict:
        """
        Process user message and return intelligent response with file results

        Args:
            user_message: User's natural language query
            top_k: Number of files to retrieve from vector search

        Returns:
            Dict with response, files, and reasoning
        """
        if not self.llm:
            raise Exception("LLM not available. Please start Ollama or configure API key.")

        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.now().isoformat()
        })

        try:
            # Step 1: Determine user intent - is this a search query or a chat question?
            intent = self._classify_intent(user_message)
            logger.info(f"User intent: {intent}")

            if intent == "general_chat":
                # Handle general questions, summarization, etc.
                result = self._handle_general_chat(user_message)
            else:
                # Handle file search
                result = self._handle_file_search(user_message, top_k)

            # Add assistant response to history
            self.conversation_history.append({
                "role": "assistant",
                "content": result["response"],
                "files": [f["file_name"] for f in result.get("files", [])],
                "timestamp": datetime.now().isoformat()
            })

            return result

        except Exception as e:
            logger.error(f"Error in RAG chat: {e}")
            error_response = f"I encountered an error: {str(e)}"
            self.conversation_history.append({
                "role": "assistant",
                "content": error_response,
                "timestamp": datetime.now().isoformat()
            })
            return {
                "response": error_response,
                "files": [],
                "reasoning": str(e)
            }

    def _classify_intent(self, user_message: str) -> str:
        """
        Smart classification using vector search confidence
        No hardcoded lists - let the AI decide based on semantic similarity

        Args:
            user_message: User's message

        Returns:
            "file_search" or "general_chat"
        """
        # Always attempt file search - let the results determine validity
        # This removes the need for hardcoded greetings/phrases
        return "file_search"

    def _detect_format_preference(self, user_message: str) -> tuple:
        """
        Detect if user has a specific file format preference in their query.
        Returns (preferred_formats, should_filter)

        Args:
            user_message: User's query

        Returns:
            Tuple of (list of preferred file extensions like ['.pdf', '.xlsx'], bool should_strictly_filter)
        """
        message_lower = user_message.lower()

        # Format keyword mappings
        format_map = {
            # PDF
            ('pdf', 'portable document'): ['.pdf'],
            
            # Word / Doc
            ('word', 'doc', '.docx', 'document'): ['.docx', '.doc'],
            
            # Excel / Spreadsheet
            ('excel', 'xlsx', 'xls', 'spreadsheet', 'sheet', 'csv'): ['.xlsx', '.xls', '.csv'],
            
            # Text files
            ('text', '.txt', 'text file', 'notepad'): ['.txt'],
            
            # Code
            ('python', '.py', 'code', 'script'): ['.py'],
            ('javascript', '.js', 'typescript', '.ts'): ['.js', '.ts'],
            ('java', '.java'): ['.java'],
            ('code files', 'source'): ['.py', '.js', '.ts', '.java', '.cpp', '.c'],
            
            # Markdown / Notes
            ('markdown', '.md', 'notes'): ['.md', '.txt'],
            
            # Images
            ('image', 'photo', 'picture', 'jpg', 'png', 'screenshot'): ['.jpg', '.jpeg', '.png', '.gif', '.bmp'],
            
            # Presentations
            ('powerpoint', 'ppt', 'presentation', 'slides'): ['.pptx', '.ppt'],
            
            # Archives
            ('zip', 'archive', 'compressed'): ['.zip', '.rar', '.7z'],
            
            # JSON / Config
            ('json', '.json', 'config'): ['.json', '.yaml', '.yml', '.ini', '.conf'],
        }

        detected_formats = []
        for keywords, formats in format_map.items():
            for keyword in keywords:
                if keyword in message_lower:
                    detected_formats.extend(formats)
                    logger.info(f"Detected format preference from '{keyword}': {formats}")
                    break

        # Remove duplicates
        detected_formats = list(set(detected_formats))

        # If user explicitly mentioned a format, strictly filter to that format
        should_strictly_filter = len(detected_formats) > 0

        return detected_formats, should_strictly_filter

    def _has_recent_file_results(self) -> bool:
        """Check if recent conversation has file results"""
        for msg in reversed(self.conversation_history[-3:]):
            if msg.get("role") == "assistant" and msg.get("files"):
                return True
        return False

    def _handle_general_chat(self, user_message: str) -> Dict:
        """
        Instant rejection - no LLM calls, just tell user to search for files

        Args:
            user_message: User's message

        Returns:
            Dict with rejection response
        """
        message_lower = user_message.lower().strip()

        # Help message
        if message_lower in ["help", "?", "how", "what can you do", "what can you do?"]:
            return {
                "response": "I'm a file search assistant. Try:\n• \"find my resume\"\n• \"budget reports\"\n• \"meeting notes team C\"\n• \"photos from trip\"",
                "files": [],
                "reasoning": "Help requested"
            }

        # Generic rejection for non-file queries
        return {
            "response": "Please search for a file.",
            "files": [],
            "reasoning": "Not a file search query"
        }

    def _extract_files_from_context(self, user_message: str) -> List[str]:
        """
        Check if user is referencing files from previous conversation

        Args:
            user_message: User's message

        Returns:
            List of file paths to analyze
        """
        files = []

        # Keywords that suggest user wants to analyze previous results
        analysis_keywords = ["summarize", "summary", "read", "what's in", "what is in", "analyze",
                            "tell me about", "explain", "content", "details"]

        message_lower = user_message.lower()
        is_analysis_request = any(keyword in message_lower for keyword in analysis_keywords)

        if not is_analysis_request:
            return files

        # Look for files mentioned in last few assistant responses
        for msg in reversed(self.conversation_history[-5:]):
            if msg["role"] == "assistant" and "files" in msg and msg["files"]:
                # If message says "first", "first one", "that", "these", etc.
                if any(ref in message_lower for ref in ["first", "that", "these", "those", "them", "it"]):
                    # Get the files from the most recent search
                    return msg["files"][:3]  # Limit to first 3 files

        return files

    def _get_file_contents(self, file_names: List[str]) -> str:
        """
        Read and extract content from files

        Args:
            file_names: List of file names to read

        Returns:
            Formatted string with file contents
        """
        contents = []

        for file_name in file_names:
            try:
                # Search for the file in the index to get its full path
                file_info = None
                for doc in self.search_engine.documents:
                    if doc["file_name"] == file_name:
                        file_info = doc
                        break

                if not file_info:
                    contents.append(f"\n--- {file_name} ---\nFile not found in index.")
                    continue

                # Read file content
                from pathlib import Path
                file_path = Path(file_info["file_path"])

                if not file_path.exists():
                    contents.append(f"\n--- {file_name} ---\nFile no longer exists at path.")
                    continue

                # Parse the file
                content = self.document_parser.parse(file_path)

                if content:
                    # Truncate if too long (keep first 3000 chars)
                    truncated = content[:3000]
                    if len(content) > 3000:
                        truncated += "\n\n[... content truncated ...]"

                    contents.append(f"\n--- {file_name} ---\n{truncated}")
                else:
                    contents.append(f"\n--- {file_name} ---\nCould not extract text content.")

            except Exception as e:
                logger.error(f"Error reading file {file_name}: {e}")
                contents.append(f"\n--- {file_name} ---\nError reading file: {str(e)}")

        if contents:
            return "\n\nFILE CONTENTS:\n" + "\n".join(contents)

        return ""

    def _handle_file_search(self, user_message: str, top_k: int = 5) -> Dict:
        """
        Handle file search queries - Use LLM reasoning to understand intent and rank results
        Now also considers file format preferences from user query.

        Args:
            user_message: User's natural language search query
            top_k: Number of files to return

        Returns:
            Dict with response, files, and reasoning
        """
        logger.info(f"User query: '{user_message}'")

        # Detect if user has a file format preference (e.g., "PDF", "Excel", "Word doc")
        preferred_formats, should_strictly_filter = self._detect_format_preference(user_message)
        if preferred_formats:
            logger.info(f"User format preference detected: {preferred_formats} (strict filter: {should_strictly_filter})")

        # Step 1: Generate multiple query phrasings using LLM
        # This captures different interpretations of what the user really wants
        try:
            logger.info("Generating alternative query phrasings...")
            phrasings = self._generate_query_phrasings(user_message)
            logger.info(f"Generated {len(phrasings)} phrasings for multi-perspective search")
        except Exception as e:
            logger.warning(f"Failed to generate phrasings, using direct search: {e}")
            # Fallback to single enhanced query
            enhanced_query = self._add_synonym_fallback(user_message, user_message)
            phrasings = [enhanced_query]

        # Step 2: Multi-phrasing search - search with all phrasings to get broader candidate set
        logger.info("Performing multi-phrasing vector search...")
        try:
            candidates = self._multi_phrasing_search(phrasings)
            logger.info(f"Multi-phrasing search found {len(candidates)} unique candidates")
        except Exception as e:
            logger.warning(f"Multi-phrasing search failed, falling back to single search: {e}")
            # Fallback to simple search
            enhanced_query = self._add_synonym_fallback(user_message, user_message)
            candidates = self.search_engine.search(enhanced_query, top_k=min(20, len(self.search_engine.documents or [])))

        # Step 2.5: Apply format filtering if user specified a format
        if preferred_formats and candidates:
            logger.info(f"Applying format filter for: {preferred_formats}")
            
            # Split candidates into format-matching and non-matching
            format_matches = [c for c in candidates if c.get('file_type', '').lower() in preferred_formats]
            non_matches = [c for c in candidates if c.get('file_type', '').lower() not in preferred_formats]
            
            if format_matches:
                logger.info(f"Found {len(format_matches)} files in preferred format(s)")
                candidates = format_matches + non_matches  # Reorder: preferred formats first
            elif should_strictly_filter:
                # User explicitly asked for a format, but no matches found
                logger.warning(f"No files found in preferred format {preferred_formats}, relaxing filter")
                # Continue with all candidates but boost format-matching ones

        # Step 3: Use LLM to reason about which files actually match user intent
        if candidates:
            logger.info(f"Using LLM to reason about top candidates (with format awareness)...")
            try:
                # Use chain-of-thought reasoning to pick the best matches
                result = self._reason_about_files_chain_of_thought(
                    user_message, candidates, top_k,
                    preferred_formats=preferred_formats
                )
                return result
            except Exception as e:
                logger.error(f"LLM reasoning failed: {e}")
                # Fallback to confidence threshold
                logger.info("Falling back to confidence-based filtering...")

        # Fallback: confidence threshold on vector scores
        CONFIDENCE_THRESHOLD = 0.15  # Lower threshold to catch more relevant matches
        if candidates and candidates[0].get('score', 0) >= CONFIDENCE_THRESHOLD:
            selected = candidates[:top_k]
            if len(selected) == 1:
                response = f"I found exactly what you're looking for!\n\n📄 {selected[0]['file_name']}"
            else:
                response = f"I found {len(selected)} files that match your request:\n\n"
                for i, f in enumerate(selected, 1):
                    response += f"{i}. 📄 {f['file_name']}\n"
            return {
                "response": response,
                "files": selected,
                "reasoning": "Vector similarity search"
            }
        else:
            # Even lower threshold as absolute fallback - if anything was found at all, show it
            if candidates:
                logger.warning(f"Low confidence ({candidates[0].get('score', 0):.3f}), showing best available matches anyway")
                selected = candidates[:min(top_k, 3)]  # Show at least the best matches
                response = f"I found {len(selected)} file(s) that might match your request (lower confidence):\n\n"
                for i, f in enumerate(selected, 1):
                    response += f"{i}. 📄 {f['file_name']}\n"
                return {
                    "response": response,
                    "files": selected,
                    "reasoning": "Low confidence matches - try being more specific"
                }
            
            logger.info(f"No matches found at all")
            return {
                "response": "I couldn't find files matching your request. Try being more specific or check that files are indexed.",
                "files": [],
                "reasoning": "No matches found"
            }

    def _generate_query_phrasings(self, user_message: str) -> List[str]:
        """
        Generate multiple different phrasings of the user's query

        Args:
            user_message: Original user query

        Returns:
            List of 4 different phrasings
        """
        prompt = f"""You are a query expansion expert. Generate 4 DIFFERENT phrasings of this search query.

Original query: "{user_message}"

IMPORTANT:
1. Each phrasing should use DIFFERENT synonyms and keywords
2. Capture different aspects/interpretations of what the user wants
3. Remove filler words (my, the, a, etc.)
4. Return space-separated keywords for each phrasing

Examples:

Input: "find my resume"
Phrasing 1: "resume professional experience"
Phrasing 2: "CV curriculum vitae"
Phrasing 3: "employment history work background"
Phrasing 4: "career profile job application document"

Input: "show travel documents"
Phrasing 1: "travel documents passport"
Phrasing 2: "visa immigration papers"
Phrasing 3: "i94 i-94 arrival departure"
Phrasing 4: "boarding pass flight ticket travel"

Now generate 4 phrasings for: "{user_message}"

Respond EXACTLY in this format:
PHRASING_1: [keywords]
PHRASING_2: [keywords]
PHRASING_3: [keywords]
PHRASING_4: [keywords]"""

        try:
            response = self.llm.generate(prompt, max_tokens=300)
            phrasings = []

            # Parse the response
            for line in response.strip().split('\n'):
                if line.startswith('PHRASING_'):
                    # Extract the keywords after the colon
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        phrasing = parts[1].strip()
                        # Add synonym fallback to each phrasing
                        enhanced = self._add_synonym_fallback(phrasing, user_message)
                        phrasings.append(enhanced)

            # Fallback if parsing failed
            if len(phrasings) < 4:
                logger.warning(f"Only got {len(phrasings)} phrasings, using fallback")
                # Use original message + synonyms as fallback
                base = self._extract_keywords(user_message)
                enhanced = self._add_synonym_fallback(base, user_message)
                phrasings = [enhanced] * 4  # Use same phrasing 4 times as fallback

            logger.info(f"Generated phrasings:")
            for i, p in enumerate(phrasings, 1):
                logger.info(f"  Phrasing {i}: {p[:80]}...")

            return phrasings

        except Exception as e:
            logger.error(f"Error generating phrasings: {e}")
            # Fallback to single enhanced query
            base = self._extract_keywords(user_message)
            enhanced = self._add_synonym_fallback(base, user_message)
            return [enhanced] * 4

    def _multi_phrasing_search(self, phrasings: List[str]) -> List[Dict]:
        """
        Search with multiple phrasings and aggregate results with weighted scoring

        Args:
            phrasings: List of different query phrasings

        Returns:
            Aggregated and ranked list of candidates
        """
        # Track file scores across all phrasings
        # file_path -> {score: float, positions: [int], appearances: int, file_data: Dict}
        file_scores = {}

        # Search with each phrasing
        for phrasing_idx, phrasing in enumerate(phrasings):
            logger.info(f"Searching with phrasing {phrasing_idx + 1}/{len(phrasings)}")
            results = self.search_engine.search(phrasing, top_k=30)

            # Process results from this phrasing
            for position, result in enumerate(results):
                file_path = result['file_path']

                # Initialize if first time seeing this file
                if file_path not in file_scores:
                    file_scores[file_path] = {
                        'positions': [],
                        'appearances': 0,
                        'file_data': result,
                        'raw_scores': []
                    }

                # Record this appearance
                file_scores[file_path]['positions'].append(position)
                file_scores[file_path]['appearances'] += 1
                file_scores[file_path]['raw_scores'].append(result.get('score', 0.0))

        # Calculate weighted scores
        ranked_files = []
        for file_path, data in file_scores.items():
            # Frequency score: how many phrasings found this file
            frequency_score = data['appearances'] / len(phrasings)

            # Position score: average of 1/position for each appearance
            position_scores = [1.0 / (pos + 1) for pos in data['positions']]
            avg_position_score = sum(position_scores) / len(position_scores)

            # Raw similarity score: average similarity from vector search
            avg_similarity = sum(data['raw_scores']) / len(data['raw_scores'])

            # Combined score: weighted combination
            # Frequency is most important (file appearing in multiple phrasings)
            # Then position (higher rank = better)
            # Then raw similarity
            combined_score = (
                frequency_score * 3.0 +  # 3x weight for appearing in multiple phrasings
                avg_position_score * 2.0 +  # 2x weight for high positions
                avg_similarity * 1.0  # 1x weight for similarity
            )

            file_info = data['file_data'].copy()
            file_info['combined_score'] = combined_score
            file_info['frequency_score'] = frequency_score
            file_info['position_score'] = avg_position_score
            file_info['appearances'] = data['appearances']
            file_info['best_position'] = min(data['positions'])

            ranked_files.append(file_info)

        # Sort by combined score
        ranked_files.sort(key=lambda x: x['combined_score'], reverse=True)

        # Log top results
        logger.info(f"Multi-phrasing ranking:")
        for i, f in enumerate(ranked_files[:5]):
            logger.info(
                f"  {i+1}. {f['file_name']} - "
                f"Score: {f['combined_score']:.3f} "
                f"(appears in {f['appearances']}/{len(phrasings)} phrasings, "
                f"best position: {f['best_position']+1})"
            )

        return ranked_files

    def _add_synonym_fallback(self, search_query: str, original_message: str) -> str:
        """
        Add semantic synonyms using LLM when possible, with fallback to hardcoded mappings.
        Ensures critical synonym mappings like "resume" -> "CV" are always available.

        Args:
            search_query: Query to enhance
            original_message: Original user message

        Returns:
            Enhanced query with synonyms
        """
        # Hardcoded synonyms for critical common terms (fallback)
        # Use broader keyword matching to catch variations
        synonym_map = {
            # Employment/Career documents
            "resume": "CV curriculum vitae professional experience work history employment history career profile job application employment record",
            "cv": "resume curriculum vitae professional experience work history employment history career profile job application employment record",
            "job": "resume CV employment career application offer letter position role hire hiring work",
            "job application": "resume CV cover letter employment application career position offer",
            "job document": "resume CV employment career application offer cover letter portfolio work history",
            "job offer": "employment offer acceptance letter position role hire contract negotiation",
            "cover letter": "job application resume CV application letter employment",
            "employment": "job resume CV work career employment history position",
            
            # Travel documents
            "travel": "passport visa i94 i-94 immigration arrival departure boarding pass flight ticket travel authorization",
            "passport": "travel visa i94 immigration documents travel",
            "visa": "travel passport i94 immigration documents",
            "i94": "travel passport visa immigration arrival departure i-94 form travel documents",
            
            # Financial/Budget documents
            "budget": "financial report expenses revenue costs spending finance accounting spreadsheet",
            "financial": "budget expenses revenue costs spending accounting statements report",
            "tax": "taxes income revenue deduction IRS W2 1040 financial return filing",
            "invoice": "bill receipt payment charge financial statement transaction",
            
            # Legal/Contract documents
            "contract": "agreement legal document terms conditions signature",
            
            # Meeting/Discussion documents
            "meeting": "notes minutes agenda discussion call conference recording transcript",
            "notes": "meeting minutes documentation memo records discussion",
            
            # Reports/Documentation
            "report": "analysis summary findings conclusion document paper",
            "document": "file paper report memo record letter",
        }

        # Check if any synonym keys appear in original message (case insensitive)
        original_lower = original_message.lower()
        added_terms = set()

        # First pass: exact phrase matching
        for key, synonyms in synonym_map.items():
            if key in original_lower:
                # Add synonyms if not already in query
                for term in synonyms.split():
                    if term.lower() not in search_query.lower():
                        added_terms.add(term)
                logger.info(f"Synonym match found for '{key}'")

        enhanced = search_query
        if added_terms:
            enhanced = search_query + " " + " ".join(added_terms)
            logger.info(f"Added {len(added_terms)} synonym terms: {', '.join(list(added_terms)[:10])}...")

        # Try LLM expansion for even better recall
        if self.llm:
            try:
                expansion_prompt = f"""Generate 8-15 additional keywords and synonyms for this search query that would help find relevant files:

Query: "{original_message}"
Current expanded query: "{enhanced}"

Add terms that:
1. Are semantically related (not just word variants)
2. Represent alternative ways someone might name or refer to similar files
3. Include domain terms, abbreviations, and related concepts
4. Think about different contexts where such files appear

Examples:
- For "job documents": also add: employment, career, CV, resume, application, offer letter, position, hire
- For "meeting notes": also add: minutes, transcript, recording, summary, discussion, agenda
- For "2023 taxes": also add: tax return, 1040, filing, income statement, W2, deduction

Return only the additional keywords, space-separated:"""

                additional = self.llm.generate(expansion_prompt, max_tokens=120).strip()
                if additional:
                    enhanced = enhanced + " " + additional
                    logger.info(f"LLM expanded query with: {additional[:80]}...")
            except Exception as e:
                logger.debug(f"LLM expansion failed (using hardcoded only): {e}")

        return enhanced

    def _extract_keywords(self, user_message: str) -> str:
        """
        Extract and expand keywords semantically using AI

        Args:
            user_message: User's natural language message

        Returns:
            Space-separated keywords and synonyms
        """
        if not self.llm:
            # Fallback: just return original message if no LLM
            return user_message

        prompt = f"""You are a semantic keyword extraction expert. Extract ALL relevant keywords and synonyms that would help find files matching this user's intent.

User's intent: "{user_message}"

Your task:
1. Identify what the user is REALLY looking for (the actual need, not just surface words)
2. List all keywords, synonyms, and related terms that file names or content might use
3. Include domain-specific terms, abbreviations, and alternative phrasings
4. Think about different ways files could be named or organized

Return ONLY space-separated keywords and synonyms. Example:
Input: "show me my 2024 tax documents"
Output: "tax 2024 taxes 1040 W2 filing return income IRS deduction document"

Input: "find my job offer letter"
Output: "job offer letter employment offer acceptance hire hiring position role contract"

For: "{user_message}"
Keywords:"""

        try:
            keywords = self.llm.generate(prompt, max_tokens=150).strip()
            logger.info(f"Extracted keywords: {keywords[:100]}...")
            return keywords if keywords else user_message
        except Exception as e:
            logger.warning(f"Keyword extraction failed, using original: {e}")
            return user_message

    def _reason_about_files_chain_of_thought(
        self,
        user_message: str,
        candidates: List[Dict],
        top_k: int,
        preferred_formats: List[str] = None
    ) -> Dict:
        """
        Use LLM with deep semantic reasoning to understand user intent and pick best files.
        The LLM reads each file preview and reasons about whether it matches the user's REAL need,
        considering file format preferences if specified.

        Args:
            user_message: User's original request
            candidates: List of candidate files from vector search
            top_k: Number of files to return
            preferred_formats: List of preferred file extensions (e.g., ['.pdf', '.xlsx'])

        Returns:
            Dict with response, selected files, and reasoning
        """
        if not candidates:
            return {
                "response": "I couldn't find any files matching your request.",
                "files": [],
                "reasoning": "No candidates found"
            }

        # Show top 25 candidates to LLM for thorough semantic analysis
        files_info = []
        for i, candidate in enumerate(candidates[:25]):
            file_format = candidate.get('file_type', 'unknown')
            # Mark preferred format files
            format_marker = " ⭐" if preferred_formats and file_format in preferred_formats else ""
            files_info.append(
                f"{i+1}. {candidate['file_name']} ({file_format}){format_marker}\n"
                f"   Preview: {candidate.get('preview', 'No preview available')[:400]}\n"
            )

        files_text = "\n".join(files_info)
        
        # Add format preference context to prompt
        format_context = ""
        if preferred_formats:
            format_context = f"\n\nUSER FORMAT PREFERENCE: {', '.join(preferred_formats)}\nPrioritize files with these formats, but also consider other formats if they're better matches."

        # Deep semantic reasoning prompt - forces LLM to UNDERSTAND not just match keywords
        prompt = f"""You are an expert file search AI with deep understanding of document types and user intent.

User's request: "{user_message}"{format_context}

CRITICAL REMINDER - UNDERSTAND USER INTENT:
- "find job documents" = looking for CV, resume, employment records, job offers, cover letters
- "find travel documents" = looking for passport, visa, i94, boarding passes, travel itineraries
- "find financial documents" = looking for taxes, budgets, invoices, bank statements
- Think SEMANTICALLY about what files match the user's REAL NEED, not just keyword overlap.

Now analyze EVERY candidate file carefully:

Available files to choose from:
{files_text}

For each file, ask yourself:
1. What type of document is this? (infer from name + preview)
2. Does it match what the user is looking for? YES/NO/MAYBE
3. How confident are you? HIGH/MEDIUM/LOW
4. Why? (be specific - reference name and preview content)
5. If user wants "job documents" - does this contain work/career info? (CV, resume, offer, etc.)

Then select the top {min(top_k, 5)} files that best match the user's ACTUAL need.
BE GENEROUS in matching - if it's plausibly related, give it credit.

OUTPUT FORMAT (EXACTLY):
FILE_ANALYSIS:
1. [filename] - [Document type]. Match: [YES/NO/MAYBE]. Confidence: [HIGH/MEDIUM/LOW]. Reason: [reason]
2. [filename] - [Document type]. Match: [YES/NO/MAYBE]. Confidence: [HIGH/MEDIUM/LOW]. Reason: [reason]
... (analyze ALL {min(len(candidates), 25)} files)

SELECTED_FILES: [comma-separated numbers, e.g., "1, 3, 5"]
CONFIDENCE: [HIGH/MEDIUM/LOW]
EXPLANATION: [1-2 sentences]

IMPORTANT:
- Analyze EVERY file - don't skip
- Be generous about what counts as a match
- Think about file PURPOSE and CONTENT first
- Consider that people name files inconsistently
- If user says "job documents", CV/resume/employment files are ALWAYS matches

Begin your analysis:"""

        try:
            llm_response = self.llm.generate(prompt, max_tokens=4000)

            # Log the full reasoning for debugging
            logger.info("=" * 100)
            logger.info("SEMANTIC ANALYSIS REASONING:")
            logger.info("=" * 100)
            logger.info(llm_response[:2000])  # Log first 2000 chars
            logger.info("=" * 100)

            # Parse LLM response
            selected_files = []
            explanation = ""
            confidence = "MEDIUM"

            lines = llm_response.strip().split('\n')
            for line in lines:
                if line.startswith("SELECTED_FILES:"):
                    # Extract file numbers
                    numbers_str = line.replace("SELECTED_FILES:", "").strip()
                    numbers_str = numbers_str.replace(',', ' ')
                    numbers = []
                    for part in numbers_str.split():
                        if part.strip().isdigit():
                            numbers.append(int(part.strip()))

                    # Convert to 0-indexed and get files
                    for num in numbers[:top_k]:
                        if 0 < num <= len(candidates):
                            selected_files.append(candidates[num - 1])

                elif line.startswith("CONFIDENCE:"):
                    confidence = line.replace("CONFIDENCE:", "").strip()

                elif line.startswith("EXPLANATION:"):
                    explanation = line.replace("EXPLANATION:", "").strip()
                elif explanation and not line.startswith("FILE_ANALYSIS"):
                    explanation += " " + line.strip()

            # Fallback if parsing failed
            if not selected_files:
                logger.warning("Failed to parse LLM selection, using top candidates")
                selected_files = candidates[:top_k]
                explanation = "Selected top matches from semantic search."

            # Create natural language response
            if selected_files:
                if len(selected_files) == 1:
                    response = f"I found exactly what you're looking for!\n\n📄 {selected_files[0]['file_name']}"
                else:
                    response = f"I found {len(selected_files)} file(s) matching your request:\n\n"
                    for i, f in enumerate(selected_files, 1):
                        response += f"{i}. 📄 {f['file_name']}\n"

                response += f"\n{explanation}"
            else:
                response = "I couldn't find files that clearly match your request. Try rephrasing or check that files are indexed."

            return {
                "response": response,
                "files": selected_files,
                "reasoning": f"{explanation} (Confidence: {confidence})"
            }

        except Exception as e:
            logger.error(f"Error in semantic reasoning: {e}")
            import traceback
            traceback.print_exc()
            # Fallback to top candidates
            return {
                "response": f"I found {len(candidates[:top_k])} potentially relevant files based on semantic similarity.",
                "files": candidates[:top_k],
                "reasoning": f"Semantic reasoning unavailable: {str(e)}"
            }

    def _reason_about_files_verbose(
        self,
        user_message: str,
        candidates: List[Dict],
        top_k: int
    ) -> Dict:
        """
        Use LLM with VERBOSE chain-of-thought reasoning to select best files
        The LLM talks through its reasoning for EVERY file

        Args:
            user_message: User's original request
            candidates: List of candidate files from multi-phrasing search
            top_k: Number of files to return

        Returns:
            Dict with response, selected files, and reasoning
        """
        # Show top 15 candidates to LLM
        files_info = []
        for i, candidate in enumerate(candidates[:15]):
            files_info.append(
                f"{i+1}. {candidate['file_name']} ({candidate['file_type']})\n"
                f"   Path: {candidate.get('file_path', 'N/A')}\n"
                f"   Preview: {candidate.get('preview', 'No preview')[:200]}\n"
                f"   Multi-phrasing score: {candidate.get('combined_score', 0):.3f}\n"
                f"   Appeared in {candidate.get('appearances', 0)}/4 phrasings\n"
            )

        files_text = "\n".join(files_info)

        # Chain-of-thought prompt - forces LLM to think out loud
        prompt = f"""You are an expert file search assistant. Analyze EVERY file and explain your reasoning.

User's request: "{user_message}"

Available files:
{files_text}

INSTRUCTIONS:
1. Go through EACH file one by one
2. For EACH file, explicitly state:
   - What type of document it appears to be
   - Whether it matches the user's request (yes/no/maybe)
   - Your reasoning (why or why not)

3. After analyzing all files, select the top {top_k} that best match

Use this EXACT format:

ANALYSIS:
File 1: [filename] - [Document type]. [Match: yes/no/maybe]. [Reasoning]
File 2: [filename] - [Document type]. [Match: yes/no/maybe]. [Reasoning]
... (continue for all files)

SELECTED: [comma-separated numbers of top {top_k} matches, e.g., "1, 3, 5"]

EXPLANATION: [Brief summary of why these files were chosen]

Begin your analysis:"""

        try:
            llm_response = self.llm.generate(prompt, max_tokens=2000)

            # Log the full chain-of-thought reasoning
            logger.info("=" * 80)
            logger.info("CHAIN-OF-THOUGHT REASONING:")
            logger.info(llm_response)
            logger.info("=" * 80)

            # Parse LLM response
            selected_files = []
            explanation = ""

            lines = llm_response.strip().split('\n')
            for line in lines:
                if line.startswith("SELECTED:"):
                    # Extract file numbers
                    numbers_str = line.replace("SELECTED:", "").strip()
                    numbers = [int(n.strip()) for n in numbers_str.split(',') if n.strip().isdigit()]
                    # Convert to 0-indexed and get files
                    for num in numbers[:top_k]:
                        if 0 < num <= len(candidates):
                            selected_files.append(candidates[num - 1])

                elif line.startswith("EXPLANATION:"):
                    explanation = line.replace("EXPLANATION:", "").strip()
                elif explanation and not line.startswith("ANALYSIS"):  # Continue explanation
                    explanation += " " + line.strip()

            # Fallback if parsing failed
            if not selected_files:
                logger.warning("Failed to parse LLM selection, using top candidates")
                selected_files = candidates[:top_k]
                explanation = "Selected top matches based on multi-phrasing scores."

            # Create natural language response
            if selected_files:
                response = f"I found {len(selected_files)} relevant file(s). {explanation}\n\nFiles:\n"
                for i, f in enumerate(selected_files, 1):
                    response += f"{i}. {f['file_name']}\n"
            else:
                response = "I couldn't find any files that closely match your request."

            return {
                "response": response,
                "files": selected_files,
                "reasoning": explanation
            }

        except Exception as e:
            logger.error(f"Error in verbose reasoning: {e}")
            # Fallback to top candidates
            return {
                "response": f"I found {len(candidates[:top_k])} potentially relevant files.",
                "files": candidates[:top_k],
                "reasoning": "LLM reasoning unavailable, showing top multi-phrasing matches"
            }

    def _reason_about_files(
        self,
        user_message: str,
        candidates: List[Dict],
        top_k: int
    ) -> Dict:
        """
        Use LLM to reason about which candidate files best match user's intent

        Args:
            user_message: User's original request
            candidates: List of candidate files from vector search
            top_k: Number of files to return

        Returns:
            Dict with response, selected files, and reasoning
        """
        # Prepare file information for LLM - show MORE candidates (top 20)
        files_info = []
        for i, candidate in enumerate(candidates[:20]):  # Show top 20 to LLM
            files_info.append(
                f"{i+1}. {candidate['file_name']} ({candidate['file_type']})\n"
                f"   Preview: {candidate.get('preview', 'No preview available')[:250]}\n"
            )

        files_text = "\n".join(files_info)

        # Create prompt for LLM reasoning
        prompt = f"""You are an expert file search assistant. Your job is to understand what the user REALLY wants and find it.

User's request: "{user_message}"

Available files to choose from:
{files_text}

CRITICAL INSTRUCTIONS:
1. Understand the USER'S INTENT, not just keywords:
   - "resume" = ANY document showing work experience, education, skills (could be named "CV", "curriculum vitae", "professional profile", etc.)
   - "travel documents" = passports, visas, i94, tickets, boarding passes
   - "budget" = financial reports, expenses, revenue sheets

2. Analyze BOTH filename AND content preview:
   - A file named "Professional_CV.pdf" IS a resume even if it doesn't say "resume"
   - A file with "Education: MIT, Work Experience: Google" IS a resume
   - Look for PURPOSE, not exact word matches

3. Common synonyms to remember:
   - Resume = CV = Curriculum Vitae = Professional Profile = Employment History
   - i94 = I-94 = arrival/departure record = immigration form
   - Budget = Financial Report = Expenses = Revenue = Costs

4. Select the top {top_k} files that match the USER'S ACTUAL NEED.

Respond EXACTLY in this format:
SELECTED: [comma-separated numbers only, e.g., "1, 3, 5"]
EXPLANATION: [Brief reason why these files match]

Response:"""

        try:
            llm_response = self.llm.generate(prompt, max_tokens=500)

            # Parse LLM response
            selected_files = []
            explanation = ""

            lines = llm_response.strip().split('\n')
            for line in lines:
                if line.startswith("SELECTED:"):
                    # Extract file numbers
                    numbers_str = line.replace("SELECTED:", "").strip()
                    numbers = [int(n.strip()) for n in numbers_str.split(',') if n.strip().isdigit()]
                    # Convert to 0-indexed and get files
                    for num in numbers[:top_k]:
                        if 0 < num <= len(candidates):
                            selected_files.append(candidates[num - 1])

                elif line.startswith("EXPLANATION:"):
                    explanation = line.replace("EXPLANATION:", "").strip()
                elif explanation:  # Continue explanation on next lines
                    explanation += " " + line.strip()

            # Fallback if parsing failed
            if not selected_files:
                selected_files = candidates[:top_k]
                explanation = "Here are the files I found based on similarity."

            # Create natural language response
            if selected_files:
                file_names = [f["file_name"] for f in selected_files]
                response = f"I found {len(selected_files)} relevant file(s). {explanation}\n\nFiles:\n"
                for i, f in enumerate(selected_files, 1):
                    response += f"{i}. {f['file_name']}\n"
            else:
                response = "I couldn't find any files that closely match your request."

            return {
                "response": response,
                "files": selected_files,
                "reasoning": explanation
            }

        except Exception as e:
            logger.error(f"Error reasoning about files: {e}")
            # Fallback to top candidates
            return {
                "response": f"I found {len(candidates[:top_k])} potentially relevant files.",
                "files": candidates[:top_k],
                "reasoning": "LLM reasoning unavailable, showing top matches"
            }

    def get_conversation_history(self) -> List[Dict]:
        """Get conversation history"""
        return self.conversation_history

    def clear_conversation(self):
        """Clear conversation history"""
        self.conversation_history = []
        logger.info("Conversation history cleared")

    def is_available(self) -> bool:
        """Check if RAG engine is ready"""
        # Only check if LLM is available
        # Search engine doesn't need to be ready yet (files can be indexed later)
        return (
            self.llm is not None
            and self.llm.is_available()
        )
