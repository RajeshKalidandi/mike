"""Security & Risk Agent for Mike.

Provides security vulnerability scanning capabilities including:
- Hardcoded secret detection (API keys, tokens, passwords)
- SQL injection pattern detection
- SSRF vulnerability detection
- Insecure cryptography usage detection
- Open redirect detection
- Missing input validation detection

All scanning is done locally with no external API calls.
"""

from mike.security.models import (
    ConfidenceLevel,
    PatternCategory,
    SecurityFinding,
    SecurityPattern,
    SecurityReport,
    SeverityLevel,
)
from mike.security.patterns import (
    AUTH_PATTERNS,
    CRYPTO_PATTERNS,
    PatternDatabase,
    REDIRECT_PATTERNS,
    SECRET_PATTERNS,
    SQL_INJECTION_PATTERNS,
    SSRF_PATTERNS,
    VALIDATION_PATTERNS,
)
from mike.security.scanner import SecurityScanner

__all__ = [
    # Models
    "SeverityLevel",
    "ConfidenceLevel",
    "PatternCategory",
    "SecurityPattern",
    "SecurityFinding",
    "SecurityReport",
    # Patterns
    "PatternDatabase",
    "SECRET_PATTERNS",
    "SQL_INJECTION_PATTERNS",
    "SSRF_PATTERNS",
    "CRYPTO_PATTERNS",
    "REDIRECT_PATTERNS",
    "VALIDATION_PATTERNS",
    "AUTH_PATTERNS",
    # Scanner
    "SecurityScanner",
]

__version__ = "0.1.0"
