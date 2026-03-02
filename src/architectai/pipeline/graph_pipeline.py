"""Pipeline for building dependency graphs from parsed code."""

import os
from pathlib import Path
from typing import Dict, List, Optional, Set

from architectai.graph.builder import DependencyGraphBuilder
from architectai.parser.parser import ASTParser


class GraphPipeline:
    """Pipeline for constructing dependency graphs."""

    def __init__(self, db):
        """Initialize graph pipeline.

        Args:
            db: Database instance for file metadata
        """
        self.db = db

    def build_from_session(self, session_id: str) -> DependencyGraphBuilder:
        """Build dependency graph from all files in a session.

        Args:
            session_id: Session identifier

        Returns:
            DependencyGraphBuilder with populated graph
        """
        builder = DependencyGraphBuilder(session_id)
        conn = self.db._get_connection()
        cursor = conn.cursor()

        # Get all files for this session
        cursor.execute(
            "SELECT * FROM files WHERE session_id = ? AND language != 'Unknown'",
            (session_id,),
        )
        files = cursor.fetchall()

        # Build file path to language mapping
        file_map: Dict[str, str] = {}
        file_languages: Dict[str, str] = {}
        for row in files:
            relative_path = row["relative_path"]
            file_map[relative_path] = row["absolute_path"]
            file_languages[relative_path] = row["language"]

            # Add node with metadata
            builder.add_node(
                relative_path,
                {
                    "language": row["language"],
                    "size_bytes": row["size_bytes"],
                    "line_count": row["line_count"],
                },
            )

        # Extract imports from each file and add edges
        all_files = set(file_map.keys())
        for relative_path, absolute_path in file_map.items():
            language = file_languages[relative_path]
            self._extract_file_edges(
                builder, relative_path, absolute_path, language, all_files
            )

        # Save to database
        builder.save_to_db(self.db)

        return builder

    def _extract_file_edges(
        self,
        builder: DependencyGraphBuilder,
        source_path: str,
        absolute_path: str,
        language: str,
        all_files: Set[str],
    ) -> None:
        """Extract import edges from a single file.

        Args:
            builder: Graph builder to add edges to
            source_path: Relative path of source file
            absolute_path: Absolute path to source file
            language: Programming language
            all_files: Set of all file paths in the codebase
        """
        try:
            # Map language to parser language
            parser_lang = self._map_language_to_parser(language)
            if not parser_lang:
                return

            # Read file content
            with open(absolute_path, "r", encoding="utf-8") as f:
                code = f.read()

            # Parse and extract imports
            parser = ASTParser()
            result = parser.parse(code, parser_lang)

            # Extract imports and resolve to file paths
            for imp in result.get("imports", []):
                module = imp.get("module", "")
                name = imp.get("name", "")

                # Determine what to resolve
                # For "import X": module=X, name=X -> resolve X
                # For "from X import Y": module=X.Y, name=Y -> resolve X
                if module and module != name:
                    # from X import Y - extract base module X
                    import_path = module.rsplit(".", 1)[0] if "." in module else module
                else:
                    # import X
                    import_path = name

                if import_path:
                    target_path = self.resolve_import_path(
                        source_path, import_path, parser_lang, all_files
                    )
                    if target_path:
                        builder.add_edge(source_path, target_path, "import")

        except Exception:
            # Silently skip files that can't be parsed
            pass

    def _map_language_to_parser(self, language: str) -> Optional[str]:
        """Map detected language to parser language.

        Args:
            language: Language from scanner

        Returns:
            Parser language name or None
        """
        mapping = {
            "Python": "python",
            "JavaScript": "javascript",
            "TypeScript": "typescript",
            "Java": "java",
            "Go": "go",
            "Rust": "rust",
            "C": "c",
            "C++": "cpp",
            "Ruby": "ruby",
            "PHP": "php",
        }
        return mapping.get(language)

    def resolve_import_path(
        self, source_path: str, import_name: str, language: str, all_files: Set[str]
    ) -> Optional[str]:
        """Resolve an import name to a file path.

        Args:
            source_path: Path of file containing the import
            import_name: The import/module name
            language: Programming language
            all_files: Set of all file paths in the codebase

        Returns:
            Resolved file path or None
        """
        source_dir = os.path.dirname(source_path)

        if language == "python":
            return self._resolve_python_import(source_dir, import_name, all_files)
        elif language in ["javascript", "typescript"]:
            return self._resolve_js_import(source_dir, import_name, all_files)
        elif language == "go":
            return self._resolve_go_import(source_dir, import_name, all_files)
        elif language == "java":
            return self._resolve_java_import(source_dir, import_name, all_files)
        elif language == "rust":
            return self._resolve_rust_import(source_dir, import_name, all_files)

        return None

    def _resolve_python_import(
        self, source_dir: str, import_name: str, all_files: Set[str]
    ) -> Optional[str]:
        """Resolve Python import to file path."""
        # Convert module path to file path
        parts = import_name.split(".")

        # Try relative to source directory
        candidates = []

        # Check if it's a relative import (starting with .)
        if import_name.startswith("."):
            # Handle relative imports
            dots = 0
            while dots < len(import_name) and import_name[dots] == ".":
                dots += 1

            # Go up directories
            base_dir = source_dir
            for _ in range(dots - 1):
                base_dir = os.path.dirname(base_dir)

            module_part = import_name[dots:]
            if module_part:
                parts = module_part.split(".")
            else:
                parts = []
        else:
            # For non-relative imports, start from source directory
            base_dir = source_dir

        if parts:
            # Try as module/file
            rel_path = os.path.join(base_dir, *parts)
            candidates.extend([rel_path + ".py", os.path.join(rel_path, "__init__.py")])

        # Check each candidate against all files
        for candidate in candidates:
            # Normalize path
            candidate = os.path.normpath(candidate)
            if candidate in all_files:
                return candidate
            # Also try without leading ./
            if candidate.startswith("./"):
                alt = candidate[2:]
                if alt in all_files:
                    return alt

        return None

    def _resolve_js_import(
        self, source_dir: str, import_name: str, all_files: Set[str]
    ) -> Optional[str]:
        """Resolve JavaScript/TypeScript import to file path."""
        # Handle relative imports
        if import_name.startswith("."):
            full_path = os.path.normpath(os.path.join(source_dir, import_name))
        else:
            # Skip node_modules imports (external packages)
            return None

        # Try different extensions
        extensions = ["", ".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs"]
        candidates = [full_path + ext for ext in extensions]
        # Also try index files
        candidates.extend(
            [
                os.path.join(full_path, "index.js"),
                os.path.join(full_path, "index.ts"),
                os.path.join(full_path, "index.jsx"),
                os.path.join(full_path, "index.tsx"),
            ]
        )

        for candidate in candidates:
            candidate = os.path.normpath(candidate)
            if candidate in all_files:
                return candidate

        return None

    def _resolve_go_import(
        self, source_dir: str, import_name: str, all_files: Set[str]
    ) -> Optional[str]:
        """Resolve Go import to file path."""
        # Go imports are usually full paths
        # For now, just check if the import path matches any file
        import_path = import_name.replace("/", os.sep)
        if import_path in all_files:
            return import_path
        return None

    def _resolve_java_import(
        self, source_dir: str, import_name: str, all_files: Set[str]
    ) -> Optional[str]:
        """Resolve Java import to file path."""
        # Convert package.Class to file path
        file_path = import_name.replace(".", os.sep) + ".java"

        # Look for matching file
        for f in all_files:
            if f.endswith(file_path) or f == file_path:
                return f

        return None

    def _resolve_rust_import(
        self, source_dir: str, import_name: str, all_files: Set[str]
    ) -> Optional[str]:
        """Resolve Rust use statement to file path."""
        # Rust modules are typically files with same name
        parts = import_name.split("::")
        if parts:
            # Try to find matching file
            file_path = parts[0] + ".rs"
            for f in all_files:
                if f.endswith(file_path) or f == file_path:
                    return f

        return None
