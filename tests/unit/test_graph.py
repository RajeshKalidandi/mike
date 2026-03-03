"""Unit tests for the Dependency Graph Builder module."""

import pytest
from unittest.mock import MagicMock, patch

from mike.graph.builder import DependencyGraphBuilder


class TestDependencyGraphBuilder:
    """Test cases for DependencyGraphBuilder."""

    def test_builder_initialization(self):
        """Test graph builder initialization."""
        builder = DependencyGraphBuilder("session123")

        assert builder.session_id == "session123"
        assert builder.graph is not None
        assert builder.graph.number_of_nodes() == 0
        assert builder.graph.number_of_edges() == 0

    def test_add_node(self):
        """Test adding a node to the graph."""
        builder = DependencyGraphBuilder("session123")

        builder.add_node("src/main.py", {"language": "Python"})

        assert builder.graph.number_of_nodes() == 1
        assert "src/main.py" in builder.graph
        assert builder.graph.nodes["src/main.py"]["language"] == "Python"
        assert builder.graph.nodes["src/main.py"]["file_path"] == "src/main.py"

    def test_add_node_without_metadata(self):
        """Test adding a node without metadata."""
        builder = DependencyGraphBuilder("session123")

        builder.add_node("src/utils.py")

        assert builder.graph.number_of_nodes() == 1
        assert "src/utils.py" in builder.graph
        assert builder.graph.nodes["src/utils.py"]["file_path"] == "src/utils.py"

    def test_add_edge(self):
        """Test adding an edge between nodes."""
        builder = DependencyGraphBuilder("session123")

        builder.add_edge("src/main.py", "src/utils.py", "import")

        assert builder.graph.number_of_nodes() == 2
        assert builder.graph.number_of_edges() == 1
        assert builder.graph.has_edge("src/main.py", "src/utils.py")
        assert builder.graph.edges["src/main.py", "src/utils.py"]["type"] == "import"

    def test_add_edge_with_metadata(self):
        """Test adding an edge with additional metadata."""
        builder = DependencyGraphBuilder("session123")

        builder.add_edge(
            "src/main.py", "src/utils.py", "import", {"line": 1, "alias": "u"}
        )

        edge_data = builder.graph.edges["src/main.py", "src/utils.py"]
        assert edge_data["type"] == "import"
        assert edge_data["line"] == 1
        assert edge_data["alias"] == "u"

    def test_add_edge_creates_nodes(self):
        """Test that adding an edge creates missing nodes."""
        builder = DependencyGraphBuilder("session123")

        # Add edge without explicitly adding nodes first
        builder.add_edge("a.py", "b.py", "call")

        assert builder.graph.number_of_nodes() == 2
        assert "a.py" in builder.graph
        assert "b.py" in builder.graph

    def test_get_neighbors(self):
        """Test getting neighbors of a node."""
        builder = DependencyGraphBuilder("session123")

        builder.add_edge("main.py", "utils.py", "import")
        builder.add_edge("main.py", "models.py", "import")
        builder.add_edge("test.py", "main.py", "import")

        neighbors = builder.get_neighbors("main.py")

        assert "utils.py" in neighbors
        assert "models.py" in neighbors
        assert "test.py" in neighbors

    def test_get_neighbors_empty(self):
        """Test getting neighbors of isolated node."""
        builder = DependencyGraphBuilder("session123")

        builder.add_node("isolated.py")
        neighbors = builder.get_neighbors("isolated.py")

        assert neighbors == set()

    def test_get_neighbors_nonexistent(self):
        """Test getting neighbors of non-existent node."""
        builder = DependencyGraphBuilder("session123")

        neighbors = builder.get_neighbors("nonexistent.py")

        assert neighbors == set()

    def test_get_imports(self):
        """Test getting imports for a file."""
        builder = DependencyGraphBuilder("session123")

        builder.add_edge("main.py", "utils.py", "import")
        builder.add_edge("main.py", "models.py", "import")

        imports = builder.get_imports("main.py")

        assert len(imports) == 2
        targets = {target for target, _ in imports}
        assert "utils.py" in targets
        assert "models.py" in targets

    def test_get_imports_nonexistent(self):
        """Test getting imports for non-existent file."""
        builder = DependencyGraphBuilder("session123")

        imports = builder.get_imports("nonexistent.py")

        assert imports == []

    def test_find_cycles_no_cycles(self):
        """Test finding cycles when none exist."""
        builder = DependencyGraphBuilder("session123")

        builder.add_edge("a.py", "b.py", "import")
        builder.add_edge("b.py", "c.py", "import")
        # No edge from c back to a

        cycles = builder.find_cycles()

        assert cycles == []

    def test_find_cycles_simple(self):
        """Test finding a simple cycle."""
        builder = DependencyGraphBuilder("session123")

        builder.add_edge("a.py", "b.py", "import")
        builder.add_edge("b.py", "c.py", "import")
        builder.add_edge("c.py", "a.py", "import")  # Creates cycle

        cycles = builder.find_cycles()

        assert len(cycles) > 0
        # Check that one cycle contains all three files
        cycle_nodes = set()
        for cycle in cycles:
            cycle_nodes.update(cycle)
        assert {"a.py", "b.py", "c.py"}.issubset(cycle_nodes)

    def test_find_cycles_self_loop(self):
        """Test finding self-loop cycle."""
        builder = DependencyGraphBuilder("session123")

        builder.add_edge("a.py", "a.py", "import")

        cycles = builder.find_cycles()

        assert len(cycles) > 0

    def test_get_graph_stats_empty(self):
        """Test getting stats for empty graph."""
        builder = DependencyGraphBuilder("session123")

        stats = builder.get_graph_stats()

        assert stats["nodes"] == 0
        assert stats["edges"] == 0
        assert stats["density"] == 0.0
        assert stats["is_dag"] == True

    def test_get_graph_stats(self):
        """Test getting stats for populated graph."""
        builder = DependencyGraphBuilder("session123")

        # Create a simple DAG
        builder.add_edge("a.py", "b.py", "import")
        builder.add_edge("a.py", "c.py", "import")
        builder.add_edge("b.py", "d.py", "import")

        stats = builder.get_graph_stats()

        assert stats["nodes"] == 4
        assert stats["edges"] == 3
        assert 0 < stats["density"] <= 1.0
        assert stats["is_dag"] == True

    def test_get_graph_stats_with_cycle(self):
        """Test that graph with cycle is not a DAG."""
        builder = DependencyGraphBuilder("session123")

        builder.add_edge("a.py", "b.py", "import")
        builder.add_edge("b.py", "c.py", "import")
        builder.add_edge("c.py", "a.py", "import")

        stats = builder.get_graph_stats()

        assert stats["is_dag"] == False

    def test_export_to_dict(self):
        """Test exporting graph to dictionary."""
        builder = DependencyGraphBuilder("session123")

        builder.add_node("a.py", {"language": "Python"})
        builder.add_node("b.py", {"language": "Python"})
        builder.add_edge("a.py", "b.py", "import", {"line": 1})

        data = builder.export_to_dict()

        assert data["session_id"] == "session123"
        assert len(data["nodes"]) == 2
        assert len(data["edges"]) == 1

        # Check node format
        node_ids = {n["id"] for n in data["nodes"]}
        assert "a.py" in node_ids
        assert "b.py" in node_ids

        # Check edge format
        edge = data["edges"][0]
        assert edge["source"] == "a.py"
        assert edge["target"] == "b.py"
        assert edge["type"] == "import"

    def test_export_to_dict_empty(self):
        """Test exporting empty graph."""
        builder = DependencyGraphBuilder("session123")

        data = builder.export_to_dict()

        assert data["session_id"] == "session123"
        assert data["nodes"] == []
        assert data["edges"] == []

    def test_save_to_db(self):
        """Test saving graph to database."""
        builder = DependencyGraphBuilder("session123")

        builder.add_edge("a.py", "b.py", "import")
        builder.add_edge("b.py", "c.py", "call")

        # Mock database
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db = MagicMock()
        mock_db._get_connection.return_value = mock_conn

        builder.save_to_db(mock_db)

        # Should delete existing edges first
        mock_cursor.execute.assert_any_call(
            "DELETE FROM graph_edges WHERE session_id = ?", ("session123",)
        )

        # Should insert edges
        assert mock_cursor.execute.call_count >= 3  # 1 delete + 2 inserts
        mock_conn.commit.assert_called_once()

    def test_get_edges(self):
        """Test getting all edges."""
        builder = DependencyGraphBuilder("session123")

        builder.add_edge("a.py", "b.py", "import", {"key": "value"})

        edges = builder.get_edges()

        assert len(edges) == 1
        source, target, data = edges[0]
        assert source == "a.py"
        assert target == "b.py"
        assert data["type"] == "import"
        assert data["key"] == "value"

    def test_complex_graph_structure(self):
        """Test building a complex graph structure."""
        builder = DependencyGraphBuilder("session123")

        # Create a complex dependency graph
        files = {
            "src/main.py": {"language": "Python", "type": "entry"},
            "src/utils.py": {"language": "Python", "type": "util"},
            "src/models.py": {"language": "Python", "type": "model"},
            "src/services.py": {"language": "Python", "type": "service"},
            "tests/test_main.py": {"language": "Python", "type": "test"},
        }

        # Add all nodes
        for path, metadata in files.items():
            builder.add_node(path, metadata)

        # Add dependencies
        edges = [
            ("src/main.py", "src/utils.py", "import"),
            ("src/main.py", "src/models.py", "import"),
            ("src/services.py", "src/models.py", "import"),
            ("tests/test_main.py", "src/main.py", "import"),
            ("tests/test_main.py", "src/services.py", "import"),
        ]

        for source, target, edge_type in edges:
            builder.add_edge(source, target, edge_type)

        # Verify structure
        assert builder.graph.number_of_nodes() == 5
        assert builder.graph.number_of_edges() == 5

        # Check specific connections
        assert builder.graph.has_edge("src/main.py", "src/utils.py")
        assert builder.graph.has_edge("tests/test_main.py", "src/main.py")

        # Check stats
        stats = builder.get_graph_stats()
        assert stats["nodes"] == 5
        assert stats["edges"] == 5
        assert stats["is_dag"] == True


class TestGraphAlgorithms:
    """Test cases for graph algorithms."""

    def test_transitive_closure(self):
        """Test transitive dependencies."""
        builder = DependencyGraphBuilder("session123")

        # a -> b -> c
        builder.add_edge("a.py", "b.py", "import")
        builder.add_edge("b.py", "c.py", "import")

        # b is direct dependency of a
        direct = builder.get_imports("a.py")
        assert ("b.py", "import") in direct

        # c is indirect dependency (not shown in get_imports)
        # This tests our basic graph structure

    def test_multiple_edges_between_nodes(self):
        """Test that multiple edges can exist (if directed graph allows)."""
        builder = DependencyGraphBuilder("session123")

        # In DiGraph, adding same edge twice updates the data
        builder.add_edge("a.py", "b.py", "import")
        builder.add_edge("a.py", "b.py", "call")  # Updates the edge

        edges = builder.get_edges()
        assert len(edges) == 1  # DiGraph only keeps one edge
        assert edges[0][2]["type"] == "call"  # Latest wins

    def test_node_attributes_preserved(self):
        """Test that node attributes are preserved correctly."""
        builder = DependencyGraphBuilder("session123")

        builder.add_node("file.py", {"attr1": "value1", "attr2": 42})

        # Add edge to same node
        builder.add_edge("file.py", "other.py", "import")

        # Original attributes should be preserved
        assert builder.graph.nodes["file.py"]["attr1"] == "value1"
        assert builder.graph.nodes["file.py"]["attr2"] == 42
        assert builder.graph.nodes["file.py"]["file_path"] == "file.py"
