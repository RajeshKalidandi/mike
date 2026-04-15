"""Patch repository for database operations."""

import json
from typing import Dict, List, Optional, Any
from datetime import datetime

from mike.db.models import Database


class PatchRepository:
    """Repository for patch applications."""

    def __init__(self, db: Database):
        self.db = db

    def save_patch(
        self,
        session_id: str,
        patch_id: str,
        suggestion_id: Optional[str] = None,
        diff_content: str = "",
        files_affected: Optional[List[str]] = None,
        source: str = "refactor",
    ) -> bool:
        """Save a patch to the database.

        Args:
            session_id: Session ID
            patch_id: Patch ID
            suggestion_id: Optional suggestion ID
            diff_content: Diff content
            files_affected: List of affected files
            source: Source of the patch

        Returns:
            True if saved successfully
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT OR REPLACE INTO patches (
                    id, session_id, suggestion_id, diff_content,
                    files_affected, status, source, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    patch_id,
                    session_id,
                    suggestion_id,
                    diff_content,
                    json.dumps(files_affected) if files_affected else "[]",
                    "pending",
                    source,
                    datetime.now().isoformat(),
                ),
            )

            conn.commit()
            return cursor.rowcount > 0

    def get_patch(self, patch_id: str) -> Optional[Dict[str, Any]]:
        """Get a patch by ID.

        Args:
            patch_id: Patch ID

        Returns:
            Patch record or None
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM patches WHERE id = ?",
                (patch_id,),
            )
            row = cursor.fetchone()

            if row:
                result = dict(row)
                if result.get("files_affected"):
                    try:
                        result["files_affected"] = json.loads(result["files_affected"])
                    except json.JSONDecodeError:
                        result["files_affected"] = []
                if result.get("backup_paths"):
                    try:
                        result["backup_paths"] = json.loads(result["backup_paths"])
                    except json.JSONDecodeError:
                        result["backup_paths"] = {}
                if result.get("errors"):
                    try:
                        result["errors"] = json.loads(result["errors"])
                    except json.JSONDecodeError:
                        result["errors"] = []
                return result
            return None

    def get_patch_by_suggestion_id(
        self, session_id: str, suggestion_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a patch by suggestion ID.

        Args:
            session_id: Session ID
            suggestion_id: Suggestion ID

        Returns:
            Patch record or None
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM patches
                WHERE session_id = ? AND suggestion_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (session_id, suggestion_id),
            )
            row = cursor.fetchone()

            if row:
                result = dict(row)
                if result.get("files_affected"):
                    try:
                        result["files_affected"] = json.loads(result["files_affected"])
                    except json.JSONDecodeError:
                        result["files_affected"] = []
                return result
            return None

    def get_patches_by_session(
        self,
        session_id: str,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get patches for a session.

        Args:
            session_id: Session ID
            status: Optional status filter
            limit: Maximum number of records

        Returns:
            List of patch records
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()

            if status:
                cursor.execute(
                    """
                    SELECT * FROM patches
                    WHERE session_id = ? AND status = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (session_id, status, limit),
                )
            else:
                cursor.execute(
                    """
                    SELECT * FROM patches
                    WHERE session_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (session_id, limit),
                )

            rows = cursor.fetchall()
            results = []

            for row in rows:
                result = dict(row)
                if result.get("files_affected"):
                    try:
                        result["files_affected"] = json.loads(result["files_affected"])
                    except json.JSONDecodeError:
                        result["files_affected"] = []
                results.append(result)

            return results

    def get_last_applied_patch(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get the most recently applied patch.

        Args:
            session_id: Session ID

        Returns:
            Patch record or None
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM patches
                WHERE session_id = ? AND status = 'applied'
                ORDER BY applied_at DESC
                LIMIT 1
                """,
                (session_id,),
            )
            row = cursor.fetchone()

            if row:
                result = dict(row)
                if result.get("files_affected"):
                    try:
                        result["files_affected"] = json.loads(result["files_affected"])
                    except json.JSONDecodeError:
                        result["files_affected"] = []
                if result.get("backup_paths"):
                    try:
                        result["backup_paths"] = json.loads(result["backup_paths"])
                    except json.JSONDecodeError:
                        result["backup_paths"] = {}
                return result
            return None

    def update_patch_status(
        self,
        patch_id: str,
        status: str,
        applied_at: Optional[str] = None,
        rolled_back_at: Optional[str] = None,
        backup_paths: Optional[Dict[str, str]] = None,
        errors: Optional[List[str]] = None,
    ) -> bool:
        """Update patch status.

        Args:
            patch_id: Patch ID
            status: New status
            applied_at: Optional applied timestamp
            rolled_back_at: Optional rolled back timestamp
            backup_paths: Optional backup paths dictionary
            errors: Optional list of errors

        Returns:
            True if updated successfully
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE patches
                SET status = ?,
                    applied_at = ?,
                    rolled_back_at = ?,
                    backup_paths = ?,
                    errors = ?
                WHERE id = ?
                """,
                (
                    status,
                    applied_at,
                    rolled_back_at,
                    json.dumps(backup_paths) if backup_paths else None,
                    json.dumps(errors) if errors else None,
                    patch_id,
                ),
            )

            conn.commit()
            return cursor.rowcount > 0

    def delete_patch(self, patch_id: str) -> bool:
        """Delete a patch.

        Args:
            patch_id: Patch ID

        Returns:
            True if deleted successfully
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM patches WHERE id = ?",
                (patch_id,),
            )
            conn.commit()
            return cursor.rowcount > 0

    def delete_old_patches(self, session_id: str, keep_count: int = 50) -> int:
        """Delete old patches keeping only the most recent ones.

        Args:
            session_id: Session ID
            keep_count: Number of recent patches to keep

        Returns:
            Number of deleted records
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                DELETE FROM patches
                WHERE session_id = ? AND id NOT IN (
                    SELECT id FROM patches
                    WHERE session_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                )
                """,
                (session_id, session_id, keep_count),
            )

            conn.commit()
            return cursor.rowcount
