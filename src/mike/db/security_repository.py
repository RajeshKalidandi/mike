"""Security findings repository for database operations."""

from typing import Dict, List, Optional, Any
from datetime import datetime

from mike.db.models import Database


class SecurityRepository:
    """Repository for security findings."""

    def __init__(self, db: Database):
        self.db = db

    def save_findings(self, session_id: str, findings: List[Any]) -> int:
        """Save security findings to database.

        Args:
            session_id: Session ID
            findings: List of SecurityFinding objects

        Returns:
            Number of findings saved
        """
        if not findings:
            return 0

        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            count = 0

            for finding in findings:
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO security_findings (
                        session_id, file_path, line_start, line_end,
                        issue_type, category, severity, confidence,
                        cvss_score, risk_score, title, description,
                        remediation, code_snippet, detected_at, rule_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        finding.file_path,
                        finding.line_number,
                        finding.line_number,
                        finding.pattern_id,
                        finding.category.value
                        if hasattr(finding.category, "value")
                        else str(finding.category),
                        finding.severity.name
                        if hasattr(finding.severity, "name")
                        else str(finding.severity),
                        finding.confidence.name
                        if hasattr(finding.confidence, "name")
                        else str(finding.confidence),
                        None,
                        finding.severity.value
                        if hasattr(finding.severity, "value")
                        else 5.0,
                        finding.message[:200]
                        if len(finding.message) > 200
                        else finding.message,
                        finding.message,
                        finding.remediation,
                        finding.matched_text[:500] if finding.matched_text else None,
                        datetime.now().isoformat(),
                        finding.pattern_id,
                    ),
                )
                count += 1

            conn.commit()
            return count

    def get_findings(
        self,
        session_id: str,
        severity: Optional[str] = None,
        category: Optional[str] = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """Get security findings for a session.

        Args:
            session_id: Session ID
            severity: Optional severity filter
            category: Optional category filter
            limit: Maximum number of records

        Returns:
            List of finding records
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()

            query = "SELECT * FROM security_findings WHERE session_id = ?"
            params = [session_id]

            if severity:
                query += " AND severity = ?"
                params.append(severity.upper())

            if category:
                query += " AND category = ?"
                params.append(category.lower())

            query += " ORDER BY severity DESC, risk_score DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_findings_summary(self, session_id: str) -> Dict[str, Any]:
        """Get summary of security findings.

        Args:
            session_id: Session ID

        Returns:
            Summary dictionary with counts by severity and category
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT severity, COUNT(*) as count
                FROM security_findings
                WHERE session_id = ?
                GROUP BY severity
                """,
                (session_id,),
            )
            by_severity = {row["severity"]: row["count"] for row in cursor.fetchall()}

            cursor.execute(
                """
                SELECT category, COUNT(*) as count
                FROM security_findings
                WHERE session_id = ?
                GROUP BY category
                """,
                (session_id,),
            )
            by_category = {row["category"]: row["count"] for row in cursor.fetchall()}

            cursor.execute(
                """
                SELECT COUNT(DISTINCT file_path) as count
                FROM security_findings
                WHERE session_id = ?
                """,
                (session_id,),
            )
            files_affected = cursor.fetchone()["count"]

            cursor.execute(
                """
                SELECT COUNT(*) as count
                FROM security_findings
                WHERE session_id = ?
                """,
                (session_id,),
            )
            total = cursor.fetchone()["count"]

            return {
                "total": total,
                "files_affected": files_affected,
                "by_severity": by_severity,
                "by_category": by_category,
            }

    def get_findings_by_file(
        self, session_id: str, file_path: str
    ) -> List[Dict[str, Any]]:
        """Get findings for a specific file.

        Args:
            session_id: Session ID
            file_path: File path

        Returns:
            List of finding records
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM security_findings
                WHERE session_id = ? AND file_path = ?
                ORDER BY line_start
                """,
                (session_id, file_path),
            )
            return [dict(row) for row in cursor.fetchall()]

    def mark_false_positive(
        self, finding_id: int, is_false_positive: bool = True
    ) -> bool:
        """Mark a finding as false positive.

        Args:
            finding_id: Finding ID
            is_false_positive: False positive flag

        Returns:
            True if updated successfully
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE security_findings
                SET false_positive = ?
                WHERE id = ?
                """,
                (1 if is_false_positive else 0, finding_id),
            )
            conn.commit()
            return cursor.rowcount > 0

    def delete_old_findings(self, session_id: str, keep_count: int = 1000) -> int:
        """Delete old findings keeping only the most recent ones.

        Args:
            session_id: Session ID
            keep_count: Number of recent findings to keep

        Returns:
            Number of deleted records
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                DELETE FROM security_findings
                WHERE session_id = ? AND id NOT IN (
                    SELECT id FROM security_findings
                    WHERE session_id = ?
                    ORDER BY detected_at DESC
                    LIMIT ?
                )
                """,
                (session_id, session_id, keep_count),
            )

            conn.commit()
            return cursor.rowcount
