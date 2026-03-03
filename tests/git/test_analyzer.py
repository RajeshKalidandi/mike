"""Tests for Git Intelligence Module analyzer."""

import os
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from git import Repo, Actor
from git.exc import InvalidGitRepositoryError

from mike.git.analyzer import GitAnalyzer
from mike.git.models import GitMetrics, FileHotspot, AuthorStats


@pytest.fixture
def temp_git_repo():
    """Create a temporary git repository for testing."""
    temp_dir = tempfile.mkdtemp()
    # Resolve any symlinks in the path (macOS temp dirs are symlinked)
    temp_dir = os.path.realpath(temp_dir)
    repo = Repo.init(temp_dir)

    # Configure git user
    config = repo.config_writer()
    config.set_value("user", "name", "Test User")
    config.set_value("user", "email", "test@example.com")
    config.release()

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def populated_repo(temp_git_repo):
    """Create a repo with sample commits for testing."""
    repo_path = temp_git_repo
    repo = Repo(repo_path)

    # Create some test files (use relative paths for git)
    file1_path = os.path.join(repo_path, "test_file.py")
    with open(file1_path, "w") as f:
        f.write("print('hello')\n")

    file2_path = os.path.join(repo_path, "buggy_file.py")
    with open(file2_path, "w") as f:
        f.write("def func():\n    pass\n")

    # First commit
    repo.index.add(["test_file.py", "buggy_file.py"])
    repo.index.commit("Initial commit")

    # Second commit - add lines
    with open(file1_path, "w") as f:
        f.write("print('hello')\nprint('world')\n")
    repo.index.add(["test_file.py"])
    repo.index.commit("Add more code")

    # Third commit - bug fix
    with open(file2_path, "w") as f:
        f.write("def func():\n    return 42\n")
    repo.index.add(["buggy_file.py"])
    repo.index.commit("Fix bug in function")

    # Fourth commit - another change
    file3_path = os.path.join(repo_path, "another_file.py")
    with open(file3_path, "w") as f:
        f.write("# New file\n")
    repo.index.add(["another_file.py"])
    repo.index.commit("Add another file")

    return repo_path


class TestGitAnalyzerInitialization:
    """Test suite for GitAnalyzer initialization."""

    def test_init_with_valid_repo(self, temp_git_repo):
        """Test initialization with a valid git repository."""
        analyzer = GitAnalyzer(temp_git_repo)
        assert analyzer.repo_path == Path(temp_git_repo).resolve()
        assert analyzer.repo is not None

    def test_init_with_current_directory(self, temp_git_repo):
        """Test initialization defaults to current directory."""
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_git_repo)
            analyzer = GitAnalyzer()
            assert analyzer.repo_path == Path(temp_git_repo).resolve()
        finally:
            os.chdir(original_cwd)

    def test_init_with_invalid_repo(self):
        """Test initialization fails with invalid repository."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(InvalidGitRepositoryError):
                GitAnalyzer(temp_dir)


class TestGitAnalyzerBugFixDetection:
    """Test suite for bug fix commit detection."""

    @pytest.mark.parametrize(
        "message,expected",
        [
            ("Fix bug in authentication", True),
            ("Fixed the error handling", True),
            ("Fixing broken tests", True),
            ("Bug fix for login issue", True),
            ("Resolve error in parsing", True),
            ("Hotfix for production", True),
            ("Bugfix: correct calculation", True),
            ("Add new feature", False),
            ("Update documentation", False),
            ("Refactor code", False),
            ("FIX: uppercase bug fix", True),
            ("BUG in the system", True),
        ],
    )
    def test_is_bug_fix_commit(self, temp_git_repo, message, expected):
        """Test detection of bug fix commits from messages."""
        analyzer = GitAnalyzer(temp_git_repo)

        # Create a commit with the given message
        repo = analyzer.repo
        file_path = os.path.join(temp_git_repo, "test.txt")
        with open(file_path, "w") as f:
            f.write("test\n")

        repo.index.add(["test.txt"])
        commit = repo.index.commit(message)

        assert analyzer._is_bug_fix_commit(commit) == expected


class TestGitAnalyzerMetrics:
    """Test suite for repository metrics calculation."""

    def test_analyze_repository_basic(self, populated_repo):
        """Test basic repository analysis."""
        analyzer = GitAnalyzer(populated_repo)
        metrics = analyzer.analyze_repository()

        assert isinstance(metrics, GitMetrics)
        assert metrics.total_commits == 4
        assert metrics.total_files == 3
        assert metrics.total_lines >= 0
        assert metrics.timestamp is not None

    def test_analyze_repository_with_limit(self, populated_repo):
        """Test analysis with commit limit."""
        analyzer = GitAnalyzer(populated_repo)
        metrics = analyzer.analyze_repository(limit=2)

        assert metrics.total_commits == 2

    def test_analyze_repository_with_since_days(self, populated_repo):
        """Test analysis with since_days filter."""
        analyzer = GitAnalyzer(populated_repo)
        # All commits are recent, so should return all
        metrics = analyzer.analyze_repository(since_days=1)

        # Should get all 4 commits (all made in the last day)
        assert metrics.total_commits == 4

    def test_calculate_churn(self, populated_repo):
        """Test churn calculation."""
        analyzer = GitAnalyzer(populated_repo)
        churn = analyzer.calculate_churn()

        # Churn should be greater than 0 (we made changes)
        assert churn > 0

    def test_calculate_churn_with_limit(self, populated_repo):
        """Test churn calculation with limit."""
        analyzer = GitAnalyzer(populated_repo)
        churn_limited = analyzer.calculate_churn(limit=2)
        churn_all = analyzer.calculate_churn(limit=100)

        # Limited churn should be less than or equal to all churn
        assert churn_limited <= churn_all


class TestGitAnalyzerHotspots:
    """Test suite for hotspot identification."""

    def test_identify_hotspots(self, populated_repo):
        """Test hotspot identification."""
        analyzer = GitAnalyzer(populated_repo)
        hotspots = analyzer.identify_hotspots()

        assert isinstance(hotspots, list)
        assert len(hotspots) > 0

        # All items should be FileHotspot instances
        for hotspot in hotspots:
            assert isinstance(hotspot, FileHotspot)
            assert hotspot.path is not None
            assert hotspot.commit_count >= 0

    def test_identify_hotspots_with_limit(self, populated_repo):
        """Test hotspot identification with limit."""
        analyzer = GitAnalyzer(populated_repo)
        hotspots = analyzer.identify_hotspots(top_n=2)

        assert len(hotspots) <= 2

    def test_identify_hotspots_sorted_by_score(self, populated_repo):
        """Test hotspots are sorted by score."""
        analyzer = GitAnalyzer(populated_repo)
        hotspots = analyzer.identify_hotspots()

        if len(hotspots) > 1:
            # Scores should be in descending order
            for i in range(len(hotspots) - 1):
                assert hotspots[i].score >= hotspots[i + 1].score

    def test_hotspot_score_calculation(self):
        """Test hotspot score calculation."""
        hotspot = FileHotspot(
            path="test.py", commit_count=10, bug_fixes=5, contributor_count=2
        )

        expected_score = (10 * 5) / 2
        assert hotspot.calculate_score() == expected_score

    def test_hotspot_score_with_zero_contributors(self):
        """Test hotspot score with zero contributors."""
        hotspot = FileHotspot(
            path="test.py", commit_count=5, bug_fixes=3, contributor_count=0
        )

        assert hotspot.calculate_score() == 0.0


class TestGitAnalyzerBugProneFiles:
    """Test suite for bug-prone file detection."""

    def test_detect_bug_prone_files(self, temp_git_repo):
        """Test detection of bug-prone files."""
        analyzer = GitAnalyzer(temp_git_repo)
        repo = analyzer.repo

        # Create a file with multiple bug fixes
        file_path = os.path.join(temp_git_repo, "buggy.py")
        with open(file_path, "w") as f:
            f.write("def buggy(): pass\n")
        repo.index.add(["buggy.py"])
        repo.index.commit("Initial buggy file")

        # Bug fix 1
        with open(file_path, "w") as f:
            f.write("def buggy(): return 1\n")
        repo.index.add(["buggy.py"])
        repo.index.commit("Fix bug #1")

        # Bug fix 2
        with open(file_path, "w") as f:
            f.write("def buggy(): return 2\n")
        repo.index.add(["buggy.py"])
        repo.index.commit("Fix another bug")

        bug_prone = analyzer.detect_bug_prone_files(min_bug_fixes=2)

        assert len(bug_prone) > 0
        assert any(h.path == "buggy.py" for h in bug_prone)

    def test_detect_bug_prone_files_with_min_bug_fixes(self, temp_git_repo):
        """Test bug-prone detection with minimum threshold."""
        analyzer = GitAnalyzer(temp_git_repo)
        repo = analyzer.repo

        # Create files with different bug fix counts
        file1_path = os.path.join(temp_git_repo, "file1.py")
        with open(file1_path, "w") as f:
            f.write("# file1\n")
        repo.index.add(["file1.py"])
        repo.index.commit("Add file1")

        # Fix 1
        with open(file1_path, "w") as f:
            f.write("# file1 fixed\n")
        repo.index.add(["file1.py"])
        repo.index.commit("Fix bug in file1")

        # Check with min_bug_fixes=2 - should be empty
        bug_prone = analyzer.detect_bug_prone_files(min_bug_fixes=2)
        assert len(bug_prone) == 0

        # Check with min_bug_fixes=1 - should find file1
        bug_prone = analyzer.detect_bug_prone_files(min_bug_fixes=1)
        assert len(bug_prone) > 0


class TestGitAnalyzerAuthorStats:
    """Test suite for author statistics."""

    def test_get_author_stats(self, populated_repo):
        """Test author statistics retrieval."""
        analyzer = GitAnalyzer(populated_repo)
        stats = analyzer.get_author_stats()

        assert isinstance(stats, list)
        assert len(stats) > 0

        # Check first author stats
        author = stats[0]
        assert isinstance(author, AuthorStats)
        assert author.commit_count > 0
        assert author.name is not None
        assert author.email is not None

    def test_author_stats_sorted_by_commits(self, populated_repo):
        """Test author stats are sorted by commit count."""
        analyzer = GitAnalyzer(populated_repo)
        stats = analyzer.get_author_stats()

        if len(stats) > 1:
            for i in range(len(stats) - 1):
                assert stats[i].commit_count >= stats[i + 1].commit_count

    def test_author_rework_rate(self):
        """Test author rework rate calculation."""
        author = AuthorStats(
            name="Test User",
            email="test@example.com",
            lines_added=100,
            lines_deleted=50,
        )

        expected_rework = 50 / (100 + 50)
        assert author.rework_rate == expected_rework

    def test_author_rework_rate_zero_lines(self):
        """Test rework rate with zero lines."""
        author = AuthorStats(
            name="Test User", email="test@example.com", lines_added=0, lines_deleted=0
        )

        assert author.rework_rate == 0.0

    def test_get_author_stats_with_multiple_authors(self, temp_git_repo):
        """Test author stats with multiple contributors."""
        analyzer = GitAnalyzer(temp_git_repo)
        repo = analyzer.repo

        # Create commits as different authors
        file1_path = os.path.join(temp_git_repo, "file1.py")
        with open(file1_path, "w") as f:
            f.write("# code\n")
        repo.index.add(["file1.py"])

        actor1 = Actor("Author One", "author1@example.com")
        repo.index.commit("Commit by author 1", author=actor1)

        # Second commit by different author
        with open(file1_path, "w") as f:
            f.write("# more code\n")
        repo.index.add(["file1.py"])

        actor2 = Actor("Author Two", "author2@example.com")
        repo.index.commit("Commit by author 2", author=actor2)

        stats = analyzer.get_author_stats()

        assert len(stats) == 2
        emails = {s.email for s in stats}
        assert "author1@example.com" in emails
        assert "author2@example.com" in emails


class TestGitAnalyzerReworkRate:
    """Test suite for rework rate calculations."""

    def test_calculate_rework_rate(self, populated_repo):
        """Test rework rate calculation."""
        analyzer = GitAnalyzer(populated_repo)
        rework_rate = analyzer.calculate_rework_rate()

        # Rework rate should be between 0 and 1
        assert 0.0 <= rework_rate <= 1.0

    def test_calculate_rework_rate_for_file(self, temp_git_repo):
        """Test rework rate calculation for specific file."""
        analyzer = GitAnalyzer(temp_git_repo)
        repo = analyzer.repo

        # Create a file with multiple lines
        file_path = os.path.join(temp_git_repo, "test.py")
        with open(file_path, "w") as f:
            f.write("line1\nline2\nline3\nline4\nline5\n")
        repo.index.add(["test.py"])
        repo.index.commit("Add lines")

        # Add more lines and delete some
        with open(file_path, "w") as f:
            f.write("line1\nline2_modified\nline3\nline4\nnew_line\n")
        repo.index.add(["test.py"])
        repo.index.commit("Modify and add lines")

        rework_rate = analyzer.calculate_rework_rate(file_path="test.py")

        # Rework rate should be calculated (between 0 and 1)
        assert 0.0 <= rework_rate <= 1.0

    def test_calculate_rework_rate_no_changes(self, temp_git_repo):
        """Test rework rate with no changes."""
        # First create a commit so we have a HEAD
        analyzer = GitAnalyzer(temp_git_repo)
        repo = analyzer.repo

        file_path = os.path.join(temp_git_repo, "dummy.txt")
        with open(file_path, "w") as f:
            f.write("dummy\n")
        repo.index.add(["dummy.txt"])
        repo.index.commit("Initial commit")

        # Now test rework rate (will only have this one commit)
        rework_rate = analyzer.calculate_rework_rate()

        # With no changes, rework rate should be 0
        assert rework_rate == 0.0


class TestGitAnalyzerEdgeCases:
    """Test suite for edge cases and error handling."""

    def test_empty_repository(self, temp_git_repo):
        """Test behavior with repository that has no commits."""
        # First add a commit so analyzer can be created, then we'll test empty state handling
        analyzer = GitAnalyzer(temp_git_repo)
        repo = analyzer.repo

        # The analyzer needs at least one commit for many operations
        # Let's verify it handles the case gracefully when no HEAD exists
        # by checking that iter_commits is protected

        # Create one commit to have a valid repo state
        file_path = os.path.join(temp_git_repo, "init.txt")
        with open(file_path, "w") as f:
            f.write("init\n")
        repo.index.add(["init.txt"])
        repo.index.commit("Initial commit")

        # Now test with limit 0 commits
        metrics = analyzer.analyze_repository(limit=0)
        assert metrics.total_commits == 0

        hotspots = analyzer.identify_hotspots(limit=0)
        assert hotspots == []

        stats = analyzer.get_author_stats(limit=0)
        assert stats == []

    def test_single_commit_repository(self, temp_git_repo):
        """Test behavior with single commit repository."""
        analyzer = GitAnalyzer(temp_git_repo)
        repo = analyzer.repo

        file_path = os.path.join(temp_git_repo, "single.py")
        with open(file_path, "w") as f:
            f.write("# single file\n")
        repo.index.add(["single.py"])
        repo.index.commit("Single commit")

        metrics = analyzer.analyze_repository()
        assert metrics.total_commits == 1

        hotspots = analyzer.identify_hotspots()
        assert len(hotspots) == 1

    def test_binary_files_ignored(self, temp_git_repo):
        """Test that binary files don't cause issues."""
        analyzer = GitAnalyzer(temp_git_repo)
        repo = analyzer.repo

        # Create a binary file
        file_path = os.path.join(temp_git_repo, "binary.bin")
        with open(file_path, "wb") as f:
            f.write(b"\x00\x01\x02\x03\x04\x05")
        repo.index.add(["binary.bin"])
        repo.index.commit("Add binary file")

        # Should not crash
        metrics = analyzer.analyze_repository()
        assert metrics.total_commits == 1

        churn = analyzer.calculate_churn()
        # Binary files might or might not contribute to churn depending on git handling
        assert isinstance(churn, int)


class TestGitAnalyzerComplexScenarios:
    """Test suite for complex scenarios."""

    def test_hotspot_with_many_contributors(self, temp_git_repo):
        """Test hotspot calculation with multiple contributors."""
        analyzer = GitAnalyzer(temp_git_repo)
        repo = analyzer.repo

        file_path = os.path.join(temp_git_repo, "shared.py")
        with open(file_path, "w") as f:
            f.write("# shared\n")
        repo.index.add(["shared.py"])

        # Multiple authors touching the same file (plus initial test user = 6 total)
        for i in range(5):
            with open(file_path, "w") as f:
                f.write(f"# shared by author {i}\n")
            repo.index.add(["shared.py"])
            actor = Actor(f"Author {i}", f"author{i}@example.com")
            repo.index.commit(f"Update by author {i}", author=actor)

        # Bug fix by test user
        with open(file_path, "w") as f:
            f.write("# fixed\n")
        repo.index.add(["shared.py"])
        repo.index.commit("Fix bug")

        hotspots = analyzer.identify_hotspots()

        # Find the shared file
        shared = next((h for h in hotspots if h.path == "shared.py"), None)
        assert shared is not None
        assert shared.contributor_count == 6  # 5 from loop + 1 initial test user
        assert shared.bug_fixes == 1

    def test_complexity_trend_calculation(self, populated_repo):
        """Test that complexity trend is tracked (placeholder for future)."""
        analyzer = GitAnalyzer(populated_repo)
        metrics = analyzer.analyze_repository()

        # Complexity trend is currently a placeholder
        assert isinstance(metrics.complexity_trend, float)

    def test_monthly_contribution_tracking(self, temp_git_repo):
        """Test monthly contribution tracking."""
        analyzer = GitAnalyzer(temp_git_repo)
        repo = analyzer.repo

        file_path = os.path.join(temp_git_repo, "monthly.py")
        with open(file_path, "w") as f:
            f.write("# code\n")
        repo.index.add(["monthly.py"])
        repo.index.commit("Monthly commit")

        stats = analyzer.get_author_stats()

        assert len(stats) > 0
        author = stats[0]

        # Should have monthly breakdown
        assert isinstance(author.contribution_by_month, dict)
        assert len(author.contribution_by_month) > 0

        # Current month should be present
        current_month = datetime.now().strftime("%Y-%m")
        assert current_month in author.contribution_by_month
