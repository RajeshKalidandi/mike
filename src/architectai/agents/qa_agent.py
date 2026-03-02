"""Q&A Agent for answering natural language questions about the codebase.

This module implements the Q&A Agent as described in the architecture:
- Query understanding and intent classification
- Semantic search using vectorstore
- Graph-aware context expansion
- Hierarchical summary injection
- Token budget management
- Answer generation with source attribution
"""

import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class QueryIntent(Enum):
    """Classification of user query intents."""

    LOCATION = "location"  # "Where is X?"
    EXPLANATION = "explanation"  # "How does X work?"
    RELATIONSHIP = "relationship"  # "What calls X?"
    MODIFICATION = "modification"  # "How do I change X?"
    COMPARISON = "comparison"  # "What's the difference between X and Y?"
    GENERAL = "general"  # General questions


@dataclass
class SourceReference:
    """Reference to a source code location."""

    file_path: str
    start_line: int
    end_line: int
    entity_name: Optional[str] = None
    entity_type: Optional[str] = None
    relevance_score: float = 0.0

    def format(self) -> str:
        """Format as a readable string reference."""
        if self.entity_name:
            ref = f"{self.file_path}:{self.start_line}-{self.end_line} ({self.entity_type}: {self.entity_name})"
        else:
            ref = f"{self.file_path}:{self.start_line}-{self.end_line}"
        return ref


@dataclass
class QAResponse:
    """Response from the Q&A Agent."""

    answer: str
    query: str
    intent: QueryIntent
    sources: List[SourceReference] = field(default_factory=list)
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary."""
        return {
            "query": self.query,
            "intent": self.intent.value,
            "answer": self.answer,
            "sources": [
                {
                    "file_path": s.file_path,
                    "start_line": s.start_line,
                    "end_line": s.end_line,
                    "entity_name": s.entity_name,
                    "entity_type": s.entity_type,
                    "relevance_score": s.relevance_score,
                }
                for s in self.sources
            ],
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


class QueryAnalyzer:
    """Analyzes and classifies user queries."""

    # Intent patterns for classification
    PATTERNS = {
        QueryIntent.LOCATION: [
            r"where\s+(?:is|are|can\s+I\s+find)",
            r"locate\s+",
            r"find\s+(?:the\s+)?.*?(?:file|function|class|code|service|module|component)",
            r"which\s+file\s+(?:contains|has)",
        ],
        QueryIntent.EXPLANATION: [
            r"how\s+(?:does|is)\s+",
            r"what\s+(?:does|is)\s+.*\s+do",
            r"explain",
            r"describe",
            r"what\s+happens\s+when",
            r"walk\s+me\s+through",
        ],
        QueryIntent.RELATIONSHIP: [
            r"what\s+(?:calls|uses|references)",
            r"who\s+(?:calls|uses)",
            r"dependencies\s+of",
            r"depends\s+on",
            r"related\s+to",
            r"connected\s+to",
        ],
        QueryIntent.MODIFICATION: [
            r"how\s+(?:do\s+I|can\s+I|to)",
            r"change\s+",
            r"modify\s+",
            r"add\s+",
            r"update\s+",
            r"implement\s+",
            r"what\s+(?:files|changes)\s+.*\s+need",
        ],
        QueryIntent.COMPARISON: [
            r"difference\s+between",
            r"compare\s+",
            r"versus\s+",
            r"vs\s+",
            r"similarities\s+between",
        ],
    }

    def classify(self, query: str) -> QueryIntent:
        """Classify query intent.

        Args:
            query: The user's natural language query

        Returns:
            Classified intent
        """
        query_lower = query.lower()

        for intent, patterns in self.PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    return intent

        return QueryIntent.GENERAL

    def extract_entities(self, query: str) -> List[str]:
        """Extract potential code entities from query.

        Args:
            query: The user's query

        Returns:
            List of potential entity names (functions, classes, etc.)
        """
        entities = []

        # Look for camelCase, PascalCase, snake_case patterns
        # PascalCase (classes)
        pascal_pattern = r"\b[A-Z][a-zA-Z0-9]*(?:[A-Z][a-zA-Z0-9]*)+\b"
        entities.extend(re.findall(pascal_pattern, query))

        # camelCase (functions/variables)
        camel_pattern = r"\b[a-z][a-z0-9]*(?:[A-Z][a-z0-9]*)+\b"
        entities.extend(re.findall(camel_pattern, query))

        # snake_case
        snake_pattern = r"\b[a-z][a-z0-9_]*[a-z0-9]\b"
        snake_matches = re.findall(snake_pattern, query)
        # Filter out common words
        common_words = {
            "the",
            "and",
            "for",
            "are",
            "but",
            "not",
            "you",
            "all",
            "can",
            "had",
            "her",
            "was",
            "one",
            "our",
            "out",
            "day",
            "get",
            "has",
            "him",
            "his",
            "how",
            "its",
            "may",
            "new",
            "now",
            "old",
            "see",
            "two",
            "who",
            "boy",
            "did",
            "she",
            "use",
            "her",
            "way",
            "many",
            "oil",
            "sit",
            "set",
            "run",
            "eat",
            "far",
            "sea",
            "eye",
            "ago",
            "off",
            "too",
            "any",
            "try",
            "ask",
            "end",
            "why",
            "let",
            "put",
            "say",
            "she",
            "try",
            "way",
            "own",
            "say",
            "too",
            "old",
            "tell",
            "very",
            "when",
            "much",
            "would",
            "there",
            "their",
            "what",
            "said",
            "each",
            "which",
            "will",
            "about",
            "could",
            "other",
            "after",
            "first",
            "never",
            "these",
            "think",
            "where",
            "being",
            "every",
            "great",
            "might",
            "shall",
            "still",
            "those",
            "under",
            "while",
            "this",
            "that",
            "with",
            "from",
            "they",
            "have",
            "were",
            "been",
            "have",
            "more",
            "some",
            "time",
            "than",
            "them",
            "into",
            "just",
            "like",
            "over",
            "also",
            "back",
            "only",
            "know",
            "take",
            "year",
            "good",
            "come",
            "make",
            "well",
            "look",
            "want",
            "here",
            "find",
            "give",
            "does",
            "made",
            "call",
            "came",
            "work",
            "life",
            "even",
            "open",
            "case",
            "show",
            "live",
            "play",
            "went",
            "told",
            "seen",
            "hear",
            "talk",
            "soon",
            "read",
            "stop",
            "face",
            "fact",
            "land",
            "line",
            "kind",
            "next",
            "word",
            "came",
            "went",
            "told",
            "seen",
            "hear",
            "talk",
            "soon",
            "read",
            "stop",
            "face",
            "fact",
            "land",
            "line",
            "kind",
            "next",
            "word",
        }
        entities.extend(
            [e for e in snake_matches if e not in common_words and len(e) > 2]
        )

        # Deduplicate while preserving order
        seen = set()
        unique_entities = []
        for e in entities:
            if e not in seen:
                seen.add(e)
                unique_entities.append(e)

        return unique_entities

    def extract_file_types(self, query: str) -> List[str]:
        """Extract file type hints from query.

        Args:
            query: The user's query

        Returns:
            List of file extensions or types mentioned
        """
        query_lower = query.lower()
        file_types = []

        # Common language hints
        hints = {
            "python": ".py",
            "javascript": ".js",
            "typescript": ".ts",
            "java": ".java",
            "go": ".go",
            "rust": ".rs",
            "c++": ".cpp",
            "cpp": ".cpp",
            "c": ".c",
            "ruby": ".rb",
            "php": ".php",
            "config": ".json",
            "configuration": ".json",
            "test": "test",
        }

        for hint, ext in hints.items():
            if hint in query_lower:
                file_types.append(ext)

        return file_types


class QAAgent:
    """Q&A Agent for answering questions about the codebase.

    The Q&A Agent processes natural language queries about the codebase and
    provides answers with source attribution. It uses a multi-stage pipeline:

    1. Query Analysis: Classify intent and extract entities
    2. Context Assembly: Gather relevant code context
    3. Answer Generation: Generate answer with source references
    """

    def __init__(
        self,
        context_assembler=None,
        llm_client=None,
        database=None,
    ):
        """Initialize the Q&A Agent.

        Args:
            context_assembler: ContextAssembler instance
            llm_client: LLM client for answer generation (local model)
            database: Database instance for metadata lookups
        """
        self.context_assembler = context_assembler
        self.llm_client = llm_client
        self.database = database
        self.query_analyzer = QueryAnalyzer()

    def ask(
        self,
        query: str,
        session_id: str,
        context_filters: Optional[Dict[str, Any]] = None,
    ) -> QAResponse:
        """Answer a question about the codebase.

        Args:
            query: Natural language question
            session_id: Current session ID
            context_filters: Optional filters for context (file types, etc.)

        Returns:
            QAResponse with answer and source references
        """
        try:
            # Step 1: Analyze query
            intent = self.query_analyzer.classify(query)
            entities = self.query_analyzer.extract_entities(query)
            file_types = self.query_analyzer.extract_file_types(query)

            # Step 2: Assemble context
            if self.context_assembler:
                context = self.context_assembler.assemble(
                    query=query,
                    session_id=session_id,
                    top_k=context_filters.get("top_k", 10) if context_filters else 10,
                )
            else:
                context = None

            # Step 3: Generate answer
            if self.llm_client:
                answer, sources = self._generate_answer_with_llm(
                    query=query,
                    intent=intent,
                    entities=entities,
                    context=context,
                )
            else:
                answer, sources = self._generate_answer_fallback(
                    query=query,
                    intent=intent,
                    entities=entities,
                    context=context,
                )

            # Calculate confidence based on sources and context
            confidence = self._calculate_confidence(sources, context)

            return QAResponse(
                answer=answer,
                query=query,
                intent=intent,
                sources=sources,
                confidence=confidence,
                metadata={
                    "entities_extracted": entities,
                    "file_types_hinted": file_types,
                    "context_tokens": context.total_tokens if context else 0,
                },
            )

        except Exception as e:
            # Return graceful error response
            return QAResponse(
                answer=f"I encountered an error while processing your question: {str(e)}. Please try rephrasing or ask a different question.",
                query=query,
                intent=QueryIntent.GENERAL,
                sources=[],
                confidence=0.0,
                metadata={"error": str(e)},
            )

    def _generate_answer_with_llm(
        self,
        query: str,
        intent: QueryIntent,
        entities: List[str],
        context: Any,
    ) -> Tuple[str, List[SourceReference]]:
        """Generate answer using LLM.

        Args:
            query: Original query
            intent: Classified intent
            entities: Extracted entities
            context: Assembled context

        Returns:
            Tuple of (answer text, list of source references)
        """
        # Build prompt
        prompt = self._build_prompt(query, intent, context)

        # Call LLM
        try:
            response = self.llm_client.generate(
                prompt=prompt,
                max_tokens=1000,
                temperature=0.3,  # Low temperature for factual responses
            )
            answer = response.get("text", "")
        except Exception as e:
            # Fallback if LLM fails
            return self._generate_answer_fallback(query, intent, entities, context)

        # Extract sources from context
        sources = self._extract_sources_from_context(context)

        return answer, sources

    def _build_prompt(self, query: str, intent: QueryIntent, context: Any) -> str:
        """Build prompt for LLM.

        Args:
            query: User query
            intent: Query intent
            context: Assembled context

        Returns:
            Formatted prompt string
        """
        prompt_parts = []

        # System instruction
        prompt_parts.append(
            "You are a helpful AI assistant that answers questions about codebases. "
            "Provide clear, accurate answers based on the provided context. "
            "Always cite specific file paths and line numbers when referencing code."
        )

        # Add context if available
        if context:
            prompt_parts.append("\n=== Context ===\n")
            prompt_parts.append(context.to_prompt_context())

        # Add query
        prompt_parts.append(f"\n=== Question ===\n{query}")

        # Add intent-specific instruction
        if intent == QueryIntent.LOCATION:
            prompt_parts.append(
                "\nProvide the exact file path and line number where this is located."
            )
        elif intent == QueryIntent.EXPLANATION:
            prompt_parts.append(
                "\nExplain how this works step by step, referencing specific code."
            )
        elif intent == QueryIntent.RELATIONSHIP:
            prompt_parts.append(
                "\nDescribe the relationships and dependencies clearly."
            )
        elif intent == QueryIntent.MODIFICATION:
            prompt_parts.append(
                "\nList the specific files and lines that would need to be changed."
            )

        prompt_parts.append(
            "\nProvide your answer in plain language with specific file references."
        )

        return "\n".join(prompt_parts)

    def _generate_answer_fallback(
        self,
        query: str,
        intent: QueryIntent,
        entities: List[str],
        context: Any,
    ) -> Tuple[str, List[SourceReference]]:
        """Generate answer without LLM (fallback).

        This is used when no LLM client is available.
        Returns a structured response based on context.

        Args:
            query: Original query
            intent: Classified intent
            entities: Extracted entities
            context: Assembled context

        Returns:
            Tuple of (answer text, list of source references)
        """
        sources = self._extract_sources_from_context(context)

        if not sources:
            return (
                "I couldn't find relevant code for your question. Please try rephrasing or check if the codebase has been indexed.",
                [],
            )

        # Build answer based on intent and available context
        if intent == QueryIntent.LOCATION:
            answer = self._build_location_answer(entities, sources)
        elif intent == QueryIntent.EXPLANATION:
            answer = self._build_explanation_answer(entities, sources)
        elif intent == QueryIntent.RELATIONSHIP:
            answer = self._build_relationship_answer(sources, context)
        elif intent == QueryIntent.MODIFICATION:
            answer = self._build_modification_answer(entities, sources)
        else:
            answer = self._build_general_answer(query, sources)

        return answer, sources

    def _build_location_answer(
        self, entities: List[str], sources: List[SourceReference]
    ) -> str:
        """Build answer for location queries."""
        if not sources:
            return f"Could not find location for: {', '.join(entities)}"

        parts = ["Found the following locations:\n"]
        for source in sources[:5]:
            parts.append(f"- {source.format()}")

        return "\n".join(parts)

    def _build_explanation_answer(
        self, entities: List[str], sources: List[SourceReference]
    ) -> str:
        """Build answer for explanation queries."""
        if entities:
            intro = f"Regarding {' and '.join(entities[:2])}, I found relevant code in:"
        else:
            intro = "I found relevant code that may help answer your question:"

        parts = [intro]
        for source in sources[:5]:
            parts.append(f"\n- {source.format()}")

        parts.append(
            "\n\nPlease review the referenced code locations to understand the implementation details."
        )

        return "\n".join(parts)

    def _build_relationship_answer(
        self, sources: List[SourceReference], context: Any
    ) -> str:
        """Build answer for relationship queries."""
        parts = ["Found the following related code:\n"]

        for source in sources[:5]:
            parts.append(f"- {source.format()}")

        if context and hasattr(context, "graph_context"):
            graph = context.graph_context
            if graph.get("callers"):
                parts.append("\nCalled by:")
                for caller in graph["callers"][:5]:
                    parts.append(f"  - {caller}")

            if graph.get("callees"):
                parts.append("\nCalls:")
                for callee in graph["callees"][:5]:
                    parts.append(f"  - {callee}")

        return "\n".join(parts)

    def _build_modification_answer(
        self, entities: List[str], sources: List[SourceReference]
    ) -> str:
        """Build answer for modification queries."""
        if entities:
            intro = f"To modify {' or '.join(entities[:2])}, you would need to change:"
        else:
            intro = "Based on the codebase, you would need to modify:"

        parts = [intro]
        for source in sources[:5]:
            parts.append(f"\n- {source.format()}")

        parts.append(
            "\n\nPlease review these locations and consider any dependencies before making changes."
        )

        return "\n".join(parts)

    def _build_general_answer(self, query: str, sources: List[SourceReference]) -> str:
        """Build general answer."""
        parts = [f"Regarding your question: '{query}'\n"]
        parts.append("I found the following relevant code:\n")

        for source in sources[:5]:
            parts.append(f"- {source.format()}")

        return "\n".join(parts)

    def _extract_sources_from_context(self, context: Any) -> List[SourceReference]:
        """Extract source references from assembled context.

        Args:
            context: Assembled context

        Returns:
            List of SourceReference objects
        """
        if not context:
            return []

        sources = []
        seen = set()

        # Extract from semantic chunks
        if hasattr(context, "semantic_chunks"):
            for chunk in context.semantic_chunks:
                key = (chunk.file_path, chunk.start_line, chunk.end_line)
                if key not in seen:
                    seen.add(key)
                    sources.append(
                        SourceReference(
                            file_path=chunk.file_path,
                            start_line=chunk.start_line,
                            end_line=chunk.end_line,
                            entity_name=chunk.entity_name,
                            entity_type=chunk.entity_type,
                            relevance_score=chunk.score,
                        )
                    )

        return sources

    def _calculate_confidence(
        self, sources: List[SourceReference], context: Any
    ) -> float:
        """Calculate confidence score for the answer.

        Args:
            sources: Source references
            context: Assembled context

        Returns:
            Confidence score between 0 and 1
        """
        if not sources:
            return 0.0

        # Base confidence on number and quality of sources
        base_confidence = min(len(sources) * 0.2, 0.6)

        # Boost for high-relevance sources
        avg_score = sum(s.relevance_score for s in sources) / len(sources)
        relevance_boost = avg_score * 0.3

        # Boost for having context
        context_boost = (
            0.1
            if context and hasattr(context, "total_tokens") and context.total_tokens > 0
            else 0.0
        )

        return min(base_confidence + relevance_boost + context_boost, 1.0)


class LocalLLMClient:
    """Client for local LLM inference.

    This is a placeholder interface for connecting to local models
    via Ollama, vLLM, or llama.cpp. The actual implementation would
    connect to your chosen local inference server.
    """

    def __init__(
        self, base_url: str = "http://localhost:11434", model: str = "llama3.2"
    ):
        """Initialize LLM client.

        Args:
            base_url: URL of the inference server
            model: Model name to use
        """
        self.base_url = base_url
        self.model = model

    def generate(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        stop_sequences: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Generate text from prompt.

        Args:
            prompt: The prompt text
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            stop_sequences: Optional stop sequences

        Returns:
            Dictionary with 'text' key containing the generated text
        """
        # This is a placeholder - actual implementation would call
        # the local inference server (Ollama, vLLM, etc.)
        raise NotImplementedError(
            "Local LLM client requires connection to inference server. "
            "Please implement with your chosen backend (Ollama, vLLM, etc.)"
        )

    def is_available(self) -> bool:
        """Check if the LLM server is available."""
        # Placeholder - would actually check server health
        return False
