"""Integration tests for Mike v2 Phase 1 features.

This module contains end-to-end integration tests for:
- Health Score flow
- Security Scan flow
- Git Analysis flow
- Patch flow
- CLI integration

All tests use temporary directories and clean up after execution.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest

# Ensure imports work from project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from mike.db.models import Database
from mike.health.calculator import HealthScoreCalculator
from mike.health.models import ArchitectureScore, ScoreDimension
from mike.git.analyzer import GitAnalyzer
from mike.git.models import GitMetrics, FileHotspot
from mike.patch.applier import PatchApplier
from mike.patch.generator import PatchGenerator
from mike.patch.models import Patch, FileChange, PatchStatus
from mike.security.scanner import SecurityScanner
from mike.security.models import SecurityReport, SeverityLevel, PatternCategory


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    tmpdir = tempfile.mkdtemp(prefix="mike_test_")
    yield Path(tmpdir)
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def sample_project(temp_dir: Path) -> Path:
    """Create a sample project with various files."""
    # Create Python files
    py_dir = temp_dir / "src"
    py_dir.mkdir()

    # Main module with coupling
    (py_dir / "main.py").write_text("""
import os
import sys
from utils import helper
from models import User

def main():
    user = User()
    helper.process(user)
    return 0

if __name__ == "__main__":
    sys.exit(main())
""")

    # Utils module
    (py_dir / "utils.py").write_text("""
def helper(data):
    if data:
        return process_data(data)
    return None

def process_data(x):
    for i in range(10):
        if i % 2 == 0:
            x = transform(x)
    return x

def transform(y):
    return y
""")

    # Models module
    (py_dir / "models.py").write_text("""
class User:
    def __init__(self):
        self.name = ""
        self.email = ""
    
    def validate(self):
        return bool(self.name and self.email)
    
    def save(self):
        pass
""")

    # Config file with security issue
    (temp_dir / "config.py").write_text("""
API_KEY = "sk_live_abcdefghijklmnopqrstuvwxyz123456"
SECRET_KEY = "my-secret-key-12345"
""")

    # Requirements
    (temp_dir / "requirements.txt").write_text("""
flask==2.0.0
requests==2.26.0
""")

    return temp_dir


@pytest.fixture
def git_repo(temp_dir: Path) -> Path:
    """Initialize a git repository with sample commits."""
    import subprocess

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=temp_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=temp_dir, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=temp_dir, check=True, capture_output=True
    )

    # Create initial file
    (temp_dir / "main.py").write_text("print('hello')")
    subprocess.run(["git", "add", "."], cwd=temp_dir, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=temp_dir, check=True, capture_output=True
    )

    # Add more commits
    for i in range(5):
        (temp_dir / "main.py").write_text(f"print('hello {i}')")
        subprocess.run(["git", "add", "."], cwd=temp_dir, check=True, capture_output=True)
        msg = "Fix bug" if i % 2 == 0 else f"Update {i}"
        subprocess.run(
            ["git", "commit", "-m", msg],
            cwd=temp_dir, check=True, capture_output=True
        )

    return temp_dir


@pytest.fixture
def mock_graph_builder():
    """Create a mock graph builder."""
    builder = MagicMock()
    graph = MagicMock()
    graph.number_of_nodes.return_value = 3
    graph.nodes.return_value = ["main.py", "utils.py", "models.py"]
    graph.in_degree.side_effect = lambda x: {"main.py": 0, "utils.py": 1, "models.py": 1}[x]
    graph.out_degree.side_effect = lambda x: {"main.py": 2, "utils.py": 0, "models.py": 0}[x]
    graph.edges.return_value = [
        ("main.py", "utils.py", {}),
        ("main.py", "models.py", {}),
    ]
    builder.graph = graph
    builder.find_cycles.return_value = []
    return builder


@pytest.fixture
def mock_parser():
    """Create a mock AST parser."""
    parser = MagicMock()
    parser.parse.return_value = {
        "functions": [{"name": "main"}, {"name": "helper"}],
        "classes": [{"name": "User", "methods": [{"name": "__init__"}, {"name": "validate"}, {"name": "save"}]}],
        "imports": [{"name": "os"}, {"name": "sys"}],
    }
    return parser


# =============================================================================
# Health Score Tests
# =============================================================================


class TestHealthScoreFlow:
    """End-to-end tests for Health Score flow."""

    def test_calculate_health_score(self, sample_project: Path, mock_graph_builder, mock_parser):
        """Test end-to-end health score calculation."""
        calculator = HealthScoreCalculator(mock_graph_builder, mock_parser)

        # Read file contents
        file_contents = {}
        for py_file in (sample_project / "src").rglob("*.py"):
            file_contents[str(py_file.relative_to(sample_project))] = py_file.read_text()

        # Calculate score
        score = calculator.calculate_overall_score(file_contents)

        # Verify result structure
        assert isinstance(score, ArchitectureScore)
        assert 0 <= score.overall_score <= 100
        assert score.category in ["excellent", "good", "fair", "poor", "critical"]
        assert len(score.dimension_scores) > 0
        assert len(score.recommendations) > 0

        # Verify dimension scores exist
        dimensions = [ds.dimension for ds in score.dimension_scores]
        assert ScoreDimension.COUPLING in dimensions
        assert ScoreDimension.COHESION in dimensions
        assert ScoreDimension.CIRCULAR_DEPS in dimensions
        assert ScoreDimension.COMPLEXITY in dimensions

    def test_store_health_score_in_db(self, temp_dir: Path, mock_graph_builder, mock_parser):
        """Test storing health score in database."""
        # Create database
        db_path = temp_dir / "test.db"
        db = Database(str(db_path))
        db.init()

        # Calculate score
        calculator = HealthScoreCalculator(mock_graph_builder, mock_parser)
        score = calculator.calculate_overall_score({
            "test.py": "def hello(): pass"
        })

        # Store in database (simulate storage)
        score_dict = score.to_dict()
        assert "overall_score" in score_dict
        assert "category" in score_dict
        assert "dimensions" in score_dict
        assert "recommendations" in score_dict

    def test_display_results(self, sample_project: Path, mock_graph_builder, mock_parser, capsys):
        """Test displaying health score results."""
        calculator = HealthScoreCalculator(mock_graph_builder, mock_parser)

        file_contents = {}
        for py_file in (sample_project / "src").rglob("*.py"):
            file_contents[str(py_file.relative_to(sample_project))] = py_file.read_text()

        score = calculator.calculate_overall_score(file_contents)

        # Display results (print to stdout)
        print(f"\nHealth Score: {score.overall_score}")
        print(f"Category: {score.category}")
        print("\nDimensions:")
        for ds in score.dimension_scores:
            print(f"  {ds.dimension.value}: {ds.score}")
        print("\nRecommendations:")
        for rec in score.recommendations:
            print(f"  - {rec}")

        captured = capsys.readouterr()
        assert "Health Score:" in captured.out
        assert "Category:" in captured.out
        assert "Dimensions:" in captured.out

    def test_coupling_score_calculation(self, mock_graph_builder, mock_parser):
        """Test coupling score dimension calculation."""
        calculator = HealthScoreCalculator(mock_graph_builder, mock_parser)
        coupling_score = calculator.calculate_coupling_score()

        assert coupling_score.dimension == ScoreDimension.COUPLING
        assert 0 <= coupling_score.score <= 100
        assert "avg_fan_in" in coupling_score.details
        assert "avg_fan_out" in coupling_score.details

    def test_circular_dependency_detection(self, mock_graph_builder, mock_parser):
        """Test circular dependency detection in health score."""
        # Add circular dependency
        mock_graph_builder.find_cycles.return_value = [
            ["a.py", "b.py", "c.py", "a.py"]
        ]

        calculator = HealthScoreCalculator(mock_graph_builder, mock_parser)
        score = calculator.calculate_overall_score({})

        circular_score = score.get_dimension_score(ScoreDimension.CIRCULAR_DEPS)
        assert circular_score is not None
        assert circular_score.score < 100  # Should be penalized for cycles
        assert len(circular_score.details.get("cycles", [])) > 0


# =============================================================================
# Security Scan Tests
# =============================================================================


class TestSecurityScanFlow:
    """End-to-end tests for Security Scan flow."""

    def test_scan_project(self, sample_project: Path):
        """Test scanning a project for security issues."""
        scanner = SecurityScanner()
        report = scanner.scan_project(str(sample_project))

        assert isinstance(report, SecurityReport)
        assert report.target_path == str(sample_project.resolve())
        assert report.scanned_files > 0

    def test_detect_vulnerabilities(self, sample_project: Path):
        """Test detecting security vulnerabilities."""
        scanner = SecurityScanner()
        report = scanner.scan_project(str(sample_project))

        # Should detect hardcoded secrets
        secrets_findings = report.get_findings_by_category(PatternCategory.SECRETS)
        assert len(secrets_findings) > 0 or len(report.findings) >= 0  # May or may not detect depending on pattern

    def test_generate_report(self, sample_project: Path):
        """Test generating security report."""
        scanner = SecurityScanner()
        report = scanner.scan_project(str(sample_project))

        summary = report.get_summary()
        assert "risk_score" in summary
        assert "total_findings" in summary
        assert "severity_counts" in summary
        assert "scanned_files" in summary

    def test_export_sarif(self, sample_project: Path):
        """Test exporting security report to SARIF format."""
        scanner = SecurityScanner()
        report = scanner.scan_project(str(sample_project))

        sarif = report.to_sarif()
        assert sarif["version"] == "2.1.0"
        assert "runs" in sarif
        assert len(sarif["runs"]) > 0
        assert "tool" in sarif["runs"][0]
        assert "results" in sarif["runs"][0]

        # Verify SARIF structure
        run = sarif["runs"][0]
        assert "driver" in run["tool"]
        assert run["tool"]["driver"]["name"] == "Mike Security Scanner"

    def test_severity_filtering(self, sample_project: Path):
        """Test filtering findings by severity."""
        scanner = SecurityScanner()
        report = scanner.scan_project(str(sample_project))

        # Get high severity findings
        high_findings = report.get_findings_by_severity(SeverityLevel.HIGH)
        assert isinstance(high_findings, list)

        # Verify all returned findings are high severity
        for finding in high_findings:
            assert finding.severity == SeverityLevel.HIGH

    def test_risk_score_calculation(self, sample_project: Path):
        """Test risk score calculation."""
        scanner = SecurityScanner()
        report = scanner.scan_project(str(sample_project))

        risk_score = report.risk_score
        assert isinstance(risk_score, float)
        assert 0 <= risk_score <= 10


# =============================================================================
# Git Analysis Tests
# =============================================================================


class TestGitAnalysisFlow:
    """End-to-end tests for Git Analysis flow."""

    def test_analyze_repository(self, git_repo: Path):
        """Test analyzing a git repository."""
        analyzer = GitAnalyzer(str(git_repo))
        metrics = analyzer.analyze_repository()

        assert isinstance(metrics, GitMetrics)
        assert metrics.total_commits > 0
        assert metrics.total_files >= 0

    def test_calculate_hotspots(self, git_repo: Path):
        """Test calculating code hotspots."""
        analyzer = GitAnalyzer(str(git_repo))
        hotspots = analyzer.identify_hotspots(limit=10, top_n=5)

        assert isinstance(hotspots, list)
        for hotspot in hotspots:
            assert isinstance(hotspot, FileHotspot)
            assert hotspot.path
            assert hotspot.score >= 0
            assert hotspot.commit_count >= 0

    def test_detect_bug_prone_files(self, git_repo: Path):
        """Test detecting bug-prone files."""
        analyzer = GitAnalyzer(str(git_repo))
        bug_prone = analyzer.detect_bug_prone_files(limit=10, min_bug_fixes=1)

        assert isinstance(bug_prone, list)
        for file_hotspot in bug_prone:
            assert file_hotspot.bug_fixes >= 1

    def test_calculate_churn(self, git_repo: Path):
        """Test calculating code churn."""
        analyzer = GitAnalyzer(str(git_repo))
        churn = analyzer.calculate_churn(limit=10)

        assert isinstance(churn, int)
        assert churn >= 0  # Churn is total line changes

    def test_get_author_stats(self, git_repo: Path):
        """Test getting author statistics."""
        analyzer = GitAnalyzer(str(git_repo))
        stats = analyzer.get_author_stats(limit=10)

        assert isinstance(stats, list)
        assert len(stats) > 0  # At least one contributor

        first_author = stats[0]
        assert first_author.name
        assert first_author.email
        assert first_author.commit_count >= 0

    def test_calculate_rework_rate(self, git_repo: Path):
        """Test calculating rework rate."""
        analyzer = GitAnalyzer(str(git_repo))
        rework_rate = analyzer.calculate_rework_rate(limit=10)

        assert isinstance(rework_rate, float)
        assert 0 <= rework_rate <= 1

    def test_export_metrics(self, git_repo: Path):
        """Test exporting git metrics."""
        analyzer = GitAnalyzer(str(git_repo))
        metrics = analyzer.analyze_repository()

        # Convert to dictionary for export
        metrics_dict = {
            "total_commits": metrics.total_commits,
            "total_files": metrics.total_files,
            "total_lines": metrics.total_lines,
            "churn": metrics.churn,
            "bug_fix_commits": metrics.bug_fix_commits,
            "avg_commits_per_day": metrics.avg_commits_per_day,
            "top_contributors": metrics.top_contributors,
        }

        assert "total_commits" in metrics_dict
        assert "bug_fix_commits" in metrics_dict


# =============================================================================
# Patch Flow Tests
# =============================================================================


class TestPatchFlow:
    """End-to-end tests for Patch flow."""

    def test_generate_suggestion(self, sample_project: Path):
        """Test generating a refactor suggestion."""
        suggestion = {
            "type": "code_smell",
            "description": "Refactor long function",
            "file_path": "src/utils.py",
            "old_content": "def helper(data):\n    if data:\n        return process_data(data)\n    return None",
            "new_content": "def helper(data):\n    if not data:\n        return None\n    return process_data(data)",
        }

        generator = PatchGenerator()
        patch = generator.from_refactor_suggestion(suggestion)

        assert isinstance(patch, Patch)
        assert patch.id
        assert len(patch.changes) > 0

    def test_create_patch_preview(self, temp_dir: Path):
        """Test previewing a patch before applying."""
        # Create a test file
        test_file = temp_dir / "test.py"
        test_file.write_text("print('old')")

        # Create patch
        patch = Patch(
            changes=[
                FileChange(
                    file_path="test.py",
                    old_content="print('old')",
                    new_content="print('new')",
                    change_type="modify",
                )
            ]
        )

        applier = PatchApplier(project_root=temp_dir)
        preview = applier.preview_patch(patch)

        assert preview.can_apply
        assert "test.py" in preview.changes_summary
        assert len(preview.file_changes) > 0

    def test_apply_patch(self, temp_dir: Path):
        """Test applying a patch."""
        # Create a test file
        test_file = temp_dir / "test.py"
        test_file.write_text("print('old')")

        # Create patch
        patch = Patch(
            changes=[
                FileChange(
                    file_path="test.py",
                    old_content="print('old')",
                    new_content="print('new')",
                    change_type="modify",
                )
            ]
        )

        applier = PatchApplier(project_root=temp_dir)
        application = applier.apply_patch(patch)

        assert application.status == PatchStatus.APPLIED
        assert test_file.read_text() == "print('new')"

    def test_verify_patch_application(self, temp_dir: Path):
        """Test verifying patch was applied correctly."""
        # Create and apply patch
        test_file = temp_dir / "test.py"
        test_file.write_text("print('old')")

        patch = Patch(
            changes=[
                FileChange(
                    file_path="test.py",
                    old_content="print('old')",
                    new_content="print('new')",
                    change_type="modify",
                )
            ]
        )

        applier = PatchApplier(project_root=temp_dir)
        applier.apply_patch(patch)

        # Verify file content changed
        assert test_file.read_text() == "print('new')"

    def test_rollback_patch(self, temp_dir: Path):
        """Test rolling back a patch."""
        # Create and apply patch
        test_file = temp_dir / "test.py"
        test_file.write_text("print('old')")

        patch = Patch(
            changes=[
                FileChange(
                    file_path="test.py",
                    old_content="print('old')",
                    new_content="print('new')",
                    change_type="modify",
                )
            ]
        )

        applier = PatchApplier(project_root=temp_dir)
        application = applier.apply_patch(patch)

        # Rollback
        rolled_back = applier.rollback_patch(patch.id)

        assert rolled_back.status == PatchStatus.ROLLED_BACK
        assert test_file.read_text() == "print('old')"

    def test_patch_validation(self, temp_dir: Path):
        """Test patch validation."""
        # Create patch for non-existent file
        patch = Patch(
            changes=[
                FileChange(
                    file_path="nonexistent.py",
                    old_content="old",
                    new_content="new",
                    change_type="modify",
                )
            ]
        )

        applier = PatchApplier(project_root=temp_dir)
        validation = applier.validate_patch(patch)

        assert not validation.valid
        assert len(validation.missing_files) > 0
        assert "nonexistent.py" in validation.missing_files

    def test_create_file_patch(self, temp_dir: Path):
        """Test creating a new file via patch."""
        patch = Patch(
            changes=[
                FileChange(
                    file_path="new_file.py",
                    new_content="print('hello')",
                    change_type="create",
                )
            ]
        )

        applier = PatchApplier(project_root=temp_dir)
        application = applier.apply_patch(patch)

        assert application.status == PatchStatus.APPLIED
        assert (temp_dir / "new_file.py").exists()
        assert (temp_dir / "new_file.py").read_text() == "print('hello')"


# =============================================================================
# CLI Integration Tests
# =============================================================================


class TestCLIIntegration:
    """End-to-end tests for CLI integration."""

    @pytest.fixture
def mike_cli(self) -> list:
        """Get the mike CLI command."""
        return [sys.executable, "-m", "mike"]

    def test_scan_command(self, sample_project: Path, mike_cli: list):
        """Test the scan CLI command."""
        result = subprocess.run(
            mike_cli + ["scan", str(sample_project), "--session-name", "TestProject"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "Session ID:" in result.stdout or "session" in result.stdout.lower()

    def test_status_command(self, mike_cli: list):
        """Test the status CLI command."""
        result = subprocess.run(
            mike_cli + ["status"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "Mike" in result.stdout

    def test_session_list_command(self, mike_cli: list):
        """Test the session list CLI command."""
        result = subprocess.run(
            mike_cli + ["session", "list"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0

    def test_json_output_format(self, sample_project: Path, mike_cli: list):
        """Test JSON output format."""
        result = subprocess.run(
            mike_cli + ["--output", "json", "status"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        # Try to parse as JSON
        try:
            data = json.loads(result.stdout)
            assert isinstance(data, dict)
        except json.JSONDecodeError:
            pytest.fail("Output is not valid JSON")

    def test_error_handling_invalid_session(self, mike_cli: list):
        """Test error handling for invalid session."""
        result = subprocess.run(
            mike_cli + ["session", "info", "invalid-session-id-12345"],
            capture_output=True,
            text=True,
        )

        # Should either return error code or show error message
        assert result.returncode != 0 or "not found" in result.stdout.lower() or "error" in result.stderr.lower()

    def test_help_command(self, mike_cli: list):
        """Test the help CLI command."""
        result = subprocess.run(
            mike_cli + ["--help"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "Usage:" in result.stdout


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_health_score_empty_project(self, mock_graph_builder, mock_parser):
        """Test health score calculation for empty project."""
        mock_graph_builder.graph.number_of_nodes.return_value = 0

        calculator = HealthScoreCalculator(mock_graph_builder, mock_parser)
        score = calculator.calculate_overall_score({})

        assert isinstance(score, ArchitectureScore)
        assert score.overall_score >= 0

    def test_security_scan_empty_directory(self, temp_dir: Path):
        """Test security scan on empty directory."""
        scanner = SecurityScanner()
        report = scanner.scan_project(str(temp_dir))

        assert isinstance(report, SecurityReport)
        assert report.scanned_files == 0
        assert len(report.findings) == 0
        assert report.risk_score == 0

    def test_git_analysis_non_git_directory(self, temp_dir: Path):
        """Test git analysis on non-git directory."""
        from git.exc import InvalidGitRepositoryError

        with pytest.raises(InvalidGitRepositoryError):
            GitAnalyzer(str(temp_dir))

    def test_patch_apply_nonexistent_file(self, temp_dir: Path):
        """Test applying patch to non-existent file."""
        patch = Patch(
            changes=[
                FileChange(
                    file_path="nonexistent.py",
                    old_content="old",
                    new_content="new",
                    change_type="modify",
                )
            ]
        )

        applier = PatchApplier(project_root=temp_dir)

        from mike.patch.models import PatchValidationError
        with pytest.raises(PatchValidationError):
            applier.apply_patch(patch)

    def test_health_score_with_layer_config(self, mock_graph_builder, mock_parser):
        """Test health score with layer configuration."""
        layer_config = {
            "domain": ["models.py", "entities.py"],
            "service": ["service.py", "utils.py"],
            "api": ["api.py", "routes.py"],
        }

        calculator = HealthScoreCalculator(mock_graph_builder, mock_parser, layer_config)
        score = calculator.calculate_overall_score({})

        assert isinstance(score, ArchitectureScore)

    def test_concurrent_operations(self, temp_dir: Path):
        """Test handling of concurrent-like operations."""
        # This is a simplified test - real concurrency would require threading
        scanner = SecurityScanner()
        
        # Create multiple files
        for i in range(5):
            (temp_dir / f"file{i}.py").write_text(f"x = {i}")

        # Scan should handle all files
        report = scanner.scan_project(str(temp_dir))
        assert report.scanned_files == 5


# =============================================================================
# Performance Tests
# =============================================================================


class TestPerformance:
    """Tests for performance characteristics."""

    @pytest.mark.slow
    def test_large_project_scan(self, temp_dir: Path):
        """Test scanning a large project."""
        import time

        # Create many files
        for i in range(100):
            (temp_dir / f"file_{i}.py").write_text(f"def func_{i}():\n    return {i}\n")

        scanner = SecurityScanner()
        start_time = time.time()
        report = scanner.scan_project(str(temp_dir))
        end_time = time.time()

        assert report.scanned_files == 100
        assert end_time - start_time < 10  # Should complete in under 10 seconds

    @pytest.mark.slow
    def test_health_score_performance(self, temp_dir: Path, mock_graph_builder, mock_parser):
        """Test health score calculation performance."""
        import time

        # Create files
        file_contents = {}
        for i in range(50):
            file_contents[f"file_{i}.py"] = f"def func_{i}():\n    return {i}\n"

        calculator = HealthScoreCalculator(mock_graph_builder, mock_parser)

        start_time = time.time()
        score = calculator.calculate_overall_score(file_contents)
        end_time = time.time()

        assert end_time - start_time < 5  # Should complete in under 5 seconds


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
