"""Git repository analyzer for calculating code metrics.

This module provides the GitAnalyzer class for analyzing git repositories
and calculating various code metrics including churn, hotspots, bug-prone files,
author statistics, and rework rates.
"""

import re
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
import git
from git import Repo, Commit
from git.exc import InvalidGitRepositoryError

from .models import GitMetrics, FileHotspot, AuthorStats


class GitAnalyzer:
    """Analyzer for git repository metrics and statistics.

    Provides methods to calculate code churn, identify hotspots,
    detect bug-prone files, and analyze contributor statistics.

    Example:
        analyzer = GitAnalyzer('/path/to/repo')
        metrics = analyzer.analyze_repository()
        hotspots = analyzer.identify_hotspots(limit=10)
    """

    # Keywords that indicate bug fixes in commit messages
    BUG_FIX_PATTERNS = [
        r"\bfix(?:ed|es|ing)?\b",
        r"\bbug(?:s)?\b",
        r"\berror(?:s)?\b",
        r"\bissue(?:s)?\b",
        r"\brepair(?:ed|s|ing)?\b",
        r"\bcorrect(?:ed|s|ing)?\b",
        r"\bresolve(?:d|s|ing)?\b",
        r"\bhotfix\b",
        r"\bbugfix\b",
    ]

    def __init__(self, repo_path: str = "."):
        """Initialize the GitAnalyzer.

        Args:
            repo_path: Path to the git repository. Defaults to current directory.

        Raises:
            InvalidGitRepositoryError: If the path is not a valid git repository.
        """
        self.repo_path = Path(repo_path).resolve()
        try:
            self.repo = Repo(str(self.repo_path))
        except InvalidGitRepositoryError as e:
            raise InvalidGitRepositoryError(
                f"'{repo_path}' is not a valid git repository"
            ) from e

        # Compile bug fix pattern
        self._bug_fix_regex = re.compile("|".join(self.BUG_FIX_PATTERNS), re.IGNORECASE)

    def analyze_repository(
        self, limit: int = 1000, since_days: Optional[int] = 30
    ) -> GitMetrics:
        """Analyze the repository and calculate comprehensive metrics.

        Args:
            limit: Maximum number of commits to analyze
            since_days: Only analyze commits from last N days (None for all)

        Returns:
            GitMetrics object with comprehensive repository statistics
        """
        commits = self._get_commits(limit, since_days)

        total_commits = len(commits)
        total_files = len(list(self.repo.git.ls_files().split("\n")))

        # Count total lines (excluding binary files)
        total_lines = self._count_total_lines()

        # Calculate churn
        churn = self.calculate_churn(limit, since_days)

        # Count bug fix commits
        bug_fix_commits = sum(
            1 for commit in commits if self._is_bug_fix_commit(commit)
        )

        # Calculate avg commits per day
        avg_commits_per_day = self._calculate_avg_commits_per_day(commits)

        # Get top contributors
        top_contributors = self._get_top_contributors(commits, limit=5)

        return GitMetrics(
            total_commits=total_commits,
            total_files=total_files,
            total_lines=total_lines,
            churn=churn,
            bug_fix_commits=bug_fix_commits,
            avg_commits_per_day=avg_commits_per_day,
            top_contributors=top_contributors,
            timestamp=datetime.now(),
        )

    def calculate_churn(
        self, limit: int = 100, since_days: Optional[int] = None
    ) -> int:
        """Calculate total line changes (added + deleted) in the specified commits.

        Churn represents the total activity in the codebase. High churn areas
        are often sources of instability.

        Args:
            limit: Maximum number of commits to analyze
            since_days: Only analyze commits from last N days (None for all)

        Returns:
            Total number of line changes (added + deleted)
        """
        commits = self._get_commits(limit, since_days)
        total_churn = 0

        for commit in commits:
            if not commit.parents:
                # First commit in repo
                continue

            try:
                diff = commit.parents[0].diff(commit, create_patch=True)
                for d in diff:
                    if d.diff:
                        # Count lines added and deleted
                        diff_text = d.diff.decode("utf-8", errors="ignore")
                        added = sum(
                            1
                            for line in diff_text.split("\n")
                            if line.startswith("+") and not line.startswith("+++")
                        )
                        deleted = sum(
                            1
                            for line in diff_text.split("\n")
                            if line.startswith("-") and not line.startswith("---")
                        )
                        total_churn += added + deleted
            except Exception:
                # Skip commits that can't be diffed
                continue

        return total_churn

    def identify_hotspots(
        self, limit: int = 100, top_n: int = 10, since_days: Optional[int] = None
    ) -> List[FileHotspot]:
        """Identify files with high change frequency and bug correlation.

        Hotspots are files that change frequently and have a high correlation
        with bug fixes. These files are candidates for refactoring attention.

        Args:
            limit: Maximum number of commits to analyze
            top_n: Number of top hotspots to return
            since_days: Only analyze commits from last N days (None for all)

        Returns:
            List of FileHotspot objects sorted by score (highest first)
        """
        commits = self._get_commits(limit, since_days)
        file_stats: Dict[str, Dict] = defaultdict(
            lambda: {
                "commits": 0,
                "bug_fixes": 0,
                "lines_added": 0,
                "lines_deleted": 0,
                "contributors": set(),
                "first_commit": None,
                "last_commit": None,
                "contributor_commits": defaultdict(int),
            }
        )

        for commit in commits:
            is_bug_fix = self._is_bug_fix_commit(commit)

            # Get files changed in this commit
            try:
                if commit.parents:
                    diff = commit.parents[0].diff(commit)
                else:
                    diff = commit.diff(git.NULL_TREE)

                for d in diff:
                    file_path = d.a_path or d.b_path
                    if not file_path:
                        continue

                    stats = file_stats[file_path]
                    stats["commits"] += 1
                    stats["contributors"].add(commit.author.email or commit.author.name)
                    stats["contributor_commits"][
                        commit.author.email or commit.author.name
                    ] += 1

                    if is_bug_fix:
                        stats["bug_fixes"] += 1

                    # Track commit dates
                    commit_date = datetime.fromtimestamp(commit.committed_date)
                    if (
                        stats["first_commit"] is None
                        or commit_date < stats["first_commit"]
                    ):
                        stats["first_commit"] = commit_date
                    if (
                        stats["last_commit"] is None
                        or commit_date > stats["last_commit"]
                    ):
                        stats["last_commit"] = commit_date

                    # Count line changes
                    if d.diff:
                        try:
                            diff_text = d.diff.decode("utf-8", errors="ignore")
                            stats["lines_added"] += sum(
                                1
                                for line in diff_text.split("\n")
                                if line.startswith("+") and not line.startswith("+++")
                            )
                            stats["lines_deleted"] += sum(
                                1
                                for line in diff_text.split("\n")
                                if line.startswith("-") and not line.startswith("---")
                            )
                        except:
                            pass
            except Exception:
                continue

        # Create hotspot objects and calculate scores
        hotspots = []
        for file_path, stats in file_stats.items():
            # Get top contributors for this file
            sorted_contributors = sorted(
                stats["contributor_commits"].items(), key=lambda x: x[1], reverse=True
            )
            top_contributors = [email for email, count in sorted_contributors[:3]]

            hotspot = FileHotspot(
                path=file_path,
                commit_count=stats["commits"],
                bug_fixes=stats["bug_fixes"],
                lines_added=stats["lines_added"],
                lines_deleted=stats["lines_deleted"],
                first_commit=stats["first_commit"],
                last_commit=stats["last_commit"],
                contributor_count=len(stats["contributors"]),
                top_contributors=top_contributors,
            )
            hotspot.score = hotspot.calculate_score()
            hotspots.append(hotspot)

        # Sort by score (descending) and return top N
        hotspots.sort(key=lambda x: x.score, reverse=True)
        return hotspots[:top_n]

    def detect_bug_prone_files(
        self, limit: int = 500, min_bug_fixes: int = 2
    ) -> List[FileHotspot]:
        """Detect files with many bug fix commits.

        Files with many bug fix commits are often complex or problematic
        and may benefit from refactoring or additional testing.

        Args:
            limit: Maximum number of commits to analyze
            min_bug_fixes: Minimum number of bug fixes to be considered bug-prone

        Returns:
            List of FileHotspot objects for bug-prone files
        """
        hotspots = self.identify_hotspots(limit, top_n=1000)
        return [h for h in hotspots if h.bug_fixes >= min_bug_fixes]

    def get_author_stats(
        self, limit: int = 1000, since_days: Optional[int] = None
    ) -> List[AuthorStats]:
        """Get contributor statistics for the repository.

        Args:
            limit: Maximum number of commits to analyze
            since_days: Only analyze commits from last N days (None for all)

        Returns:
            List of AuthorStats objects sorted by commit count
        """
        commits = self._get_commits(limit, since_days)
        author_data: Dict[str, Dict] = defaultdict(
            lambda: {
                "name": "",
                "email": "",
                "commits": 0,
                "files": set(),
                "lines_added": 0,
                "lines_deleted": 0,
                "first_commit": None,
                "last_commit": None,
                "bug_fix_commits": 0,
                "file_commits": defaultdict(int),
                "monthly_commits": defaultdict(int),
            }
        )

        for commit in commits:
            author_email = commit.author.email or commit.author.name
            author_name = commit.author.name or commit.author.email

            if not author_email:
                continue

            data = author_data[author_email]
            data["name"] = author_name
            data["email"] = author_email
            data["commits"] += 1

            # Track commit dates
            commit_date = datetime.fromtimestamp(commit.committed_date)
            month_key = commit_date.strftime("%Y-%m")
            data["monthly_commits"][month_key] += 1

            if data["first_commit"] is None or commit_date < data["first_commit"]:
                data["first_commit"] = commit_date
            if data["last_commit"] is None or commit_date > data["last_commit"]:
                data["last_commit"] = commit_date

            # Check if bug fix commit
            if self._is_bug_fix_commit(commit):
                data["bug_fix_commits"] += 1

            # Get files and line changes
            try:
                if commit.parents:
                    diff = commit.parents[0].diff(commit)
                else:
                    diff = commit.diff(git.NULL_TREE)

                for d in diff:
                    file_path = d.a_path or d.b_path
                    if file_path:
                        data["files"].add(file_path)
                        data["file_commits"][file_path] += 1

                    if d.diff:
                        try:
                            diff_text = d.diff.decode("utf-8", errors="ignore")
                            data["lines_added"] += sum(
                                1
                                for line in diff_text.split("\n")
                                if line.startswith("+") and not line.startswith("+++")
                            )
                            data["lines_deleted"] += sum(
                                1
                                for line in diff_text.split("\n")
                                if line.startswith("-") and not line.startswith("---")
                            )
                        except:
                            pass
            except Exception:
                continue

        # Create AuthorStats objects
        stats = []
        for email, data in author_data.items():
            # Get top files for this author
            sorted_files = sorted(
                data["file_commits"].items(), key=lambda x: x[1], reverse=True
            )
            top_files = [f for f, count in sorted_files[:5]]

            author_stat = AuthorStats(
                name=data["name"],
                email=data["email"],
                commit_count=data["commits"],
                files_touched=len(data["files"]),
                lines_added=data["lines_added"],
                lines_deleted=data["lines_deleted"],
                first_commit=data["first_commit"],
                last_commit=data["last_commit"],
                bug_fix_commits=data["bug_fix_commits"],
                avg_commit_size=(data["lines_added"] + data["lines_deleted"])
                / max(data["commits"], 1),
                top_files=top_files,
                contribution_by_month=dict(data["monthly_commits"]),
            )
            stats.append(author_stat)

        # Sort by commit count (descending)
        stats.sort(key=lambda x: x.commit_count, reverse=True)
        return stats

    def calculate_rework_rate(
        self,
        file_path: Optional[str] = None,
        limit: int = 100,
        since_days: Optional[int] = None,
    ) -> float:
        """Calculate rework rate: deleted_lines / (added_lines + deleted_lines).

        Rework rate indicates how much code is being modified vs. new code being
        added. A high rework rate may indicate instability or technical debt.

        Args:
            file_path: Specific file to analyze (None for entire repo)
            limit: Maximum number of commits to analyze
            since_days: Only analyze commits from last N days (None for all)

        Returns:
            Rework rate between 0.0 and 1.0
        """
        commits = self._get_commits(limit, since_days)
        total_added = 0
        total_deleted = 0

        for commit in commits:
            try:
                if commit.parents:
                    diff = commit.parents[0].diff(commit)
                else:
                    diff = commit.diff(git.NULL_TREE)

                for d in diff:
                    # Filter by file path if specified
                    if file_path:
                        current_path = d.a_path or d.b_path
                        if current_path != file_path:
                            continue

                    if d.diff:
                        try:
                            diff_text = d.diff.decode("utf-8", errors="ignore")
                            total_added += sum(
                                1
                                for line in diff_text.split("\n")
                                if line.startswith("+") and not line.startswith("+++")
                            )
                            total_deleted += sum(
                                1
                                for line in diff_text.split("\n")
                                if line.startswith("-") and not line.startswith("---")
                            )
                        except:
                            pass
            except Exception:
                continue

        total = total_added + total_deleted
        if total == 0:
            return 0.0

        return total_deleted / total

    def _get_commits(
        self, limit: int = 100, since_days: Optional[int] = None
    ) -> List[Commit]:
        """Get commits from the repository.

        Args:
            limit: Maximum number of commits to return
            since_days: Only return commits from last N days (None for all)

        Returns:
            List of Commit objects
        """
        # Check if repo has any commits
        try:
            self.repo.head.commit
        except ValueError:
            # No commits in repository yet
            return []

        kwargs = {"max_count": limit}

        if since_days is not None:
            since_date = datetime.now() - timedelta(days=since_days)
            kwargs["since"] = since_date.strftime("%Y-%m-%d")

        try:
            return list(self.repo.iter_commits(**kwargs))
        except ValueError:
            # No commits match the criteria
            return []

    def _is_bug_fix_commit(self, commit: Commit) -> bool:
        """Check if a commit message indicates a bug fix.

        Args:
            commit: Git commit object

        Returns:
            True if commit appears to be a bug fix
        """
        message = commit.message.lower()
        return bool(self._bug_fix_regex.search(message))

    def _count_total_lines(self) -> int:
        """Count total lines in tracked text files.

        Returns:
            Total number of lines
        """
        total = 0
        try:
            for item in self.repo.head.commit.tree.traverse():
                if item.type == "blob":
                    try:
                        content = item.data_stream.read().decode(
                            "utf-8", errors="ignore"
                        )
                        total += len(content.split("\n"))
                    except:
                        pass
        except:
            pass
        return total

    def _calculate_avg_commits_per_day(self, commits: List[Commit]) -> float:
        """Calculate average commits per day.

        Args:
            commits: List of commits

        Returns:
            Average commits per day
        """
        if not commits:
            return 0.0

        dates = [datetime.fromtimestamp(c.committed_date) for c in commits]
        if not dates:
            return 0.0

        min_date = min(dates)
        max_date = max(dates)
        days = max(1, (max_date - min_date).days)

        return len(commits) / days

    def _get_top_contributors(self, commits: List[Commit], limit: int = 5) -> List[str]:
        """Get top contributors by commit count.

        Args:
            commits: List of commits
            limit: Number of top contributors to return

        Returns:
            List of contributor names/emails
        """
        counts: Dict[str, int] = defaultdict(int)
        for commit in commits:
            author = commit.author.name or commit.author.email or "Unknown"
            counts[author] += 1

        sorted_contributors = sorted(counts.items(), key=lambda x: x[1], reverse=True)
        return [name for name, count in sorted_contributors[:limit]]
