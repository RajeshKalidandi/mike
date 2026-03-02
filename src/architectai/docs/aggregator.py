"""Data aggregation for documentation generation."""

from typing import Dict, List, Any, Optional
from collections import defaultdict


class DataAggregator:
    """Aggregates and structures data from parsed codebase."""

    COMMON_ENTRY_NAMES = [
        "main",
        "app",
        "server",
        "index",
        "cli",
        "entry",
        "manage",
        "run",
        "start",
        "bootstrap",
    ]

    def __init__(self, db):
        """Initialize with database connection."""
        self.db = db

    def aggregate_session_data(self, session_id: str) -> Dict[str, Any]:
        """Aggregate all data for a session.

        Returns:
            Dict with:
            - total_files: int
            - total_lines: int
            - languages: Dict[str, int] (language -> file count)
            - file_tree: Dict (hierarchical file structure)
            - entry_points: List[str]
        """
        files = self.db.get_files_for_session(session_id)

        # Basic stats
        total_files = len(files)
        total_lines = sum(f.get("line_count", 0) for f in files)

        # Language breakdown
        languages = defaultdict(int)
        for f in files:
            lang = f.get("language", "Unknown")
            languages[lang] += 1

        # Build file tree
        file_tree = self.build_module_hierarchy(files)

        # Detect entry points
        entry_points = self.detect_entry_points(files)

        return {
            "total_files": total_files,
            "total_lines": total_lines,
            "languages": dict(languages),
            "file_tree": file_tree,
            "entry_points": entry_points,
            "files": files,
        }

    def build_module_hierarchy(self, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build hierarchical module structure from file paths."""
        tree = {}

        for file_info in files:
            path = file_info["relative_path"]
            parts = path.split("/")

            current = tree
            for i, part in enumerate(parts[:-1]):
                if part not in current:
                    current[part] = {}
                current = current[part]

            # Add file to leaf
            filename = parts[-1]
            if "__files__" not in current:
                current["__files__"] = []
            current["__files__"].append(
                {
                    "name": filename,
                    "language": file_info.get("language", "Unknown"),
                    "lines": file_info.get("line_count", 0),
                    "path": path,
                }
            )

        return tree

    def detect_entry_points(self, files: List[Dict[str, Any]]) -> List[str]:
        """Detect potential entry points in the codebase."""
        entry_points = []

        for file_info in files:
            path = file_info["relative_path"]
            filename = path.split("/")[-1]
            name_without_ext = filename.split(".")[0].lower()

            if name_without_ext in self.COMMON_ENTRY_NAMES:
                entry_points.append(path)

        return entry_points

    def get_file_by_path(
        self, session_id: str, relative_path: str
    ) -> Optional[Dict[str, Any]]:
        """Get specific file info by relative path."""
        files = self.db.get_files_for_session(session_id)
        for f in files:
            if f["relative_path"] == relative_path:
                return f
        return None
