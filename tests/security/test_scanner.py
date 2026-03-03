"""Tests for security scanner module."""

import pytest
from pathlib import Path
from datetime import datetime

from mike.security.models import (
    SeverityLevel,
    ConfidenceLevel,
    SecurityFinding,
    SecurityReport,
)
from mike.security.patterns import PatternDatabase, PatternCategory
from mike.security.scanner import SecurityScanner


class TestSeverityLevel:
    """Test severity level enum."""

    def test_severity_ordering(self):
        """Test severity levels can be compared."""
        assert SeverityLevel.CRITICAL > SeverityLevel.HIGH
        assert SeverityLevel.HIGH > SeverityLevel.MEDIUM
        assert SeverityLevel.MEDIUM > SeverityLevel.LOW
        assert SeverityLevel.LOW > SeverityLevel.INFO

    def test_severity_numeric_value(self):
        """Test numeric value mapping."""
        assert SeverityLevel.CRITICAL.value == 5
        assert SeverityLevel.HIGH.value == 4
        assert SeverityLevel.MEDIUM.value == 3
        assert SeverityLevel.LOW.value == 2
        assert SeverityLevel.INFO.value == 1


class TestSecurityFinding:
    """Test security finding data class."""

    def test_finding_creation(self):
        """Test creating a security finding."""
        finding = SecurityFinding(
            pattern_id="SECRET_API_KEY",
            category=PatternCategory.SECRETS,
            severity=SeverityLevel.HIGH,
            confidence=ConfidenceLevel.HIGH,
            file_path="/test/file.py",
            line_number=10,
            column_start=5,
            column_end=50,
            matched_text="api_key = 'sk-1234567890abcdef'",
            message="Hardcoded API key detected",
            remediation="Use environment variables or a secrets manager",
        )

        assert finding.pattern_id == "SECRET_API_KEY"
        assert finding.category == PatternCategory.SECRETS
        assert finding.severity == SeverityLevel.HIGH
        assert finding.confidence == ConfidenceLevel.HIGH
        assert finding.file_path == "/test/file.py"
        assert finding.line_number == 10
        assert finding.matched_text == "api_key = 'sk-1234567890abcdef'"

    def test_finding_to_dict(self):
        """Test converting finding to dictionary."""
        finding = SecurityFinding(
            pattern_id="TEST_001",
            category=PatternCategory.INJECTION,
            severity=SeverityLevel.CRITICAL,
            confidence=ConfidenceLevel.MEDIUM,
            file_path="/test/file.py",
            line_number=1,
            column_start=0,
            column_end=10,
            matched_text="test",
            message="Test message",
            remediation="Fix it",
        )

        data = finding.to_dict()
        assert data["pattern_id"] == "TEST_001"
        assert data["severity"] == "CRITICAL"
        assert data["confidence"] == "MEDIUM"

    def test_finding_from_dict(self):
        """Test creating finding from dictionary."""
        data = {
            "pattern_id": "TEST_002",
            "category": "SECRETS",
            "severity": "HIGH",
            "confidence": "HIGH",
            "file_path": "/test/file.py",
            "line_number": 5,
            "column_start": 0,
            "column_end": 20,
            "matched_text": "password = 'secret'",
            "message": "Hardcoded password",
            "remediation": "Use env var",
            "context_lines": [],
        }

        finding = SecurityFinding.from_dict(data)
        assert finding.pattern_id == "TEST_002"
        assert finding.severity == SeverityLevel.HIGH
        assert finding.category == PatternCategory.SECRETS


class TestSecurityReport:
    """Test security report class."""

    def test_empty_report(self):
        """Test creating empty report."""
        report = SecurityReport(
            target_path="/test/project",
            scan_timestamp=datetime.now(),
            findings=[],
        )

        assert report.target_path == "/test/project"
        assert len(report.findings) == 0
        assert report.risk_score == 0.0

    def test_report_with_findings(self):
        """Test report with multiple findings."""
        findings = [
            SecurityFinding(
                pattern_id="CRIT_001",
                category=PatternCategory.SECRETS,
                severity=SeverityLevel.CRITICAL,
                confidence=ConfidenceLevel.HIGH,
                file_path="/test/file1.py",
                line_number=1,
                column_start=0,
                column_end=10,
                matched_text="test",
                message="Critical issue",
                remediation="Fix it",
            ),
            SecurityFinding(
                pattern_id="HIGH_001",
                category=PatternCategory.INJECTION,
                severity=SeverityLevel.HIGH,
                confidence=ConfidenceLevel.MEDIUM,
                file_path="/test/file2.py",
                line_number=2,
                column_start=0,
                column_end=10,
                matched_text="test",
                message="High issue",
                remediation="Fix it",
            ),
        ]

        report = SecurityReport(
            target_path="/test/project",
            scan_timestamp=datetime.now(),
            findings=findings,
        )

        assert len(report.findings) == 2
        assert len(report.get_findings_by_severity(SeverityLevel.CRITICAL)) == 1
        assert len(report.get_findings_by_severity(SeverityLevel.HIGH)) == 1
        assert report.risk_score > 0

    def test_report_risk_score_calculation(self):
        """Test risk score calculation."""
        findings = [
            SecurityFinding(
                pattern_id="INFO_001",
                category=PatternCategory.SECRETS,
                severity=SeverityLevel.INFO,
                confidence=ConfidenceLevel.HIGH,
                file_path="/test/file.py",
                line_number=1,
                column_start=0,
                column_end=10,
                matched_text="test",
                message="Info issue",
                remediation="Fix it",
            ),
        ]

        report = SecurityReport(
            target_path="/test/project",
            scan_timestamp=datetime.now(),
            findings=findings,
        )

        # Risk score should be low for single info finding
        assert 0 < report.risk_score < 3

    def test_report_to_sarif(self):
        """Test SARIF output format."""
        finding = SecurityFinding(
            pattern_id="TEST_001",
            category=PatternCategory.SECRETS,
            severity=SeverityLevel.HIGH,
            confidence=ConfidenceLevel.HIGH,
            file_path="/test/file.py",
            line_number=10,
            column_start=5,
            column_end=50,
            matched_text="api_key = 'secret'",
            message="API key found",
            remediation="Use env var",
        )

        report = SecurityReport(
            target_path="/test/project",
            scan_timestamp=datetime.now(),
            findings=[finding],
        )

        sarif = report.to_sarif()
        assert sarif["version"] == "2.1.0"
        assert "runs" in sarif
        assert len(sarif["runs"]) == 1
        assert len(sarif["runs"][0]["results"]) == 1


class TestPatternDatabase:
    """Test pattern database."""

    def test_patterns_loaded(self):
        """Test that patterns are loaded."""
        db = PatternDatabase()
        assert len(db.patterns) > 0

    def test_get_patterns_by_category(self):
        """Test filtering patterns by category."""
        db = PatternDatabase()
        secret_patterns = db.get_patterns_by_category(PatternCategory.SECRETS)
        assert len(secret_patterns) > 0

        for pattern in secret_patterns:
            assert pattern.category == PatternCategory.SECRETS

    def test_pattern_matching(self):
        """Test pattern matching functionality."""
        db = PatternDatabase()

        # Test secret pattern matching
        code = "api_key = 'sk-12345678901234567890'"
        matches = db.match_patterns(code, PatternCategory.SECRETS)
        assert len(matches) > 0

    def test_pattern_has_required_fields(self):
        """Test all patterns have required fields."""
        db = PatternDatabase()

        for pattern in db.patterns:
            assert pattern.id
            assert pattern.name
            assert pattern.category
            assert pattern.severity
            assert pattern.pattern
            assert pattern.description
            assert pattern.remediation


class TestSecurityScanner:
    """Test security scanner."""

    def test_scanner_initialization(self):
        """Test scanner can be initialized."""
        scanner = SecurityScanner()
        assert scanner.pattern_db is not None

    def test_scan_file_with_secrets(self, tmp_path):
        """Test scanning file with hardcoded secrets."""
        test_file = tmp_path / "test_secrets.py"
        test_file.write_text("""
api_key = 'sk-12345678901234567890abcdefghij'
password = 'super_secret_password_123'
""")

        scanner = SecurityScanner()
        findings = scanner.scan_file(str(test_file))

        assert len(findings) >= 2

        # Check for API key finding
        api_key_findings = [f for f in findings if "api_key" in f.matched_text.lower()]
        assert len(api_key_findings) > 0

    def test_scan_file_with_sql_injection(self, tmp_path):
        """Test scanning file with SQL injection vulnerability."""
        test_file = tmp_path / "test_sql.py"
        test_file.write_text("""
def get_user(user_id):
    query = "SELECT * FROM users WHERE id = " + user_id
    cursor.execute(query)
    
def get_data(name):
    cursor.execute("SELECT * FROM data WHERE name = '%s'" % name)
""")

        scanner = SecurityScanner()
        findings = scanner.scan_file(str(test_file))

        sql_injection_findings = [
            f for f in findings if f.category == PatternCategory.INJECTION
        ]
        assert len(sql_injection_findings) > 0

    def test_scan_file_with_ssrf(self, tmp_path):
        """Test scanning file with SSRF vulnerability."""
        test_file = tmp_path / "test_ssrf.py"
        test_file.write_text("""
import requests

def fetch_url(url):
    return requests.get(url)

def fetch_user_data(user_url):
    response = urllib.request.urlopen(user_url)
    return response.read()
""")

        scanner = SecurityScanner()
        findings = scanner.scan_file(str(test_file))

        ssrf_findings = [f for f in findings if f.category == PatternCategory.SSRF]
        assert len(ssrf_findings) > 0

    def test_scan_file_with_insecure_crypto(self, tmp_path):
        """Test scanning file with insecure crypto usage."""
        test_file = tmp_path / "test_crypto.py"
        test_file.write_text("""
import hashlib

def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()

def encrypt_data(data):
    cipher = AES.new(key, AES.MODE_ECB)
    return cipher.encrypt(data)
""")

        scanner = SecurityScanner()
        findings = scanner.scan_file(str(test_file))

        crypto_findings = [f for f in findings if f.category == PatternCategory.CRYPTO]
        assert len(crypto_findings) > 0

    def test_scan_project(self, tmp_path):
        """Test scanning entire project."""
        # Create project structure
        (tmp_path / "src").mkdir()

        # File 1: Secrets
        (tmp_path / "src" / "config.py").write_text("""
API_KEY = 'sk-12345678901234567890abcdefghij'
SECRET_KEY = 'my-secret-key-value-12345'
""")

        # File 2: SQL Injection
        (tmp_path / "src" / "database.py").write_text("""
def query_user(name):
    cursor.execute("SELECT * FROM users WHERE name = '" + name + "'")
""")

        # File 3: Safe file
        (tmp_path / "src" / "utils.py").write_text("""
def add(a, b):
    return a + b
""")

        scanner = SecurityScanner()
        report = scanner.scan_project(str(tmp_path))

        assert report.target_path == str(tmp_path)
        assert len(report.findings) > 0
        assert report.risk_score > 0

    def test_entropy_detection(self, tmp_path):
        """Test entropy-based secret detection."""
        test_file = tmp_path / "test_entropy.py"
        test_file.write_text("""
# High entropy string that looks like a secret
secret_value = 'a1b2c3d4e5f6789012345678901234567890abcd'
# Normal string
normal_value = 'this is a normal string value'
""")

        scanner = SecurityScanner()
        findings = scanner.scan_file(str(test_file))

        # Should detect high entropy strings
        high_entropy_findings = [f for f in findings if "entropy" in f.message.lower()]
        assert len(high_entropy_findings) > 0

    def test_false_positive_handling(self, tmp_path):
        """Test handling of potential false positives."""
        test_file = tmp_path / "test_fp.py"
        test_file.write_text("""
# These should not trigger or should have low confidence
api_key = os.environ.get('API_KEY')
password = None  # placeholder
secret_key = settings.SECRET_KEY
""")

        scanner = SecurityScanner()
        findings = scanner.scan_file(str(test_file))

        # Should not flag environment variable access
        env_findings = [f for f in findings if "os.environ" in f.matched_text]
        assert len(env_findings) == 0

    def test_minified_file_handling(self, tmp_path):
        """Test handling of minified files."""
        test_file = tmp_path / "bundle.min.js"
        # Create very long line (minified style)
        test_file.write_text("x" * 10000 + "\n")

        scanner = SecurityScanner()
        findings = scanner.scan_file(str(test_file))

        # Should handle minified files gracefully
        # (may skip or reduce patterns applied)
        assert isinstance(findings, list)

    def test_empty_file_handling(self, tmp_path):
        """Test handling of empty files."""
        test_file = tmp_path / "empty.py"
        test_file.write_text("")

        scanner = SecurityScanner()
        findings = scanner.scan_file(str(test_file))

        assert findings == []

    def test_binary_file_handling(self, tmp_path):
        """Test handling of binary files."""
        test_file = tmp_path / "binary.bin"
        test_file.write_bytes(b"\x00\x01\x02\x03\xff\xfe")

        scanner = SecurityScanner()
        findings = scanner.scan_file(str(test_file))

        assert findings == []
