"""Context assembly engine for Mike.

Replaces the stubbed ContextAssembler with real semantic retrieval,
graph-aware expansion, execution memory injection, and token budgeting.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class ContextBundle:
    """Assembled context for an agent execution."""
    query: str
    agent_type: str
    semantic_chunks: List[Dict[str, Any]] = field(default_factory=list)
    structural_context: Dict[str, Any] = field(default_factory=dict)
    execution_memory: Dict[str, Any] = field(default_factory=dict)
    shared_context: Dict[str, Any] = field(default_factory=dict)
    token_budget: int = 8000
    estimated_tokens: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "agent_type": self.agent_type,
            "semantic_chunks": self.semantic_chunks,
            "structural_context": self.structural_context,
            "execution_memory": self.execution_memory,
            "shared_context": self.shared_context,
            "token_budget": self.token_budget,
            "estimated_tokens": self.estimated_tokens,
            "metadata": self.metadata,
        }


class ContextEngine:
    """Assembles rich, token-budgeted context for agent execution.

    Pipeline:
    1. Semantic retrieval — embed query, search vector store for top-K chunks
    2. Graph-aware expansion — fetch 1-hop neighbors for referenced files
    3. Execution memory injection — past successes/failures for this agent
    4. Token budget management — trim to fit model context window
    """

    def __init__(
        self,
        vector_store: Any,
        embedding_service: Any,
        graph_builder: Optional[Any] = None,
        execution_memory: Optional[Any] = None,
    ):
        self._vector_store = vector_store
        self._embedding_service = embedding_service
        self._graph_builder = graph_builder
        self._execution_memory = execution_memory

    def build(
        self,
        query: str,
        agent_type: str,
        session_id: str,
        token_budget: int = 8000,
        include_structural: bool = True,
        include_semantic: bool = True,
        top_k: int = 10,
        shared_context: Optional[Dict[str, Any]] = None,
    ) -> ContextBundle:
        semantic_chunks: List[Dict[str, Any]] = []
        structural_context: Dict[str, Any] = {}
        exec_memory: Dict[str, Any] = {}

        # Step 1: Semantic retrieval
        if include_semantic:
            semantic_chunks = self._retrieve_semantic(query, session_id, top_k)

        # Step 2: Graph-aware expansion
        if include_structural and self._graph_builder is not None:
            referenced_files = {
                chunk.get("metadata", {}).get("file_path")
                for chunk in semantic_chunks
                if chunk.get("metadata", {}).get("file_path")
            }
            structural_context = self._expand_graph(referenced_files, len(semantic_chunks))

        # Step 3: Execution memory injection
        if self._execution_memory is not None:
            exec_memory = self._assemble_execution_memory(agent_type)

        bundle = ContextBundle(
            query=query,
            agent_type=agent_type,
            semantic_chunks=semantic_chunks,
            structural_context=structural_context,
            execution_memory=exec_memory,
            shared_context=shared_context or {},
            token_budget=token_budget,
            metadata={"session_id": session_id},
        )

        # Step 4: Token budget management
        bundle.estimated_tokens = self._estimate_tokens(bundle)
        if bundle.estimated_tokens > token_budget:
            self._trim_to_budget(bundle, token_budget)

        return bundle

    def _retrieve_semantic(self, query: str, session_id: str, top_k: int) -> List[Dict[str, Any]]:
        query_embedding = self._embedding_service.embed(query)
        results = self._vector_store.search(
            query_embedding=query_embedding,
            session_id=session_id,
            n_results=top_k,
        )
        return results

    def _expand_graph(self, referenced_files: Set[Optional[str]], chunk_count: int) -> Dict[str, Any]:
        expanded_files: Set[str] = set()
        max_expansion = chunk_count * 2

        for file_path in referenced_files:
            if file_path is None:
                continue
            neighbors = self._graph_builder.get_neighbors(file_path)
            expanded_files.update(neighbors)
            if len(expanded_files) >= max_expansion:
                break

        return {
            "referenced_files": [f for f in referenced_files if f],
            "expanded_files": sorted(expanded_files),
        }

    def _assemble_execution_memory(self, agent_type: str) -> Dict[str, Any]:
        mem = self._execution_memory
        return {
            "failed_approaches": mem.failed_approaches.get(agent_type, []),
            "successful_patterns": mem.successful_patterns.get(agent_type, []),
            "learnings": mem.get_learnings(agent_type) if hasattr(mem, "get_learnings") else [],
            "average_iterations": mem.get_average_iterations(agent_type) if hasattr(mem, "get_average_iterations") else 0.0,
        }

    def _estimate_tokens(self, bundle: ContextBundle) -> int:
        total = len(json.dumps(bundle.to_dict()))
        return total // 4

    def _trim_to_budget(self, bundle: ContextBundle, budget: int) -> None:
        if self._estimate_tokens(bundle) > budget and bundle.shared_context:
            bundle.shared_context = {}
            bundle.estimated_tokens = self._estimate_tokens(bundle)

        if self._estimate_tokens(bundle) > budget and bundle.structural_context:
            bundle.structural_context = {}
            bundle.estimated_tokens = self._estimate_tokens(bundle)

        if self._estimate_tokens(bundle) > budget and bundle.execution_memory:
            bundle.execution_memory = {}
            bundle.estimated_tokens = self._estimate_tokens(bundle)

        while self._estimate_tokens(bundle) > budget and len(bundle.semantic_chunks) > 2:
            bundle.semantic_chunks.pop()
            bundle.estimated_tokens = self._estimate_tokens(bundle)
