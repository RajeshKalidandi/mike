"""Context assembly pipeline for preparing context before agent calls.

This module implements the Context Assembly Pipeline as described in the architecture:
1. Semantic Search -> Top-K Chunks
2. Graph-Aware Expansion (Fetch callers + callees)
3. Hierarchical Summary Injection
4. Token Budget Manager (Trim to fit context window)
"""

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
import json


@dataclass
class CodeChunk:
    """Represents a code chunk with metadata."""

    chunk_id: str
    file_path: str
    content: str
    start_line: int
    end_line: int
    language: str
    entity_type: str  # function, class, module, etc.
    entity_name: Optional[str] = None
    score: float = 0.0  # relevance score from semantic search


@dataclass
class AssembledContext:
    """Represents fully assembled context for an agent."""

    query: str
    semantic_chunks: List[CodeChunk]
    graph_context: Dict[str, Any] = field(default_factory=dict)
    hierarchical_summaries: List[Dict[str, Any]] = field(default_factory=list)
    total_tokens: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_prompt_context(self) -> str:
        """Convert assembled context to a formatted string for LLM prompt."""
        sections = []

        # Add query
        sections.append(f"Question: {self.query}\n")

        # Add hierarchical summaries (high-level context first)
        if self.hierarchical_summaries:
            sections.append("=== Project Structure ===")
            for summary in self.hierarchical_summaries:
                level = summary.get("level", "unknown")
                name = summary.get("name", "")
                desc = summary.get("description", "")
                sections.append(f"{level}: {name}")
                if desc:
                    sections.append(f"  {desc}")
            sections.append("")

        # Add graph context (dependencies)
        if self.graph_context:
            sections.append("=== Dependencies ===")
            if "callers" in self.graph_context:
                sections.append("Called by:")
                for caller in self.graph_context["callers"][:5]:  # Limit to top 5
                    sections.append(f"  - {caller}")
            if "callees" in self.graph_context:
                sections.append("Calls:")
                for callee in self.graph_context["callees"][:5]:  # Limit to top 5
                    sections.append(f"  - {callee}")
            sections.append("")

        # Add semantic chunks (the actual code)
        if self.semantic_chunks:
            sections.append("=== Relevant Code ===")
            for chunk in self.semantic_chunks:
                sections.append(f"\nFile: {chunk.file_path}")
                if chunk.entity_name:
                    sections.append(
                        f"Entity: {chunk.entity_name} ({chunk.entity_type})"
                    )
                sections.append(f"Lines: {chunk.start_line}-{chunk.end_line}")
                sections.append("```")
                sections.append(chunk.content)
                sections.append("```")

        return "\n".join(sections)


class ContextAssembler:
    """Assembles context from multiple sources for agent consumption.

    Implements the Context Assembly Pipeline:
    Query -> Semantic Search -> Graph Expansion -> Summary Injection -> Token Trimming
    """

    def __init__(
        self,
        vector_store=None,
        graph_builder=None,
        embedding_service=None,
        token_budget: int = 4000,
    ):
        """Initialize the context assembler.

        Args:
            vector_store: Vector store instance for semantic search
            graph_builder: Graph builder instance for dependency traversal
            embedding_service: Service for embedding queries
            token_budget: Maximum tokens to include in context
        """
        self.vector_store = vector_store
        self.graph_builder = graph_builder
        self.embedding_service = embedding_service
        self.token_budget = token_budget
        self._token_estimate_ratio = 0.75  # chars per token (approximate)

    def assemble(
        self,
        query: str,
        session_id: str,
        top_k: int = 10,
        expand_graph: bool = True,
        include_summaries: bool = True,
    ) -> AssembledContext:
        """Assemble context for a query.

        Args:
            query: The user's natural language query
            session_id: Current session ID
            top_k: Number of top semantic matches to retrieve
            expand_graph: Whether to perform graph-aware expansion
            include_summaries: Whether to include hierarchical summaries

        Returns:
            AssembledContext with all context components
        """
        context = AssembledContext(query=query, semantic_chunks=[])

        # Step 1: Semantic Search
        semantic_chunks = self._semantic_search(query, session_id, top_k)
        context.semantic_chunks = semantic_chunks

        # Step 2: Graph-Aware Expansion
        if expand_graph and self.graph_builder:
            graph_context = self._expand_graph(semantic_chunks, session_id)
            context.graph_context = graph_context

        # Step 3: Hierarchical Summary Injection
        if include_summaries:
            summaries = self._get_hierarchical_summaries(semantic_chunks, session_id)
            context.hierarchical_summaries = summaries

        # Step 4: Token Budget Management
        context = self._apply_token_budget(context)

        # Calculate total tokens
        context.total_tokens = self._estimate_tokens(context.to_prompt_context())

        return context

    def _semantic_search(
        self, query: str, session_id: str, top_k: int
    ) -> List[CodeChunk]:
        """Perform semantic search to find relevant code chunks.

        Args:
            query: The search query
            session_id: Session ID for namespacing
            top_k: Number of results to return

        Returns:
            List of CodeChunk objects ordered by relevance
        """
        if not self.vector_store:
            return []

        try:
            # Embed the query
            if self.embedding_service:
                query_embedding = self.embedding_service.embed(query)
            else:
                # Fallback: use vector store's embedding method
                query_embedding = self._embed_query(query)

            # Search vector store
            results = self.vector_store.search(
                query_embedding=query_embedding,
                session_id=session_id,
                top_k=top_k,
            )

            # Convert results to CodeChunk objects
            chunks = []
            for result in results:
                chunk = CodeChunk(
                    chunk_id=result.get("id", ""),
                    file_path=result.get("file_path", ""),
                    content=result.get("content", ""),
                    start_line=result.get("start_line", 0),
                    end_line=result.get("end_line", 0),
                    language=result.get("language", ""),
                    entity_type=result.get("entity_type", "code"),
                    entity_name=result.get("entity_name"),
                    score=result.get("score", 0.0),
                )
                chunks.append(chunk)

            return chunks

        except Exception as e:
            # Log error but return empty list to allow graceful degradation
            print(f"Warning: Semantic search failed: {e}")
            return []

    def _embed_query(self, query: str) -> List[float]:
        """Embed a query string into a vector.

        This is a fallback method if no embedding service is provided.
        In production, this should use the same embedding model as the indexing.

        Args:
            query: The query string

        Returns:
            Vector embedding of the query
        """
        # This is a placeholder - in real implementation, this would use
        # the actual embedding model (nomic-embed-text, mxbai-embed-large, etc.)
        # For now, return an empty vector that will trigger fallback behavior
        return []

    def _expand_graph(self, chunks: List[CodeChunk], session_id: str) -> Dict[str, Any]:
        """Expand context using dependency graph (callers and callees).

        Args:
            chunks: The semantic search results
            session_id: Session ID for graph namespacing

        Returns:
            Dictionary with graph context (callers, callees, related files)
        """
        if not self.graph_builder:
            return {}

        try:
            graph_context = {
                "callers": [],
                "callees": [],
                "related_files": set(),
            }

            for chunk in chunks:
                if not chunk.entity_name:
                    continue

                # Get callers (functions that call this entity)
                callers = self.graph_builder.get_callers(
                    entity_name=chunk.entity_name,
                    file_path=chunk.file_path,
                    session_id=session_id,
                )
                graph_context["callers"].extend(callers)

                # Get callees (functions called by this entity)
                callees = self.graph_builder.get_callees(
                    entity_name=chunk.entity_name,
                    file_path=chunk.file_path,
                    session_id=session_id,
                )
                graph_context["callees"].extend(callees)

                # Get related files
                related = self.graph_builder.get_related_files(
                    file_path=chunk.file_path,
                    session_id=session_id,
                )
                graph_context["related_files"].update(related)

            # Convert set to list for JSON serialization
            graph_context["related_files"] = list(graph_context["related_files"])

            # Deduplicate and limit
            graph_context["callers"] = list(dict.fromkeys(graph_context["callers"]))[
                :10
            ]
            graph_context["callees"] = list(dict.fromkeys(graph_context["callees"]))[
                :10
            ]
            graph_context["related_files"] = graph_context["related_files"][:10]

            return graph_context

        except Exception as e:
            print(f"Warning: Graph expansion failed: {e}")
            return {}

    def _get_hierarchical_summaries(
        self, chunks: List[CodeChunk], session_id: str
    ) -> List[Dict[str, Any]]:
        """Get hierarchical summaries for context.

        Args:
            chunks: The semantic search results
            session_id: Session ID for retrieving summaries

        Returns:
            List of summary dictionaries at different hierarchy levels
        """
        try:
            summaries = []

            # Collect unique files from chunks
            files = set(chunk.file_path for chunk in chunks)

            for file_path in files:
                # Get file-level summary
                file_summary = self._get_file_summary(file_path, session_id)
                if file_summary:
                    summaries.append(file_summary)

                # Get module-level summary (directory)
                module_path = self._get_module_path(file_path)
                if module_path:
                    module_summary = self._get_module_summary(module_path, session_id)
                    if module_summary and module_summary not in summaries:
                        summaries.append(module_summary)

            # Get system-level summary (if available)
            system_summary = self._get_system_summary(session_id)
            if system_summary:
                summaries.insert(0, system_summary)  # System first

            return summaries

        except Exception as e:
            print(f"Warning: Failed to get hierarchical summaries: {e}")
            return []

    def _get_file_summary(
        self, file_path: str, session_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get summary for a specific file."""
        # This would retrieve from database or cache
        # For now, return a basic structure
        return {
            "level": "file",
            "name": file_path,
            "description": None,  # Would be populated from database
        }

    def _get_module_path(self, file_path: str) -> Optional[str]:
        """Extract module path from file path."""
        import os

        parts = file_path.split(os.sep)
        if len(parts) > 1:
            return os.sep.join(parts[:-1])
        return None

    def _get_module_summary(
        self, module_path: str, session_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get summary for a module (directory)."""
        return {
            "level": "module",
            "name": module_path,
            "description": None,
        }

    def _get_system_summary(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get system-level summary."""
        # This would be stored during the summarization phase
        return None  # Placeholder

    def _apply_token_budget(self, context: AssembledContext) -> AssembledContext:
        """Apply token budget constraints to context.

        Trims context to fit within token_budget while preserving
        the most important information (semantic chunks > graph > summaries).

        Args:
            context: The assembled context

        Returns:
            Context trimmed to fit token budget
        """
        # Start with highest priority: semantic chunks
        chunks_text = self._format_chunks(context.semantic_chunks)
        chunks_tokens = self._estimate_tokens(chunks_text)

        if chunks_tokens >= self.token_budget:
            # Only keep most relevant chunks
            context.semantic_chunks = self._trim_chunks(
                context.semantic_chunks,
                self.token_budget,
            )
            context.hierarchical_summaries = []
            context.graph_context = {}
            return context

        remaining = self.token_budget - chunks_tokens

        # Next priority: graph context
        if context.graph_context:
            graph_text = json.dumps(context.graph_context)
            graph_tokens = self._estimate_tokens(graph_text)

            if graph_tokens >= remaining:
                # Trim graph context
                context.graph_context = self._trim_graph_context(
                    context.graph_context, remaining
                )
                context.hierarchical_summaries = []
                return context

            remaining -= graph_tokens

        # Lowest priority: summaries
        if context.hierarchical_summaries:
            summaries_text = json.dumps(context.hierarchical_summaries)
            summaries_tokens = self._estimate_tokens(summaries_text)

            if summaries_tokens >= remaining:
                context.hierarchical_summaries = self._trim_summaries(
                    context.hierarchical_summaries, remaining
                )

        return context

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count from text.

        Uses a simple character-to-token ratio. In production,
        this should use the actual tokenizer for the target model.

        Args:
            text: Text to estimate

        Returns:
            Estimated token count
        """
        return int(len(text) / self._token_estimate_ratio)

    def _format_chunks(self, chunks: List[CodeChunk]) -> str:
        """Format chunks as text for token estimation."""
        parts = []
        for chunk in chunks:
            parts.append(chunk.content)
            parts.append(chunk.file_path)
        return "\n".join(parts)

    def _trim_chunks(
        self, chunks: List[CodeChunk], token_budget: int
    ) -> List[CodeChunk]:
        """Trim chunks to fit token budget."""
        trimmed = []
        current_tokens = 0

        for chunk in chunks:
            chunk_text = self._format_chunks([chunk])
            chunk_tokens = self._estimate_tokens(chunk_text)

            if current_tokens + chunk_tokens > token_budget:
                # Try to take partial content if it's a large chunk
                available = token_budget - current_tokens
                if available > 200 and len(chunk.content) > 500:
                    # Truncate content
                    truncated_content = chunk.content[
                        : int(available * self._token_estimate_ratio)
                    ]
                    chunk.content = truncated_content + "\n... [truncated]"
                    trimmed.append(chunk)
                break

            trimmed.append(chunk)
            current_tokens += chunk_tokens

        return trimmed

    def _trim_graph_context(
        self, graph_context: Dict[str, Any], token_budget: int
    ) -> Dict[str, Any]:
        """Trim graph context to fit token budget."""
        trimmed = {"callers": [], "callees": [], "related_files": []}
        current_tokens = 0

        for key in ["callers", "callees", "related_files"]:
            for item in graph_context.get(key, []):
                item_tokens = self._estimate_tokens(str(item))
                if current_tokens + item_tokens > token_budget:
                    break
                trimmed[key].append(item)
                current_tokens += item_tokens

        return trimmed

    def _trim_summaries(
        self, summaries: List[Dict[str, Any]], token_budget: int
    ) -> List[Dict[str, Any]]:
        """Trim summaries to fit token budget."""
        trimmed = []
        current_tokens = 0

        for summary in summaries:
            summary_tokens = self._estimate_tokens(json.dumps(summary))
            if current_tokens + summary_tokens > token_budget:
                break
            trimmed.append(summary)
            current_tokens += summary_tokens

        return trimmed


class SimpleTokenizer:
    """Simple tokenizer for token estimation.

    This is a fallback when no specific tokenizer is available.
    For production, use the actual tokenizer for your model.
    """

    def __init__(self, chars_per_token: float = 4.0):
        """Initialize tokenizer.

        Args:
            chars_per_token: Average characters per token
        """
        self.chars_per_token = chars_per_token

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count."""
        return int(len(text) / self.chars_per_token)

    def truncate(self, text: str, max_tokens: int) -> str:
        """Truncate text to fit max tokens."""
        max_chars = int(max_tokens * self.chars_per_token)
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "..."
