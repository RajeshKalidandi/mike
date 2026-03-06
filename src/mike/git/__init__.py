"""Git Intelligence Module for Mike v2.

Provides git repository analysis capabilities including:
- Code churn metrics
- Hotspot detection
- Bug-prone file identification
- Author statistics
- Rework rate calculation
"""

from .models import GitMetrics, FileHotspot, AuthorStats
from .analyzer import GitAnalyzer

__all__ = ["GitMetrics", "FileHotspot", "AuthorStats", "GitAnalyzer"]
