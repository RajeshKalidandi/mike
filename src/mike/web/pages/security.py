"""Security Scanner page for Mike v2 Phase 1.

Provides security scan results, vulnerability filtering,
risk score display, and SARIF export functionality.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List

import streamlit as st

from mike.web.components.security_card import (
    render_risk_score_display,
    render_security_scan_summary,
    render_vulnerability_card,
    render_vulnerability_table,
)
from mike.web.utils import format_timestamp, get_db_path


def render_security_scanner():
    """Render the security scanner page."""
    st.title("🔒 Security Scanner")
    st.markdown("Detect and analyze security vulnerabilities in your codebase")

    # Check for active session
    if not st.session_state.get("current_session_id"):
        st.warning("No active session. Please select or create a session first.")
        if st.button("📁 Go to Sessions", use_container_width=True):
            st.session_state.current_page = "sessions"
            st.rerun()
        return

    session_id = st.session_state.current_session_id
    session_name = st.session_state.get("current_session_name", "Unnamed Session")

    st.markdown(f"**Session:** {session_name} (`{session_id[:8]}`)")

    # Generate sample security data
    security_data = _generate_sample_security_data()

    # Scan summary
    render_security_scan_summary(
        scan_timestamp=security_data["scan_timestamp"],
        files_scanned=security_data["files_scanned"],
        scan_duration=security_data["scan_duration"],
        vulnerabilities_found=len(security_data["vulnerabilities"]),
        risk_score=security_data["risk_score"],
    )

    # Risk score and vulnerability distribution
    st.markdown("### 🎯 Risk Assessment")
    render_risk_score_display(
        risk_score=security_data["risk_score"],
        vulnerabilities_by_severity=security_data["by_severity"],
    )

    st.divider()

    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(
        ["📋 Vulnerability List", "🔍 Detailed View", "📊 Statistics"]
    )

    with tab1:
        render_vulnerability_list_tab(security_data["vulnerabilities"])

    with tab2:
        render_detailed_view_tab(security_data["vulnerabilities"])

    with tab3:
        render_statistics_tab(security_data)

    st.divider()

    # Actions
    st.markdown("### 🚀 Actions")

    action_cols = st.columns(4)
    with action_cols[0]:
        if st.button("🔍 Run Security Scan", use_container_width=True):
            with st.spinner("Scanning for vulnerabilities..."):
                # In real implementation: call backend API
                st.success("Security scan completed!")
                st.rerun()

    with action_cols[1]:
        # Export SARIF
        sarif_data = _generate_sarif(security_data)
        st.download_button(
            label="📄 Export SARIF",
            data=sarif_data,
            file_name=f"security_scan_{session_id[:8]}.sarif",
            mime="application/sarif+json",
            use_container_width=True,
        )

    with action_cols[2]:
        # Export JSON
        json_data = json.dumps(security_data, indent=2, default=str)
        st.download_button(
            label="📊 Export JSON",
            data=json_data,
            file_name=f"security_scan_{session_id[:8]}.json",
            mime="application/json",
            use_container_width=True,
        )

    with action_cols[3]:
        if st.button("🔧 Apply Fixes", use_container_width=True):
            st.info("Navigate to Patch Manager to apply security fixes")
            st.session_state.current_page = "patch"
            st.rerun()


def render_vulnerability_list_tab(vulnerabilities: List[Dict[str, Any]]):
    """Render the vulnerability list tab."""
    st.markdown("### 📋 Vulnerabilities")

    # Filters
    filter_cols = st.columns([2, 2, 1])

    with filter_cols[0]:
        severity_filter = st.multiselect(
            "Filter by Severity",
            ["Critical", "High", "Medium", "Low", "Info"],
            default=["Critical", "High", "Medium"],
        )

    with filter_cols[1]:
        search_term = st.text_input(
            "🔍 Search", placeholder="Search vulnerabilities..."
        )

    with filter_cols[2]:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()

    # Filter vulnerabilities
    filtered = vulnerabilities
    if severity_filter:
        filtered = [v for v in filtered if v.get("severity") in severity_filter]

    if search_term:
        search_lower = search_term.lower()
        filtered = [
            v
            for v in filtered
            if search_lower in v.get("title", "").lower()
            or search_lower in v.get("description", "").lower()
            or search_lower in v.get("file_path", "").lower()
        ]

    # Display table
    render_vulnerability_table(
        vulnerabilities=filtered,
        filter_severity=None,  # Already filtered above
        max_items=100,
    )


def render_detailed_view_tab(vulnerabilities: List[Dict[str, Any]]):
    """Render the detailed view tab with expandable cards."""
    st.markdown("### 🔍 Vulnerability Details")

    # Severity filter for detailed view
    severity_filter = st.multiselect(
        "Show Severities",
        ["Critical", "High", "Medium", "Low", "Info"],
        default=["Critical", "High", "Medium", "Low"],
        key="detailed_severity_filter",
    )

    # Filter and sort by severity
    filtered = vulnerabilities
    if severity_filter:
        filtered = [v for v in filtered if v.get("severity") in severity_filter]

    severity_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3, "Info": 4}
    filtered.sort(key=lambda x: severity_order.get(x.get("severity"), 5))

    # Display cards
    st.markdown(f"**Showing {len(filtered)} vulnerabilities**")

    for vuln in filtered:

        def on_fix(v):
            st.success(f"Applied fix for: {v['title']}")

        def on_ignore(v):
            st.warning(f"Ignored: {v['title']}")

        render_vulnerability_card(
            vulnerability=vuln,
            expanded=False,
            on_fix=on_fix,
            on_ignore=on_ignore,
        )


def render_statistics_tab(security_data: Dict[str, Any]):
    """Render the statistics tab."""
    import plotly.express as px
    from mike.web.theme_utils import apply_chart_theme, get_current_theme

    theme = get_current_theme()

    st.markdown("### 📊 Security Statistics")

    # Severity distribution chart
    severity_data = security_data["by_severity"]

    col1, col2 = st.columns(2)

    with col1:
        fig = px.pie(
            names=list(severity_data.keys()),
            values=list(severity_data.values()),
            title="Vulnerabilities by Severity",
            color=list(severity_data.keys()),
            color_discrete_map={
                "Critical": "#ff4444",
                "High": "#ff6b6b",
                "Medium": "#ffbb33",
                "Low": "#3498db",
                "Info": "#95a5a6",
            },
        )
        fig = apply_chart_theme(fig, theme)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # CWE distribution
        cwe_counts = {}
        for v in security_data["vulnerabilities"]:
            cwe = v.get("cwe_id", "Unknown")
            cwe_counts[cwe] = cwe_counts.get(cwe, 0) + 1

        top_cwes = dict(
            sorted(cwe_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        )

        fig = px.bar(
            x=list(top_cwes.keys()),
            y=list(top_cwes.values()),
            title="Top 10 CWE Categories",
            labels={"x": "CWE ID", "y": "Count"},
        )
        fig = apply_chart_theme(fig, theme)
        st.plotly_chart(fig, use_container_width=True)

    # File distribution
    st.markdown("### 📁 Vulnerabilities by File")
    file_counts = {}
    for v in security_data["vulnerabilities"]:
        file_path = v.get("file_path", "Unknown")
        file_counts[file_path] = file_counts.get(file_path, 0) + 1

    top_files = dict(sorted(file_counts.items(), key=lambda x: x[1], reverse=True)[:10])

    fig = px.bar(
        x=list(top_files.values()),
        y=list(top_files.keys()),
        orientation="h",
        title="Top 10 Files with Most Vulnerabilities",
        labels={"x": "Vulnerability Count", "y": "File"},
    )
    fig = apply_chart_theme(fig, theme)
    st.plotly_chart(fig, use_container_width=True)


def _generate_sample_security_data() -> Dict[str, Any]:
    """Generate sample security data for demonstration."""
    import random

    vulnerabilities = [
        {
            "id": "VULN-001",
            "title": "SQL Injection in user input",
            "description": "User input is directly concatenated into SQL queries without parameterization",
            "severity": "Critical",
            "file_path": "src/services/database.py",
            "line_number": 45,
            "cwe_id": "CWE-89",
            "cvss_score": 9.8,
            "remediation": "Use parameterized queries or ORM methods instead of string concatenation",
            "code_snippet": 'query = f"SELECT * FROM users WHERE id = {user_id}"',
        },
        {
            "id": "VULN-002",
            "title": "Hardcoded API Key",
            "description": "API key is hardcoded in source code",
            "severity": "High",
            "file_path": "config.py",
            "line_number": 12,
            "cwe_id": "CWE-798",
            "cvss_score": 7.5,
            "remediation": "Move API keys to environment variables or secure vault",
            "code_snippet": 'API_KEY = "sk-1234567890abcdef"',
        },
        {
            "id": "VULN-003",
            "title": "Insecure Direct Object Reference",
            "description": "User can access resources by modifying object references",
            "severity": "High",
            "file_path": "src/controllers/user.py",
            "line_number": 78,
            "cwe_id": "CWE-639",
            "cvss_score": 6.5,
            "remediation": "Implement proper authorization checks",
            "code_snippet": "user = User.query.get(request.args.get('id'))",
        },
        {
            "id": "VULN-004",
            "title": "Weak Password Hashing",
            "description": "Using MD5 for password hashing which is cryptographically broken",
            "severity": "Medium",
            "file_path": "src/auth.py",
            "line_number": 34,
            "cwe_id": "CWE-916",
            "cvss_score": 5.3,
            "remediation": "Use bcrypt, Argon2, or PBKDF2 for password hashing",
            "code_snippet": "hash = md5(password.encode()).hexdigest()",
        },
        {
            "id": "VULN-005",
            "title": "Missing Input Validation",
            "description": "Input is not validated before processing",
            "severity": "Medium",
            "file_path": "src/api.py",
            "line_number": 56,
            "cwe_id": "CWE-20",
            "cvss_score": 5.0,
            "remediation": "Add input validation and sanitization",
            "code_snippet": "data = request.get_json()",
        },
        {
            "id": "VULN-006",
            "title": "Debug Mode Enabled",
            "description": "Application is running in debug mode in production",
            "severity": "Low",
            "file_path": "app.py",
            "line_number": 15,
            "cwe_id": "CWE-489",
            "cvss_score": 4.0,
            "remediation": "Set debug=False in production",
            "code_snippet": "app.run(debug=True)",
        },
    ]

    # Add more random vulnerabilities
    for i in range(7, 15):
        severities = ["Critical", "High", "Medium", "Low", "Info"]
        weights = [0.1, 0.2, 0.3, 0.25, 0.15]
        severity = random.choices(severities, weights=weights)[0]

        vulnerabilities.append(
            {
                "id": f"VULN-{i:03d}",
                "title": f"Security Issue #{i}",
                "description": f"Description of security issue {i}",
                "severity": severity,
                "file_path": f"src/module{i}.py",
                "line_number": random.randint(1, 100),
                "cwe_id": f"CWE-{random.randint(1, 1000)}",
                "cvss_score": random.uniform(0, 10),
            }
        )

    # Calculate counts by severity
    by_severity = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0, "Info": 0}
    for v in vulnerabilities:
        sev = v.get("severity", "Info")
        by_severity[sev] = by_severity.get(sev, 0) + 1

    # Calculate risk score
    risk_score = (
        (
            by_severity["Critical"] * 10
            + by_severity["High"] * 7
            + by_severity["Medium"] * 4
            + by_severity["Low"] * 1
        )
        / max(len(vulnerabilities), 1)
        * 10
    )

    return {
        "scan_timestamp": format_timestamp(datetime.now().isoformat()),
        "files_scanned": random.randint(50, 200),
        "scan_duration": random.uniform(5, 30),
        "vulnerabilities": vulnerabilities,
        "by_severity": by_severity,
        "risk_score": min(risk_score, 100),
    }


def _generate_sarif(security_data: Dict[str, Any]) -> str:
    """Generate SARIF format output."""
    sarif = {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "Mike Security Scanner",
                        "version": "2.0.0",
                    }
                },
                "results": [
                    {
                        "ruleId": v["cwe_id"],
                        "message": {"text": v["title"]},
                        "level": v["severity"].lower(),
                        "locations": [
                            {
                                "physicalLocation": {
                                    "artifactLocation": {"uri": v["file_path"]},
                                    "region": {"startLine": v["line_number"]},
                                }
                            }
                        ],
                    }
                    for v in security_data["vulnerabilities"]
                ],
            }
        ],
    }

    return json.dumps(sarif, indent=2)


# Page entry point
if __name__ == "__main__":
    render_security_scanner()
