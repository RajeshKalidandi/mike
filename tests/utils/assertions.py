"""Custom assertions for Mike tests."""

from typing import Any, Dict, List, Optional
import re


class CodeAssertions:
    """Custom assertions for code-related testing."""

    @staticmethod
    def assert_valid_file_info(file_info: Dict[str, Any]) -> None:
        """Assert that file info has all required fields."""
        required_fields = [
            "relative_path",
            "absolute_path",
            "language",
            "size_bytes",
            "line_count",
            "content_hash",
            "extension",
        ]
        for field in required_fields:
            assert field in file_info, f"Missing required field: {field}"
        assert isinstance(file_info["size_bytes"], int)
        assert isinstance(file_info["line_count"], int)
        assert len(file_info["content_hash"]) == 64  # SHA-256 hex

    @staticmethod
    def assert_valid_chunk(chunk: Dict[str, Any]) -> None:
        """Assert that chunk has valid structure."""
        assert "content" in chunk, "Chunk must have content"
        assert "metadata" in chunk, "Chunk must have metadata"
        assert isinstance(chunk["content"], str)
        assert isinstance(chunk["metadata"], dict)

    @staticmethod
    def assert_valid_ast_result(result: Dict[str, Any]) -> None:
        """Assert that AST parsing result is valid."""
        assert "functions" in result, "Result must have functions"
        assert "classes" in result, "Result must have classes"
        assert "imports" in result, "Result must have imports"
        assert "language" in result, "Result must have language"
        assert isinstance(result["functions"], list)
        assert isinstance(result["classes"], list)
        assert isinstance(result["imports"], list)

    @staticmethod
    def assert_function_valid(func: Dict[str, Any]) -> None:
        """Assert that function metadata is valid."""
        assert "name" in func, "Function must have name"
        assert "start_line" in func, "Function must have start_line"
        assert "end_line" in func, "Function must have end_line"
        assert isinstance(func["start_line"], int)
        assert isinstance(func["end_line"], int)
        assert func["start_line"] > 0
        assert func["end_line"] >= func["start_line"]

    @staticmethod
    def assert_valid_embedding(
        embedding: List[float], expected_dim: int = 1024
    ) -> None:
        """Assert that embedding vector is valid."""
        assert isinstance(embedding, list), "Embedding must be a list"
        assert len(embedding) == expected_dim, (
            f"Embedding must have {expected_dim} dimensions"
        )
        # Check all values are floats
        for i, val in enumerate(embedding):
            assert isinstance(val, (int, float)), (
                f"Embedding value at index {i} must be numeric"
            )

    @staticmethod
    def assert_valid_graph_stats(stats: Dict[str, Any]) -> None:
        """Assert that graph statistics are valid."""
        assert "nodes" in stats, "Stats must have nodes count"
        assert "edges" in stats, "Stats must have edges count"
        assert "density" in stats, "Stats must have density"
        assert isinstance(stats["nodes"], int)
        assert isinstance(stats["edges"], int)
        assert isinstance(stats["density"], float)
        assert stats["nodes"] >= 0
        assert stats["edges"] >= 0
        assert 0 <= stats["density"] <= 1

    @staticmethod
    def assert_valid_qa_response(response: Dict[str, Any]) -> None:
        """Assert that Q&A response is valid."""
        assert "answer" in response, "Response must have answer"
        assert "query" in response, "Response must have query"
        assert "intent" in response, "Response must have intent"
        assert isinstance(response["answer"], str)
        assert len(response["answer"]) > 0

    @staticmethod
    def assert_valid_code_smell(smell: Dict[str, Any]) -> None:
        """Assert that code smell is valid."""
        required = ["smell_type", "file_path", "line_start", "severity", "description"]
        for field in required:
            assert field in smell, f"Code smell missing field: {field}"
        assert smell["severity"] in ["critical", "high", "medium", "low"]
        assert isinstance(smell["line_start"], int)

    @staticmethod
    def assert_no_secrets_in_code(code: str, file_path: str = "") -> None:
        """Assert that code doesn't contain obvious secrets."""
        secret_patterns = [
            r'password\s*=\s*["\'][^"\']+["\']',
            r'api_key\s*=\s*["\'][^"\']+["\']',
            r'secret\s*=\s*["\'][^"\']+["\']',
            r'token\s*=\s*["\'][^"\']+["\']',
            r'private_key\s*=\s*["\'][^"\']+["\']',
        ]
        for pattern in secret_patterns:
            matches = re.findall(pattern, code, re.IGNORECASE)
            assert len(matches) == 0, (
                f"Potential secret found in {file_path}: {matches}"
            )


class MetricAssertions:
    """Custom assertions for performance and metrics testing."""

    @staticmethod
    def assert_execution_time_under(duration_ms: float, max_ms: float) -> None:
        """Assert that execution time is under threshold."""
        assert duration_ms < max_ms, (
            f"Execution time {duration_ms}ms exceeds max {max_ms}ms"
        )

    @staticmethod
    def assert_memory_usage_under(memory_mb: float, max_mb: float) -> None:
        """Assert that memory usage is under threshold."""
        assert memory_mb < max_mb, f"Memory usage {memory_mb}MB exceeds max {max_mb}MB"

    @staticmethod
    def assert_coverage_above(coverage_pct: float, min_pct: float = 90.0) -> None:
        """Assert that code coverage is above threshold."""
        assert coverage_pct >= min_pct, (
            f"Coverage {coverage_pct}% below minimum {min_pct}%"
        )


# Make assertions available as module-level functions
assert_valid_file_info = CodeAssertions.assert_valid_file_info
assert_valid_chunk = CodeAssertions.assert_valid_chunk
assert_valid_ast_result = CodeAssertions.assert_valid_ast_result
assert_function_valid = CodeAssertions.assert_function_valid
assert_valid_embedding = CodeAssertions.assert_valid_embedding
assert_valid_graph_stats = CodeAssertions.assert_valid_graph_stats
assert_valid_qa_response = CodeAssertions.assert_valid_qa_response
assert_valid_code_smell = CodeAssertions.assert_valid_code_smell
assert_no_secrets_in_code = CodeAssertions.assert_no_secrets_in_code
assert_execution_time_under = MetricAssertions.assert_execution_time_under
assert_memory_usage_under = MetricAssertions.assert_memory_usage_under
assert_coverage_above = MetricAssertions.assert_coverage_above
