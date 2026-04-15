# Three Missing Primitives Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add ContextEngine, Progressive Planning Architecture, DAGExecutor, and ModelProvider to turn Mike from a scheduler into a real multi-agent orchestration system.

**Architecture:** Four new files in `src/mike/orchestrator/` — `model_provider.py` (foundation, no dependencies on other new files), `context_engine.py` (depends on existing VectorStore/EmbeddingService/GraphBuilder), `planner.py` (depends on ModelProvider), `dag_executor.py` (depends on ContextEngine + AgentRegistry). Engine and __init__ get wired up last.

**Tech Stack:** Python 3.10+, asyncio, networkx (existing), chromadb (existing), ollama (existing), httpx (existing), Pydantic v2 (existing)

**Spec:** `docs/superpowers/specs/2026-04-15-three-primitives-architecture-design.md`

---

## File Map

| Action | File | Responsibility |
|--------|------|---------------|
| Create | `src/mike/orchestrator/model_provider.py` | ModelProvider ABC, OllamaProvider, OpenAICompatibleProvider, ModelRouter |
| Create | `tests/unit/test_model_provider.py` | Unit tests for all providers and router |
| Create | `src/mike/orchestrator/context_engine.py` | ContextEngine with semantic retrieval, graph expansion, token budgeting |
| Create | `tests/unit/test_context_engine.py` | Unit tests for context assembly pipeline |
| Create | `src/mike/orchestrator/planner.py` | IntentClassifier, StrategyRouter, RulePlanner, TemplatePlanner, LLMPlanner |
| Create | `tests/unit/test_planner.py` | Unit tests for all planners and intent classification |
| Create | `src/mike/orchestrator/dag_executor.py` | DAGExecutor with topological execution, parallel branches, cancellation |
| Create | `tests/unit/test_dag_executor.py` | Unit tests for DAG execution |
| Modify | `src/mike/orchestrator/engine.py` | Add `run()` method, wire new components, delegate ContextAssembler |
| Modify | `src/mike/orchestrator/__init__.py` | Export new classes |
| Create | `tests/integration/test_orchestrator_integration.py` | End-to-end orchestrator integration test |

---

## Task 1: ModelProvider Abstraction

**Files:**
- Create: `src/mike/orchestrator/model_provider.py`
- Create: `tests/unit/test_model_provider.py`

This is the foundation — no dependencies on other new files.

- [ ] **Step 1: Write failing tests for ModelProvider ABC and OllamaProvider**

```python
# tests/unit/test_model_provider.py
"""Unit tests for ModelProvider abstraction."""

import json
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from mike.orchestrator.model_provider import (
    ModelCapabilities,
    ModelProvider,
    OllamaProvider,
    OpenAICompatibleProvider,
    ModelRouter,
)


class TestModelCapabilities:
    """Test ModelCapabilities dataclass."""

    def test_create_capabilities(self):
        caps = ModelCapabilities(
            max_context=8192,
            supports_json_mode=True,
            supports_tool_calling=False,
            supports_streaming=True,
            is_code_specialized=True,
        )
        assert caps.max_context == 8192
        assert caps.supports_json_mode is True
        assert caps.is_code_specialized is True


class TestOllamaProvider:
    """Test OllamaProvider implementation."""

    def test_init_default_endpoint(self):
        provider = OllamaProvider(model="gemma3:12b")
        assert provider.model_name() == "gemma3:12b"
        assert provider._endpoint == "http://localhost:11434"

    def test_init_custom_endpoint(self):
        provider = OllamaProvider(model="qwen2.5-coder:14b", endpoint="http://gpu-box:11434")
        assert provider.model_name() == "qwen2.5-coder:14b"
        assert provider._endpoint == "http://gpu-box:11434"

    def test_capabilities_code_model(self):
        provider = OllamaProvider(model="qwen2.5-coder:14b")
        caps = provider.capabilities()
        assert caps.is_code_specialized is True

    def test_capabilities_general_model(self):
        provider = OllamaProvider(model="gemma3:12b")
        caps = provider.capabilities()
        assert caps.is_code_specialized is False

    @patch("mike.orchestrator.model_provider.httpx")
    def test_generate_calls_ollama_api(self, mock_httpx):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "Hello world"}
        mock_response.raise_for_status = MagicMock()
        mock_httpx.post.return_value = mock_response

        provider = OllamaProvider(model="gemma3:12b")
        result = provider.generate("Say hello")

        assert result == "Hello world"
        mock_httpx.post.assert_called_once()
        call_args = mock_httpx.post.call_args
        assert "/api/generate" in call_args[0][0]

    @patch("mike.orchestrator.model_provider.httpx")
    def test_generate_with_system_prompt(self, mock_httpx):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "result"}
        mock_response.raise_for_status = MagicMock()
        mock_httpx.post.return_value = mock_response

        provider = OllamaProvider(model="gemma3:12b")
        provider.generate("query", system="You are helpful")

        call_body = mock_httpx.post.call_args[1]["json"]
        assert call_body["system"] == "You are helpful"

    @patch("mike.orchestrator.model_provider.httpx")
    def test_generate_json_parses_response(self, mock_httpx):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": '{"key": "value"}'}
        mock_response.raise_for_status = MagicMock()
        mock_httpx.post.return_value = mock_response

        provider = OllamaProvider(model="gemma3:12b")
        result = provider.generate_json("Return JSON")

        assert result == {"key": "value"}

    @patch("mike.orchestrator.model_provider.httpx")
    def test_generate_json_handles_markdown_wrapped_json(self, mock_httpx):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": '```json\n{"key": "value"}\n```'}
        mock_response.raise_for_status = MagicMock()
        mock_httpx.post.return_value = mock_response

        provider = OllamaProvider(model="gemma3:12b")
        result = provider.generate_json("Return JSON")

        assert result == {"key": "value"}

    @patch("mike.orchestrator.model_provider.httpx")
    def test_generate_json_returns_empty_on_invalid(self, mock_httpx):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"response": "not json at all"}
        mock_response.raise_for_status = MagicMock()
        mock_httpx.post.return_value = mock_response

        provider = OllamaProvider(model="gemma3:12b")
        result = provider.generate_json("Return JSON")

        assert result == {}


class TestOpenAICompatibleProvider:
    """Test OpenAICompatibleProvider implementation."""

    def test_init(self):
        provider = OpenAICompatibleProvider(
            model="llama-3.3-70b",
            endpoint="http://localhost:8000/v1",
            api_key="test-key",
        )
        assert provider.model_name() == "llama-3.3-70b"

    @patch("mike.orchestrator.model_provider.httpx")
    def test_generate_uses_chat_completions(self, mock_httpx):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Hello"}}]
        }
        mock_response.raise_for_status = MagicMock()
        mock_httpx.post.return_value = mock_response

        provider = OpenAICompatibleProvider(
            model="llama-3.3-70b", endpoint="http://localhost:8000/v1"
        )
        result = provider.generate("Say hello")

        assert result == "Hello"
        call_url = mock_httpx.post.call_args[0][0]
        assert "/chat/completions" in call_url


class TestModelRouter:
    """Test ModelRouter task-aware selection."""

    def _make_provider(self, name, is_code=False, max_context=8192):
        provider = MagicMock(spec=ModelProvider)
        provider.model_name.return_value = name
        provider.capabilities.return_value = ModelCapabilities(
            max_context=max_context,
            supports_json_mode=True,
            supports_tool_calling=False,
            supports_streaming=True,
            is_code_specialized=is_code,
        )
        return provider

    def test_select_default(self):
        default = self._make_provider("default-model")
        router = ModelRouter(providers={"default": default}, default="default")
        selected = router.select("general")
        assert selected.model_name() == "default-model"

    def test_select_code_model_for_code_task(self):
        general = self._make_provider("general", is_code=False)
        coder = self._make_provider("coder", is_code=True)
        router = ModelRouter(
            providers={"general": general, "coder": coder},
            default="general",
            tags={"coder": ["code"]},
        )
        selected = router.select("code_generation")
        assert selected.model_name() == "coder"

    def test_select_largest_context_for_large_input(self):
        small = self._make_provider("small", max_context=4096)
        big = self._make_provider("big", max_context=128000)
        router = ModelRouter(
            providers={"small": small, "big": big},
            default="small",
            tags={"big": ["large_context"]},
        )
        selected = router.select("qa", context_size=32000)
        assert selected.model_name() == "big"

    def test_falls_back_to_default_when_no_tag_match(self):
        default = self._make_provider("default")
        router = ModelRouter(providers={"default": default}, default="default")
        selected = router.select("unknown_task_type")
        assert selected.model_name() == "default"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/krissdev/mike && python -m pytest tests/unit/test_model_provider.py -v 2>&1 | head -30`
Expected: ModuleNotFoundError — `mike.orchestrator.model_provider` does not exist

- [ ] **Step 3: Implement model_provider.py**

```python
# src/mike/orchestrator/model_provider.py
"""Model provider abstraction for Mike.

Decouples agent logic from model backend. Enables loading any free/open
model (Gemma, Qwen, Llama, Mistral, etc.) through a unified interface.
"""

from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

# Patterns that indicate code-specialized models
CODE_MODEL_PATTERNS = [
    "coder", "code", "codellama", "starcoder", "deepseek-coder",
    "wizard-coder", "phind", "magicoder",
]


@dataclass
class ModelCapabilities:
    """Describes what a model can do."""

    max_context: int = 8192
    supports_json_mode: bool = False
    supports_tool_calling: bool = False
    supports_streaming: bool = True
    is_code_specialized: bool = False


class ModelProvider(ABC):
    """Abstract base class for model providers."""

    @abstractmethod
    def generate(self, prompt: str, system: Optional[str] = None, **kwargs) -> str:
        """Generate text from a prompt."""
        ...

    @abstractmethod
    def generate_json(self, prompt: str, system: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Generate and parse JSON from a prompt."""
        ...

    @abstractmethod
    def capabilities(self) -> ModelCapabilities:
        """Return model capabilities."""
        ...

    @abstractmethod
    def model_name(self) -> str:
        """Return the model identifier."""
        ...


def _extract_json(text: str) -> Dict[str, Any]:
    """Extract JSON from text, handling markdown code fences."""
    # Try direct parse first
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code fence
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Try finding first { ... } block
    brace_start = text.find("{")
    brace_end = text.rfind("}")
    if brace_start != -1 and brace_end > brace_start:
        try:
            return json.loads(text[brace_start : brace_end + 1])
        except json.JSONDecodeError:
            pass

    logger.warning(f"Could not extract JSON from response: {text[:100]}...")
    return {}


def _is_code_model(model: str) -> bool:
    """Check if a model name indicates code specialization."""
    model_lower = model.lower()
    return any(pattern in model_lower for pattern in CODE_MODEL_PATTERNS)


class OllamaProvider(ModelProvider):
    """Provider for any Ollama-hosted model."""

    def __init__(
        self,
        model: str,
        endpoint: str = "http://localhost:11434",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: float = 120.0,
    ):
        self._model = model
        self._endpoint = endpoint.rstrip("/")
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._timeout = timeout

    def generate(self, prompt: str, system: Optional[str] = None, **kwargs) -> str:
        body: Dict[str, Any] = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", self._temperature),
                "num_predict": kwargs.get("max_tokens", self._max_tokens),
            },
        }
        if system:
            body["system"] = system

        response = httpx.post(
            f"{self._endpoint}/api/generate",
            json=body,
            timeout=self._timeout,
        )
        response.raise_for_status()
        return response.json()["response"]

    def generate_json(self, prompt: str, system: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        raw = self.generate(prompt, system=system, **kwargs)
        return _extract_json(raw)

    def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            max_context=8192,
            supports_json_mode=False,
            supports_tool_calling=False,
            supports_streaming=True,
            is_code_specialized=_is_code_model(self._model),
        )

    def model_name(self) -> str:
        return self._model


class OpenAICompatibleProvider(ModelProvider):
    """Provider for OpenAI-compatible APIs (vLLM, LM Studio, Together, OpenRouter)."""

    def __init__(
        self,
        model: str,
        endpoint: str,
        api_key: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: float = 120.0,
    ):
        self._model = model
        self._endpoint = endpoint.rstrip("/")
        self._api_key = api_key
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._timeout = timeout

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def generate(self, prompt: str, system: Optional[str] = None, **kwargs) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        body = {
            "model": self._model,
            "messages": messages,
            "temperature": kwargs.get("temperature", self._temperature),
            "max_tokens": kwargs.get("max_tokens", self._max_tokens),
        }

        response = httpx.post(
            f"{self._endpoint}/chat/completions",
            json=body,
            headers=self._headers(),
            timeout=self._timeout,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    def generate_json(self, prompt: str, system: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        raw = self.generate(prompt, system=system, **kwargs)
        return _extract_json(raw)

    def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            max_context=8192,
            supports_json_mode=True,
            supports_tool_calling=False,
            supports_streaming=True,
            is_code_specialized=_is_code_model(self._model),
        )

    def model_name(self) -> str:
        return self._model


class ModelRouter:
    """Task-aware model selection.

    Selects the best model for a given task based on tags and capabilities.
    """

    # Task types that benefit from code-specialized models
    CODE_TASKS = {"code_generation", "refactor", "rebuild", "code_review"}

    def __init__(
        self,
        providers: Dict[str, ModelProvider],
        default: str,
        tags: Optional[Dict[str, List[str]]] = None,
    ):
        self._providers = providers
        self._default = default
        self._tags = tags or {}

    def select(self, task_type: str, context_size: int = 0) -> ModelProvider:
        """Select best model for a task."""
        # If context is large, prefer large-context model
        if context_size > 16000:
            for name, provider in self._providers.items():
                if (
                    "large_context" in self._tags.get(name, [])
                    and provider.capabilities().max_context >= context_size
                ):
                    return provider

        # If code task, prefer code-specialized model
        if task_type in self.CODE_TASKS:
            for name, provider in self._providers.items():
                if "code" in self._tags.get(name, []):
                    return provider

        # Default
        return self._providers[self._default]

    def get(self, name: str) -> Optional[ModelProvider]:
        """Get a provider by name."""
        return self._providers.get(name)

    def list_providers(self) -> List[str]:
        """List all registered provider names."""
        return list(self._providers.keys())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/krissdev/mike && python -m pytest tests/unit/test_model_provider.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/krissdev/mike
git add src/mike/orchestrator/model_provider.py tests/unit/test_model_provider.py
git commit -m "feat: add ModelProvider abstraction with Ollama and OpenAI-compatible backends"
```

---

## Task 2: ContextEngine

**Files:**
- Create: `src/mike/orchestrator/context_engine.py`
- Create: `tests/unit/test_context_engine.py`

Depends on existing `VectorStore`, `EmbeddingService`, `DependencyGraphBuilder`, `ExecutionMemory`.

- [ ] **Step 1: Write failing tests for ContextEngine**

```python
# tests/unit/test_context_engine.py
"""Unit tests for ContextEngine."""

import json
import pytest
from unittest.mock import MagicMock, patch

from mike.orchestrator.context_engine import ContextEngine, ContextBundle


@pytest.fixture
def mock_embedding_service():
    svc = MagicMock()
    svc.embed.return_value = [0.1] * 1024
    svc.dimension = 1024
    return svc


@pytest.fixture
def mock_vector_store():
    store = MagicMock()
    store.search.return_value = [
        {
            "id": "chunk_0",
            "content": "def hello(): pass",
            "metadata": {"file_path": "src/main.py", "language": "python", "start_line": 1, "end_line": 3},
            "distance": 0.15,
        },
        {
            "id": "chunk_1",
            "content": "def world(): pass",
            "metadata": {"file_path": "src/utils.py", "language": "python", "start_line": 10, "end_line": 15},
            "distance": 0.25,
        },
    ]
    return store


@pytest.fixture
def mock_graph_builder():
    builder = MagicMock()
    builder.get_neighbors.return_value = {"src/helpers.py"}
    return builder


@pytest.fixture
def mock_execution_memory():
    memory = MagicMock()
    memory.failed_approaches = {"qa": ["bad approach: it failed"]}
    memory.successful_patterns = {"qa": [{"query": "what", "result_keys": ["answer"]}]}
    memory.get_learnings.return_value = ["Use specific file paths"]
    memory.get_average_iterations.return_value = 1.5
    return memory


class TestContextBundle:
    """Test ContextBundle dataclass."""

    def test_create_bundle(self):
        bundle = ContextBundle(
            query="How does auth work?",
            agent_type="qa",
            semantic_chunks=[{"content": "test"}],
            structural_context={"files": []},
            execution_memory={"failed_approaches": []},
            shared_context={},
            token_budget=8000,
            estimated_tokens=500,
            metadata={},
        )
        assert bundle.query == "How does auth work?"
        assert len(bundle.semantic_chunks) == 1

    def test_to_dict(self):
        bundle = ContextBundle(
            query="test", agent_type="qa",
            semantic_chunks=[], structural_context={},
            execution_memory={}, shared_context={},
            token_budget=8000, estimated_tokens=0, metadata={},
        )
        d = bundle.to_dict()
        assert d["query"] == "test"
        assert "token_budget" in d


class TestContextEngine:
    """Test ContextEngine assembly pipeline."""

    def test_build_returns_context_bundle(
        self, mock_vector_store, mock_embedding_service, mock_graph_builder, mock_execution_memory
    ):
        engine = ContextEngine(
            vector_store=mock_vector_store,
            embedding_service=mock_embedding_service,
            graph_builder=mock_graph_builder,
            execution_memory=mock_execution_memory,
        )
        bundle = engine.build(
            query="How does auth work?",
            agent_type="qa",
            session_id="session123",
        )
        assert isinstance(bundle, ContextBundle)
        assert bundle.query == "How does auth work?"
        assert bundle.agent_type == "qa"

    def test_semantic_retrieval_embeds_query(
        self, mock_vector_store, mock_embedding_service
    ):
        engine = ContextEngine(
            vector_store=mock_vector_store,
            embedding_service=mock_embedding_service,
        )
        engine.build(query="test query", agent_type="qa", session_id="s1")

        mock_embedding_service.embed.assert_called_once_with("test query")
        mock_vector_store.search.assert_called_once()

    def test_semantic_chunks_included(
        self, mock_vector_store, mock_embedding_service
    ):
        engine = ContextEngine(
            vector_store=mock_vector_store,
            embedding_service=mock_embedding_service,
        )
        bundle = engine.build(query="test", agent_type="qa", session_id="s1")

        assert len(bundle.semantic_chunks) == 2
        assert bundle.semantic_chunks[0]["content"] == "def hello(): pass"

    def test_graph_expansion_fetches_neighbors(
        self, mock_vector_store, mock_embedding_service, mock_graph_builder
    ):
        engine = ContextEngine(
            vector_store=mock_vector_store,
            embedding_service=mock_embedding_service,
            graph_builder=mock_graph_builder,
        )
        bundle = engine.build(query="test", agent_type="qa", session_id="s1")

        mock_graph_builder.get_neighbors.assert_called()
        assert "src/helpers.py" in bundle.structural_context.get("expanded_files", [])

    def test_skip_structural_when_disabled(
        self, mock_vector_store, mock_embedding_service, mock_graph_builder
    ):
        engine = ContextEngine(
            vector_store=mock_vector_store,
            embedding_service=mock_embedding_service,
            graph_builder=mock_graph_builder,
        )
        bundle = engine.build(
            query="test", agent_type="qa", session_id="s1",
            include_structural=False,
        )

        mock_graph_builder.get_neighbors.assert_not_called()
        assert bundle.structural_context == {}

    def test_skip_semantic_when_disabled(
        self, mock_vector_store, mock_embedding_service
    ):
        engine = ContextEngine(
            vector_store=mock_vector_store,
            embedding_service=mock_embedding_service,
        )
        bundle = engine.build(
            query="test", agent_type="qa", session_id="s1",
            include_semantic=False,
        )

        mock_embedding_service.embed.assert_not_called()
        assert bundle.semantic_chunks == []

    def test_execution_memory_included(
        self, mock_vector_store, mock_embedding_service, mock_execution_memory
    ):
        engine = ContextEngine(
            vector_store=mock_vector_store,
            embedding_service=mock_embedding_service,
            execution_memory=mock_execution_memory,
        )
        bundle = engine.build(query="test", agent_type="qa", session_id="s1")

        assert "failed_approaches" in bundle.execution_memory
        assert "successful_patterns" in bundle.execution_memory

    def test_token_budget_estimation(
        self, mock_vector_store, mock_embedding_service
    ):
        engine = ContextEngine(
            vector_store=mock_vector_store,
            embedding_service=mock_embedding_service,
        )
        bundle = engine.build(
            query="test", agent_type="qa", session_id="s1",
            token_budget=8000,
        )

        assert bundle.token_budget == 8000
        assert bundle.estimated_tokens > 0

    def test_works_without_optional_dependencies(
        self, mock_vector_store, mock_embedding_service
    ):
        """Engine works with just vector store and embedding service."""
        engine = ContextEngine(
            vector_store=mock_vector_store,
            embedding_service=mock_embedding_service,
        )
        bundle = engine.build(query="test", agent_type="qa", session_id="s1")

        assert isinstance(bundle, ContextBundle)
        assert bundle.structural_context == {}
        assert bundle.execution_memory == {}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/krissdev/mike && python -m pytest tests/unit/test_context_engine.py -v 2>&1 | head -20`
Expected: ModuleNotFoundError — `mike.orchestrator.context_engine` does not exist

- [ ] **Step 3: Implement context_engine.py**

```python
# src/mike/orchestrator/context_engine.py
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
        """Convert to dictionary for agent consumption."""
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
        """Assemble context for an agent execution."""
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

        # Build bundle
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

    def _retrieve_semantic(
        self, query: str, session_id: str, top_k: int
    ) -> List[Dict[str, Any]]:
        """Embed query and search vector store."""
        query_embedding = self._embedding_service.embed(query)
        results = self._vector_store.search(
            query_embedding=query_embedding,
            session_id=session_id,
            n_results=top_k,
        )
        return results

    def _expand_graph(
        self, referenced_files: Set[Optional[str]], chunk_count: int
    ) -> Dict[str, Any]:
        """Fetch 1-hop neighbors for referenced files."""
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
        """Pull execution memory for this agent type."""
        mem = self._execution_memory
        return {
            "failed_approaches": mem.failed_approaches.get(agent_type, []),
            "successful_patterns": mem.successful_patterns.get(agent_type, []),
            "learnings": mem.get_learnings(agent_type) if hasattr(mem, "get_learnings") else [],
            "average_iterations": mem.get_average_iterations(agent_type) if hasattr(mem, "get_average_iterations") else 0.0,
        }

    def _estimate_tokens(self, bundle: ContextBundle) -> int:
        """Estimate token count. ~4 chars per token."""
        total = len(json.dumps(bundle.to_dict()))
        return total // 4

    def _trim_to_budget(self, bundle: ContextBundle, budget: int) -> None:
        """Trim context to fit token budget.

        Priority (lowest trimmed first):
        1. shared_context
        2. structural_context
        3. execution_memory
        4. semantic_chunks (never below 2)
        """
        # Trim shared context first
        if self._estimate_tokens(bundle) > budget and bundle.shared_context:
            bundle.shared_context = {}
            bundle.estimated_tokens = self._estimate_tokens(bundle)

        # Trim structural context
        if self._estimate_tokens(bundle) > budget and bundle.structural_context:
            bundle.structural_context = {}
            bundle.estimated_tokens = self._estimate_tokens(bundle)

        # Trim execution memory
        if self._estimate_tokens(bundle) > budget and bundle.execution_memory:
            bundle.execution_memory = {}
            bundle.estimated_tokens = self._estimate_tokens(bundle)

        # Trim semantic chunks (keep at least 2)
        while self._estimate_tokens(bundle) > budget and len(bundle.semantic_chunks) > 2:
            bundle.semantic_chunks.pop()
            bundle.estimated_tokens = self._estimate_tokens(bundle)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/krissdev/mike && python -m pytest tests/unit/test_context_engine.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/krissdev/mike
git add src/mike/orchestrator/context_engine.py tests/unit/test_context_engine.py
git commit -m "feat: add ContextEngine with semantic retrieval, graph expansion, token budgeting"
```

---

## Task 3: Planner (Progressive Planning Architecture)

**Files:**
- Create: `src/mike/orchestrator/planner.py`
- Create: `tests/unit/test_planner.py`

Depends on `ModelProvider` from Task 1.

- [ ] **Step 1: Write failing tests for planner types and IntentClassifier**

```python
# tests/unit/test_planner.py
"""Unit tests for Progressive Planning Architecture."""

import json
import pytest
from unittest.mock import MagicMock

from mike.orchestrator.planner import (
    Complexity,
    IntentResult,
    PlanNode,
    ExecutionPlan,
    IntentClassifier,
    StrategyRouter,
    RulePlanner,
    TemplatePlanner,
    LLMPlanner,
)
from mike.orchestrator.model_provider import ModelProvider


# --- Data types ---

class TestComplexity:
    def test_enum_values(self):
        assert Complexity.SIMPLE == "simple"
        assert Complexity.MULTI_STEP == "multi_step"
        assert Complexity.OPEN_ENDED == "open_ended"


class TestIntentResult:
    def test_create(self):
        result = IntentResult(
            intent="explain_code",
            complexity=Complexity.SIMPLE,
            confidence=0.95,
            parameters={"file": "main.py"},
        )
        assert result.intent == "explain_code"
        assert result.complexity == Complexity.SIMPLE


class TestPlanNode:
    def test_create(self):
        node = PlanNode(
            id="step1", agent_type="qa",
            description="Analyze code", depends_on=[],
            parameters={"focus": "auth"},
        )
        assert node.id == "step1"
        assert node.depends_on == []

    def test_condition_defaults_to_none(self):
        node = PlanNode(id="s", agent_type="qa", description="x", depends_on=[], parameters={})
        assert node.condition is None


class TestExecutionPlan:
    def test_create(self):
        plan = ExecutionPlan(
            nodes=[PlanNode(id="a", agent_type="qa", description="test", depends_on=[], parameters={})],
            reasoning="Simple query",
            planner_type="rule",
        )
        assert len(plan.nodes) == 1
        assert plan.planner_type == "rule"

    def test_node_ids(self):
        plan = ExecutionPlan(
            nodes=[
                PlanNode(id="a", agent_type="qa", description="x", depends_on=[], parameters={}),
                PlanNode(id="b", agent_type="docs", description="y", depends_on=["a"], parameters={}),
            ],
            reasoning="test", planner_type="template",
        )
        assert plan.node_ids() == ["a", "b"]

    def test_is_valid_dag_accepts_valid(self):
        plan = ExecutionPlan(
            nodes=[
                PlanNode(id="a", agent_type="qa", description="x", depends_on=[], parameters={}),
                PlanNode(id="b", agent_type="docs", description="y", depends_on=["a"], parameters={}),
            ],
            reasoning="test", planner_type="template",
        )
        assert plan.is_valid_dag() is True

    def test_is_valid_dag_rejects_cycle(self):
        plan = ExecutionPlan(
            nodes=[
                PlanNode(id="a", agent_type="qa", description="x", depends_on=["b"], parameters={}),
                PlanNode(id="b", agent_type="docs", description="y", depends_on=["a"], parameters={}),
            ],
            reasoning="test", planner_type="template",
        )
        assert plan.is_valid_dag() is False

    def test_is_valid_dag_rejects_missing_dependency(self):
        plan = ExecutionPlan(
            nodes=[
                PlanNode(id="a", agent_type="qa", description="x", depends_on=["nonexistent"], parameters={}),
            ],
            reasoning="test", planner_type="template",
        )
        assert plan.is_valid_dag() is False


# --- IntentClassifier ---

class TestIntentClassifier:
    def _make_mock_provider(self, json_response):
        provider = MagicMock(spec=ModelProvider)
        provider.generate_json.return_value = json_response
        return provider

    def test_classify_returns_intent_result(self):
        provider = self._make_mock_provider({
            "intent": "explain_code",
            "complexity": "simple",
            "confidence": 0.9,
            "parameters": {},
        })
        classifier = IntentClassifier(provider)
        result = classifier.classify("What does this function do?")

        assert isinstance(result, IntentResult)
        assert result.intent == "explain_code"
        assert result.complexity == Complexity.SIMPLE

    def test_classify_falls_back_on_invalid_json(self):
        provider = MagicMock(spec=ModelProvider)
        provider.generate_json.return_value = {}
        classifier = IntentClassifier(provider)
        result = classifier.classify("tell me about the code")

        assert isinstance(result, IntentResult)
        assert result.intent == "general_qa"
        assert result.confidence < 1.0

    def test_classify_falls_back_on_exception(self):
        provider = MagicMock(spec=ModelProvider)
        provider.generate_json.side_effect = Exception("connection refused")
        classifier = IntentClassifier(provider)
        result = classifier.classify("explain auth")

        assert isinstance(result, IntentResult)
        assert result.intent == "explain_code"

    def test_keyword_fallback_detects_docs(self):
        provider = MagicMock(spec=ModelProvider)
        provider.generate_json.side_effect = Exception("offline")
        classifier = IntentClassifier(provider)
        result = classifier.classify("generate documentation for this project")

        assert result.intent == "generate_docs"

    def test_keyword_fallback_detects_refactor(self):
        provider = MagicMock(spec=ModelProvider)
        provider.generate_json.side_effect = Exception("offline")
        classifier = IntentClassifier(provider)
        result = classifier.classify("refactor the authentication module")

        assert result.intent == "refactor"


# --- RulePlanner ---

class TestRulePlanner:
    def test_simple_qa_produces_single_node(self):
        planner = RulePlanner()
        intent = IntentResult(intent="explain_code", complexity=Complexity.SIMPLE, confidence=0.9, parameters={})
        plan = planner.plan(intent)

        assert len(plan.nodes) == 1
        assert plan.nodes[0].agent_type == "qa"
        assert plan.planner_type == "rule"

    def test_docs_intent_maps_to_docs_agent(self):
        planner = RulePlanner()
        intent = IntentResult(intent="generate_docs", complexity=Complexity.SIMPLE, confidence=0.9, parameters={})
        plan = planner.plan(intent)

        assert plan.nodes[0].agent_type == "docs"

    def test_unknown_intent_defaults_to_qa(self):
        planner = RulePlanner()
        intent = IntentResult(intent="totally_unknown", complexity=Complexity.SIMPLE, confidence=0.5, parameters={})
        plan = planner.plan(intent)

        assert plan.nodes[0].agent_type == "qa"


# --- TemplatePlanner ---

class TestTemplatePlanner:
    def test_architecture_review_template(self):
        planner = TemplatePlanner()
        intent = IntentResult(intent="architecture_review", complexity=Complexity.MULTI_STEP, confidence=0.9, parameters={})
        plan = planner.plan(intent)

        assert len(plan.nodes) >= 2
        assert plan.planner_type == "template"
        assert plan.is_valid_dag() is True

    def test_full_documentation_template(self):
        planner = TemplatePlanner()
        intent = IntentResult(intent="full_documentation", complexity=Complexity.MULTI_STEP, confidence=0.9, parameters={})
        plan = planner.plan(intent)

        assert len(plan.nodes) >= 3
        assert plan.is_valid_dag() is True

    def test_parameters_merged_into_nodes(self):
        planner = TemplatePlanner()
        intent = IntentResult(
            intent="architecture_review", complexity=Complexity.MULTI_STEP,
            confidence=0.9, parameters={"target_dir": "src/auth"},
        )
        plan = planner.plan(intent)

        for node in plan.nodes:
            assert "target_dir" in node.parameters

    def test_unknown_template_falls_back_to_single_node(self):
        planner = TemplatePlanner()
        intent = IntentResult(intent="unknown_workflow", complexity=Complexity.MULTI_STEP, confidence=0.5, parameters={})
        plan = planner.plan(intent)

        assert len(plan.nodes) >= 1
        assert plan.is_valid_dag() is True


# --- LLMPlanner ---

class TestLLMPlanner:
    def _make_mock_provider(self, json_response):
        provider = MagicMock(spec=ModelProvider)
        provider.generate_json.return_value = json_response
        return provider

    def test_valid_llm_plan(self):
        provider = self._make_mock_provider({
            "reasoning": "Need to analyze then fix",
            "steps": [
                {"id": "analyze", "agent": "qa", "description": "Find the issue", "depends_on": [], "parameters": {}},
                {"id": "fix", "agent": "refactor", "description": "Fix it", "depends_on": ["analyze"], "parameters": {}},
            ],
        })
        planner = LLMPlanner(provider)
        intent = IntentResult(intent="complex_task", complexity=Complexity.OPEN_ENDED, confidence=0.8, parameters={})
        plan = planner.plan(intent)

        assert len(plan.nodes) == 2
        assert plan.planner_type == "llm"
        assert plan.is_valid_dag() is True

    def test_rejects_invalid_agent_type(self):
        provider = self._make_mock_provider({
            "reasoning": "test",
            "steps": [
                {"id": "s1", "agent": "INVALID_AGENT", "description": "bad", "depends_on": [], "parameters": {}},
            ],
        })
        planner = LLMPlanner(provider)
        intent = IntentResult(intent="test", complexity=Complexity.OPEN_ENDED, confidence=0.8, parameters={})
        plan = planner.plan(intent)

        # Should fall back to single-node plan
        assert plan.planner_type == "llm_fallback"
        assert plan.is_valid_dag() is True

    def test_rejects_cyclic_plan(self):
        provider = self._make_mock_provider({
            "reasoning": "test",
            "steps": [
                {"id": "a", "agent": "qa", "description": "x", "depends_on": ["b"], "parameters": {}},
                {"id": "b", "agent": "qa", "description": "y", "depends_on": ["a"], "parameters": {}},
            ],
        })
        planner = LLMPlanner(provider)
        intent = IntentResult(intent="test", complexity=Complexity.OPEN_ENDED, confidence=0.8, parameters={})
        plan = planner.plan(intent)

        assert plan.planner_type == "llm_fallback"

    def test_rejects_too_many_nodes(self):
        provider = self._make_mock_provider({
            "reasoning": "test",
            "steps": [
                {"id": f"s{i}", "agent": "qa", "description": f"step {i}", "depends_on": [], "parameters": {}}
                for i in range(6)
            ],
        })
        planner = LLMPlanner(provider)
        intent = IntentResult(intent="test", complexity=Complexity.OPEN_ENDED, confidence=0.8, parameters={})
        plan = planner.plan(intent)

        assert plan.planner_type == "llm_fallback"

    def test_falls_back_on_llm_error(self):
        provider = MagicMock(spec=ModelProvider)
        provider.generate_json.side_effect = Exception("timeout")
        planner = LLMPlanner(provider)
        intent = IntentResult(intent="test", complexity=Complexity.OPEN_ENDED, confidence=0.8, parameters={})
        plan = planner.plan(intent)

        assert plan.planner_type == "llm_fallback"
        assert plan.is_valid_dag() is True


# --- StrategyRouter ---

class TestStrategyRouter:
    def test_routes_simple_to_rule_planner(self):
        rule = MagicMock(spec=RulePlanner)
        rule.plan.return_value = ExecutionPlan(
            nodes=[PlanNode(id="a", agent_type="qa", description="x", depends_on=[], parameters={})],
            reasoning="simple", planner_type="rule",
        )
        router = StrategyRouter(rule_planner=rule, template_planner=MagicMock(), llm_planner=MagicMock())
        intent = IntentResult(intent="explain_code", complexity=Complexity.SIMPLE, confidence=0.9, parameters={})

        plan = router.plan(intent)
        rule.plan.assert_called_once_with(intent)
        assert plan.planner_type == "rule"

    def test_routes_multi_step_to_template_planner(self):
        template = MagicMock(spec=TemplatePlanner)
        template.plan.return_value = ExecutionPlan(
            nodes=[], reasoning="template", planner_type="template",
        )
        router = StrategyRouter(rule_planner=MagicMock(), template_planner=template, llm_planner=MagicMock())
        intent = IntentResult(intent="architecture_review", complexity=Complexity.MULTI_STEP, confidence=0.9, parameters={})

        router.plan(intent)
        template.plan.assert_called_once_with(intent)

    def test_routes_open_ended_to_llm_planner(self):
        llm = MagicMock(spec=LLMPlanner)
        llm.plan.return_value = ExecutionPlan(
            nodes=[], reasoning="llm", planner_type="llm",
        )
        router = StrategyRouter(rule_planner=MagicMock(), template_planner=MagicMock(), llm_planner=llm)
        intent = IntentResult(intent="complex", complexity=Complexity.OPEN_ENDED, confidence=0.8, parameters={})

        router.plan(intent)
        llm.plan.assert_called_once_with(intent)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/krissdev/mike && python -m pytest tests/unit/test_planner.py -v 2>&1 | head -20`
Expected: ModuleNotFoundError

- [ ] **Step 3: Implement planner.py**

```python
# src/mike/orchestrator/planner.py
"""Progressive Planning Architecture for Mike.

Three-tier planning system:
- RulePlanner: direct intent-to-agent mapping for simple queries
- TemplatePlanner: parametric workflow templates for known multi-step patterns
- LLMPlanner: constrained LLM composition for novel queries

IntentClassifier uses LLM to classify query intent and complexity,
with keyword-based fallback when LLM is unavailable.
"""

from __future__ import annotations

import copy
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

import networkx as nx

from .model_provider import ModelProvider

logger = logging.getLogger(__name__)

ALLOWED_AGENTS = {"qa", "docs", "refactor", "rebuild"}
MAX_LLM_PLAN_NODES = 4


class Complexity(str, Enum):
    SIMPLE = "simple"
    MULTI_STEP = "multi_step"
    OPEN_ENDED = "open_ended"


@dataclass
class IntentResult:
    intent: str
    complexity: Complexity
    confidence: float
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlanNode:
    id: str
    agent_type: str
    description: str
    depends_on: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    condition: Optional[str] = None


@dataclass
class ExecutionPlan:
    nodes: List[PlanNode]
    reasoning: str
    planner_type: str
    estimated_duration: Optional[str] = None

    def node_ids(self) -> List[str]:
        return [n.id for n in self.nodes]

    def is_valid_dag(self) -> bool:
        """Check that nodes form a valid DAG with existing dependencies."""
        ids = set(self.node_ids())
        # Check all depends_on references exist
        for node in self.nodes:
            for dep in node.depends_on:
                if dep not in ids:
                    return False
        # Check acyclic
        g = nx.DiGraph()
        for node in self.nodes:
            g.add_node(node.id)
            for dep in node.depends_on:
                g.add_edge(dep, node.id)
        return nx.is_directed_acyclic_graph(g)


# --- Keyword fallback (preserves existing TaskRouter logic) ---

_KEYWORD_RULES = [
    (["document", "readme", "architecture doc", "api reference", "generate docs", "create documentation"], "generate_docs", Complexity.SIMPLE),
    (["refactor", "improve", "code smell", "clean up", "optimize", "restructure", "simplify"], "refactor", Complexity.SIMPLE),
    (["scaffold", "generate project", "create app", "new project", "template", "boilerplate", "rebuild"], "rebuild_project", Complexity.MULTI_STEP),
    (["explain", "how does", "what does", "where is", "find"], "explain_code", Complexity.SIMPLE),
    (["compare", "difference between", "vs"], "compare", Complexity.SIMPLE),
    (["fix", "bug", "error", "broken"], "fix_bug", Complexity.MULTI_STEP),
    (["review", "audit", "assess", "analyze architecture", "health"], "architecture_review", Complexity.MULTI_STEP),
    (["full doc", "all documentation", "complete docs"], "full_documentation", Complexity.MULTI_STEP),
]


def _keyword_classify(query: str) -> IntentResult:
    """Classify intent using keyword matching (fallback)."""
    q = query.lower()
    for keywords, intent, complexity in _KEYWORD_RULES:
        if any(kw in q for kw in keywords):
            return IntentResult(intent=intent, complexity=complexity, confidence=0.6, parameters={})
    return IntentResult(intent="general_qa", complexity=Complexity.SIMPLE, confidence=0.4, parameters={})


# --- IntentClassifier ---

_INTENT_PROMPT = """Classify the following user query about a codebase.

Query: "{query}"

Respond with ONLY a JSON object:
{{
  "intent": "<one of: explain_code, find_code, architecture_review, refactor, generate_docs, full_documentation, rebuild_project, fix_bug, compare, general_qa>",
  "complexity": "<one of: simple, multi_step, open_ended>",
  "confidence": <float 0.0-1.0>,
  "parameters": {{<extracted entities like file names, function names, concepts>}}
}}"""


class IntentClassifier:
    """Classifies user queries using LLM with keyword fallback."""

    def __init__(self, model_provider: ModelProvider):
        self._provider = model_provider

    def classify(self, query: str) -> IntentResult:
        try:
            raw = self._provider.generate_json(
                _INTENT_PROMPT.format(query=query),
                system="You are a query classifier. Return only valid JSON.",
            )
            if not raw or "intent" not in raw:
                return _keyword_classify(query)

            complexity_str = raw.get("complexity", "simple")
            try:
                complexity = Complexity(complexity_str)
            except ValueError:
                complexity = Complexity.SIMPLE

            return IntentResult(
                intent=raw["intent"],
                complexity=complexity,
                confidence=float(raw.get("confidence", 0.7)),
                parameters=raw.get("parameters", {}),
            )
        except Exception as e:
            logger.warning(f"LLM intent classification failed, using keyword fallback: {e}")
            return _keyword_classify(query)


# --- RulePlanner ---

_INTENT_TO_AGENT = {
    "explain_code": "qa",
    "find_code": "qa",
    "general_qa": "qa",
    "compare": "qa",
    "generate_docs": "docs",
    "refactor": "refactor",
    "rebuild_project": "rebuild",
    "fix_bug": "refactor",
}


class RulePlanner:
    """Direct intent-to-single-agent mapping for simple queries."""

    def plan(self, intent: IntentResult) -> ExecutionPlan:
        agent_type = _INTENT_TO_AGENT.get(intent.intent, "qa")
        node = PlanNode(
            id="main",
            agent_type=agent_type,
            description=f"Handle {intent.intent} query",
            depends_on=[],
            parameters=intent.parameters.copy(),
        )
        return ExecutionPlan(
            nodes=[node],
            reasoning=f"Simple {intent.intent} query routed to {agent_type} agent",
            planner_type="rule",
        )


# --- TemplatePlanner ---

def _build_templates() -> Dict[str, List[PlanNode]]:
    """Build parametric workflow templates."""
    return {
        "architecture_review": [
            PlanNode(id="scan", agent_type="qa", description="Analyze codebase structure",
                     depends_on=[], parameters={"focus": "architecture"}),
            PlanNode(id="health", agent_type="refactor", description="Assess architecture health",
                     depends_on=["scan"], parameters={"focus": "health_scoring"}),
            PlanNode(id="suggest", agent_type="refactor", description="Generate improvement suggestions",
                     depends_on=["health"], parameters={"focus": "suggestions"}),
        ],
        "full_documentation": [
            PlanNode(id="scan", agent_type="qa", description="Survey codebase",
                     depends_on=[], parameters={}),
            PlanNode(id="readme", agent_type="docs", description="Generate README",
                     depends_on=["scan"], parameters={"doc_type": "readme"}),
            PlanNode(id="arch", agent_type="docs", description="Generate architecture docs",
                     depends_on=["scan"], parameters={"doc_type": "architecture"}),
            PlanNode(id="api", agent_type="docs", description="Generate API reference",
                     depends_on=["scan"], parameters={"doc_type": "api"}),
        ],
        "refactor_with_review": [
            PlanNode(id="analyze", agent_type="refactor", description="Analyze code smells",
                     depends_on=[], parameters={}),
            PlanNode(id="suggest", agent_type="refactor", description="Generate refactoring plan",
                     depends_on=["analyze"], parameters={}),
            PlanNode(id="verify", agent_type="qa", description="Verify suggestions are safe",
                     depends_on=["suggest"], parameters={"focus": "safety_check"},
                     condition="if_suggestions_exist"),
        ],
        "rebuild_project": [
            PlanNode(id="analyze", agent_type="qa", description="Understand existing architecture",
                     depends_on=[], parameters={"depth": "comprehensive"}),
            PlanNode(id="plan", agent_type="rebuild", description="Generate build plan",
                     depends_on=["analyze"], parameters={}),
            PlanNode(id="scaffold", agent_type="rebuild", description="Scaffold project",
                     depends_on=["plan"], parameters={}),
        ],
        "fix_bug": [
            PlanNode(id="locate", agent_type="qa", description="Locate bug in codebase",
                     depends_on=[], parameters={"focus": "bug_location"}),
            PlanNode(id="fix", agent_type="refactor", description="Suggest fix",
                     depends_on=["locate"], parameters={}),
        ],
    }


class TemplatePlanner:
    """Parametric workflow templates for known multi-step patterns."""

    def __init__(self):
        self._templates = _build_templates()

    def plan(self, intent: IntentResult) -> ExecutionPlan:
        template = self._templates.get(intent.intent)
        if template is None:
            # Fall back to single-node plan using rule mapping
            agent_type = _INTENT_TO_AGENT.get(intent.intent, "qa")
            return ExecutionPlan(
                nodes=[PlanNode(id="main", agent_type=agent_type, description=f"Handle {intent.intent}",
                                depends_on=[], parameters=intent.parameters.copy())],
                reasoning=f"No template for {intent.intent}, using single agent",
                planner_type="template",
            )

        # Deep copy template and merge intent parameters
        nodes = []
        for node in template:
            new_node = PlanNode(
                id=node.id,
                agent_type=node.agent_type,
                description=node.description,
                depends_on=list(node.depends_on),
                parameters={**node.parameters, **intent.parameters},
                condition=node.condition,
            )
            nodes.append(new_node)

        return ExecutionPlan(
            nodes=nodes,
            reasoning=f"Using {intent.intent} template with {len(nodes)} steps",
            planner_type="template",
        )


# --- LLMPlanner ---

_LLM_PLANNING_PROMPT = """You are a planning engine. Given a user query about a codebase,
create an execution plan using ONLY these available agents:

Available agents:
- qa: Answer questions, explain code, find code locations
- docs: Generate documentation (README, architecture, API reference)
- refactor: Analyze code quality, suggest improvements, detect smells
- rebuild: Scaffold new projects, generate code, create boilerplate

Constraints:
- Maximum {max_nodes} steps
- Must form a valid DAG (no cycles)
- Each step must specify depends_on as a list of step IDs

Query: "{query}"

Respond with ONLY a JSON object:
{{
  "reasoning": "<why this plan>",
  "steps": [
    {{"id": "<unique_id>", "agent": "<agent_type>", "description": "<what>", "depends_on": [], "parameters": {{}}}}
  ]
}}"""


class LLMPlanner:
    """Constrained LLM composition for open-ended queries.

    The LLM selects and orders agents from the known set — it does NOT
    invent new agent types. Plans are validated post-generation.
    """

    def __init__(self, model_provider: ModelProvider):
        self._provider = model_provider

    def plan(self, intent: IntentResult) -> ExecutionPlan:
        try:
            raw = self._provider.generate_json(
                _LLM_PLANNING_PROMPT.format(query=intent.intent, max_nodes=MAX_LLM_PLAN_NODES),
                system="You are a planning engine. Return only valid JSON.",
            )
            if not raw or "steps" not in raw:
                return self._fallback(intent, "LLM returned no steps")

            nodes = self._parse_steps(raw["steps"])
            plan = ExecutionPlan(
                nodes=nodes,
                reasoning=raw.get("reasoning", "LLM-generated plan"),
                planner_type="llm",
            )

            # Validate
            if not self._validate(plan):
                return self._fallback(intent, "LLM plan failed validation")

            return plan

        except Exception as e:
            logger.warning(f"LLM planning failed: {e}")
            return self._fallback(intent, str(e))

    def _parse_steps(self, steps: List[Dict[str, Any]]) -> List[PlanNode]:
        nodes = []
        for step in steps:
            nodes.append(PlanNode(
                id=step.get("id", f"step_{len(nodes)}"),
                agent_type=step.get("agent", "qa"),
                description=step.get("description", ""),
                depends_on=step.get("depends_on", []),
                parameters=step.get("parameters", {}),
            ))
        return nodes

    def _validate(self, plan: ExecutionPlan) -> bool:
        # Check node count
        if len(plan.nodes) > MAX_LLM_PLAN_NODES:
            logger.warning(f"LLM plan has {len(plan.nodes)} nodes, max is {MAX_LLM_PLAN_NODES}")
            return False

        # Check all agent types are allowed
        for node in plan.nodes:
            if node.agent_type not in ALLOWED_AGENTS:
                logger.warning(f"LLM plan contains invalid agent type: {node.agent_type}")
                return False

        # Check DAG validity
        if not plan.is_valid_dag():
            logger.warning("LLM plan is not a valid DAG")
            return False

        return True

    def _fallback(self, intent: IntentResult, reason: str) -> ExecutionPlan:
        """Fall back to single QA agent node."""
        logger.info(f"LLM planner falling back: {reason}")
        return ExecutionPlan(
            nodes=[PlanNode(
                id="main", agent_type="qa",
                description=f"Handle query (LLM planning failed: {reason})",
                depends_on=[], parameters=intent.parameters.copy(),
            )],
            reasoning=f"Fallback: {reason}",
            planner_type="llm_fallback",
        )


# --- StrategyRouter ---

class StrategyRouter:
    """Routes intent to the appropriate planner based on complexity."""

    def __init__(
        self,
        rule_planner: RulePlanner,
        template_planner: TemplatePlanner,
        llm_planner: LLMPlanner,
    ):
        self._rule = rule_planner
        self._template = template_planner
        self._llm = llm_planner

    def plan(self, intent: IntentResult) -> ExecutionPlan:
        if intent.complexity == Complexity.SIMPLE:
            return self._rule.plan(intent)
        elif intent.complexity == Complexity.MULTI_STEP:
            return self._template.plan(intent)
        else:
            return self._llm.plan(intent)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/krissdev/mike && python -m pytest tests/unit/test_planner.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/krissdev/mike
git add src/mike/orchestrator/planner.py tests/unit/test_planner.py
git commit -m "feat: add Progressive Planning Architecture with 3-tier planner system"
```

---

## Task 4: DAGExecutor

**Files:**
- Create: `src/mike/orchestrator/dag_executor.py`
- Create: `tests/unit/test_dag_executor.py`

Depends on `ContextEngine` (Task 2), `AgentRegistry` (existing), `planner.py` types (Task 3).

- [ ] **Step 1: Write failing tests for DAGExecutor**

```python
# tests/unit/test_dag_executor.py
"""Unit tests for DAGExecutor."""

import asyncio
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from mike.orchestrator.dag_executor import DAGExecutor, NodeResult, DAGResult
from mike.orchestrator.planner import PlanNode, ExecutionPlan
from mike.orchestrator.context_engine import ContextBundle


def _make_plan(*node_specs):
    """Helper: create ExecutionPlan from (id, agent_type, depends_on) tuples."""
    nodes = [
        PlanNode(id=nid, agent_type=atype, description=f"Do {nid}",
                 depends_on=deps, parameters={})
        for nid, atype, deps in node_specs
    ]
    return ExecutionPlan(nodes=nodes, reasoning="test plan", planner_type="test")


def _make_mock_agent(result=None):
    agent = MagicMock()
    agent.execute.return_value = result or {"status": "success", "data": "mock result"}
    agent.validate_result.return_value = True
    agent.requires_approval.return_value = False
    return agent


def _make_mock_registry(agents=None):
    registry = MagicMock()
    agents = agents or {}
    registry.get.side_effect = lambda t: agents.get(t.value if hasattr(t, "value") else t)
    return registry


def _make_mock_context_engine():
    engine = MagicMock()
    engine.build.return_value = ContextBundle(
        query="test", agent_type="qa",
        semantic_chunks=[], structural_context={},
        execution_memory={}, shared_context={},
        token_budget=8000, estimated_tokens=100, metadata={},
    )
    return engine


class TestNodeResult:
    def test_create(self):
        result = NodeResult(
            node_id="step1", agent_type="qa",
            status="success", result={"data": "x"},
            error=None, duration_ms=150,
        )
        assert result.status == "success"
        assert result.duration_ms == 150


class TestDAGExecutorSingleNode:
    def test_executes_single_node(self):
        plan = _make_plan(("main", "qa", []))
        agent = _make_mock_agent()
        registry = _make_mock_registry({"qa": agent})
        context_engine = _make_mock_context_engine()

        executor = DAGExecutor(agent_registry=registry, context_engine=context_engine)
        result = executor.execute_sync(plan, session_id="s1")

        assert isinstance(result, DAGResult)
        assert result.status == "success"
        assert "main" in result.node_results
        assert result.node_results["main"].status == "success"
        agent.execute.assert_called_once()


class TestDAGExecutorSequentialDependencies:
    def test_respects_dependency_order(self):
        """B depends on A; both should execute, A first."""
        plan = _make_plan(
            ("a", "qa", []),
            ("b", "refactor", ["a"]),
        )
        agent_a = _make_mock_agent({"status": "success", "data": "from_a"})
        agent_b = _make_mock_agent({"status": "success", "data": "from_b"})
        registry = _make_mock_registry({"qa": agent_a, "refactor": agent_b})
        context_engine = _make_mock_context_engine()

        executor = DAGExecutor(agent_registry=registry, context_engine=context_engine)
        result = executor.execute_sync(plan, session_id="s1")

        assert result.status == "success"
        assert result.node_results["a"].status == "success"
        assert result.node_results["b"].status == "success"

    def test_passes_predecessor_results_in_shared_context(self):
        """B should receive A's result in shared_context."""
        plan = _make_plan(
            ("a", "qa", []),
            ("b", "refactor", ["a"]),
        )
        agent_a = _make_mock_agent({"status": "success", "data": "from_a"})
        agent_b = _make_mock_agent()
        registry = _make_mock_registry({"qa": agent_a, "refactor": agent_b})
        context_engine = _make_mock_context_engine()

        executor = DAGExecutor(agent_registry=registry, context_engine=context_engine)
        executor.execute_sync(plan, session_id="s1")

        # Context engine should have been called with shared_context containing A's result
        calls = context_engine.build.call_args_list
        b_call = [c for c in calls if c[1].get("agent_type") == "refactor" or
                  (c[0] and len(c[0]) > 1 and c[0][1] == "refactor")]
        assert len(b_call) >= 1


class TestDAGExecutorParallelBranches:
    def test_independent_nodes_both_execute(self):
        """A and B have no dependencies — both should execute."""
        plan = _make_plan(
            ("a", "qa", []),
            ("b", "docs", []),
        )
        agent_qa = _make_mock_agent()
        agent_docs = _make_mock_agent()
        registry = _make_mock_registry({"qa": agent_qa, "docs": agent_docs})
        context_engine = _make_mock_context_engine()

        executor = DAGExecutor(agent_registry=registry, context_engine=context_engine)
        result = executor.execute_sync(plan, session_id="s1")

        assert result.node_results["a"].status == "success"
        assert result.node_results["b"].status == "success"


class TestDAGExecutorFailureHandling:
    def test_failed_node_cancels_dependents(self):
        """If A fails, B (depends on A) should be cancelled. C (independent) should succeed."""
        plan = _make_plan(
            ("a", "qa", []),
            ("b", "refactor", ["a"]),
            ("c", "docs", []),
        )
        failing_agent = MagicMock()
        failing_agent.execute.side_effect = Exception("boom")
        failing_agent.requires_approval.return_value = False
        ok_agent = _make_mock_agent()
        registry = _make_mock_registry({"qa": failing_agent, "refactor": ok_agent, "docs": ok_agent})
        context_engine = _make_mock_context_engine()

        executor = DAGExecutor(agent_registry=registry, context_engine=context_engine)
        result = executor.execute_sync(plan, session_id="s1")

        assert result.node_results["a"].status == "failed"
        assert result.node_results["b"].status == "cancelled"
        assert result.node_results["c"].status == "success"
        assert result.status == "partial"

    def test_missing_agent_fails_node(self):
        plan = _make_plan(("a", "nonexistent", []))
        registry = _make_mock_registry({})
        context_engine = _make_mock_context_engine()

        executor = DAGExecutor(agent_registry=registry, context_engine=context_engine)
        result = executor.execute_sync(plan, session_id="s1")

        assert result.node_results["a"].status == "failed"
        assert result.status == "failed"


class TestDAGExecutorConditions:
    def test_skips_node_when_condition_not_met(self):
        plan = ExecutionPlan(
            nodes=[
                PlanNode(id="a", agent_type="refactor", description="analyze",
                         depends_on=[], parameters={}),
                PlanNode(id="b", agent_type="qa", description="verify",
                         depends_on=["a"], parameters={},
                         condition="if_suggestions_exist"),
            ],
            reasoning="test", planner_type="test",
        )
        # A returns no suggestions
        agent_a = _make_mock_agent({"status": "success", "suggestions": []})
        agent_b = _make_mock_agent()
        registry = _make_mock_registry({"refactor": agent_a, "qa": agent_b})
        context_engine = _make_mock_context_engine()

        executor = DAGExecutor(agent_registry=registry, context_engine=context_engine)
        result = executor.execute_sync(plan, session_id="s1")

        assert result.node_results["a"].status == "success"
        assert result.node_results["b"].status == "skipped"

    def test_executes_node_when_condition_met(self):
        plan = ExecutionPlan(
            nodes=[
                PlanNode(id="a", agent_type="refactor", description="analyze",
                         depends_on=[], parameters={}),
                PlanNode(id="b", agent_type="qa", description="verify",
                         depends_on=["a"], parameters={},
                         condition="if_suggestions_exist"),
            ],
            reasoning="test", planner_type="test",
        )
        agent_a = _make_mock_agent({"status": "success", "suggestions": ["fix X", "fix Y"]})
        agent_b = _make_mock_agent()
        registry = _make_mock_registry({"refactor": agent_a, "qa": agent_b})
        context_engine = _make_mock_context_engine()

        executor = DAGExecutor(agent_registry=registry, context_engine=context_engine)
        result = executor.execute_sync(plan, session_id="s1")

        assert result.node_results["b"].status == "success"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/krissdev/mike && python -m pytest tests/unit/test_dag_executor.py -v 2>&1 | head -20`
Expected: ModuleNotFoundError

- [ ] **Step 3: Implement dag_executor.py**

```python
# src/mike/orchestrator/dag_executor.py
"""DAG-based execution engine for Mike.

Executes ExecutionPlans respecting dependencies, enabling parallel branches,
result passing between nodes, conditional execution, and cancellation propagation.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from .context_engine import ContextEngine
from .planner import ExecutionPlan, PlanNode

logger = logging.getLogger(__name__)


@dataclass
class NodeResult:
    """Result of executing a single plan node."""

    node_id: str
    agent_type: str
    status: str  # "success", "failed", "skipped", "cancelled"
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_ms: int = 0


@dataclass
class DAGResult:
    """Aggregate result of executing an entire plan."""

    plan: ExecutionPlan
    node_results: Dict[str, NodeResult] = field(default_factory=dict)
    total_duration_ms: int = 0
    status: str = "pending"  # "success", "partial", "failed"


def _evaluate_condition(condition: Optional[str], predecessor_results: Dict[str, NodeResult]) -> bool:
    """Evaluate a PlanNode condition against predecessor results."""
    if condition is None:
        return True

    if condition == "if_suggestions_exist":
        for nr in predecessor_results.values():
            if nr.result and nr.result.get("suggestions"):
                return True
        return False

    if condition == "if_needed=True":
        for nr in predecessor_results.values():
            if nr.result and nr.result.get("action_needed") is False:
                return False
        return True

    # Unknown condition — execute by default
    return True


class DAGExecutor:
    """Executes an ExecutionPlan as a DAG with topological ordering.

    Supports:
    - Parallel execution of independent branches
    - Result passing from predecessors to successors via shared_context
    - Conditional node skipping
    - Cancellation propagation on failure
    """

    def __init__(
        self,
        agent_registry: Any,
        context_engine: ContextEngine,
        max_workers: int = 4,
    ):
        self._registry = agent_registry
        self._context_engine = context_engine
        self._max_workers = max_workers

    async def execute(
        self,
        plan: ExecutionPlan,
        session_id: str,
        shared_context: Optional[Dict[str, Any]] = None,
    ) -> DAGResult:
        """Execute plan as a DAG with parallel branches."""
        start_time = time.monotonic()
        dag_result = DAGResult(plan=plan)
        node_map = {n.id: n for n in plan.nodes}

        # Build in-degree map
        in_degree: Dict[str, int] = {n.id: 0 for n in plan.nodes}
        successors: Dict[str, List[str]] = {n.id: [] for n in plan.nodes}
        for node in plan.nodes:
            for dep in node.depends_on:
                in_degree[node.id] += 1
                successors[dep].append(node.id)

        # Track failed nodes for cancellation propagation
        failed_nodes: Set[str] = set()

        # Kahn's algorithm with parallel execution per level
        ready = [nid for nid, deg in in_degree.items() if deg == 0]

        while ready:
            # Execute all ready nodes in parallel
            tasks = []
            for nid in ready:
                node = node_map[nid]

                # Check if any predecessor failed — cancel this node
                if any(dep in failed_nodes for dep in node.depends_on):
                    dag_result.node_results[nid] = NodeResult(
                        node_id=nid, agent_type=node.agent_type,
                        status="cancelled", error="Predecessor failed",
                    )
                    failed_nodes.add(nid)
                    continue

                # Check condition
                pred_results = {
                    dep: dag_result.node_results[dep]
                    for dep in node.depends_on
                    if dep in dag_result.node_results
                }
                if not _evaluate_condition(node.condition, pred_results):
                    dag_result.node_results[nid] = NodeResult(
                        node_id=nid, agent_type=node.agent_type,
                        status="skipped",
                    )
                    continue

                tasks.append(self._execute_node(node, session_id, dag_result, shared_context))

            if tasks:
                await asyncio.gather(*tasks)

            # Update failed set
            for nid in ready:
                if nid in dag_result.node_results and dag_result.node_results[nid].status == "failed":
                    failed_nodes.add(nid)

            # Find next ready nodes
            next_ready = []
            for nid in ready:
                for succ in successors.get(nid, []):
                    in_degree[succ] -= 1
                    if in_degree[succ] == 0:
                        next_ready.append(succ)
            ready = next_ready

        # Compute overall status
        statuses = {nr.status for nr in dag_result.node_results.values()}
        if all(s in ("success", "skipped") for s in statuses):
            dag_result.status = "success"
        elif "success" in statuses:
            dag_result.status = "partial"
        else:
            dag_result.status = "failed"

        dag_result.total_duration_ms = int((time.monotonic() - start_time) * 1000)
        return dag_result

    async def _execute_node(
        self,
        node: PlanNode,
        session_id: str,
        dag_result: DAGResult,
        shared_context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Execute a single plan node."""
        start = time.monotonic()

        # Build shared context from predecessor results
        pred_shared = dict(shared_context or {})
        for dep_id in node.depends_on:
            if dep_id in dag_result.node_results:
                dep_result = dag_result.node_results[dep_id]
                if dep_result.result:
                    pred_shared[f"result_{dep_id}"] = dep_result.result

        try:
            # Get agent from registry
            agent = self._registry.get(node.agent_type)
            if agent is None:
                raise ValueError(f"No agent registered for type: {node.agent_type}")

            # Build context
            context_bundle = self._context_engine.build(
                query=node.description,
                agent_type=node.agent_type,
                session_id=session_id,
                shared_context=pred_shared,
            )

            # Execute agent
            agent_context = context_bundle.to_dict()
            agent_context.update(node.parameters)
            result = agent.execute(node.description, agent_context)

            duration = int((time.monotonic() - start) * 1000)
            dag_result.node_results[node.id] = NodeResult(
                node_id=node.id, agent_type=node.agent_type,
                status="success", result=result, duration_ms=duration,
            )

        except Exception as e:
            duration = int((time.monotonic() - start) * 1000)
            logger.error(f"Node {node.id} failed: {e}")
            dag_result.node_results[node.id] = NodeResult(
                node_id=node.id, agent_type=node.agent_type,
                status="failed", error=str(e), duration_ms=duration,
            )

    def execute_sync(
        self,
        plan: ExecutionPlan,
        session_id: str,
        shared_context: Optional[Dict[str, Any]] = None,
    ) -> DAGResult:
        """Sync wrapper for CLI callers."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # Already in async context — create a new thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(
                    asyncio.run,
                    self.execute(plan, session_id, shared_context),
                )
                return future.result()
        else:
            return asyncio.run(self.execute(plan, session_id, shared_context))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/krissdev/mike && python -m pytest tests/unit/test_dag_executor.py -v`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/krissdev/mike
git add src/mike/orchestrator/dag_executor.py tests/unit/test_dag_executor.py
git commit -m "feat: add DAGExecutor with topological execution, parallel branches, cancellation"
```

---

## Task 5: Wire Everything Into the Orchestrator

**Files:**
- Modify: `src/mike/orchestrator/engine.py` — add `run()` method, wire new components
- Modify: `src/mike/orchestrator/__init__.py` — export new classes
- Create: `tests/integration/test_orchestrator_integration.py`

- [ ] **Step 1: Write failing integration test**

```python
# tests/integration/test_orchestrator_integration.py
"""Integration test for the full orchestrator pipeline."""

import pytest
from unittest.mock import MagicMock, patch

from mike.orchestrator.engine import AgentOrchestrator
from mike.orchestrator.state import OrchestratorState, AgentType
from mike.orchestrator.model_provider import OllamaProvider, ModelRouter
from mike.orchestrator.context_engine import ContextEngine
from mike.orchestrator.planner import (
    IntentClassifier, StrategyRouter, RulePlanner, TemplatePlanner, LLMPlanner,
)
from mike.orchestrator.dag_executor import DAGExecutor, DAGResult


class TestOrchestratorRunPipeline:
    """Test the full classify -> plan -> execute pipeline."""

    def _setup_orchestrator(self):
        """Create orchestrator with mocked dependencies."""
        # Mock model provider
        model_provider = MagicMock()
        model_provider.generate_json.return_value = {
            "intent": "explain_code",
            "complexity": "simple",
            "confidence": 0.95,
            "parameters": {},
        }
        model_provider.model_name.return_value = "test-model"

        # Mock vector store and embedding service
        vector_store = MagicMock()
        vector_store.search.return_value = [
            {"id": "c0", "content": "def main(): pass", "metadata": {"file_path": "main.py"}, "distance": 0.1}
        ]
        embedding_service = MagicMock()
        embedding_service.embed.return_value = [0.1] * 1024

        # Build components
        context_engine = ContextEngine(
            vector_store=vector_store,
            embedding_service=embedding_service,
        )
        intent_classifier = IntentClassifier(model_provider)
        strategy_router = StrategyRouter(
            rule_planner=RulePlanner(),
            template_planner=TemplatePlanner(),
            llm_planner=LLMPlanner(model_provider),
        )

        # Create orchestrator
        state = OrchestratorState()
        orchestrator = AgentOrchestrator(state=state)

        # Register a mock QA agent
        mock_agent = MagicMock()
        mock_agent.agent_type = AgentType.QA
        mock_agent.execute.return_value = {"status": "success", "answer": "The function does X"}
        mock_agent.validate_result.return_value = True
        mock_agent.requires_approval.return_value = False
        orchestrator.register_agent(mock_agent)

        # Wire new components
        orchestrator.intent_classifier = intent_classifier
        orchestrator.strategy_router = strategy_router
        orchestrator.context_engine = context_engine
        orchestrator.dag_executor = DAGExecutor(
            agent_registry=orchestrator.registry,
            context_engine=context_engine,
        )

        return orchestrator

    def test_run_simple_query(self):
        orchestrator = self._setup_orchestrator()
        result = orchestrator.run("What does the main function do?", session_id="test-session")

        assert isinstance(result, DAGResult)
        assert result.status == "success"
        assert len(result.node_results) == 1

    def test_run_returns_agent_output(self):
        orchestrator = self._setup_orchestrator()
        result = orchestrator.run("explain the code", session_id="test-session")

        node_result = list(result.node_results.values())[0]
        assert node_result.result["answer"] == "The function does X"

    def test_run_with_plan_explainability(self):
        orchestrator = self._setup_orchestrator()
        result = orchestrator.run("What does this do?", session_id="test-session")

        assert result.plan.reasoning is not None
        assert result.plan.planner_type == "rule"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/krissdev/mike && python -m pytest tests/integration/test_orchestrator_integration.py -v 2>&1 | head -20`
Expected: AttributeError — `AgentOrchestrator` has no `run` method

- [ ] **Step 3: Add `run()` method to engine.py**

Add this method to the `AgentOrchestrator` class in `src/mike/orchestrator/engine.py`, after the existing `execute()` method (around line 618):

```python
    # --- New: Full pipeline entry point ---

    def run(
        self,
        query: str,
        session_id: str = "default",
        shared_context: Optional[Dict[str, Any]] = None,
    ):
        """Full pipeline: classify intent -> plan DAG -> execute.

        This is the primary entry point for the new orchestration system.
        The old execute() method is preserved for single-agent backward compat.

        Args:
            query: User query
            session_id: Session identifier for context retrieval
            shared_context: Optional shared context to pass to all agents

        Returns:
            DAGResult with per-node results and overall status
        """
        from .dag_executor import DAGResult

        # Step 1: Classify intent
        if hasattr(self, "intent_classifier") and self.intent_classifier:
            intent = self.intent_classifier.classify(query)
        else:
            # Fallback: use old router logic
            agent_type = self.router.route(query)
            from .planner import IntentResult, Complexity, PlanNode, ExecutionPlan
            intent = IntentResult(
                intent=agent_type.value if agent_type else "general_qa",
                complexity=Complexity.SIMPLE,
                confidence=0.5,
                parameters={},
            )

        # Step 2: Plan
        if hasattr(self, "strategy_router") and self.strategy_router:
            plan = self.strategy_router.plan(intent)
        else:
            from .planner import PlanNode, ExecutionPlan
            plan = ExecutionPlan(
                nodes=[PlanNode(
                    id="main", agent_type=intent.intent,
                    description=query, depends_on=[], parameters={},
                )],
                reasoning="Legacy fallback",
                planner_type="legacy",
            )

        self.log_action("plan_created", {
            "query": query,
            "intent": intent.intent,
            "complexity": intent.complexity.value if hasattr(intent.complexity, 'value') else str(intent.complexity),
            "planner_type": plan.planner_type,
            "node_count": len(plan.nodes),
            "reasoning": plan.reasoning,
        })

        # Step 3: Execute DAG
        if hasattr(self, "dag_executor") and self.dag_executor:
            result = self.dag_executor.execute_sync(plan, session_id, shared_context)
        else:
            # Fallback: execute first node only via old path
            from .dag_executor import DAGResult, NodeResult
            node = plan.nodes[0] if plan.nodes else None
            if node:
                execution = self.execute(query, agent_type=AgentType(node.agent_type))
                result = DAGResult(
                    plan=plan,
                    node_results={"main": NodeResult(
                        node_id="main", agent_type=node.agent_type,
                        status="success" if execution.status.name == "SUCCESS" else "failed",
                        result=execution.result,
                        error=execution.error,
                        duration_ms=0,
                    )},
                    status="success" if execution.status.name == "SUCCESS" else "failed",
                )
            else:
                result = DAGResult(plan=plan, status="failed")

        self.log_action("pipeline_completed", {
            "status": result.status,
            "node_count": len(result.node_results),
            "total_duration_ms": result.total_duration_ms,
        })

        return result
```

Also add the required import at the top of engine.py (after line 23):

```python
from typing import Any, Callable, Dict, List, Optional, Set, Type, Union
```

This import already exists — no change needed.

- [ ] **Step 4: Update __init__.py exports**

Replace the contents of `src/mike/orchestrator/__init__.py`:

```python
"""Agent Orchestrator for Mike.

Provides a multi-agent orchestration system with:
- Progressive Planning Architecture (intent -> plan -> DAG)
- ContextEngine (semantic retrieval, graph expansion, token budgeting)
- DAGExecutor (topological execution, parallel branches, cancellation)
- ModelProvider abstraction (Ollama, OpenAI-compatible, model routing)
"""

from .state import OrchestratorState, AgentExecution, SessionContext, ExecutionMemory
from .engine import AgentOrchestrator, AgentRegistry, TaskRouter
from .model_provider import (
    ModelCapabilities,
    ModelProvider,
    OllamaProvider,
    OpenAICompatibleProvider,
    ModelRouter,
)
from .context_engine import ContextEngine, ContextBundle
from .planner import (
    Complexity,
    IntentResult,
    PlanNode,
    ExecutionPlan,
    IntentClassifier,
    StrategyRouter,
    RulePlanner,
    TemplatePlanner,
    LLMPlanner,
)
from .dag_executor import DAGExecutor, NodeResult, DAGResult

__all__ = [
    # State
    "OrchestratorState",
    "AgentExecution",
    "SessionContext",
    "ExecutionMemory",
    # Engine
    "AgentOrchestrator",
    "AgentRegistry",
    "TaskRouter",
    # Model Provider
    "ModelCapabilities",
    "ModelProvider",
    "OllamaProvider",
    "OpenAICompatibleProvider",
    "ModelRouter",
    # Context
    "ContextEngine",
    "ContextBundle",
    # Planner
    "Complexity",
    "IntentResult",
    "PlanNode",
    "ExecutionPlan",
    "IntentClassifier",
    "StrategyRouter",
    "RulePlanner",
    "TemplatePlanner",
    "LLMPlanner",
    # DAG Executor
    "DAGExecutor",
    "NodeResult",
    "DAGResult",
]
```

- [ ] **Step 5: Run all tests**

Run: `cd /Users/krissdev/mike && python -m pytest tests/unit/test_model_provider.py tests/unit/test_context_engine.py tests/unit/test_planner.py tests/unit/test_dag_executor.py tests/integration/test_orchestrator_integration.py -v`
Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
cd /Users/krissdev/mike
git add src/mike/orchestrator/engine.py src/mike/orchestrator/__init__.py tests/integration/test_orchestrator_integration.py
git commit -m "feat: wire ContextEngine, PPA, DAGExecutor into AgentOrchestrator with run() pipeline"
```

---

## Task 6: Run Full Test Suite and Verify No Regressions

- [ ] **Step 1: Run all existing tests plus new tests**

Run: `cd /Users/krissdev/mike && python -m pytest tests/ -v --tb=short 2>&1 | tail -40`
Expected: All existing tests still pass. No regressions.

- [ ] **Step 2: Fix any import or compatibility issues**

If any existing test breaks due to `__init__.py` changes, fix the import. The new exports are purely additive — existing exports are unchanged.

- [ ] **Step 3: Commit any fixes**

```bash
cd /Users/krissdev/mike
git add -u
git commit -m "fix: resolve test regressions from orchestrator integration"
```

(Skip this commit if no fixes were needed.)
