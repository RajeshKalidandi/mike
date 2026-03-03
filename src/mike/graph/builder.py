"""Dependency graph builder using NetworkX."""

from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx


class DependencyGraphBuilder:
    """Builds and manages dependency graphs for codebases."""

    def __init__(self, session_id: str):
        """Initialize graph builder.

        Args:
            session_id: Unique session identifier
        """
        self.session_id = session_id
        self.graph = nx.DiGraph()

    def add_node(self, file_path: str, metadata: Optional[Dict] = None) -> None:
        """Add a file node to the graph.

        Args:
            file_path: Relative path to the file
            metadata: Optional node metadata (language, size, etc.)
        """
        if metadata is None:
            metadata = {}
        metadata["file_path"] = file_path
        self.graph.add_node(file_path, **metadata)

    def add_edge(
        self, source: str, target: str, edge_type: str, metadata: Optional[Dict] = None
    ) -> None:
        """Add a dependency edge between two files.

        Args:
            source: Source file path
            target: Target file path
            edge_type: Type of dependency (import, call, inheritance, etc.)
            metadata: Optional edge metadata
        """
        if metadata is None:
            metadata = {}
        metadata["type"] = edge_type

        # Ensure nodes exist
        if source not in self.graph:
            self.add_node(source)
        if target not in self.graph:
            self.add_node(target)

        self.graph.add_edge(source, target, **metadata)

    def get_edges(self) -> List[Tuple[str, str, Dict]]:
        """Get all edges in the graph.

        Returns:
            List of (source, target, metadata) tuples
        """
        return [(u, v, d) for u, v, d in self.graph.edges(data=True)]

    def get_neighbors(self, file_path: str) -> Set[str]:
        """Get all files that depend on or are depended upon by file_path.

        Args:
            file_path: File to get neighbors for

        Returns:
            Set of neighboring file paths
        """
        if file_path not in self.graph:
            return set()

        # Get both successors and predecessors
        successors = set(self.graph.successors(file_path))
        predecessors = set(self.graph.predecessors(file_path))
        return successors | predecessors

    def get_imports(self, file_path: str) -> List[Tuple[str, str]]:
        """Get all files imported by file_path.

        Args:
            file_path: File to get imports for

        Returns:
            List of (target_file, edge_type) tuples
        """
        if file_path not in self.graph:
            return []
        return [(v, d.get("type", "unknown")) for v, d in self.graph[file_path].items()]

    def find_cycles(self) -> List[List[str]]:
        """Find all circular dependencies in the graph.

        Returns:
            List of cycles, where each cycle is a list of file paths
        """
        try:
            cycles = list(nx.simple_cycles(self.graph))
            return cycles
        except nx.NetworkXNoCycle:
            return []

    def get_graph_stats(self) -> Dict[str, Any]:
        """Get statistics about the graph.

        Returns:
            Dictionary with node count, edge count, etc.
        """
        return {
            "nodes": self.graph.number_of_nodes(),
            "edges": self.graph.number_of_edges(),
            "density": nx.density(self.graph),
            "is_dag": (
                nx.is_directed_acyclic_graph(self.graph)
                if self.graph.number_of_nodes() > 0
                else True
            ),
        }

    def export_to_dict(self) -> Dict:
        """Export graph as dictionary for serialization.

        Returns:
            Dictionary with nodes and edges
        """
        return {
            "session_id": self.session_id,
            "nodes": [{"id": n, **self.graph.nodes[n]} for n in self.graph.nodes()],
            "edges": [
                {"source": u, "target": v, **d}
                for u, v, d in self.graph.edges(data=True)
            ],
        }

    def save_to_db(self, db) -> None:
        """Save graph edges to database.

        Args:
            db: Database instance
        """
        conn = db._get_connection()
        cursor = conn.cursor()

        # Clear existing edges for this session
        cursor.execute(
            "DELETE FROM graph_edges WHERE session_id = ?", (self.session_id,)
        )

        # Insert all edges
        for source, target, data in self.graph.edges(data=True):
            edge_type = data.get("type", "unknown")
            cursor.execute(
                """INSERT INTO graph_edges (session_id, source_file, target_file, edge_type)
                   VALUES (?, ?, ?, ?)""",
                (self.session_id, source, target, edge_type),
            )

        conn.commit()
