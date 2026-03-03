"""Security pattern definitions and detection database."""

import math
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from mike.security.models import (
    ConfidenceLevel,
    PatternCategory,
    SecurityFinding,
    SecurityPattern,
    SeverityLevel,
)


# =============================================================================
# SECRET PATTERNS
# =============================================================================

SECRET_PATTERNS = [
    SecurityPattern(
        id="SECRET_API_KEY_GENERIC",
        name="Generic API Key",
        category=PatternCategory.SECRETS,
        severity=SeverityLevel.CRITICAL,
        pattern=r"(?i)(api[_-]?key|apikey)\s*[=:]\s*['\"]([a-zA-Z0-9_\-]{20,})['\"]",
        description="Hardcoded API key detected in source code",
        remediation="Use environment variables or a secure secrets manager (e.g., AWS Secrets Manager, HashiCorp Vault)",
        confidence=ConfidenceLevel.HIGH,
    ),
    SecurityPattern(
        id="SECRET_OPENAI_KEY",
        name="OpenAI API Key",
        category=PatternCategory.SECRETS,
        severity=SeverityLevel.CRITICAL,
        pattern=r"sk-[a-zA-Z0-9]{20,48}",
        description="OpenAI API key detected",
        remediation="Move API key to environment variables and use os.environ.get() to access it",
        confidence=ConfidenceLevel.HIGH,
    ),
    SecurityPattern(
        id="SECRET_AWS_KEY",
        name="AWS Access Key",
        category=PatternCategory.SECRETS,
        severity=SeverityLevel.CRITICAL,
        pattern=r"AKIA[0-9A-Z]{16}",
        description="AWS access key ID detected",
        remediation="Use IAM roles instead of hardcoded credentials, or AWS Secrets Manager",
        confidence=ConfidenceLevel.HIGH,
    ),
    SecurityPattern(
        id="SECRET_AWS_SECRET",
        name="AWS Secret Key",
        category=PatternCategory.SECRETS,
        severity=SeverityLevel.CRITICAL,
        pattern=r"(?i)(aws[_-]?secret[_-]?access[_-]?key)\s*[=:]\s*['\"]([a-zA-Z0-9/+=]{40})['\"]",
        description="AWS secret access key detected",
        remediation="Use IAM roles or AWS Secrets Manager instead of hardcoded credentials",
        confidence=ConfidenceLevel.HIGH,
    ),
    SecurityPattern(
        id="SECRET_GITHUB_TOKEN",
        name="GitHub Token",
        category=PatternCategory.SECRETS,
        severity=SeverityLevel.CRITICAL,
        pattern=r"gh[pousr]_[a-zA-Z0-9_]{36,}",
        description="GitHub personal access token detected",
        remediation="Use environment variables or GitHub's built-in secret scanning protection",
        confidence=ConfidenceLevel.HIGH,
    ),
    SecurityPattern(
        id="SECRET_SLACK_TOKEN",
        name="Slack Token",
        category=PatternCategory.SECRETS,
        severity=SeverityLevel.CRITICAL,
        pattern=r"xox[baprs]-[a-zA-Z0-9-]+",
        description="Slack API token detected",
        remediation="Store in environment variables or use Slack's app configuration",
        confidence=ConfidenceLevel.HIGH,
    ),
    SecurityPattern(
        id="SECRET_PRIVATE_KEY",
        name="Private Key",
        category=PatternCategory.SECRETS,
        severity=SeverityLevel.CRITICAL,
        pattern=r"-----BEGIN (RSA |DSA |EC |OPENSSH )?PRIVATE KEY-----",
        description="Private key detected in source code",
        remediation="Never commit private keys. Use SSH agent, environment variables, or a secrets manager",
        confidence=ConfidenceLevel.HIGH,
    ),
    SecurityPattern(
        id="SECRET_PASSWORD_HARDCODED",
        name="Hardcoded Password",
        category=PatternCategory.SECRETS,
        severity=SeverityLevel.HIGH,
        pattern=r"(?i)(password|passwd|pwd)\s*[=:]\s*['\"]([^'\"]{4,})['\"]",
        description="Hardcoded password detected",
        remediation="Use environment variables, config files excluded from version control, or a secrets manager",
        confidence=ConfidenceLevel.MEDIUM,
    ),
    SecurityPattern(
        id="SECRET_DB_CONNECTION",
        name="Database Connection String",
        category=PatternCategory.SECRETS,
        severity=SeverityLevel.CRITICAL,
        pattern=r"(?i)(mongodb(\+srv)?|mysql|postgres(ql)?|redis|sqlite)://[^:]+:[^@]+@",
        description="Database connection string with credentials detected",
        remediation="Use connection string from environment variables or secrets manager",
        confidence=ConfidenceLevel.HIGH,
    ),
    SecurityPattern(
        id="SECRET_JWT_TOKEN",
        name="JWT Token",
        category=PatternCategory.SECRETS,
        severity=SeverityLevel.HIGH,
        pattern=r"eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*",
        description="JWT token detected",
        remediation="Do not hardcode JWT tokens. They should be generated dynamically",
        confidence=ConfidenceLevel.MEDIUM,
    ),
    SecurityPattern(
        id="SECRET_BEARER_TOKEN",
        name="Bearer Token",
        category=PatternCategory.SECRETS,
        severity=SeverityLevel.HIGH,
        pattern=r"(?i)bearer\s+[a-zA-Z0-9_\-\.=]{20,}",
        description="Bearer token detected",
        remediation="Use environment variables or secure token storage",
        confidence=ConfidenceLevel.MEDIUM,
    ),
]


# =============================================================================
# SQL INJECTION PATTERNS
# =============================================================================

SQL_INJECTION_PATTERNS = [
    SecurityPattern(
        id="SQLI_STRING_CONCAT",
        name="SQL String Concatenation",
        category=PatternCategory.INJECTION,
        severity=SeverityLevel.CRITICAL,
        pattern=r"(?i)cursor\.execute\s*\(\s*['\"][^'\"]*\+\s*",
        description="Potential SQL injection via string concatenation",
        remediation="Use parameterized queries/prepared statements instead of string concatenation",
        confidence=ConfidenceLevel.HIGH,
    ),
    SecurityPattern(
        id="SQLI_FORMAT_STRING",
        name="SQL Format String",
        category=PatternCategory.INJECTION,
        severity=SeverityLevel.CRITICAL,
        pattern=r"(?i)(?:execute|query|cursor\.execute)\s*\(\s*['\"][^'\"]*%s",
        description="Potential SQL injection via string formatting",
        remediation="Use parameterized queries/prepared statements instead of string formatting",
        confidence=ConfidenceLevel.HIGH,
    ),
    SecurityPattern(
        id="SQLI_SIMPLE_CONCAT",
        name="SQL Simple Concatenation",
        category=PatternCategory.INJECTION,
        severity=SeverityLevel.CRITICAL,
        pattern=r"(?i)(?:SELECT|INSERT|UPDATE|DELETE).*\+\s*\w+",
        description="SQL query built with string concatenation",
        remediation="Use ORM methods or parameterized queries",
        confidence=ConfidenceLevel.HIGH,
    ),
    SecurityPattern(
        id="SQLI_FORMAT_STRING_OLD",
        name="SQL Format String Old",
        category=PatternCategory.INJECTION,
        severity=SeverityLevel.CRITICAL,
        pattern=r"(?i)(execute|query|raw)\s*\(\s*['\"][^'\"]*%\([^)]+\)",
        description="Potential SQL injection via Python string formatting",
        remediation="Use parameterized queries with placeholders (%s, ?) instead of string formatting",
        confidence=ConfidenceLevel.HIGH,
    ),
    SecurityPattern(
        id="SQLI_F_STRING",
        name="SQL F-String",
        category=PatternCategory.INJECTION,
        severity=SeverityLevel.CRITICAL,
        pattern=r"(?i)(execute|query|raw)\s*\(\s*f['\"][^'\"]*\{[^}]+\}",
        description="Potential SQL injection via f-string",
        remediation="Use parameterized queries instead of f-strings for SQL",
        confidence=ConfidenceLevel.HIGH,
    ),
    SecurityPattern(
        id="SQLI_STRING_INTERPOLATION",
        name="SQL String Interpolation",
        category=PatternCategory.INJECTION,
        severity=SeverityLevel.CRITICAL,
        pattern=r"(?i)(?:SELECT|INSERT|UPDATE|DELETE|WHERE).*\+\s*\w+",
        description="SQL query built with string concatenation",
        remediation="Use ORM methods or parameterized queries",
        confidence=ConfidenceLevel.MEDIUM,
    ),
]


# =============================================================================
# SSRF PATTERNS
# =============================================================================

SSRF_PATTERNS = [
    SecurityPattern(
        id="SSRF_REQUESTS_GET",
        name="SSRF via requests.get()",
        category=PatternCategory.SSRF,
        severity=SeverityLevel.HIGH,
        pattern=r"requests\.get\s*\(\s*\w+",
        description="Potential SSRF vulnerability - user-controlled URL passed to requests.get()",
        remediation="Validate and sanitize URLs, use allowlists for allowed domains",
        confidence=ConfidenceLevel.MEDIUM,
    ),
    SecurityPattern(
        id="SSRF_URLOPEN",
        name="SSRF via urlopen()",
        category=PatternCategory.SSRF,
        severity=SeverityLevel.HIGH,
        pattern=r"urllib\.request\.urlopen\s*\(\s*\w+",
        description="Potential SSRF vulnerability - user-controlled URL passed to urlopen()",
        remediation="Validate URLs against allowlist, avoid passing user input directly to urlopen()",
        confidence=ConfidenceLevel.MEDIUM,
    ),
    SecurityPattern(
        id="SSRF_FETCH",
        name="SSRF via fetch/axios",
        category=PatternCategory.SSRF,
        severity=SeverityLevel.HIGH,
        pattern=r"(?i)(fetch|axios\.get|axios\.post)\s*\(\s*\w+",
        description="Potential SSRF vulnerability in JavaScript/TypeScript",
        remediation="Validate and sanitize URLs, use allowlists for allowed endpoints",
        confidence=ConfidenceLevel.MEDIUM,
        languages=["javascript", "typescript"],
    ),
]


# =============================================================================
# CRYPTO PATTERNS
# =============================================================================

CRYPTO_PATTERNS = [
    SecurityPattern(
        id="CRYPTO_MD5",
        name="Insecure Hash - MD5",
        category=PatternCategory.CRYPTO,
        severity=SeverityLevel.HIGH,
        pattern=r"hashlib\.md5\s*\(",
        description="MD5 is cryptographically broken and unsuitable for security purposes",
        remediation="Use SHA-256 or SHA-3 family for hashing. For password hashing, use bcrypt, Argon2, or PBKDF2",
        confidence=ConfidenceLevel.HIGH,
    ),
    SecurityPattern(
        id="CRYPTO_SHA1",
        name="Insecure Hash - SHA1",
        category=PatternCategory.CRYPTO,
        severity=SeverityLevel.MEDIUM,
        pattern=r"hashlib\.sha1\s*\(",
        description="SHA1 is considered weak for security purposes",
        remediation="Use SHA-256 or SHA-3 for security-sensitive operations",
        confidence=ConfidenceLevel.HIGH,
    ),
    SecurityPattern(
        id="CRYPTO_ECB_MODE",
        name="ECB Encryption Mode",
        category=PatternCategory.CRYPTO,
        severity=SeverityLevel.CRITICAL,
        pattern=r"(?i)AES\.MODE_ECB|\.new\s*\([^,]+,\s*[^)]*MODE_ECB",
        description="ECB mode is insecure - it does not provide semantic security",
        remediation="Use CBC, GCM, or other authenticated encryption modes instead of ECB",
        confidence=ConfidenceLevel.HIGH,
    ),
    SecurityPattern(
        id="CRYPTO_WEAK_RANDOM",
        name="Weak Random Number Generation",
        category=PatternCategory.CRYPTO,
        severity=SeverityLevel.MEDIUM,
        pattern=r"(?i)(random\.randint|random\.random|random\.choice|Math\.random)\s*\(",
        description="Standard random is not cryptographically secure",
        remediation="Use secrets module (Python) or crypto.randomBytes (Node.js) for security-sensitive randomness",
        confidence=ConfidenceLevel.MEDIUM,
    ),
    SecurityPattern(
        id="CRYPTO_HARDCODED_IV",
        name="Hardcoded Encryption IV/Nonce",
        category=PatternCategory.CRYPTO,
        severity=SeverityLevel.HIGH,
        pattern=r"(?i)iv\s*=\s*['\"][a-fA-F0-9]{16,32}['\"]",
        description="Hardcoded IV/nonce reduces security of encryption",
        remediation="Generate IV/nonce randomly for each encryption operation",
        confidence=ConfidenceLevel.LOW,
    ),
]


# =============================================================================
# OPEN REDIRECT PATTERNS
# =============================================================================

REDIRECT_PATTERNS = [
    SecurityPattern(
        id="REDIRECT_USER_CONTROLLED",
        name="Open Redirect",
        category=PatternCategory.REDIRECT,
        severity=SeverityLevel.MEDIUM,
        pattern=r"(?i)redirect\s*\(\s*request\.(?:args|form|json)",
        description="Potential open redirect vulnerability",
        remediation="Validate redirect URLs against allowlist, avoid user-controlled redirects",
        confidence=ConfidenceLevel.MEDIUM,
    ),
    SecurityPattern(
        id="REDIRECT_NEXT_PARAM",
        name="Redirect via 'next' Parameter",
        category=PatternCategory.REDIRECT,
        severity=SeverityLevel.MEDIUM,
        pattern=r"(?i)(?:redirect|location)\s*[=:]\s*['\"]?[^'\"]*next=",
        description="Potential open redirect via 'next' parameter",
        remediation="Validate the 'next' parameter against allowed domains/paths",
        confidence=ConfidenceLevel.MEDIUM,
    ),
]


# =============================================================================
# INPUT VALIDATION PATTERNS
# =============================================================================

VALIDATION_PATTERNS = [
    SecurityPattern(
        id="VALIDATION_EVAL",
        name="Dangerous eval() Usage",
        category=PatternCategory.VALIDATION,
        severity=SeverityLevel.CRITICAL,
        pattern=r"(?i)(eval|exec)\s*\(\s*(?:request\.|input\(|sys\.argv)",
        description="Dangerous use of eval() with user input",
        remediation="Avoid eval() with user input. Use ast.literal_eval for literals or proper parsing",
        confidence=ConfidenceLevel.HIGH,
    ),
    SecurityPattern(
        id="VALIDATION_EXEC",
        name="Dangerous exec() Usage",
        category=PatternCategory.VALIDATION,
        severity=SeverityLevel.CRITICAL,
        pattern=r"(?i)exec\s*\(\s*(?:request\.|input\(|sys\.argv)",
        description="Dangerous use of exec() with user input",
        remediation="Never use exec() with user input. Refactor to avoid dynamic code execution",
        confidence=ConfidenceLevel.HIGH,
    ),
    SecurityPattern(
        id="VALIDATION_SUBPROCESS_SHELL",
        name="Subprocess with Shell=True",
        category=PatternCategory.VALIDATION,
        severity=SeverityLevel.CRITICAL,
        pattern=r"subprocess\.(?:call|run|Popen)\s*\([^)]*shell\s*=\s*True",
        description="Subprocess call with shell=True is dangerous with user input",
        remediation="Use shell=False and pass command as list. If shell=True is required, strictly validate input",
        confidence=ConfidenceLevel.HIGH,
    ),
    SecurityPattern(
        id="VALIDATION_PICKLE",
        name="Unsafe Pickle Usage",
        category=PatternCategory.VALIDATION,
        severity=SeverityLevel.CRITICAL,
        pattern=r"pickle\.loads?\s*\(\s*(?:request\.|input\(|socket\.recv)",
        description="Unpickling user-controlled data can lead to arbitrary code execution",
        remediation="Use JSON or other safe serialization formats instead of pickle for untrusted data",
        confidence=ConfidenceLevel.HIGH,
    ),
    SecurityPattern(
        id="VALIDATION_YAML_LOAD",
        name="Unsafe YAML Loading",
        category=PatternCategory.VALIDATION,
        severity=SeverityLevel.CRITICAL,
        pattern=r"yaml\.load\s*\([^)]*\)",
        description="yaml.load without Loader is unsafe with untrusted input",
        remediation="Use yaml.safe_load() instead of yaml.load()",
        confidence=ConfidenceLevel.HIGH,
    ),
]


# =============================================================================
# AUTHENTICATION PATTERNS
# =============================================================================

AUTH_PATTERNS = [
    SecurityPattern(
        id="AUTH_WEAK_PASSWORD",
        name="Weak Password Policy",
        category=PatternCategory.AUTH,
        severity=SeverityLevel.MEDIUM,
        pattern=r"(?i)(min_length\s*=\s*[0-5]|password.*length.*[0-5])",
        description="Weak minimum password length detected",
        remediation="Enforce minimum password length of at least 12 characters",
        confidence=ConfidenceLevel.LOW,
    ),
    SecurityPattern(
        id="AUTH_DEBUG_ENABLED",
        name="Debug Mode Enabled",
        category=PatternCategory.AUTH,
        severity=SeverityLevel.HIGH,
        pattern=r"(?i)(debug\s*=\s*True|DEBUG\s*=\s*True|app\.run.*debug\s*=\s*True)",
        description="Debug mode enabled in production code",
        remediation="Disable debug mode in production. Use environment variables to control debug mode",
        confidence=ConfidenceLevel.HIGH,
    ),
    SecurityPattern(
        id="AUTH_EXPOSED_ENV",
        name="Exposed Environment Variables",
        category=PatternCategory.SECRETS,
        severity=SeverityLevel.LOW,
        pattern=r"(?i)app\.config\[['\"]SECRET_KEY['\"]\]\s*=\s*['\"](?!\$\{|os\.environ)",
        description="Secret key hardcoded instead of using environment variable",
        remediation="Load SECRET_KEY from environment variables",
        confidence=ConfidenceLevel.MEDIUM,
    ),
]


class PatternDatabase:
    """Database of security patterns."""

    def __init__(self):
        """Initialize pattern database with all security patterns."""
        self.patterns: List[SecurityPattern] = []
        self._load_patterns()

    def _load_patterns(self):
        """Load all security patterns."""
        all_patterns = (
            SECRET_PATTERNS
            + SQL_INJECTION_PATTERNS
            + SSRF_PATTERNS
            + CRYPTO_PATTERNS
            + REDIRECT_PATTERNS
            + VALIDATION_PATTERNS
            + AUTH_PATTERNS
        )
        self.patterns = all_patterns

    def get_patterns_by_category(
        self, category: PatternCategory
    ) -> List[SecurityPattern]:
        """Get patterns filtered by category."""
        return [p for p in self.patterns if p.category == category]

    def get_patterns_by_severity(
        self, severity: SeverityLevel
    ) -> List[SecurityPattern]:
        """Get patterns filtered by severity."""
        return [p for p in self.patterns if p.severity == severity]

    def get_patterns_by_language(self, language: str) -> List[SecurityPattern]:
        """Get patterns applicable to a specific language."""
        return [
            p
            for p in self.patterns
            if not p.languages
            or language.lower() in [lang.lower() for lang in p.languages]
        ]

    def match_patterns(
        self,
        content: str,
        category: Optional[PatternCategory] = None,
        language: Optional[str] = None,
    ) -> List[Tuple[SecurityPattern, re.Match]]:
        """Match patterns against content.

        Args:
            content: Source code content to scan
            category: Optional category filter
            language: Optional language filter

        Returns:
            List of tuples containing matched patterns and their matches
        """
        patterns = self.patterns

        if category:
            patterns = [p for p in patterns if p.category == category]

        if language:
            patterns = [
                p
                for p in patterns
                if not p.languages
                or language.lower() in [lang.lower() for lang in p.languages]
            ]

        matches = []
        for pattern in patterns:
            for match in re.finditer(pattern.pattern, content):
                matches.append((pattern, match))

        return matches

    def calculate_entropy(self, string: str) -> float:
        """Calculate Shannon entropy of a string.

        High entropy strings are more likely to be secrets/tokens.

        Args:
            string: String to analyze

        Returns:
            Entropy value (0-8 for typical text)
        """
        if not string:
            return 0.0

        # Calculate frequency of each character
        freq = {}
        for char in string:
            freq[char] = freq.get(char, 0) + 1

        # Calculate entropy
        length = len(string)
        entropy = 0.0
        for count in freq.values():
            probability = count / length
            entropy -= probability * math.log2(probability)

        return entropy

    def is_likely_secret(
        self, string: str, min_entropy: float = 4.0, min_length: int = 20
    ) -> bool:
        """Check if a string is likely a secret based on entropy.

        Args:
            string: String to check
            min_entropy: Minimum entropy threshold
            min_length: Minimum length to consider

        Returns:
            True if string is likely a secret
        """
        if len(string) < min_length:
            return False

        entropy = self.calculate_entropy(string)
        return entropy >= min_entropy

    def get_pattern_count(self) -> int:
        """Get total number of patterns."""
        return len(self.patterns)

    def get_category_counts(self) -> dict:
        """Get count of patterns per category."""
        counts = {}
        for category in PatternCategory:
            counts[category.value] = len(self.get_patterns_by_category(category))
        return counts
