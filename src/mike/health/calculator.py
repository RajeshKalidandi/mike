"""Health Score Calculator for architecture analysis."""

import math
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict

import networkx as nx

from src.mike.graph.builder import DependencyGraphBuilder
from src.mike.parser.parser import ASTParser

from .models import (
    ArchitectureScore,
    DimensionScore,
    ScoreDimension,
    ScoreThresholds,
    DIMENSION_WEIGHTS,
)


class HealthScoreCalculator:
    """Calculates architecture health scores based on codebase metrics."""

    def __init__(
        self,
        graph_builder: DependencyGraphBuilder,
        parser: ASTParser,
        layer_config: Optional[Dict[str, List[str]]] = None,
    ):
        """Initialize the health score calculator.

        Args:
            graph_builder: Dependency graph builder with populated graph
            parser: AST parser for code analysis
            layer_config: Optional layer configuration for architecture validation
                Format: {"layer_name": [file_patterns], ...}
        """
        self.graph_builder = graph_builder
        self.parser = parser
        self.layer_config = layer_config or {}
        self.thresholds = ScoreThresholds()

    def calculate_coupling_score(self) -> DimensionScore:
        """Calculate coupling score based on fan-in/fan-out analysis.

        Lower coupling (fewer dependencies) results in higher scores.
        Uses average fan-in and fan-out metrics to determine coupling level.

        Returns:
            DimensionScore for coupling dimension
        """
        graph = self.graph_builder.graph
        if graph.number_of_nodes() == 0:
            return DimensionScore(
                dimension=ScoreDimension.COUPLING,
                score=100.0,
                weight=DIMENSION_WEIGHTS[ScoreDimension.COUPLING],
                details={"message": "Empty graph - no coupling issues"},
                issues=[],
            )

        fan_in_scores = []
        fan_out_scores = []
        high_coupling_files = []

        for node in graph.nodes():
            # Fan-in: number of files depending on this file
            fan_in = graph.in_degree(node)
            # Fan-out: number of files this file depends on
            fan_out = graph.out_degree(node)

            fan_in_scores.append(fan_in)
            fan_out_scores.append(fan_out)

            # Flag files with high coupling
            if fan_in > 10 or fan_out > 10:
                high_coupling_files.append(
                    {
                        "file": node,
                        "fan_in": fan_in,
                        "fan_out": fan_out,
                    }
                )

        avg_fan_in = sum(fan_in_scores) / len(fan_in_scores) if fan_in_scores else 0
        avg_fan_out = sum(fan_out_scores) / len(fan_out_scores) if fan_out_scores else 0

        # Calculate coupling score (lower is better, so we invert)
        # Normalize: expect avg coupling <= 5 for perfect score
        coupling_factor = (avg_fan_in + avg_fan_out) / 2
        score = max(0, 100 - (coupling_factor * 10))

        issues = []
        if high_coupling_files:
            issues.append(
                f"Found {len(high_coupling_files)} files with high coupling "
                f"(fan-in > 10 or fan-out > 10)"
            )

        return DimensionScore(
            dimension=ScoreDimension.COUPLING,
            score=round(score, 2),
            weight=DIMENSION_WEIGHTS[ScoreDimension.COUPLING],
            details={
                "avg_fan_in": round(avg_fan_in, 2),
                "avg_fan_out": round(avg_fan_out, 2),
                "max_fan_in": max(fan_in_scores) if fan_in_scores else 0,
                "max_fan_out": max(fan_out_scores) if fan_out_scores else 0,
                "high_coupling_files": high_coupling_files[:10],  # Limit to top 10
            },
            issues=issues,
        )

    def calculate_cohesion_score(self, file_contents: Dict[str, str]) -> DimensionScore:
        """Calculate cohesion score using LCOM (Lack of Cohesion of Methods) metric.

        LCOM measures how well the methods of a class are related to each other.
        Lower LCOM indicates better cohesion.

        Args:
            file_contents: Dictionary mapping file paths to their content

        Returns:
            DimensionScore for cohesion dimension
        """
        if not file_contents:
            return DimensionScore(
                dimension=ScoreDimension.COHESION,
                score=100.0,
                weight=DIMENSION_WEIGHTS[ScoreDimension.COHESION],
                details={"message": "No files to analyze"},
                issues=[],
            )

        lcom_scores = []
        low_cohesion_classes = []

        for file_path, content in file_contents.items():
            try:
                # Detect language from file extension
                language = self._detect_language(file_path)
                if not language:
                    continue

                ast_data = self.parser.parse(content, language)

                for class_info in ast_data.get("classes", []):
                    methods = class_info.get("methods", [])
                    if len(methods) < 2:
                        # Classes with 0 or 1 method have perfect cohesion by definition
                        lcom_scores.append(0)
                        continue

                    # Simplified LCOM calculation
                    # Count methods that don't share instance variables
                    # For this simplified version, we'll use method count as a proxy
                    # In a full implementation, we'd analyze instance variable usage
                    lcom = self._calculate_lcom_heuristic(methods)
                    lcom_scores.append(lcom)

                    if lcom > 0.7:  # Threshold for low cohesion
                        low_cohesion_classes.append(
                            {
                                "file": file_path,
                                "class": class_info.get("name", "unknown"),
                                "lcom": round(lcom, 2),
                                "method_count": len(methods),
                            }
                        )
            except Exception:
                # Skip files that can't be parsed
                continue

        avg_lcom = sum(lcom_scores) / len(lcom_scores) if lcom_scores else 0
        # Convert LCOM to score (lower LCOM is better)
        score = max(0, 100 - (avg_lcom * 100))

        issues = []
        if low_cohesion_classes:
            issues.append(
                f"Found {len(low_cohesion_classes)} classes with low cohesion (LCOM > 0.7)"
            )

        return DimensionScore(
            dimension=ScoreDimension.COHESION,
            score=round(score, 2),
            weight=DIMENSION_WEIGHTS[ScoreDimension.COHESION],
            details={
                "avg_lcom": round(avg_lcom, 2),
                "classes_analyzed": len(lcom_scores),
                "low_cohesion_classes": low_cohesion_classes[:10],
            },
            issues=issues,
        )

    def _calculate_lcom_heuristic(self, methods: List[Dict]) -> float:
        """Calculate a heuristic LCOM score based on method characteristics.

        Args:
            methods: List of method dictionaries

        Returns:
            LCOM score between 0 and 1
        """
        if len(methods) < 2:
            return 0.0

        # Simple heuristic: more methods = potentially lower cohesion
        # Normalize: 2-5 methods = good, 10+ methods = concerning
        method_count = len(methods)
        if method_count <= 5:
            return 0.2
        elif method_count <= 10:
            return 0.4
        elif method_count <= 15:
            return 0.6
        else:
            return min(1.0, 0.7 + (method_count - 15) * 0.02)

    def calculate_circular_deps_score(self) -> DimensionScore:
        """Calculate score based on circular dependency detection.

        Returns:
            DimensionScore for circular dependencies dimension
        """
        cycles = self.graph_builder.find_cycles()
        cycle_count = len(cycles)

        # Score decreases with more cycles
        # 0 cycles = 100, 1-3 cycles = 80, 4-10 cycles = 60, 10+ cycles = 40
        if cycle_count == 0:
            score = 100.0
        elif cycle_count <= 3:
            score = 80.0
        elif cycle_count <= 10:
            score = 60.0
        else:
            score = max(0, 40 - (cycle_count - 10) * 2)

        issues = []
        if cycles:
            cycle_details = [
                {"length": len(cycle), "files": cycle}
                for cycle in cycles[:10]  # Limit to first 10 cycles
            ]
            issues.append(f"Found {cycle_count} circular dependencies")
        else:
            cycle_details = []

        return DimensionScore(
            dimension=ScoreDimension.CIRCULAR_DEPS,
            score=round(score, 2),
            weight=DIMENSION_WEIGHTS[ScoreDimension.CIRCULAR_DEPS],
            details={
                "cycle_count": cycle_count,
                "cycles": cycle_details,
            },
            issues=issues,
        )

    def calculate_complexity_score(
        self, file_contents: Dict[str, str]
    ) -> DimensionScore:
        """Calculate complexity score based on cyclomatic complexity.

        Args:
            file_contents: Dictionary mapping file paths to their content

        Returns:
            DimensionScore for complexity dimension
        """
        if not file_contents:
            return DimensionScore(
                dimension=ScoreDimension.COMPLEXITY,
                score=100.0,
                weight=DIMENSION_WEIGHTS[ScoreDimension.COMPLEXITY],
                details={"message": "No files to analyze"},
                issues=[],
            )

        complexity_scores = []
        complex_functions = []

        for file_path, content in file_contents.items():
            try:
                language = self._detect_language(file_path)
                if not language:
                    continue

                # Calculate cyclomatic complexity
                complexity = self._calculate_cyclomatic_complexity(content, language)
                complexity_scores.append(complexity)

                # Flag overly complex files
                if complexity > 15:
                    complex_functions.append(
                        {
                            "file": file_path,
                            "complexity": complexity,
                        }
                    )
            except Exception:
                continue

        avg_complexity = (
            sum(complexity_scores) / len(complexity_scores) if complexity_scores else 0
        )

        # Score based on average complexity
        # 0-5: excellent (100), 5-10: good (80), 10-20: fair (60), 20+: poor
        if avg_complexity <= 5:
            score = 100.0
        elif avg_complexity <= 10:
            score = 80.0
        elif avg_complexity <= 20:
            score = 60.0
        else:
            score = max(0, 60 - (avg_complexity - 20) * 2)

        issues = []
        if complex_functions:
            issues.append(
                f"Found {len(complex_functions)} files with high complexity (> 15)"
            )

        return DimensionScore(
            dimension=ScoreDimension.COMPLEXITY,
            score=round(score, 2),
            weight=DIMENSION_WEIGHTS[ScoreDimension.COMPLEXITY],
            details={
                "avg_complexity": round(avg_complexity, 2),
                "max_complexity": max(complexity_scores) if complexity_scores else 0,
                "files_analyzed": len(complexity_scores),
                "complex_functions": complex_functions[:10],
            },
            issues=issues,
        )

    def _calculate_cyclomatic_complexity(self, code: str, language: str) -> int:
        """Calculate cyclomatic complexity for code.

        Args:
            code: Source code
            language: Programming language

        Returns:
            Cyclomatic complexity value
        """
        # Count decision points
        complexity = 1  # Base complexity

        # Decision keywords by language
        decision_keywords = {
            "python": ["if", "elif", "for", "while", "except", "with", "and", "or"],
            "javascript": ["if", "else", "for", "while", "case", "catch", "&&", "||"],
            "typescript": ["if", "else", "for", "while", "case", "catch", "&&", "||"],
            "java": ["if", "else", "for", "while", "case", "catch", "&&", "||"],
            "go": ["if", "else", "for", "switch", "case"],
            "rust": ["if", "else", "for", "while", "match"],
            "c": ["if", "else", "for", "while", "case", "&&", "||"],
            "cpp": ["if", "else", "for", "while", "case", "&&", "||"],
            "ruby": ["if", "unless", "else", "for", "while", "case"],
            "php": ["if", "else", "for", "while", "case", "catch", "&&", "||"],
        }

        keywords = decision_keywords.get(language, [])
        lines = code.split("\n")

        for line in lines:
            stripped = line.strip()
            # Skip comments
            if stripped.startswith("#") or stripped.startswith("//"):
                continue

            # Count decision points
            for keyword in keywords:
                if keyword in ["&&", "||"]:
                    complexity += stripped.count(keyword)
                elif stripped.startswith(keyword + " ") or stripped.startswith(
                    keyword + ":"
                ):
                    complexity += 1

        return complexity

    def calculate_layer_violations_score(self) -> DimensionScore:
        """Calculate score based on architectural layer violations.

        Returns:
            DimensionScore for layer violations dimension
        """
        if not self.layer_config:
            return DimensionScore(
                dimension=ScoreDimension.LAYER_VIOLATIONS,
                score=100.0,
                weight=DIMENSION_WEIGHTS[ScoreDimension.LAYER_VIOLATIONS],
                details={"message": "No layer configuration provided"},
                issues=[],
            )

        violations = []
        graph = self.graph_builder.graph

        # Define layer order (lower layers shouldn't depend on higher layers)
        layer_order = list(self.layer_config.keys())

        for source, target, data in graph.edges(data=True):
            source_layer = self._get_file_layer(source)
            target_layer = self._get_file_layer(target)

            if source_layer and target_layer:
                source_idx = layer_order.index(source_layer)
                target_idx = layer_order.index(target_layer)

                # Violation: lower layer depends on higher layer
                if source_idx < target_idx:
                    violations.append(
                        {
                            "source": source,
                            "target": target,
                            "source_layer": source_layer,
                            "target_layer": target_layer,
                        }
                    )

        violation_count = len(violations)

        # Score based on violations
        if violation_count == 0:
            score = 100.0
        elif violation_count <= 5:
            score = 80.0
        elif violation_count <= 15:
            score = 60.0
        else:
            score = max(0, 40 - (violation_count - 15) * 2)

        issues = []
        if violations:
            issues.append(f"Found {violation_count} layer violations")

        return DimensionScore(
            dimension=ScoreDimension.LAYER_VIOLATIONS,
            score=round(score, 2),
            weight=DIMENSION_WEIGHTS[ScoreDimension.LAYER_VIOLATIONS],
            details={
                "violation_count": violation_count,
                "violations": violations[:10],
                "layers": layer_order,
            },
            issues=issues,
        )

    def _get_file_layer(self, file_path: str) -> Optional[str]:
        """Determine which architectural layer a file belongs to.

        Args:
            file_path: Path to the file

        Returns:
            Layer name or None if not in any layer
        """
        for layer_name, patterns in self.layer_config.items():
            for pattern in patterns:
                if pattern in file_path:
                    return layer_name
        return None

    def calculate_unused_exports_score(
        self, file_contents: Dict[str, str]
    ) -> DimensionScore:
        """Calculate score based on unused exports detection.

        Args:
            file_contents: Dictionary mapping file paths to their content

        Returns:
            DimensionScore for unused exports dimension
        """
        if not file_contents:
            return DimensionScore(
                dimension=ScoreDimension.UNUSED_EXPORTS,
                score=100.0,
                weight=DIMENSION_WEIGHTS[ScoreDimension.UNUSED_EXPORTS],
                details={"message": "No files to analyze"},
                issues=[],
            )

        # Track exports and imports
        exports_by_file: Dict[str, Set[str]] = defaultdict(set)
        imports_by_file: Dict[str, Set[str]] = defaultdict(set)

        for file_path, content in file_contents.items():
            try:
                language = self._detect_language(file_path)
                if not language:
                    continue

                ast_data = self.parser.parse(content, language)

                # Extract exports
                exports = self._extract_exports(ast_data, language)
                exports_by_file[file_path] = exports

                # Extract imports
                for imp in ast_data.get("imports", []):
                    name = imp.get("name", "")
                    if name:
                        imports_by_file[file_path].add(name)
            except Exception:
                continue

        # Find unused exports
        unused_exports = []
        all_imported = set()
        for imports in imports_by_file.values():
            all_imported.update(imports)

        for file_path, exports in exports_by_file.items():
            for export in exports:
                # Check if this export is imported anywhere
                is_used = export in all_imported
                if not is_used:
                    unused_exports.append(
                        {
                            "file": file_path,
                            "export": export,
                        }
                    )

        # Calculate score based on unused export ratio
        total_exports = sum(len(exports) for exports in exports_by_file.values())
        unused_count = len(unused_exports)

        if total_exports == 0:
            score = 100.0
        else:
            unused_ratio = unused_count / total_exports
            score = max(0, 100 - (unused_ratio * 100))

        issues = []
        if unused_exports:
            issues.append(f"Found {unused_count} unused exports out of {total_exports}")

        return DimensionScore(
            dimension=ScoreDimension.UNUSED_EXPORTS,
            score=round(score, 2),
            weight=DIMENSION_WEIGHTS[ScoreDimension.UNUSED_EXPORTS],
            details={
                "total_exports": total_exports,
                "unused_count": unused_count,
                "unused_ratio": round(unused_count / total_exports, 4)
                if total_exports
                else 0,
                "unused_exports": unused_exports[:20],  # Limit to first 20
            },
            issues=issues,
        )

    def _extract_exports(self, ast_data: Dict, language: str) -> Set[str]:
        """Extract exported symbols from AST data.

        Args:
            ast_data: Parsed AST data
            language: Programming language

        Returns:
            Set of exported symbol names
        """
        exports = set()

        # Functions and classes are considered exports
        for func in ast_data.get("functions", []):
            name = func.get("name", "")
            if name and not name.startswith("_"):
                exports.add(name)

        for cls in ast_data.get("classes", []):
            name = cls.get("name", "")
            if name:
                exports.add(name)

        return exports

    def calculate_overall_score(
        self,
        file_contents: Optional[Dict[str, str]] = None,
        include_test_coverage: bool = False,
        test_coverage_score: Optional[float] = None,
    ) -> ArchitectureScore:
        """Calculate overall architecture health score.

        Args:
            file_contents: Dictionary mapping file paths to their content
            include_test_coverage: Whether to include test coverage in scoring
            test_coverage_score: Test coverage score (0-100) if available

        Returns:
            Complete ArchitectureScore with all dimensions
        """
        dimension_scores = []

        # Calculate all dimensions
        dimension_scores.append(self.calculate_coupling_score())
        dimension_scores.append(self.calculate_circular_deps_score())
        dimension_scores.append(self.calculate_layer_violations_score())

        if file_contents:
            dimension_scores.append(self.calculate_cohesion_score(file_contents))
            dimension_scores.append(self.calculate_complexity_score(file_contents))
            dimension_scores.append(self.calculate_unused_exports_score(file_contents))
        else:
            # Use default scores if no file contents provided
            for dimension in [
                ScoreDimension.COHESION,
                ScoreDimension.COMPLEXITY,
                ScoreDimension.UNUSED_EXPORTS,
            ]:
                dimension_scores.append(
                    DimensionScore(
                        dimension=dimension,
                        score=50.0,
                        weight=DIMENSION_WEIGHTS[dimension],
                        details={"message": "No file contents provided for analysis"},
                        issues=["File contents required for detailed analysis"],
                    )
                )

        # Add test coverage if provided
        if include_test_coverage and test_coverage_score is not None:
            dimension_scores.append(
                DimensionScore(
                    dimension=ScoreDimension.TEST_COVERAGE,
                    score=test_coverage_score,
                    weight=DIMENSION_WEIGHTS[ScoreDimension.TEST_COVERAGE],
                    details={"coverage": test_coverage_score},
                    issues=[],
                )
            )

        # Calculate weighted overall score
        total_weight = sum(ds.weight for ds in dimension_scores)
        overall_score = sum(ds.weighted_score for ds in dimension_scores) / total_weight

        # Get category
        category = self.thresholds.get_category(overall_score)

        # Generate recommendations
        recommendations = self._generate_recommendations(dimension_scores)

        return ArchitectureScore(
            overall_score=round(overall_score, 2),
            dimension_scores=dimension_scores,
            category=category,
            recommendations=recommendations,
        )

    def _generate_recommendations(
        self, dimension_scores: List[DimensionScore]
    ) -> List[str]:
        """Generate improvement recommendations based on scores.

        Args:
            dimension_scores: List of dimension scores

        Returns:
            List of recommendation strings
        """
        recommendations = []

        for ds in dimension_scores:
            if ds.score < 60:
                if ds.dimension == ScoreDimension.COUPLING:
                    recommendations.append(
                        "High coupling detected. Consider reducing dependencies between modules."
                    )
                elif ds.dimension == ScoreDimension.COHESION:
                    recommendations.append(
                        "Low cohesion detected. Consider splitting large classes into smaller, focused ones."
                    )
                elif ds.dimension == ScoreDimension.CIRCULAR_DEPS:
                    recommendations.append(
                        "Circular dependencies detected. Review and refactor import structures."
                    )
                elif ds.dimension == ScoreDimension.COMPLEXITY:
                    recommendations.append(
                        "High complexity detected. Consider refactoring complex functions."
                    )
                elif ds.dimension == ScoreDimension.LAYER_VIOLATIONS:
                    recommendations.append(
                        "Layer violations detected. Ensure lower layers don't depend on higher layers."
                    )
                elif ds.dimension == ScoreDimension.UNUSED_EXPORTS:
                    recommendations.append(
                        "Unused exports detected. Consider removing dead code."
                    )

        if not recommendations:
            recommendations.append(
                "Architecture is in good shape. Continue maintaining code quality."
            )

        return recommendations

    def _detect_language(self, file_path: str) -> Optional[str]:
        """Detect programming language from file extension.

        Args:
            file_path: Path to the file

        Returns:
            Language name or None if not supported
        """
        extensions = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".go": "go",
            ".java": "java",
            ".rs": "rust",
            ".c": "c",
            ".cpp": "cpp",
            ".h": "c",
            ".hpp": "cpp",
            ".rb": "ruby",
            ".php": "php",
        }

        for ext, lang in extensions.items():
            if file_path.endswith(ext):
                return lang

        return None
