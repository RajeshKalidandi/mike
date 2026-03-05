"""File tree widget for browsing session files."""

from textual.widgets import Tree, Static
from textual.reactive import reactive
from pathlib import Path
from typing import Dict, List, Any


class FileTree(Tree):
    """Tree widget for browsing session files."""

    def __init__(self, files: List[Dict[str, Any]], **kwargs):
        super().__init__("Files", **kwargs)
        self.files = files
        self._build_tree()

    def _build_tree(self):
        """Build the tree structure from files."""
        # Group files by directory
        dirs: Dict[str, Any] = {}

        for file_info in self.files:
            rel_path = file_info.get("relative_path", "")
            path_parts = Path(rel_path).parts

            current = dirs
            for i, part in enumerate(path_parts[:-1]):
                if part not in current:
                    current[part] = {"_files": [], "_type": "dir"}
                current = current[part]

            if path_parts:
                file_name = path_parts[-1]
                if "_files" not in current:
                    current["_files"] = []
                current["_files"].append((file_name, file_info))

        # Build tree nodes
        self._add_nodes(self.root, dirs)

    def _add_nodes(self, parent_node, dirs: Dict):
        """Recursively add nodes to tree."""
        # Add subdirectories first
        for name, content in sorted(dirs.items()):
            if name.startswith("_"):
                continue

            if isinstance(content, dict) and content.get("_type") == "dir":
                dir_node = parent_node.add(name, expand=True)
                self._add_nodes(dir_node, content)

        # Add files
        if "_files" in dirs:
            for file_name, file_info in sorted(dirs["_files"]):
                lang = file_info.get("language", "unknown")
                lines = file_info.get("line_count", 0)
                label = f"{file_name} ({lang}, {lines} lines)"
                parent_node.add_leaf(label, data=file_info)
