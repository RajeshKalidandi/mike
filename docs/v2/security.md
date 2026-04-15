# Security Agent

The Security Agent provides comprehensive vulnerability scanning capabilities for your codebase. It detects security issues ranging from hardcoded secrets to injection vulnerabilities, with support for multiple languages and export formats.

## Overview

The Security Scanner analyzes code using:

1. **Pattern-Based Detection** - Regex patterns for known vulnerabilities
2. **Entropy Analysis** - High-entropy string detection for secrets
3. **Language-Specific Rules** - Tailored detection per language
4. **False Positive Reduction** - Built-in filtering

## Pattern Categories

### 1. Secrets & Credentials

Detects hardcoded sensitive data:

| Pattern | Description | Severity |
|---------|-------------|----------|
| `API_KEY` | API keys in various formats | High |
| `PASSWORD` | Hardcoded passwords | Critical |
| `PRIVATE_KEY` | Cryptographic private keys | Critical |
| `TOKEN` | Authentication tokens | High |
| `DATABASE_URL` | Database connection strings | High |

**Example Detection:**
```python
# Will be flagged
API_KEY = "sk_live_abcdefghijklmnopqrstuvwxyz123456"
SECRET = "my-password-123"
```

### 2. Injection Vulnerabilities

Detects code injection risks:

| Pattern | Description | Severity |
|---------|-------------|----------|
| `SQL_INJECTION` | SQL injection via string formatting | Critical |
| `COMMAND_INJECTION` | Shell command injection | Critical |
| `EVAL` | Use of eval() with untrusted input | High |
| `FORMAT_STRING` | Format string vulnerabilities | Medium |

**Example Detection:**
```python
# SQL Injection risk
query = f"SELECT * FROM users WHERE id = {user_id}"
cursor.execute(query)

# Command Injection
os.system(f"ping {user_input}")
```

### 3. Cryptographic Issues

Detects weak cryptographic practices:

| Pattern | Description | Severity |
|---------|-------------|----------|
| `MD5_HASH` | Use of broken MD5 hash | High |
| `SHA1_HASH` | Use of weak SHA1 hash | Medium |
| `ECB_MODE` | Insecure ECB encryption mode | Critical |
| `WEAK_RANDOM` | Predictable random numbers | High |
| `HARDCODED_IV` | Hardcoded initialization vectors | Medium |

**Example Detection:**
```python
import hashlib
# Weak hashing
hashlib.md5(data).hexdigest()

# Insecure encryption
from Crypto.Cipher import AES
cipher = AES.new(key, AES.MODE_ECB)  # ECB mode is insecure
```

### 4. SSRF (Server-Side Request Forgery)

Detects potential SSRF vulnerabilities:

| Pattern | Description | Severity |
|---------|-------------|----------|
| `UNVALIDATED_URL` | URL requests with user input | High |
| `DNS_REBINDING` | DNS rebinding risks | Medium |

**Example Detection:**
```python
import requests

# SSRF risk
url = request.args.get('url')
response = requests.get(url)  # Could access internal services
```

### 5. Open Redirects

Detects potential open redirect vulnerabilities:

| Pattern | Description | Severity |
|---------|-------------|----------|
| `UNVALIDATED_REDIRECT` | Redirects with user input | Medium |

**Example Detection:**
```python
from flask import redirect

# Open redirect risk
return redirect(request.args.get('next'))
```

### 6. Input Validation

Detects missing input validation:

| Pattern | Description | Severity |
|---------|-------------|----------|
| `NO_VALIDATION` | Direct use of user input | Medium |
| `TYPE_JUGGLING` | Type juggling vulnerabilities | Medium |

## Risk Scoring

### Severity Levels

| Level | Weight | Description |
|-------|--------|-------------|
| **Critical** | 5 | Immediate risk, likely exploitable |
| **High** | 4 | Significant risk, should fix soon |
| **Medium** | 3 | Moderate risk, fix in next sprint |
| **Low** | 2 | Minor risk, fix when convenient |
| **Info** | 1 | Informational only |

### Confidence Levels

| Level | Weight | Description |
|-------|--------|-------------|
| **High** | 1.0 | Very likely a true positive |
| **Medium** | 0.6 | Likely a true positive |
| **Low** | 0.3 | Possible false positive |

### Overall Risk Score

The risk score (0-10) is calculated as:

```
Risk Score = Σ(Severity × Confidence) / 5
```

Where:
- Critical finding with High confidence = 5 points
- 10 such findings = maximum score of 10

## Usage

### Basic Scan

```python
from mike.security import SecurityScanner

scanner = SecurityScanner()
report = scanner.scan_project("/path/to/project")

print(f"Risk Score: {report.risk_score}/10")
print(f"Total Findings: {len(report.findings)}")
```

### Scan Single File

```python
# Scan a specific file
findings = scanner.scan_file("/path/to/file.py")

for finding in findings:
    print(f"{finding.severity.name}: {finding.message}")
    print(f"  File: {finding.file_path}:{finding.line_number}")
    print(f"  Remediation: {finding.remediation}")
```

### Custom Configuration

```python
# Scan with custom extensions
report = scanner.scan_project(
    project_path="/path/to/project",
    include_extensions={".py", ".js", ".ts"},
    exclude_patterns=["test_", "_test.py", ".venv/"],
)
```

### Filter by Severity

```python
from mike.security.models import SeverityLevel

# Get only critical findings
critical = report.get_findings_by_severity(SeverityLevel.CRITICAL)
print(f"Critical issues: {len(critical)}")

# Get only high severity and above
high_and_above = [
    f for f in report.findings 
    if f.severity >= SeverityLevel.HIGH
]
```

### Filter by Category

```python
from mike.security.models import PatternCategory

# Get only secrets
secrets = report.get_findings_by_category(PatternCategory.SECRETS)

# Get injection vulnerabilities
injections = report.get_findings_by_category(PatternCategory.INJECTION)
```

## False Positive Handling

### Automatic Filtering

The scanner automatically filters common false positives:

1. **Environment Variable Access**
   ```python
   os.environ.get('API_KEY')  # Not flagged
   os.getenv('SECRET')        # Not flagged
   ```

2. **Placeholder Values**
   ```python
   API_KEY = "your-api-key"   # Not flagged
   PASSWORD = "changeme"      # Not flagged
   SECRET = "placeholder"     # Not flagged
   ```

3. **Config References**
   ```python
   settings.API_KEY   # Not flagged
   config.SECRET_KEY  # Not flagged
   ```

4. **None Assignments**
   ```python
   API_KEY = None     # Not flagged
   SECRET = null      # Not flagged (JavaScript)
   ```

### Manual Suppression

Add comments to suppress specific findings:

```python
# nosec - This is a test credential
TEST_API_KEY = "test-key-123"

# mike-ignore - Intentionally weak for backward compatibility
hashlib.md5(data).hexdigest()  # noqa: MD5_WARNING
```

## SARIF Export

SARIF (Static Analysis Results Interchange Format) is a standard format for security tools.

### Export to SARIF

```python
import json

sarif_report = report.to_sarif()

with open("security_report.sarif", "w") as f:
    json.dump(sarif_report, f, indent=2)
```

### SARIF Structure

```json
{
  "version": "2.1.0",
  "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
  "runs": [{
    "tool": {
      "driver": {
        "name": "Mike Security Scanner",
        "version": "0.1.0",
        "rules": [...]
      }
    },
    "results": [{
      "ruleId": "HARDCODED_SECRET",
      "level": "error",
      "message": {"text": "Hardcoded API key detected"},
      "locations": [{
        "physicalLocation": {
          "artifactLocation": {"uri": "config.py"},
          "region": {
            "startLine": 5,
            "startColumn": 10,
            "endColumn": 50
          }
        }
      }]
    }]
  }]
}
```

### GitHub Integration

Upload SARIF to GitHub for security alerts:

```yaml
name: Security Scan

on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Run Security Scan
        run: |
          pip install mike
          mike security . --sarif-output security.sarif
      
      - name: Upload SARIF
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: security.sarif
```

## Reports and Summaries

### Summary Report

```python
summary = report.get_summary()

print(f"""
Security Scan Summary
====================
Target: {summary['target_path']}
Risk Score: {summary['risk_score']}/10
Total Findings: {summary['total_findings']}
Files Scanned: {summary['scanned_files']}
Duration: {summary['scan_duration_seconds']:.2f}s

Severity Breakdown:
  Critical: {summary['severity_counts']['CRITICAL']}
  High: {summary['severity_counts']['HIGH']}
  Medium: {summary['severity_counts']['MEDIUM']}
  Low: {summary['severity_counts']['LOW']}
  Info: {summary['severity_counts']['INFO']}
""")
```

### Detailed Report

```python
# Generate markdown report
with open("SECURITY_REPORT.md", "w") as f:
    f.write("# Security Scan Report\n\n")
    f.write(f"**Risk Score:** {report.risk_score}/10\n\n")
    f.write(f"**Scanned:** {report.scanned_files} files\n\n")
    
    # Group by severity
    for severity in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        findings = report.get_findings_by_severity(SeverityLevel[severity])
        if findings:
            f.write(f"## {severity} ({len(findings)})\n\n")
            for finding in findings:
                f.write(f"### {finding.pattern_id}\n\n")
                f.write(f"- **File:** `{finding.file_path}:{finding.line_number}`\n")
                f.write(f"- **Message:** {finding.message}\n")
                f.write(f"- **Remediation:** {finding.remediation}\n\n")
```

## Best Practices

### 1. Regular Scanning

Add to your CI/CD pipeline:

```yaml
security-scan:
  script:
    - mike security . --fail-on-critical
```

### 2. Severity Thresholds

Fail builds based on severity:

```python
# Fail if any critical findings
critical = report.get_findings_by_severity(SeverityLevel.CRITICAL)
if critical:
    raise Exception(f"Found {len(critical)} critical security issues!")

# Or fail based on risk score
if report.risk_score > 5.0:
    raise Exception(f"Risk score {report.risk_score} exceeds threshold!")
```

### 3. Custom Rules

Add custom patterns for your codebase:

```python
from mike.security.models import SecurityPattern, PatternCategory, SeverityLevel

# Add custom pattern
custom_pattern = SecurityPattern(
    id="INTERNAL_SECRET",
    name="Internal Secret",
    category=PatternCategory.SECRETS,
    severity=SeverityLevel.HIGH,
    pattern=r'INTERNAL_TOKEN\s*=\s*["\'][^"\']{20,}["\']',
    description="Internal service token detected",
    remediation="Move to environment variables",
)

scanner.pattern_db.add_pattern(custom_pattern)
```

### 4. Whitelist Files

Exclude test files and documentation:

```python
exclude_patterns = [
    r"test_.*\.py$",
    r".*_test\.py$",
    r"\.md$",
    r"docs/.*",
    r"\.venv/.*",
]

report = scanner.scan_project(
    "/path/to/project",
    exclude_patterns=exclude_patterns,
)
```

### 5. Monitor Trends

Track security over time:

```python
import json
from datetime import datetime

# Load previous report
try:
    with open("security_history.json") as f:
        history = json.load(f)
except FileNotFoundError:
    history = []

# Add current report
history.append({
    "date": datetime.now().isoformat(),
    "risk_score": report.risk_score,
    "critical": len(report.get_findings_by_severity(SeverityLevel.CRITICAL)),
    "high": len(report.get_findings_by_severity(SeverityLevel.HIGH)),
})

# Save history
with open("security_history.json", "w") as f:
    json.dump(history, f, indent=2)

# Check trend
if len(history) >= 2:
    prev = history[-2]
    curr = history[-1]
    if curr["risk_score"] > prev["risk_score"] + 1:
        print("⚠️ Risk score increased significantly!")
```

## CLI Integration

### Scan Command

```bash
# Scan current directory
mike security .

# Scan specific path
mike security /path/to/project

# Export SARIF
mike security . --format sarif --output security.sarif

# Fail on critical findings
mike security . --fail-on-critical

# Show only high severity and above
mike security . --min-severity high
```

### Output Formats

```bash
# Plain text (default)
mike security . --format plain

# JSON
mike security . --format json

# SARIF
mike security . --format sarif

# Markdown
mike security . --format markdown
```

## Troubleshooting

### High False Positive Rate

If you're seeing too many false positives:

1. **Check exclusions** - Ensure test files and docs are excluded
2. **Review patterns** - Some patterns may need tuning for your codebase
3. **Use confidence filtering** - Only report high-confidence findings

```python
high_confidence = [
    f for f in report.findings
    if f.confidence == ConfidenceLevel.HIGH
]
```

### Missing Findings

If expected vulnerabilities aren't detected:

1. **Check file extensions** - Ensure file type is supported
2. **Verify patterns** - Pattern may need updating
3. **Check encoding** - Files must be UTF-8 readable

### Performance Issues

For large codebases:

1. **Use parallel scanning** - Process files concurrently
2. **Limit file types** - Only scan code files
3. **Exclude directories** - Skip node_modules, .venv, etc.

```python
report = scanner.scan_project(
    "/path/to/project",
    include_extensions={".py", ".js"},  # Limit to specific types
)
```
