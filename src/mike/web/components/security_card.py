"""Security card component for displaying vulnerability information.

Provides cards and tables for security scan results with severity indicators.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import streamlit as st

from mike.web.theme_utils import get_current_theme, get_theme_colors


def render_vulnerability_card(
    vulnerability: Dict[str, Any],
    expanded: bool = False,
    on_fix: Optional[callable] = None,
    on_ignore: Optional[callable] = None,
) -> None:
    """Render a vulnerability card with details.

    Args:
        vulnerability: Vulnerability data dict
        expanded: Whether to expand the card by default
        on_fix: Callback when fix button is clicked
        on_ignore: Callback when ignore button is clicked
    """
    theme = get_current_theme()
    colors = get_theme_colors(theme)

    severity = vulnerability.get("severity", "Unknown").upper()
    title = vulnerability.get("title", "Unknown Vulnerability")
    description = vulnerability.get("description", "No description available")
    file_path = vulnerability.get("file_path", "")
    line_number = vulnerability.get("line_number", 0)
    cwe_id = vulnerability.get("cwe_id", "")
    cvss_score = vulnerability.get("cvss_score", 0)

    # Severity colors
    severity_config = {
        "CRITICAL": {
            "color": colors["error"],
            "icon": "🔴",
            "bg": f"{colors['error']}15",
        },
        "HIGH": {"color": "#ff6b6b", "icon": "🟠", "bg": "#ff6b6b15"},
        "MEDIUM": {
            "color": colors["warning"],
            "icon": "🟡",
            "bg": f"{colors['warning']}15",
        },
        "LOW": {"color": colors["info"], "icon": "🔵", "bg": f"{colors['info']}15"},
        "INFO": {
            "color": colors["text_secondary"],
            "icon": "⚪",
            "bg": f"{colors['text_secondary']}15",
        },
    }
    config = severity_config.get(severity, severity_config["INFO"])

    with st.container():
        # Card header
        st.markdown(
            f"""
        <div style="
            background-color: {colors["card_background"]};
            border-left: 4px solid {config["color"]};
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 10px;
            border: 1px solid {colors["border"]};
        ">
            <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                <div>
                    <span style="
                        background-color: {config["bg"]};
                        color: {config["color"]};
                        padding: 2px 8px;
                        border-radius: 4px;
                        font-size: 12px;
                        font-weight: bold;
                        margin-right: 10px;
                    ">{config["icon"]} {severity}</span>
                    <strong style="color: {colors["text"]};">{title}</strong>
                </div>
                {f'<span style="color: {colors["text_secondary"]}; font-size: 12px;">CVSS: {cvss_score}</span>' if cvss_score else ""}
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        # Expandable details
        with st.expander("View Details", expanded=expanded):
            st.markdown(f"**Description:** {description}")

            if file_path:
                st.markdown(
                    f"**Location:** `{file_path}`{f':{line_number}' if line_number else ''}"
                )

            if cwe_id:
                st.markdown(
                    f"**CWE:** [{cwe_id}](https://cwe.mitre.org/data/definitions/{cwe_id.replace('CWE-', '')}.html)"
                )

            # Remediation
            remediation = vulnerability.get("remediation", "")
            if remediation:
                st.markdown("**Remediation:**")
                st.info(remediation)

            # Code snippet
            code_snippet = vulnerability.get("code_snippet", "")
            if code_snippet:
                st.markdown("**Code:**")
                st.code(code_snippet, language="python")

            # Action buttons
            col1, col2, col3 = st.columns([1, 1, 3])
            with col1:
                if on_fix and st.button(
                    "🔧 Fix",
                    key=f"fix_{vulnerability.get('id', 'unknown')}",
                    use_container_width=True,
                ):
                    on_fix(vulnerability)
            with col2:
                if on_ignore and st.button(
                    "🚫 Ignore",
                    key=f"ignore_{vulnerability.get('id', 'unknown')}",
                    use_container_width=True,
                ):
                    on_ignore(vulnerability)

        st.divider()


def render_vulnerability_table(
    vulnerabilities: List[Dict[str, Any]],
    filter_severity: Optional[List[str]] = None,
    max_items: int = 100,
) -> None:
    """Render a table of vulnerabilities with filtering.

    Args:
        vulnerabilities: List of vulnerability dicts
        filter_severity: List of severities to include (e.g., ['Critical', 'High'])
        max_items: Maximum number of items to display
    """
    import pandas as pd

    theme = get_current_theme()
    colors = get_theme_colors(theme)

    if not vulnerabilities:
        st.info("No vulnerabilities found")
        return

    # Filter by severity
    if filter_severity:
        vulnerabilities = [
            v
            for v in vulnerabilities
            if v.get("severity", "").upper() in [s.upper() for s in filter_severity]
        ]

    # Sort by severity (Critical first)
    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
    sorted_vulns = sorted(
        vulnerabilities,
        key=lambda x: severity_order.get(x.get("severity", "").upper(), 5),
    )[:max_items]

    # Prepare data
    df_data = []
    for v in sorted_vulns:
        severity = v.get("severity", "Unknown")
        if severity.upper() == "CRITICAL":
            icon = "🔴"
        elif severity.upper() == "HIGH":
            icon = "🟠"
        elif severity.upper() == "MEDIUM":
            icon = "🟡"
        elif severity.upper() == "LOW":
            icon = "🔵"
        else:
            icon = "⚪"

        df_data.append(
            {
                "Severity": f"{icon} {severity}",
                "Title": v.get("title", "Unknown"),
                "File": v.get("file_path", "").split("/")[-1]
                if v.get("file_path")
                else "",
                "Line": v.get("line_number", ""),
                "CWE": v.get("cwe_id", ""),
                "CVSS": v.get("cvss_score", ""),
            }
        )

    df = pd.DataFrame(df_data)

    # Display with styling
    st.markdown(f"**Showing {len(df_data)} of {len(vulnerabilities)} vulnerabilities**")
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_risk_score_display(
    risk_score: float,
    vulnerabilities_by_severity: Dict[str, int],
) -> None:
    """Render the overall risk score with breakdown.

    Args:
        risk_score: Overall risk score (0-100, higher is worse)
        vulnerabilities_by_severity: Dict of severity -> count
    """
    theme = get_current_theme()
    colors = get_theme_colors(theme)

    # Determine risk level
    if risk_score >= 80:
        risk_level = "Critical"
        risk_color = colors["error"]
        risk_icon = "🔴"
    elif risk_score >= 60:
        risk_level = "High"
        risk_color = "#ff6b6b"
        risk_icon = "🟠"
    elif risk_score >= 40:
        risk_level = "Medium"
        risk_color = colors["warning"]
        risk_icon = "🟡"
    elif risk_score >= 20:
        risk_level = "Low"
        risk_color = colors["info"]
        risk_icon = "🔵"
    else:
        risk_level = "Minimal"
        risk_color = colors["success"]
        risk_icon = "🟢"

    col1, col2 = st.columns([1, 2])

    with col1:
        # Risk score circle
        st.markdown(
            f"""
        <div style="
            width: 150px;
            height: 150px;
            border-radius: 50%;
            background-color: {risk_color}20;
            border: 4px solid {risk_color};
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            margin: 0 auto;
        ">
            <div style="font-size: 36px; font-weight: bold; color: {risk_color};">
                {risk_score:.1f}
            </div>
            <div style="font-size: 12px; color: {colors["text_secondary"]};">
                Risk Score
            </div>
        </div>
        <div style="text-align: center; margin-top: 10px;">
            <span style="
                background-color: {risk_color}20;
                color: {risk_color};
                padding: 5px 15px;
                border-radius: 20px;
                font-weight: bold;
            ">{risk_icon} {risk_level}</span>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with col2:
        # Severity breakdown
        st.markdown("**Vulnerability Distribution**")

        severity_icons = {
            "Critical": "🔴",
            "High": "🟠",
            "Medium": "🟡",
            "Low": "🔵",
            "Info": "⚪",
        }

        for severity in ["Critical", "High", "Medium", "Low", "Info"]:
            count = vulnerabilities_by_severity.get(severity, 0)
            icon = severity_icons.get(severity, "⚪")

            st.markdown(f"{icon} **{severity}:** {count}")


def render_security_scan_summary(
    scan_timestamp: str,
    files_scanned: int,
    scan_duration: float,
    vulnerabilities_found: int,
    risk_score: float,
) -> None:
    """Render a summary card for security scan results.

    Args:
        scan_timestamp: When the scan was performed
        files_scanned: Number of files scanned
        scan_duration: Scan duration in seconds
        vulnerabilities_found: Total vulnerabilities found
        risk_score: Overall risk score
    """
    theme = get_current_theme()
    colors = get_theme_colors(theme)

    st.markdown(
        f"""
    <div style="
        background-color: {colors["card_background"]};
        border: 1px solid {colors["border"]};
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
    ">
        <h4 style="margin-top: 0; color: {colors["text"]};">🔒 Security Scan Summary</h4>
        <div style="display: grid; grid-template-columns: repeat(5, 1fr); gap: 15px;">
            <div style="text-align: center;">
                <div style="font-size: 12px; color: {colors["text_secondary"]};">Scan Date</div>
                <div style="font-weight: bold; color: {colors["text"]};">{scan_timestamp}</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 12px; color: {colors["text_secondary"]};">Files Scanned</div>
                <div style="font-weight: bold; color: {colors["text"]};">{files_scanned:,}</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 12px; color: {colors["text_secondary"]};">Scan Duration</div>
                <div style="font-weight: bold; color: {colors["text"]};">{scan_duration:.1f}s</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 12px; color: {colors["text_secondary"]};">Vulnerabilities</div>
                <div style="font-weight: bold; color: {colors["error"] if vulnerabilities_found > 0 else colors["success"]};">
                    {vulnerabilities_found}
                </div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 12px; color: {colors["text_secondary"]};">Risk Score</div>
                <div style="font-weight: bold; color: {colors["error"] if risk_score > 60 else colors["warning"] if risk_score > 40 else colors["success"]};">
                    {risk_score:.1f}
                </div>
            </div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )
