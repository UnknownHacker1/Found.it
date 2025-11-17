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
        Handle file search queries - FAST semantic search with confidence filtering

        Args:
            user_message: User's natural language search query
            top_k: Number of files to return

        Returns:
            Dict with response, files, and reasoning
        """
        # Use the full natural language query for semantic search
        search_query = user_message

        # Add synonym expansion for better recall on common terms
        enhanced_query = self._add_synonym_fallback(search_query, user_message)
        logger.info(f"Search query: {enhanced_query}")

        # Vector search handles natural language understanding
        candidates = self.search_engine.search(enhanced_query, top_k=top_k)
        logger.info(f"Vector search found {len(candidates)} candidates")

        # CONFIDENCE THRESHOLD: Filter out low-confidence results
        # Greetings like "hey how are u" will have very low similarity to any file
        # Typical similarity scores:
        # - Good match: 0.3-1.0
        # - Random text/greetings: 0.0-0.2
        CONFIDENCE_THRESHOLD = 0.25

        if candidates and candidates[0].get('score', 0) >= CONFIDENCE_THRESHOLD:
            # High confidence - these are real file matches
            if len(candidates) == 1:
                response = f"I found exactly what you're looking for!\n\n📄 {candidates[0]['file_name']}"
            else:
                response = f"I found {len(candidates)} files that match your request:\n\n"
                for i, f in enumerate(candidates, 1):
                    response += f"{i}. 📄 {f['file_name']}\n"

            return {
                "response": response,
                "files": candidates,
                "reasoning": "Semantic vector search"
            }
        else:
            # Low confidence or no results - likely not a file search query
            logger.info(f"Low confidence (top score: {candidates[0].get('score', 0) if candidates else 0:.3f}), treating as non-file query")
            return {
                "response": "Please search for a file.",
                "files": [],
                "reasoning": "Query has low semantic similarity to indexed files"
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
        Add hardcoded synonyms for common terms that might not be expanded by LLM
        This ensures critical synonym mappings like "resume" -> "CV" always work

        Args:
            search_query: Query expanded by LLM
            original_message: Original user message

        Returns:
            Enhanced query with guaranteed synonyms
        """
        # Common synonym mappings for better semantic search
        synonym_map = {
            "resume": "CV curriculum vitae professional experience work history employment history career profile job application",
            "cv": "resume curriculum vitae professional experience work history employment history career profile job application",
            "job application": "resume CV cover letter employment application career",
            "cover letter": "job application resume CV application letter",
            "travel": "passport visa i94 i-94 immigration arrival departure boarding pass flight ticket",
            "passport": "travel visa i94 immigration",
            "visa": "travel passport i94 immigration",
            "i94": "travel passport visa immigration arrival departure i-94",
            "budget": "financial report expenses revenue costs spending finance accounting",
            "financial": "budget expenses revenue costs spending accounting",
            "tax": "taxes income revenue deduction IRS W2 1040 financial",
            "invoice": "bill receipt payment charge financial",
            "contract": "agreement legal document terms conditions",
            "meeting": "notes minutes agenda discussion call conference",
            "notes": "meeting minutes documentation memo",
        }

        # Check if any synonym keys appear in original message (case insensitive)
        original_lower = original_message.lower()
        added_terms = set()

        for key, synonyms in synonym_map.items():
            if key in original_lower:
                # Add synonyms if not already in query
                for term in synonyms.split():
                    if term.lower() not in search_query.lower():
                        added_terms.add(term)

        if added_terms:
            enhanced_query = search_query + " " + " ".join(added_terms)
            logger.info(f"Added synonym fallback terms: {added_terms}")
            return enhanced_query

        return search_query

    def _extract_keywords(self, user_message: str) -> str:
        """
        Extract keywords from user's search query using AI

        Args:
            user_message: User's natural language message

        Returns:
            Space-separated keywords
        """
        prompt = f"""You are a keyword extraction expert. Extract the ESSENTIAL keywords from this search query.

User query: "{user_message}"

Rules:
1. Extract ONLY the most important keywords (nouns, verbs, key concepts)
2. Include ALL synonyms and related terms for those keywords
3. Remove filler words (the, a, an, my, etc.)
4. Return space-separated keywords ONLY

Examples:
Input: "find my resume"
Output: "resume CV curriculum vitae professional experience work history employment"

Input: "show me travel documents"
Output: "travel documents passport visa i94 immigration boarding pass ticket"

Input: "where are my tax files from 2023"
Output: "tax taxes 2023 income revenue IRS W2 1040 financial documents"

Now extract keywords from: "{user_message}"

Keywords (space-separated):"""

        try:
            keywords = self.llm.generate(prompt, max_tokens=200)
            extracted = keywords.strip()
            logger.info(f"Original query: '{user_message}'")
            logger.info(f"Extracted keywords: '{extracted}'")
            return extracted
        except Exception as e:
            logger.error(f"Error extracting keywords: {e}")
            # Fallback to original message
            return user_message

    def _reason_about_files_chain_of_thought(
        self,
        user_message: str,
        candidates: List[Dict],
        top_k: int
    ) -> Dict:
        """
        Use LLM with FULL chain-of-thought reasoning to analyze EVERY file
        The LLM must explicitly explain its reasoning for each candidate

        Args:
            user_message: User's original request
            candidates: List of candidate files from vector search
            top_k: Number of files to return

        Returns:
            Dict with response, selected files, and reasoning
        """
        # Show top 20 candidates to LLM for thorough analysis
        files_info = []
        for i, candidate in enumerate(candidates[:20]):
            files_info.append(
                f"{i+1}. {candidate['file_name']} ({candidate['file_type']})\n"
                f"   Preview: {candidate.get('preview', 'No preview available')[:300]}...\n"
            )

        files_text = "\n".join(files_info)

        # Enhanced chain-of-thought prompt - forces EXPLICIT reasoning for each file
        prompt = f"""You are an expert file search assistant. You must analyze EVERY SINGLE file and explain your reasoning out loud.

User's request: "{user_message}"

Available files to analyze:
{files_text}

CRITICAL INSTRUCTIONS:
1. GO THROUGH EACH FILE ONE BY ONE - DO NOT SKIP ANY
2. For EACH file, you MUST write:
   - What type of document it is (based on name and preview)
   - Does it match what the user wants? (YES/NO/MAYBE)
   - WHY or WHY NOT (be specific about your reasoning)

3. Think about:
   - File NAME (does it suggest the right content?)
   - File TYPE (PDF, DOCX, etc.)
   - PREVIEW content (what does the text tell you?)
   - User's INTENT (what are they really looking for?)

4. Remember common synonyms:
   - Resume = CV = Curriculum Vitae = Professional Experience = Employment History
   - Travel documents = Passport = Visa = i94 = Immigration papers
   - Budget = Financial report = Expenses = Revenue

FORMAT YOUR RESPONSE EXACTLY LIKE THIS:

ANALYSIS:
File 1: [filename]
Type: [what kind of document]
Match: [YES/NO/MAYBE]
Reasoning: [explain why - be specific about what you see in the preview and name]

File 2: [filename]
Type: [what kind of document]
Match: [YES/NO/MAYBE]
Reasoning: [explain why - be specific]

... (CONTINUE FOR ALL {min(20, len(candidates))} FILES - DO NOT SKIP ANY!)

SELECTED: [comma-separated file numbers of top {top_k} matches, e.g., "1, 5, 8"]

SUMMARY: [One sentence explaining why you chose these files]

BEGIN YOUR ANALYSIS NOW:"""

        try:
            llm_response = self.llm.generate(prompt, max_tokens=3000)

            # Log the FULL chain-of-thought reasoning
            logger.info("=" * 100)
            logger.info("FULL CHAIN-OF-THOUGHT REASONING:")
            logger.info("=" * 100)
            logger.info(llm_response)
            logger.info("=" * 100)

            # Parse LLM response
            selected_files = []
            summary = ""

            lines = llm_response.strip().split('\n')
            for line in lines:
                if line.startswith("SELECTED:"):
                    # Extract file numbers
                    numbers_str = line.replace("SELECTED:", "").strip()
                    # Handle various formats: "1, 3, 5" or "1,3,5" or "1 3 5"
                    numbers_str = numbers_str.replace(',', ' ')
                    numbers = []
                    for part in numbers_str.split():
                        if part.strip().isdigit():
                            numbers.append(int(part.strip()))

                    # Convert to 0-indexed and get files
                    for num in numbers[:top_k]:
                        if 0 < num <= len(candidates):
                            selected_files.append(candidates[num - 1])

                elif line.startswith("SUMMARY:"):
                    summary = line.replace("SUMMARY:", "").strip()
                elif summary:  # Continue summary on next lines
                    if not line.startswith("ANALYSIS") and not line.startswith("File "):
                        summary += " " + line.strip()

            # Fallback if parsing failed
            if not selected_files:
                logger.warning("Failed to parse LLM selection, using top candidates from vector search")
                selected_files = candidates[:top_k]
                summary = "Selected top matches based on vector similarity scores."

            # Create natural language response
            if selected_files:
                if len(selected_files) == 1:
                    response = f"I found exactly what you're looking for! {summary}\n\n📄 {selected_files[0]['file_name']}"
                else:
                    response = f"I found {len(selected_files)} files that match your request. {summary}\n\n"
                    for i, f in enumerate(selected_files, 1):
                        response += f"{i}. 📄 {f['file_name']}\n"
            else:
                response = "I couldn't find any files that match your request. Try:\n• Indexing more folders\n• Using different keywords\n• Rephrasing your search"

            return {
                "response": response,
                "files": selected_files,
                "reasoning": summary
            }

        except Exception as e:
            logger.error(f"Error in chain-of-thought reasoning: {e}")
            import traceback
            traceback.print_exc()
            # Fallback to top candidates
            return {
                "response": f"I found {len(candidates[:top_k])} potentially relevant files based on similarity.",
                "files": candidates[:top_k],
                "reasoning": f"Chain-of-thought reasoning failed: {str(e)}"
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
