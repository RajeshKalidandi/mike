"""Security scanner data models."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class SeverityLevel(Enum):
    """Security finding severity levels."""

    INFO = 1
    LOW = 2
    MEDIUM = 3
    HIGH = 4
    CRITICAL = 5

    def __gt__(self, other: "SeverityLevel") -> bool:
        """Compare severity levels."""
        if self.__class__ is other.__class__:
            return self.value > other.value
        return NotImplemented

    def __lt__(self, other: "SeverityLevel") -> bool:
        """Compare severity levels."""
        if self.__class__ is other.__class__:
            return self.value < other.value
        return NotImplemented

    def __ge__(self, other: "SeverityLevel") -> bool:
        """Compare severity levels."""
        if self.__class__ is other.__class__:
            return self.value >= other.value
        return NotImplemented

    def __le__(self, other: "SeverityLevel") -> bool:
        """Compare severity levels."""
        if self.__class__ is other.__class__:
            return self.value <= other.value
        return NotImplemented


class ConfidenceLevel(Enum):
    """Confidence level for security findings."""

    LOW = 1
    MEDIUM = 2
    HIGH = 3


class PatternCategory(Enum):
    """Categories of security patterns."""

    SECRETS = "secrets"
    INJECTION = "injection"
    SSRF = "ssrf"
    CRYPTO = "crypto"
    REDIRECT = "redirect"
    VALIDATION = "validation"
    AUTH = "auth"
    OTHER = "other"


@dataclass
class SecurityPattern:
    """Definition of a security detection pattern."""

    id: str
    name: str
    category: PatternCategory
    severity: SeverityLevel
    pattern: str
    description: str
    remediation: str
    confidence: ConfidenceLevel = ConfidenceLevel.HIGH
    languages: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert pattern to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "severity": self.severity.name,
            "pattern": self.pattern,
            "description": self.description,
            "remediation": self.remediation,
            "confidence": self.confidence.name,
            "languages": self.languages,
        }


@dataclass
class SecurityFinding:
    """A single security finding."""

    pattern_id: str
    category: PatternCategory
    severity: SeverityLevel
    confidence: ConfidenceLevel
    file_path: str
    line_number: int
    column_start: int
    column_end: int
    matched_text: str
    message: str
    remediation: str
    context_lines: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert finding to dictionary."""
        return {
            "pattern_id": self.pattern_id,
            "category": self.category.value,
            "severity": self.severity.name,
            "confidence": self.confidence.name,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "column_start": self.column_start,
            "column_end": self.column_end,
            "matched_text": self.matched_text,
            "message": self.message,
            "remediation": self.remediation,
            "context_lines": self.context_lines,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SecurityFinding":
        """Create finding from dictionary."""
        # Handle PatternCategory - can be either name or value
        category_val = data["category"]
        if isinstance(category_val, str):
            try:
                category = PatternCategory[category_val.upper()]
            except KeyError:
                category = PatternCategory(category_val.lower())
        else:
            category = category_val

        return cls(
            pattern_id=data["pattern_id"],
            category=category,
            severity=SeverityLevel[data["severity"]],
            confidence=ConfidenceLevel[data["confidence"]],
            file_path=data["file_path"],
            line_number=data["line_number"],
            column_start=data["column_start"],
            column_end=data["column_end"],
            matched_text=data["matched_text"],
            message=data["message"],
            remediation=data["remediation"],
            context_lines=data.get("context_lines", []),
        )


@dataclass
class SecurityReport:
    """Complete security scan report."""

    target_path: str
    scan_timestamp: datetime
    findings: List[SecurityFinding]
    scanned_files: int = 0
    scan_duration_seconds: float = 0.0

    @property
    def risk_score(self) -> float:
        """Calculate overall risk score (0-10)."""
        if not self.findings:
            return 0.0

        # Weight by severity and confidence
        total_weight = 0.0
        for finding in self.findings:
            severity_weight = finding.severity.value
            confidence_weight = finding.confidence.value / 3.0  # Normalize to 0-1
            total_weight += severity_weight * confidence_weight

        # Normalize to 0-10 scale
        # Critical (5) * High confidence (1.0) = 5 points per finding
        # With 10 critical findings at high confidence = 50 points = max score
        risk_score = min(10.0, total_weight / 5.0)
        return round(risk_score, 2)

    def get_findings_by_severity(
        self, severity: SeverityLevel
    ) -> List[SecurityFinding]:
        """Get findings filtered by severity level."""
        return [f for f in self.findings if f.severity == severity]

    def get_findings_by_category(
        self, category: PatternCategory
    ) -> List[SecurityFinding]:
        """Get findings filtered by category."""
        return [f for f in self.findings if f.category == category]

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics."""
        severity_counts = {
            "CRITICAL": len(self.get_findings_by_severity(SeverityLevel.CRITICAL)),
            "HIGH": len(self.get_findings_by_severity(SeverityLevel.HIGH)),
            "MEDIUM": len(self.get_findings_by_severity(SeverityLevel.MEDIUM)),
            "LOW": len(self.get_findings_by_severity(SeverityLevel.LOW)),
            "INFO": len(self.get_findings_by_severity(SeverityLevel.INFO)),
        }

        return {
            "target_path": self.target_path,
            "scan_timestamp": self.scan_timestamp.isoformat(),
            "risk_score": self.risk_score,
            "total_findings": len(self.findings),
            "severity_counts": severity_counts,
            "scanned_files": self.scanned_files,
            "scan_duration_seconds": self.scan_duration_seconds,
        }

    def to_sarif(self) -> Dict[str, Any]:
        """Convert report to SARIF format."""
        rules = {}
        results = []

        for finding in self.findings:
            # Add rule if not already present
            if finding.pattern_id not in rules:
                rules[finding.pattern_id] = {
                    "id": finding.pattern_id,
                    "name": finding.pattern_id,
                    "shortDescription": {"text": finding.message},
                    "fullDescription": {"text": finding.message},
                    "defaultConfiguration": {
                        "level": self._severity_to_sarif_level(finding.severity)
                    },
                }

            # Add result
            results.append(
                {
                    "ruleId": finding.pattern_id,
                    "level": self._severity_to_sarif_level(finding.severity),
                    "message": {"text": finding.message},
                    "locations": [
                        {
                            "physicalLocation": {
                                "artifactLocation": {"uri": finding.file_path},
                                "region": {
                                    "startLine": finding.line_number,
                                    "startColumn": finding.column_start,
                                    "endColumn": finding.column_end,
                                    "snippet": {"text": finding.matched_text},
                                },
                            },
                        }
                    ],
                }
            )

        return {
            "version": "2.1.0",
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "runs": [
                {
                    "tool": {
                        "driver": {
                            "name": "Mike Security Scanner",
                            "version": "0.1.0",
                            "informationUri": "https://github.com/mike/mike",
                            "rules": list(rules.values()),
                        },
                    },
                    "results": results,
                }
            ],
        }

    def _severity_to_sarif_level(self, severity: SeverityLevel) -> str:
        """Convert severity to SARIF level."""
        mapping = {
            SeverityLevel.CRITICAL: "error",
            SeverityLevel.HIGH: "error",
            SeverityLevel.MEDIUM: "warning",
            SeverityLevel.LOW: "note",
            SeverityLevel.INFO: "note",
        }
        return mapping.get(severity, "warning")

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "target_path": self.target_path,
            "scan_timestamp": self.scan_timestamp.isoformat(),
            "risk_score": self.risk_score,
            "scanned_files": self.scanned_files,
            "scan_duration_seconds": self.scan_duration_seconds,
            "findings": [f.to_dict() for f in self.findings],
        }
