"""Code chunking module with AST-aware splitting."""

import re
from typing import Dict, List, Optional


class CodeChunk:
    """Represents a code chunk with metadata."""

    def __init__(self, content: str, metadata: Dict):
        self.content = content
        self.metadata = metadata

    def to_dict(self) -> Dict:
        """Convert chunk to dictionary."""
        return {"content": self.content, "metadata": self.metadata}


class CodeChunker:
    """Chunks code while respecting AST boundaries."""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """Initialize chunker.

        Args:
            chunk_size: Target size of each chunk in characters
            chunk_overlap: Number of characters to overlap between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_code(self, code: str, language: str, file_path: str) -> List[Dict]:
        """Chunk code while respecting structural boundaries.

        Args:
            code: Source code to chunk
            language: Programming language
            file_path: Path to the file

        Returns:
            List of chunk dictionaries with content and metadata
        """
        if not code.strip():
            return []

        # Split by structural boundaries first
        sections = self._split_by_structure(code, language)

        chunks = []
        for section in sections:
            if len(section["content"]) <= self.chunk_size:
                # Section fits in one chunk
                chunks.append(section)
            else:
                # Split large sections with overlap
                section_chunks = self._split_with_overlap(
                    section["content"], section["metadata"]
                )
                chunks.extend(section_chunks)

        return chunks

    def _split_by_structure(self, code: str, language: str) -> List[Dict]:
        """Split code by structural boundaries (functions, classes, etc).

        Args:
            code: Source code
            language: Programming language

        Returns:
            List of sections with metadata
        """
        lines = code.split("\n")
        sections = []
        current_section = {"content": [], "type": "header", "name": ""}

        # Pattern for function/class definitions
        patterns = {
            "python": r"^(def |class |async def )",
            "javascript": r"^(function |class |const .* = |async function )",
            "typescript": r"^(function |class |const .* = |async function |interface |type )",
            "java": r"^(public |private |protected |class |interface |enum )",
            "go": r"^(func |type )",
            "rust": r"^(fn |pub fn |struct |impl |trait |enum )",
            "ruby": r"^(def |class |module )",
            "php": r"^(function |class |namespace )",
        }

        pattern = patterns.get(language.lower(), r"^(def |function |class )")

        for i, line in enumerate(lines):
            if re.match(pattern, line.strip()):
                # Start of new section
                if current_section["content"]:
                    content_str = "\n".join(current_section["content"])
                    if content_str.strip():
                        sections.append(
                            {
                                "content": content_str,
                                "metadata": {
                                    "type": current_section["type"],
                                    "name": current_section["name"],
                                    "start_line": i
                                    - len(current_section["content"])
                                    + 1,
                                },
                            }
                        )

                # Extract name from definition line
                name = self._extract_name(line, language)
                current_section = {
                    "content": [line],
                    "type": "definition",
                    "name": name,
                }
            else:
                current_section["content"].append(line)

        # Don't forget the last section
        if current_section["content"]:
            content_str = "\n".join(current_section["content"])
            if content_str.strip():
                sections.append(
                    {
                        "content": content_str,
                        "metadata": {
                            "type": current_section["type"],
                            "name": current_section["name"],
                            "start_line": len(lines)
                            - len(current_section["content"])
                            + 1,
                        },
                    }
                )

        return sections

    def _extract_name(self, line: str, language: str) -> str:
        """Extract name from a definition line."""
        line = line.strip()

        if language == "python":
            if line.startswith("def "):
                return line.split("(")[0].replace("def ", "").strip()
            elif line.startswith("class "):
                return line.split("(")[0].split(":")[0].replace("class ", "").strip()

        elif language in ["javascript", "typescript"]:
            if line.startswith("function "):
                return line.split("(")[0].replace("function ", "").strip()
            elif line.startswith("class "):
                return line.split("{")[0].replace("class ", "").strip()

        elif language == "go":
            if line.startswith("func "):
                # Handle receiver methods: func (s *Server) Start() {
                parts = line.split()
                if len(parts) >= 2:
                    second_part = parts[1]
                    # Check if it's a receiver method (starts with "(")
                    if second_part.startswith("("):
                        # Return the receiver part like "(s"
                        return second_part
                    else:
                        # Regular function
                        return second_part.split("(")[0]

        # Default: return first word after keyword
        words = line.split()
        if len(words) >= 2:
            return words[1].split("(")[0].split(":")[0].split("{")[0].strip()

        return ""

    def _split_with_overlap(self, content: str, metadata: Dict) -> List[Dict]:
        """Split content into overlapping chunks.

        Args:
            content: Content to split
            metadata: Base metadata for chunks

        Returns:
            List of chunk dictionaries
        """
        chunks = []
        start = 0

        while start < len(content):
            end = start + self.chunk_size

            # Get chunk content
            chunk_content = content[start:end]

            # Create chunk with metadata
            chunk_metadata = metadata.copy()
            chunk_metadata["chunk_index"] = len(chunks)

            chunks.append({"content": chunk_content, "metadata": chunk_metadata})

            # Move start with overlap
            start = end - self.chunk_overlap

            # Safety check to prevent infinite loop
            if start >= end:
                break

        return chunks

    def chunk_file(self, file_path: str, language: str) -> List[Dict]:
        """Chunk a file by reading it.

        Args:
            file_path: Path to the file
            language: Programming language

        Returns:
            List of chunk dictionaries
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                code = f.read()
            return self.chunk_code(code, language, file_path)
        except Exception:
            return []
