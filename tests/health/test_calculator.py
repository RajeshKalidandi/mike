"""Tests for the Architecture Health Score Calculator."""

import pytest
from unittest.mock import Mock, MagicMock

from src.mike.health.models import (
    ArchitectureScore,
    DimensionScore,
    ScoreDimension,
    ScoreThresholds,
    DIMENSION_WEIGHTS,
)
from src.mike.health.calculator import HealthScoreCalculator


class TestScoreDimension:
    """Tests for ScoreDimension enum."""

    def test_dimension_values(self):
        """Test that all expected dimensions exist."""
        assert ScoreDimension.COUPLING.value == "coupling"
        assert ScoreDimension.COHESION.value == "cohesion"
        assert ScoreDimension.CIRCULAR_DEPS.value == "circular_deps"
        assert ScoreDimension.COMPLEXITY.value == "complexity"
        assert ScoreDimension.TEST_COVERAGE.value == "test_coverage"
        assert ScoreDimension.LAYER_VIOLATIONS.value == "layer_violations"
        assert ScoreDimension.UNUSED_EXPORTS.value == "unused_exports"


class TestDimensionScore:
    """Tests for DimensionScore dataclass."""

    def test_valid_score(self):
        """Test creating a valid dimension score."""
        score = DimensionScore(
            dimension=ScoreDimension.COUPLING,
            score=85.0,
            weight=0.20,
            details={"avg_fan_in": 2.5},
            issues=[],
        )
        assert score.dimension == ScoreDimension.COUPLING
        assert score.score == 85.0
        assert score.weighted_score == 17.0  # 85 * 0.20

    def test_invalid_score_low(self):
        """Test that scores below 0 raise ValueError."""
        with pytest.raises(ValueError, match="Score must be between 0 and 100"):
            DimensionScore(
                dimension=ScoreDimension.COUPLING,
                score=-1.0,
                weight=0.20,
                details={},
                issues=[],
            )

    def test_invalid_score_high(self):
        """Test that scores above 100 raise ValueError."""
        with pytest.raises(ValueError, match="Score must be between 0 and 100"):
            DimensionScore(
                dimension=ScoreDimension.COUPLING,
                score=101.0,
                weight=0.20,
                details={},
                issues=[],
            )


class TestScoreThresholds:
    """Tests for ScoreThresholds dataclass."""

    def test_default_thresholds(self):
        """Test default threshold values."""
        thresholds = ScoreThresholds()
        assert thresholds.excellent == 90.0
        assert thresholds.good == 75.0
        assert thresholds.fair == 60.0
        assert thresholds.poor == 40.0

    def test_get_category_excellent(self):
        """Test excellent category."""
        thresholds = ScoreThresholds()
        assert thresholds.get_category(95.0) == "excellent"
        assert thresholds.get_category(90.0) == "excellent"

    def test_get_category_good(self):
        """Test good category."""
        thresholds = ScoreThresholds()
        assert thresholds.get_category(89.0) == "good"
        assert thresholds.get_category(75.0) == "good"

    def test_get_category_fair(self):
        """Test fair category."""
        thresholds = ScoreThresholds()
        assert thresholds.get_category(74.0) == "fair"
        assert thresholds.get_category(60.0) == "fair"

    def test_get_category_poor(self):
        """Test poor category."""
        thresholds = ScoreThresholds()
        assert thresholds.get_category(59.0) == "poor"
        assert thresholds.get_category(40.0) == "poor"

    def test_get_category_critical(self):
        """Test critical category."""
        thresholds = ScoreThresholds()
        assert thresholds.get_category(39.0) == "critical"
        assert thresholds.get_category(0.0) == "critical"


class TestArchitectureScore:
    """Tests for ArchitectureScore dataclass."""

    def test_valid_overall_score(self):
        """Test creating a valid architecture score."""
        dimensions = [
            DimensionScore(
                dimension=ScoreDimension.COUPLING,
                score=80.0,
                weight=0.20,
                details={},
                issues=[],
            )
        ]
        score = ArchitectureScore(
            overall_score=80.0,
            dimension_scores=dimensions,
            category="good",
            recommendations=["Keep improving"],
        )
        assert score.overall_score == 80.0
        assert len(score.dimension_scores) == 1

    def test_invalid_overall_score(self):
        """Test that overall scores outside 0-100 raise ValueError."""
        with pytest.raises(ValueError, match="Overall score must be between 0 and 100"):
            ArchitectureScore(
                overall_score=150.0,
                dimension_scores=[],
                category="invalid",
                recommendations=[],
            )

    def test_get_dimension_score(self):
        """Test retrieving a specific dimension score."""
        dimensions = [
            DimensionScore(
                dimension=ScoreDimension.COUPLING,
                score=80.0,
                weight=0.20,
                details={},
                issues=["issue1"],
            ),
            DimensionScore(
                dimension=ScoreDimension.COHESION,
                score=70.0,
                weight=0.15,
                details={},
                issues=[],
            ),
        ]
        score = ArchitectureScore(
            overall_score=75.0,
            dimension_scores=dimensions,
            category="good",
            recommendations=[],
        )

        coupling_score = score.get_dimension_score(ScoreDimension.COUPLING)
        assert coupling_score is not None
        assert coupling_score.score == 80.0

        missing_score = score.get_dimension_score(ScoreDimension.COMPLEXITY)
        assert missing_score is None

    def test_get_issues_by_dimension(self):
        """Test retrieving issues for a specific dimension."""
        dimensions = [
            DimensionScore(
                dimension=ScoreDimension.COUPLING,
                score=80.0,
                weight=0.20,
                details={},
                issues=["issue1", "issue2"],
            ),
        ]
        score = ArchitectureScore(
            overall_score=80.0,
            dimension_scores=dimensions,
            category="good",
            recommendations=[],
        )

        issues = score.get_issues_by_dimension(ScoreDimension.COUPLING)
        assert len(issues) == 2
        assert "issue1" in issues

    def test_to_dict(self):
        """Test conversion to dictionary."""
        dimensions = [
            DimensionScore(
                dimension=ScoreDimension.COUPLING,
                score=80.0,
                weight=0.20,
                details={"detail": "value"},
                issues=["issue"],
            ),
        ]
        score = ArchitectureScore(
            overall_score=80.0,
            dimension_scores=dimensions,
            category="good",
            recommendations=["rec1"],
            timestamp="2024-01-01",
        )

        result = score.to_dict()
        assert result["overall_score"] == 80.0
        assert result["category"] == "good"
        assert len(result["dimensions"]) == 1
        assert result["recommendations"] == ["rec1"]
        assert result["timestamp"] == "2024-01-01"


class TestHealthScoreCalculator:
    """Tests for HealthScoreCalculator."""

    @pytest.fixture
    def mock_graph_builder(self):
        """Create a mock graph builder."""
        mock = Mock()
        mock.graph = Mock()
        mock.graph.number_of_nodes.return_value = 0
        mock.graph.nodes.return_value = []
        mock.graph.edges.return_value = []
        mock.graph.in_degree.return_value = 0
        mock.graph.out_degree.return_value = 0
        mock.find_cycles.return_value = []
        return mock

    @pytest.fixture
    def mock_parser(self):
        """Create a mock parser."""
        mock = Mock()
        return mock

    @pytest.fixture
    def calculator(self, mock_graph_builder, mock_parser):
        """Create a calculator instance."""
        return HealthScoreCalculator(mock_graph_builder, mock_parser)

    def test_calculate_coupling_score_empty_graph(self, calculator, mock_graph_builder):
        """Test coupling score with empty graph."""
        mock_graph_builder.graph.number_of_nodes.return_value = 0

        result = calculator.calculate_coupling_score()

        assert result.dimension == ScoreDimension.COUPLING
        assert result.score == 100.0
        assert result.weight == DIMENSION_WEIGHTS[ScoreDimension.COUPLING]

    def test_calculate_coupling_score_with_dependencies(
        self, calculator, mock_graph_builder
    ):
        """Test coupling score with file dependencies."""
        mock_graph_builder.graph.number_of_nodes.return_value = 3
        mock_graph_builder.graph.nodes.return_value = ["a.py", "b.py", "c.py"]

        # Set up fan-in/fan-out
        def mock_in_degree(node):
            return {"a.py": 2, "b.py": 1, "c.py": 0}[node]

        def mock_out_degree(node):
            return {"a.py": 0, "b.py": 1, "c.py": 2}[node]

        mock_graph_builder.graph.in_degree.side_effect = mock_in_degree
        mock_graph_builder.graph.out_degree.side_effect = mock_out_degree

        result = calculator.calculate_coupling_score()

        assert result.dimension == ScoreDimension.COUPLING
        assert 0 <= result.score <= 100
        assert "avg_fan_in" in result.details
        assert "avg_fan_out" in result.details

    def test_calculate_circular_deps_score_no_cycles(
        self, calculator, mock_graph_builder
    ):
        """Test circular deps score with no cycles."""
        mock_graph_builder.find_cycles.return_value = []

        result = calculator.calculate_circular_deps_score()

        assert result.dimension == ScoreDimension.CIRCULAR_DEPS
        assert result.score == 100.0
        assert result.details["cycle_count"] == 0

    def test_calculate_circular_deps_score_with_cycles(
        self, calculator, mock_graph_builder
    ):
        """Test circular deps score with cycles."""
        mock_graph_builder.find_cycles.return_value = [
            ["a.py", "b.py", "c.py", "a.py"],
            ["d.py", "e.py", "d.py"],
        ]

        result = calculator.calculate_circular_deps_score()

        assert result.dimension == ScoreDimension.CIRCULAR_DEPS
        assert result.score < 100.0
        assert result.details["cycle_count"] == 2

    def test_calculate_layer_violations_score_no_config(self, calculator):
        """Test layer violations score with no layer config."""
        result = calculator.calculate_layer_violations_score()

        assert result.dimension == ScoreDimension.LAYER_VIOLATIONS
        assert result.score == 100.0
        assert "No layer configuration" in result.details["message"]

    def test_calculate_layer_violations_score_with_violations(
        self, mock_graph_builder, mock_parser
    ):
        """Test layer violations score with actual violations."""
        layer_config = {
            "domain": ["domain/"],
            "application": ["application/"],
            "infrastructure": ["infrastructure/"],
        }

        # Mock edges with layer violations (domain -> infrastructure)
        mock_graph_builder.graph.edges.return_value = [
            ("domain/models.py", "infrastructure/db.py", {"type": "import"}),
        ]

        calculator = HealthScoreCalculator(
            mock_graph_builder, mock_parser, layer_config=layer_config
        )

        result = calculator.calculate_layer_violations_score()

        # Domain layer (index 0) depends on infrastructure (index 2) - this is a violation
        assert result.dimension == ScoreDimension.LAYER_VIOLATIONS
        assert result.details["violation_count"] == 1

    def test_calculate_overall_score_without_file_contents(self, calculator):
        """Test overall score calculation without file contents."""
        result = calculator.calculate_overall_score()

        assert isinstance(result, ArchitectureScore)
        assert 0 <= result.overall_score <= 100
        assert result.category in ["excellent", "good", "fair", "poor", "critical"]
        assert len(result.dimension_scores) > 0
        assert len(result.recommendations) > 0

    def test_calculate_overall_score_with_file_contents(self, calculator, mock_parser):
        """Test overall score calculation with file contents."""
        file_contents = {
            "test.py": "def hello(): pass",
        }

        # Mock parser response
        mock_parser.parse.return_value = {
            "functions": [{"name": "hello", "parameters": []}],
            "classes": [],
            "imports": [],
            "language": "python",
        }

        result = calculator.calculate_overall_score(file_contents=file_contents)

        assert isinstance(result, ArchitectureScore)
        assert 0 <= result.overall_score <= 100
        mock_parser.parse.assert_called()

    def test_calculate_overall_score_with_test_coverage(self, calculator):
        """Test overall score with test coverage included."""
        result = calculator.calculate_overall_score(
            include_test_coverage=True,
            test_coverage_score=85.0,
        )

        coverage_score = result.get_dimension_score(ScoreDimension.TEST_COVERAGE)
        assert coverage_score is not None
        assert coverage_score.score == 85.0

    def test_cohesion_score_empty_files(self, calculator):
        """Test cohesion score with no files."""
        result = calculator.calculate_cohesion_score({})

        assert result.dimension == ScoreDimension.COHESION
        assert result.score == 100.0

    def test_complexity_score_empty_files(self, calculator):
        """Test complexity score with no files."""
        result = calculator.calculate_complexity_score({})

        assert result.dimension == ScoreDimension.COMPLEXITY
        assert result.score == 100.0

    def test_unused_exports_score_empty_files(self, calculator):
        """Test unused exports score with no files."""
        result = calculator.calculate_unused_exports_score({})

        assert result.dimension == ScoreDimension.UNUSED_EXPORTS
        assert result.score == 100.0

    def test_calculate_cyclomatic_complexity(self, calculator):
        """Test cyclomatic complexity calculation."""
        code = """
def simple():
    pass

def complex_func(x):
    if x > 0:
        if x > 10:
            return True
        else:
            return False
    elif x < 0:
        for i in range(10):
            if i % 2 == 0:
                print(i)
    return None
"""
        complexity = calculator._calculate_cyclomatic_complexity(code, "python")

        assert complexity > 1  # Base complexity
        # Should detect: if, if, elif, for, if = at least 5 decision points + 1 base

    def test_detect_language(self, calculator):
        """Test language detection from file extension."""
        assert calculator._detect_language("test.py") == "python"
        assert calculator._detect_language("test.js") == "javascript"
        assert calculator._detect_language("test.ts") == "typescript"
        assert calculator._detect_language("test.go") == "go"
        assert calculator._detect_language("test.java") == "java"
        assert calculator._detect_language("test.rs") == "rust"
        assert calculator._detect_language("test.c") == "c"
        assert calculator._detect_language("test.cpp") == "cpp"
        assert calculator._detect_language("test.rb") == "ruby"
        assert calculator._detect_language("test.php") == "php"
        assert calculator._detect_language("test.unknown") is None

    def test_get_file_layer(self, mock_graph_builder, mock_parser):
        """Test file layer detection."""
        layer_config = {
            "domain": ["domain/"],
            "application": ["application/"],
        }

        calculator = HealthScoreCalculator(
            mock_graph_builder, mock_parser, layer_config=layer_config
        )

        assert calculator._get_file_layer("domain/models.py") == "domain"
        assert calculator._get_file_layer("application/services.py") == "application"
        assert calculator._get_file_layer("other/file.py") is None

    def test_calculate_lcom_heuristic(self, calculator):
        """Test LCOM heuristic calculation."""
        # Single method - perfect cohesion
        assert calculator._calculate_lcom_heuristic([{"name": "m1"}]) == 0.0

        # 2 methods - good cohesion
        methods = [{"name": "m1"}, {"name": "m2"}]
        assert calculator._calculate_lcom_heuristic(methods) == 0.2

        # 10 methods - moderate cohesion
        methods = [{"name": f"m{i}"} for i in range(10)]
        assert calculator._calculate_lcom_heuristic(methods) == 0.4

        # 20 methods - poor cohesion
        methods = [{"name": f"m{i}"} for i in range(20)]
        assert calculator._calculate_lcom_heuristic(methods) > 0.7

    def test_extract_exports(self, calculator):
        """Test export extraction from AST data."""
        ast_data = {
            "functions": [
                {"name": "public_func"},
                {"name": "_private_func"},  # Should be excluded
            ],
            "classes": [
                {"name": "MyClass"},
            ],
        }

        exports = calculator._extract_exports(ast_data, "python")

        assert "public_func" in exports
        assert "_private_func" not in exports
        assert "MyClass" in exports

    def test_generate_recommendations_high_scores(self, calculator):
        """Test recommendations generation with good scores."""
        dimensions = [
            DimensionScore(
                dimension=ScoreDimension.COUPLING,
                score=85.0,
                weight=0.20,
                details={},
                issues=[],
            ),
        ]

        recommendations = calculator._generate_recommendations(dimensions)

        assert len(recommendations) == 1
        assert "good shape" in recommendations[0].lower()

    def test_generate_recommendations_low_scores(self, calculator):
        """Test recommendations generation with poor scores."""
        dimensions = [
            DimensionScore(
                dimension=ScoreDimension.COUPLING,
                score=50.0,
                weight=0.20,
                details={},
                issues=["High coupling"],
            ),
            DimensionScore(
                dimension=ScoreDimension.COHESION,
                score=45.0,
                weight=0.15,
                details={},
                issues=["Low cohesion"],
            ),
        ]

        recommendations = calculator._generate_recommendations(dimensions)

        assert len(recommendations) >= 2
        assert any("coupling" in r.lower() for r in recommendations)
        assert any("cohesion" in r.lower() for r in recommendations)
