"""Pattern detection utilities for code analysis."""

import hashlib
import re
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass
from tree_sitter import Node


@dataclass
class CodeSmell:
    """Represents a detected code smell."""

    smell_type: str
    file_path: str
    line_start: int
    line_end: int
    severity: str  # 'critical', 'high', 'medium', 'low'
    score: float  # 0.0 to 10.0
    description: str
    suggestion: str
    entity_name: Optional[str] = None


@dataclass
class ComplexityMetrics:
    """Complexity metrics for a code block."""

    cyclomatic_complexity: int
    nesting_depth: int
    line_count: int
    parameter_count: int


class ASTPatternMatcher:
    """Matches patterns in AST nodes."""

    # Security anti-patterns
    SECURITY_PATTERNS = {
        "eval_usage": [
            r"\beval\s*\(",
            r"\bexec\s*\(",
        ],
        "dangerous_functions": [
            r"\bsubprocess\.call\s*\([^)]*shell\s*=\s*True",
            r"\bos\.system\s*\(",
            r"\bos\.popen\s*\(",
        ],
        "hardcoded_secrets": [
            r'password\s*=\s*["\'][^"\']+["\']',
            r'secret\s*=\s*["\'][^"\']+["\']',
            r'api_key\s*=\s*["\'][^"\']+["\']',
            r'token\s*=\s*["\'][^"\']+["\']',
            r'AWS_ACCESS_KEY_ID\s*=\s*["\'][^"\']+["\']',
            r'AWS_SECRET_ACCESS_KEY\s*=\s*["\'][^"\']+["\']',
        ],
        "sql_injection": [
            r'execute\s*\(\s*["\'].*%s',
            r'execute\s*\(\s*["\'].*\+',
            r'execute\s*\(\s*f["\']',
        ],
    }

    def __init__(self):
        self._compiled_patterns: Dict[str, List[re.Pattern]] = {}
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compile regex patterns for efficiency."""
        for category, patterns in self.SECURITY_PATTERNS.items():
            self._compiled_patterns[category] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]

    def find_security_issues(
        self, code: str, file_path: str, language: str
    ) -> List[CodeSmell]:
        """Find security anti-patterns in code.

        Args:
            code: Source code to analyze
            file_path: Path to the file
            language: Programming language

        Returns:
            List of detected security issues
        """
        issues = []
        lines = code.split("\n")

        for line_num, line in enumerate(lines, 1):
            # Check eval/exec usage
            for pattern in self._compiled_patterns.get("eval_usage", []):
                if pattern.search(line):
                    issues.append(
                        CodeSmell(
                            smell_type="security_eval",
                            file_path=file_path,
                            line_start=line_num,
                            line_end=line_num,
                            severity="critical",
                            score=9.0,
                            description=f"Dangerous eval()/exec() usage detected",
                            suggestion="Avoid using eval() or exec(). Use safer alternatives like ast.literal_eval() or proper parsing.",
                        )
                    )

            # Check hardcoded secrets
            for pattern in self._compiled_patterns.get("hardcoded_secrets", []):
                if pattern.search(line):
                    # Skip common false positives
                    if not self._is_likely_false_positive(line):
                        issues.append(
                            CodeSmell(
                                smell_type="security_hardcoded_secret",
                                file_path=file_path,
                                line_start=line_num,
                                line_end=line_num,
                                severity="critical",
                                score=9.5,
                                description="Potential hardcoded secret detected",
                                suggestion="Move secrets to environment variables or a secure vault. Never hardcode credentials.",
                            )
                        )

            # Check SQL injection
            for pattern in self._compiled_patterns.get("sql_injection", []):
                if pattern.search(line):
                    issues.append(
                        CodeSmell(
                            smell_type="security_sql_injection",
                            file_path=file_path,
                            line_start=line_num,
                            line_end=line_num,
                            severity="high",
                            score=8.5,
                            description="Potential SQL injection vulnerability",
                            suggestion="Use parameterized queries or ORM methods instead of string concatenation.",
                        )
                    )

        return issues

    def _is_likely_false_positive(self, line: str) -> bool:
        """Check if a line is likely a false positive for secrets."""
        false_positive_patterns = [
            r'password\s*=\s*["\']\*+["\']',  # Masked passwords
            r'password\s*=\s*["\']<[^>]+>["\']',  # Template placeholders
            r'password\s*=\s*["\']\$\{[^}]+\}["\']',  # Shell variables
            r'password\s*=\s*["\']\$[A-Z_]+["\']',  # Environment variable references
            r"password\s*=\s*os\.environ",  # Getting from environment
            r"password\s*=\s*getenv",  # Getting from environment
            r"password\s*=\s*config",  # From config
            r"password\s*=\s*settings",  # From settings
            r"#.*password",  # Comments
            r'""".*password',  # Docstrings
            r"'''.*password",  # Docstrings
        ]

        for pattern in false_positive_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                return True

        return False

    def calculate_nesting_depth(self, node: Node, language: str) -> int:
        """Calculate maximum nesting depth of a node.

        Args:
            node: AST node to analyze
            language: Programming language

        Returns:
            Maximum nesting depth
        """
        nesting_nodes = self._get_nesting_node_types(language)
        max_depth = 0

        def traverse(n: Node, current_depth: int) -> None:
            nonlocal max_depth

            if n.type in nesting_nodes:
                current_depth += 1
                max_depth = max(max_depth, current_depth)

            for child in n.children:
                traverse(child, current_depth)

        traverse(node, 0)
        return max_depth

    def _get_nesting_node_types(self, language: str) -> Set[str]:
        """Get AST node types that increase nesting depth."""
        common = {
            "if_statement",
            "for_statement",
            "while_statement",
            "try_statement",
            "with_statement",
            "match_statement",
            "function_definition",
            "class_definition",
            "method_definition",
        }

        language_specific = {
            "python": {
                "if_statement",
                "for_statement",
                "while_statement",
                "try_statement",
                "with_statement",
                "match_statement",
                "function_definition",
                "class_definition",
            },
            "javascript": {
                "if_statement",
                "for_statement",
                "while_statement",
                "do_statement",
                "try_statement",
                "switch_statement",
                "function_declaration",
                "function",
                "arrow_function",
                "class_declaration",
                "method_definition",
            },
            "typescript": {
                "if_statement",
                "for_statement",
                "while_statement",
                "do_statement",
                "try_statement",
                "switch_statement",
                "function_declaration",
                "function",
                "arrow_function",
                "class_declaration",
                "method_definition",
            },
            "java": {
                "if_statement",
                "for_statement",
                "while_statement",
                "do_statement",
                "try_statement",
                "switch_statement",
                "synchronized_statement",
                "method_declaration",
                "class_declaration",
                "interface_declaration",
            },
            "go": {
                "if_statement",
                "for_statement",
                "select_statement",
                "switch_statement",
                "function_declaration",
                "method_declaration",
            },
            "rust": {
                "if_expression",
                "if_let_expression",
                "for_expression",
                "while_expression",
                "while_let_expression",
                "loop_expression",
                "match_expression",
                "function_item",
                "impl_item",
            },
            "c": {
                "if_statement",
                "for_statement",
                "while_statement",
                "do_statement",
                "switch_statement",
                "function_definition",
            },
            "cpp": {
                "if_statement",
                "for_statement",
                "while_statement",
                "do_statement",
                "switch_statement",
                "try_statement",
                "function_definition",
                "class_specifier",
            },
            "ruby": {
                "if",
                "unless",
                "for",
                "while",
                "until",
                "begin",
                "case",
                "method",
                "class",
                "module",
            },
            "php": {
                "if_statement",
                "for_statement",
                "while_statement",
                "do_statement",
                "switch_statement",
                "try_statement",
                "function_definition",
                "class_declaration",
            },
        }

        return language_specific.get(language, common)

    def count_methods_in_class(self, node: Node, language: str) -> int:
        """Count methods in a class definition.

        Args:
            node: Class node to analyze
            language: Programming language

        Returns:
            Number of methods
        """
        method_types = self._get_method_node_types(language)
        count = 0

        def traverse(n: Node) -> None:
            nonlocal count

            if n.type in method_types:
                count += 1

            for child in n.children:
                traverse(child)

        traverse(node)
        return count

    def _get_method_node_types(self, language: str) -> Set[str]:
        """Get AST node types for methods."""
        return {
            "python": {"function_definition"},
            "javascript": {"method_definition", "function_declaration"},
            "typescript": {"method_definition", "function_declaration"},
            "java": {"method_declaration"},
            "go": {"method_declaration", "function_declaration"},
            "rust": {"function_item"},
            "c": {"function_definition"},
            "cpp": {"function_definition", "method_definition"},
            "ruby": {"method"},
            "php": {"method_declaration", "function_definition"},
        }.get(language, {"function_definition"})


class DuplicateDetector:
    """Detects duplicated code blocks."""

    def __init__(self, min_lines: int = 5, similarity_threshold: float = 0.8):
        """Initialize duplicate detector.

        Args:
            min_lines: Minimum number of lines to consider for duplication
            similarity_threshold: Minimum similarity ratio (0.0-1.0) to flag as duplicate
        """
        self.min_lines = min_lines
        self.similarity_threshold = similarity_threshold

    def find_duplicates(
        self, files_content: Dict[str, str], ast_data: Dict[str, Dict[str, Any]]
    ) -> List[CodeSmell]:
        """Find duplicated code across files.

        Args:
            files_content: Dictionary mapping file paths to content
            ast_data: Dictionary mapping file paths to AST data

        Returns:
            List of duplicate code smells
        """
        duplicates = []
        code_blocks: List[
            Tuple[str, int, int, str, str]
        ] = []  # file, start, end, content, hash

        # Extract code blocks from functions
        for file_path, content in files_content.items():
            lines = content.split("\n")
            ast_info = ast_data.get(file_path, {})

            for func in ast_info.get("functions", []):
                start_line = func.get("start_line", 1)
                end_line = func.get("end_line", start_line)

                if end_line - start_line + 1 >= self.min_lines:
                    block_lines = lines[start_line - 1 : end_line]
                    block_content = "\n".join(block_lines)
                    normalized = self._normalize_code(block_content)
                    block_hash = hashlib.md5(normalized.encode()).hexdigest()

                    code_blocks.append(
                        (file_path, start_line, end_line, block_content, block_hash)
                    )

        # Find duplicates
        for i, (file1, start1, end1, content1, hash1) in enumerate(code_blocks):
            for j, (file2, start2, end2, content2, hash2) in enumerate(
                code_blocks[i + 1 :], i + 1
            ):
                if hash1 == hash2:
                    # Exact match
                    duplicates.append(
                        self._create_duplicate_smell(
                            file1,
                            start1,
                            end1,
                            file2,
                            start2,
                            end2,
                            content1,
                            similarity=1.0,
                        )
                    )
                else:
                    # Check similarity
                    similarity = self._calculate_similarity(content1, content2)
                    if similarity >= self.similarity_threshold:
                        duplicates.append(
                            self._create_duplicate_smell(
                                file1,
                                start1,
                                end1,
                                file2,
                                start2,
                                end2,
                                content1,
                                similarity,
                            )
                        )

        return duplicates

    def _normalize_code(self, code: str) -> str:
        """Normalize code for comparison.

        Args:
            code: Source code

        Returns:
            Normalized code string
        """
        # Remove comments
        code = re.sub(r"#.*$", "", code, flags=re.MULTILINE)
        code = re.sub(r"//.*$", "", code, flags=re.MULTILINE)
        code = re.sub(r"/\*.*?\*/", "", code, flags=re.DOTALL)

        # Normalize whitespace
        lines = code.split("\n")
        normalized_lines = []

        for line in lines:
            # Strip leading/trailing whitespace
            line = line.strip()
            # Normalize internal whitespace
            line = " ".join(line.split())
            if line:
                normalized_lines.append(line)

        return "\n".join(normalized_lines)

    def _calculate_similarity(self, code1: str, code2: str) -> float:
        """Calculate similarity between two code blocks.

        Args:
            code1: First code block
            code2: Second code block

        Returns:
            Similarity ratio between 0.0 and 1.0
        """
        norm1 = self._normalize_code(code1)
        norm2 = self._normalize_code(code2)

        if not norm1 or not norm2:
            return 0.0

        # Use simple token-based similarity
        tokens1 = set(norm1.split())
        tokens2 = set(norm2.split())

        if not tokens1 or not tokens2:
            return 0.0

        intersection = tokens1 & tokens2
        union = tokens1 | tokens2

        return len(intersection) / len(union)

    def _create_duplicate_smell(
        self,
        file1: str,
        start1: int,
        end1: int,
        file2: str,
        start2: int,
        end2: int,
        content: str,
        similarity: float,
    ) -> CodeSmell:
        """Create a CodeSmell for duplicate code.

        Args:
            file1, start1, end1: First location
            file2, start2, end2: Second location
            content: Code content
            similarity: Similarity ratio

        Returns:
            CodeSmell instance
        """
        if file1 == file2:
            description = (
                f"Duplicated code detected in same file "
                f"({similarity * 100:.0f}% similar)"
            )
        else:
            description = (
                f"Duplicated code detected across files: {file1} and {file2} "
                f"({similarity * 100:.0f}% similar)"
            )

        severity = "high" if similarity >= 0.9 else "medium"
        score = 7.0 + (similarity * 2.0)

        return CodeSmell(
            smell_type="duplicate_code",
            file_path=file1,
            line_start=start1,
            line_end=end1,
            severity=severity,
            score=min(score, 9.0),
            description=description,
            suggestion="Extract duplicated code into a shared function or utility. Consider using the DRY principle.",
        )


class ComplexityAnalyzer:
    """Analyzes code complexity metrics."""

    def __init__(self):
        self.branching_keywords = {
            "if",
            "else",
            "elif",
            "for",
            "while",
            "switch",
            "case",
            "try",
            "catch",
            "except",
            "finally",
            "with",
            "match",
            "and",
            "or",
            "?",
            "&&",
            "||",
        }

    def calculate_cyclomatic_complexity(self, node: Node, language: str) -> int:
        """Calculate cyclomatic complexity of a node.

        Args:
            node: AST node
            language: Programming language

        Returns:
            Cyclomatic complexity value
        """
        complexity = 1  # Base complexity

        branching_types = self._get_branching_node_types(language)

        def traverse(n: Node) -> None:
            nonlocal complexity

            if n.type in branching_types:
                complexity += 1

            # Handle boolean operators
            if n.type in ("boolean_operator", "binary_expression"):
                complexity += 1

            for child in n.children:
                traverse(child)

        traverse(node)
        return complexity

    def _get_branching_node_types(self, language: str) -> Set[str]:
        """Get AST node types that increase cyclomatic complexity."""
        return {
            "python": {
                "if_statement",
                "for_statement",
                "while_statement",
                "except_clause",
                "finally_clause",
                "with_statement",
                "boolean_operator",
            },
            "javascript": {
                "if_statement",
                "for_statement",
                "while_statement",
                "do_statement",
                "switch_statement",
                "catch_clause",
                "conditional_expression",
                "logical_expression",
            },
            "typescript": {
                "if_statement",
                "for_statement",
                "while_statement",
                "do_statement",
                "switch_statement",
                "catch_clause",
                "conditional_expression",
                "logical_expression",
            },
            "java": {
                "if_statement",
                "for_statement",
                "while_statement",
                "do_statement",
                "switch_statement",
                "catch_clause",
                "conditional_expression",
                "binary_expression",
            },
            "go": {
                "if_statement",
                "for_statement",
                "select_statement",
                "switch_statement",
            },
            "rust": {
                "if_expression",
                "if_let_expression",
                "for_expression",
                "while_expression",
                "while_let_expression",
                "match_expression",
                "match_arm",
            },
            "c": {
                "if_statement",
                "for_statement",
                "while_statement",
                "do_statement",
                "switch_statement",
                "conditional_expression",
            },
            "cpp": {
                "if_statement",
                "for_statement",
                "while_statement",
                "do_statement",
                "switch_statement",
                "catch_clause",
                "conditional_expression",
            },
            "ruby": {
                "if",
                "unless",
                "for",
                "while",
                "until",
                "case",
                "rescue",
                "ensure",
            },
            "php": {
                "if_statement",
                "for_statement",
                "while_statement",
                "do_statement",
                "switch_statement",
                "catch_clause",
            },
        }.get(language, {"if_statement", "for_statement", "while_statement"})

    def count_lines(self, node: Node) -> int:
        """Count lines in a node.

        Args:
            node: AST node

        Returns:
            Number of lines
        """
        return node.end_point[0] - node.start_point[0] + 1

    def is_complex_function(
        self,
        node: Node,
        language: str,
        max_lines: int = 50,
        max_complexity: int = 10,
        max_nesting: int = 4,
    ) -> Optional[Tuple[str, float]]:
        """Check if a function is overly complex.

        Args:
            node: Function AST node
            language: Programming language
            max_lines: Maximum allowed lines
            max_complexity: Maximum allowed cyclomatic complexity
            max_nesting: Maximum allowed nesting depth

        Returns:
            Tuple of (issue_type, severity_score) if complex, None otherwise
        """
        lines = self.count_lines(node)
        complexity = self.calculate_cyclomatic_complexity(node, language)
        nesting = ASTPatternMatcher().calculate_nesting_depth(node, language)

        issues = []

        if lines > max_lines:
            score = min(5.0 + (lines - max_lines) / 10, 9.0)
            issues.append(("long_function", score))

        if complexity > max_complexity:
            score = min(5.0 + (complexity - max_complexity) * 0.5, 8.5)
            issues.append(("high_complexity", score))

        if nesting > max_nesting:
            score = min(5.0 + (nesting - max_nesting) * 0.8, 8.0)
            issues.append(("deep_nesting", score))

        if not issues:
            return None

        # Return the highest scoring issue
        return max(issues, key=lambda x: x[1])


class DependencyAnalyzer:
    """Analyzes code dependencies."""

    def __init__(self):
        self.call_graph: Dict[str, Set[str]] = {}
        self.definitions: Dict[str, Tuple[str, int]] = {}  # name -> (file, line)

    def build_call_graph(
        self, files_content: Dict[str, str], ast_data: Dict[str, Dict[str, Any]]
    ) -> None:
        """Build a call graph from AST data.

        Args:
            files_content: Dictionary mapping file paths to content
            ast_data: Dictionary mapping file paths to AST data
        """
        self.call_graph = {}
        self.definitions = {}

        # First pass: collect all definitions
        for file_path, ast_info in ast_data.items():
            for func in ast_info.get("functions", []):
                name = func.get("name", "")
                if name:
                    self.definitions[name] = (file_path, func.get("start_line", 0))
                    self.call_graph[name] = set()

        # Second pass: find calls
        for file_path, content in files_content.items():
            lines = content.split("\n")

            for func_name in self.definitions:
                for line_num, line in enumerate(lines, 1):
                    # Simple pattern matching for function calls
                    # This is a basic implementation - could be improved with proper AST analysis
                    pattern = rf"\b{re.escape(func_name)}\s*\("
                    if re.search(pattern, line):
                        # Find which function this line is in
                        containing_func = self._find_containing_function(
                            file_path, line_num, ast_data
                        )
                        if containing_func and containing_func != func_name:
                            if containing_func not in self.call_graph:
                                self.call_graph[containing_func] = set()
                            self.call_graph[containing_func].add(func_name)

    def _find_containing_function(
        self, file_path: str, line_num: int, ast_data: Dict[str, Dict[str, Any]]
    ) -> Optional[str]:
        """Find the function containing a given line.

        Args:
            file_path: Path to file
            line_num: Line number
            ast_data: AST data dictionary

        Returns:
            Function name or None
        """
        ast_info = ast_data.get(file_path, {})

        for func in ast_info.get("functions", []):
            start = func.get("start_line", 0)
            end = func.get("end_line", 0)
            if start <= line_num <= end:
                return func.get("name", "")

        return None

    def find_circular_dependencies(self) -> List[List[str]]:
        """Find circular dependencies in the call graph.

        Returns:
            List of circular dependency chains
        """
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(node: str, path: List[str]) -> None:
            visited.add(node)
            rec_stack.add(node)

            for neighbor in self.call_graph.get(node, set()):
                if neighbor not in visited:
                    dfs(neighbor, path + [neighbor])
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = (
                        path.index(neighbor) if neighbor in path else len(path)
                    )
                    cycle = path[cycle_start:] + [neighbor]
                    if len(cycle) > 1:
                        cycles.append(cycle)

            rec_stack.remove(node)

        for node in self.call_graph:
            if node not in visited:
                dfs(node, [node])

        return cycles

    def find_dead_code(self) -> List[Tuple[str, str, int]]:
        """Find functions that are never called.

        Returns:
            List of (function_name, file_path, line) tuples
        """
        dead = []
        all_calls = set()

        # Collect all called functions
        for calls in self.call_graph.values():
            all_calls.update(calls)

        # Find uncalled functions
        for func_name, (file_path, line) in self.definitions.items():
            if func_name not in all_calls:
                dead.append((func_name, file_path, line))

        return dead
