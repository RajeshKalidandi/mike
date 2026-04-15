"""Health score repository for database operations."""

from typing import Dict, List, Optional, Any
from datetime import datetime

from mike.db.models import Database


class HealthRepository:
    """Repository for architecture health scores."""

    def __init__(self, db: Database):
        self.db = db

    def save_score(self, session_id: str, score: Any) -> int:
        """Save architecture score to database.

        Args:
            session_id: Session ID
            score: ArchitectureScore object

        Returns:
            ID of the saved score record
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO architecture_scores (
                    session_id, timestamp, overall_score,
                    coupling_score, cohesion_score, circular_deps_score,
                    complexity_score, test_coverage_score, layer_violations_score,
                    unused_exports_score, total_files, total_functions,
                    circular_dependencies_count, layer_violations_count,
                    unused_exports_count
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    score.timestamp or datetime.now().isoformat(),
                    score.overall_score,
                    self._get_dimension_score(score, "coupling"),
                    self._get_dimension_score(score, "cohesion"),
                    self._get_dimension_score(score, "circular_deps"),
                    self._get_dimension_score(score, "complexity"),
                    self._get_dimension_score(score, "test_coverage"),
                    self._get_dimension_score(score, "layer_violations"),
                    self._get_dimension_score(score, "unused_exports"),
                    score.metadata.get("total_files", 0) if score.metadata else 0,
                    score.metadata.get("total_functions", 0) if score.metadata else 0,
                    score.metadata.get("circular_dependencies_count", 0)
                    if score.metadata
                    else 0,
                    score.metadata.get("layer_violations_count", 0)
                    if score.metadata
                    else 0,
                    score.metadata.get("unused_exports_count", 0)
                    if score.metadata
                    else 0,
                ),
            )

            score_id = cursor.lastrowid

            # Save component scores if available
            if score.metadata and "component_scores" in score.metadata:
                for component in score.metadata["component_scores"]:
                    cursor.execute(
                        """
                        INSERT INTO score_components (
                            score_id, component_type, component_path,
                            dimension, score, raw_value, threshold
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            score_id,
                            component.get("type", "file"),
                            component.get("path", ""),
                            component.get("dimension", ""),
                            component.get("score", 0.0),
                            component.get("raw_value"),
                            component.get("threshold"),
                        ),
                    )

            conn.commit()
            return score_id

    def _get_dimension_score(self, score: Any, dimension: str) -> float:
        """Get score for a specific dimension."""
        for ds in score.dimension_scores:
            if ds.dimension.value == dimension:
                return ds.score
        return 0.0

    def get_latest_score(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get the most recent score for a session.

        Args:
            session_id: Session ID

        Returns:
            Score record or None
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM architecture_scores
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT 1
                """,
                (session_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_score_history(
        self, session_id: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get historical scores for a session.

        Args:
            session_id: Session ID
            limit: Maximum number of records

        Returns:
            List of score records
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM architecture_scores
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (session_id, limit),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_components_below_threshold(
        self, session_id: str, dimension: Optional[str] = None, threshold: float = 50.0
    ) -> List[Dict[str, Any]]:
        """Get components with scores below threshold.

        Args:
            session_id: Session ID
            dimension: Optional dimension filter
            threshold: Score threshold

        Returns:
            List of component records
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()

            query = """
                SELECT sc.* FROM score_components sc
                JOIN architecture_scores a ON sc.score_id = a.id
                WHERE a.session_id = ? AND sc.score < ?
            """
            params = [session_id, threshold]

            if dimension:
                query += " AND sc.dimension = ?"
                params.append(dimension)

            query += " ORDER BY sc.score ASC"

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def delete_old_scores(self, session_id: str, keep_count: int = 10) -> int:
        """Delete old scores keeping only the most recent ones.

        Args:
            session_id: Session ID
            keep_count: Number of recent scores to keep

        Returns:
            Number of deleted records
        """
        with self.db._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                DELETE FROM architecture_scores
                WHERE session_id = ? AND id NOT IN (
                    SELECT id FROM architecture_scores
                    WHERE session_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                )
                """,
                (session_id, session_id, keep_count),
            )

            conn.commit()
            return cursor.rowcount
