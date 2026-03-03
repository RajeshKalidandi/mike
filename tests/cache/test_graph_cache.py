import pytest
import tempfile
import networkx as nx
from mike.cache.graph_cache import GraphCache


class TestGraphCache:
    def test_graph_cache_creation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = GraphCache(base_path=tmpdir)
            assert cache is not None

    def test_generate_graph_key(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = GraphCache(base_path=tmpdir)
            key = cache.generate_graph_key("repo123", "deps")
            assert isinstance(key, str)
            assert len(key) == 64

    def test_cache_graph_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = GraphCache(base_path=tmpdir)

            graph = nx.DiGraph()
            graph.add_node("A", type="function")
            graph.add_node("B", type="class")
            graph.add_edge("A", "B", relation="calls")

            cache.set_graph("repo123", "deps", graph)
            retrieved = cache.get_graph("repo123", "deps")

            assert retrieved is not None
            assert list(retrieved.nodes()) == ["A", "B"]
            assert list(retrieved.edges()) == [("A", "B")]
            assert retrieved.nodes["A"]["type"] == "function"
            assert retrieved.edges["A", "B"]["relation"] == "calls"

    def test_serialize_undirected_graph(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = GraphCache(base_path=tmpdir)

            graph = nx.Graph()
            graph.add_edge("A", "B", weight=5)

            cache.set_graph("repo", "undirected", graph)
            retrieved = cache.get_graph("repo", "undirected")

            assert not retrieved.is_directed()
            assert list(retrieved.edges()) == [("A", "B")]

    def test_graph_diff(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = GraphCache(base_path=tmpdir)

            old_graph = nx.DiGraph()
            old_graph.add_edges_from([("A", "B"), ("B", "C")])
            old_graph.nodes["A"]["attr"] = "old"

            new_graph = nx.DiGraph()
            new_graph.add_edges_from([("A", "B"), ("B", "D")])
            new_graph.nodes["A"]["attr"] = "new"

            diff = cache.compute_diff(old_graph, new_graph)

            assert "removed_nodes" in diff
            assert "added_nodes" in diff
            assert "removed_edges" in diff
            assert "added_edges" in diff
            assert "modified_nodes" in diff

            assert "C" in diff["removed_nodes"]
            assert "D" in diff["added_nodes"]
            assert ("B", "C") in diff["removed_edges"]
            assert ("B", "D") in diff["added_edges"]

            summary = diff["summary"]
            assert summary["nodes_removed"] == 1
            assert summary["nodes_added"] == 1
            assert summary["nodes_modified"] == 1
            assert summary["edges_removed"] == 1
            assert summary["edges_added"] == 1

    def test_has_graph(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = GraphCache(base_path=tmpdir)

            assert not cache.has_graph("missing", "deps")

            graph = nx.DiGraph()
            graph.add_node("A")
            cache.set_graph("exists", "deps", graph)

            assert cache.has_graph("exists", "deps")

    def test_get_graph_info(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = GraphCache(base_path=tmpdir)

            graph = nx.DiGraph()
            graph.add_nodes_from(["A", "B", "C"])
            graph.add_edges_from([("A", "B"), ("B", "C")])

            cache.set_graph("repo", "deps", graph)
            info = cache.get_graph_info("repo", "deps")

            assert info is not None
            assert info["repo_hash"] == "repo"
            assert info["graph_type"] == "deps"
            assert info["node_count"] == 3
            assert info["edge_count"] == 2

    def test_config_in_key(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = GraphCache(base_path=tmpdir)

            graph = nx.DiGraph()
            graph.add_node("A")

            config1 = {"depth": 2}
            config2 = {"depth": 3}

            cache.set_graph("repo", "deps", graph, config=config1)

            # Different config should be a miss
            assert cache.get_graph("repo", "deps", config=config2) is None

            # Same config should be a hit
            assert cache.get_graph("repo", "deps", config=config1) is not None
