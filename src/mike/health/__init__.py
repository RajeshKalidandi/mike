"""Architecture Health Score Engine for Mike v2.

This module provides functionality to calculate architecture health scores
based on various metrics like coupling, cohesion, circular dependencies,
complexity, layer violations, and unused exports.
"""

from .models import (
    ArchitectureScore,
    DimensionScore,
    ScoreDimension,
    ScoreThresholds,
    DIMENSION_WEIGHTS,
)
from .calculator import HealthScoreCalculator

__all__ = [
    "ArchitectureScore",
    "DimensionScore",
    "ScoreDimension",
    "ScoreThresholds",
    "DIMENSION_WEIGHTS",
    "HealthScoreCalculator",
]
