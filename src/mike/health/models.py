"""Data models for the Architecture Health Score Engine."""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


class ScoreDimension(Enum):
    """Architecture health score dimensions."""

    COUPLING = "coupling"
    COHESION = "cohesion"
    CIRCULAR_DEPS = "circular_deps"
    COMPLEXITY = "complexity"
    TEST_COVERAGE = "test_coverage"
    LAYER_VIOLATIONS = "layer_violations"
    UNUSED_EXPORTS = "unused_exports"


# Dimension weights for overall score calculation
DIMENSION_WEIGHTS: Dict[ScoreDimension, float] = {
    ScoreDimension.COUPLING: 0.20,
    ScoreDimension.COHESION: 0.15,
    ScoreDimension.CIRCULAR_DEPS: 0.20,
    ScoreDimension.COMPLEXITY: 0.25,
    ScoreDimension.TEST_COVERAGE: 0.10,
    ScoreDimension.LAYER_VIOLATIONS: 0.05,
    ScoreDimension.UNUSED_EXPORTS: 0.05,
}


@dataclass
class DimensionScore:
    """Score for a single architecture dimension."""

    dimension: ScoreDimension
    score: float
    weight: float
    details: Dict
    issues: List[str]

    def __post_init__(self):
        """Validate score is in valid range [0, 100]."""
        if not 0 <= self.score <= 100:
            raise ValueError(f"Score must be between 0 and 100, got {self.score}")

    @property
    def weighted_score(self) -> float:
        """Calculate weighted score contribution."""
        return self.score * self.weight


@dataclass
class ScoreThresholds:
    """Thresholds for health score categorization."""

    excellent: float = 90.0
    good: float = 75.0
    fair: float = 60.0
    poor: float = 40.0

    def get_category(self, score: float) -> str:
        """Get health category for a score.

        Args:
            score: The score to categorize (0-100)

        Returns:
            Category string: 'excellent', 'good', 'fair', 'poor', or 'critical'
        """
        if score >= self.excellent:
            return "excellent"
        elif score >= self.good:
            return "good"
        elif score >= self.fair:
            return "fair"
        elif score >= self.poor:
            return "poor"
        else:
            return "critical"


@dataclass
class ArchitectureScore:
    """Complete architecture health score with all dimensions."""

    overall_score: float
    dimension_scores: List[DimensionScore]
    category: str
    recommendations: List[str]
    timestamp: Optional[str] = None
    metadata: Optional[Dict] = None

    def __post_init__(self):
        """Validate overall score is in valid range."""
        if not 0 <= self.overall_score <= 100:
            raise ValueError(
                f"Overall score must be between 0 and 100, got {self.overall_score}"
            )

    def get_dimension_score(
        self, dimension: ScoreDimension
    ) -> Optional[DimensionScore]:
        """Get score for a specific dimension.

        Args:
            dimension: The dimension to get score for

        Returns:
            DimensionScore if found, None otherwise
        """
        for ds in self.dimension_scores:
            if ds.dimension == dimension:
                return ds
        return None

    def get_issues_by_dimension(self, dimension: ScoreDimension) -> List[str]:
        """Get all issues for a specific dimension.

        Args:
            dimension: The dimension to get issues for

        Returns:
            List of issue strings
        """
        ds = self.get_dimension_score(dimension)
        return ds.issues if ds else []

    def to_dict(self) -> Dict:
        """Convert to dictionary representation.

        Returns:
            Dictionary with all score data
        """
        return {
            "overall_score": self.overall_score,
            "category": self.category,
            "dimensions": [
                {
                    "name": ds.dimension.value,
                    "score": ds.score,
                    "weight": ds.weight,
                    "weighted_score": ds.weighted_score,
                    "details": ds.details,
                    "issues": ds.issues,
                }
                for ds in self.dimension_scores
            ],
            "recommendations": self.recommendations,
            "timestamp": self.timestamp,
            "metadata": self.metadata or {},
        }
