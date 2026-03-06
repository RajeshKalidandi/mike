"""Data models for Git Intelligence Module."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path


@dataclass
class GitMetrics:
    """Overall git repository metrics.

    Attributes:
        total_commits: Total number of commits in the repository
        total_files: Total number of tracked files
        total_lines: Total lines of code
        churn: Total line changes (added + deleted) in last N commits
        complexity_trend: Trend of complexity over time (positive = increasing)
        bug_fix_commits: Number of commits with bug fix keywords
        avg_commits_per_day: Average commits per day over last 30 days
        top_contributors: List of top 5 contributors by commit count
        timestamp: When the metrics were calculated
        metadata: Additional metrics and metadata
    """

    total_commits: int
    total_files: int
    total_lines: int
    churn: int = 0
    complexity_trend: float = 0.0
    bug_fix_commits: int = 0
    avg_commits_per_day: float = 0.0
    top_contributors: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FileHotspot:
    """Represents a file with high change frequency and bug correlation.

    Hotspot Score = (commits × bug_fixes) / contributors
    Higher scores indicate files that change frequently and have bugs.

    Attributes:
        path: Relative path to the file
        score: Calculated hotspot score
        commit_count: Number of commits touching this file
        bug_fixes: Number of bug fix commits touching this file
        lines_added: Total lines added to this file
        lines_deleted: Total lines deleted from this file
        first_commit: Date of first commit to this file
        last_commit: Date of last commit to this file
        contributor_count: Number of unique contributors
        top_contributors: Top contributors to this file
    """

    path: str
    score: float = 0.0
    commit_count: int = 0
    bug_fixes: int = 0
    lines_added: int = 0
    lines_deleted: int = 0
    first_commit: Optional[datetime] = None
    last_commit: Optional[datetime] = None
    contributor_count: int = 0
    top_contributors: List[str] = field(default_factory=list)

    def calculate_score(self) -> float:
        """Calculate hotspot score: (commits × bug_fixes) / contributors.

        Returns:
            Hotspot score, higher is more problematic
        """
        if self.contributor_count == 0:
            return 0.0
        return (self.commit_count * self.bug_fixes) / self.contributor_count


@dataclass
class AuthorStats:
    """Statistics for a git repository contributor.

    Attributes:
        name: Author name from git config
        email: Author email
        commit_count: Total number of commits
        files_touched: Number of unique files modified
        lines_added: Total lines added
        lines_deleted: Total lines deleted
        first_commit: Date of first commit
        last_commit: Date of most recent commit
        bug_fix_commits: Number of bug fix commits
        avg_commit_size: Average lines changed per commit
        top_files: Most frequently modified files by this author
        contribution_by_month: Monthly commit counts
    """

    name: str
    email: str
    commit_count: int = 0
    files_touched: int = 0
    lines_added: int = 0
    lines_deleted: int = 0
    first_commit: Optional[datetime] = None
    last_commit: Optional[datetime] = None
    bug_fix_commits: int = 0
    avg_commit_size: float = 0.0
    top_files: List[str] = field(default_factory=list)
    contribution_by_month: Dict[str, int] = field(default_factory=dict)

    @property
    def rework_rate(self) -> float:
        """Calculate rework rate: deleted_lines / (added_lines + deleted_lines).

        Returns:
            Rework rate between 0.0 and 1.0, where higher means more rework
        """
        total = self.lines_added + self.lines_deleted
        if total == 0:
            return 0.0
        return self.lines_deleted / total
