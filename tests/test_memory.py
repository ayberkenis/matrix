"""Tests for memory systems."""

import unittest
from living_matrix.memory import SemanticGraph, EpisodicMemory, Episode


class TestSemanticGraph(unittest.TestCase):
    
    def test_add_token(self):
        graph = SemanticGraph()
        graph.add_token("test", weight=1.0)
        self.assertEqual(graph.nodes["test"], 1.0)
        graph.add_token("test", weight=0.5)
        self.assertEqual(graph.nodes["test"], 1.5)
    
    def test_add_edge(self):
        graph = SemanticGraph()
        graph.add_edge("a", "b", weight=1.0)
        self.assertIn("a", graph.edges)
        self.assertEqual(graph.edges["a"]["b"], 1.0)
        graph.add_edge("a", "b", weight=0.5)
        self.assertEqual(graph.edges["a"]["b"], 1.5)
    
    def test_get_neighbors(self):
        graph = SemanticGraph()
        graph.add_edge("a", "b", weight=2.0)
        graph.add_edge("a", "c", weight=1.0)
        neighbors = graph.get_neighbors("a", top_k=10)
        self.assertEqual(len(neighbors), 2)
        self.assertEqual(neighbors[0][0], "b")  # Highest weight first
    
    def test_get_cluster(self):
        graph = SemanticGraph()
        graph.add_edge("a", "b", weight=1.0)
        graph.add_edge("b", "c", weight=1.0)
        cluster = graph.get_cluster("a", depth=2, top_k=10)
        self.assertIn("b", cluster)
        self.assertIn("c", cluster)
    
    def test_serialization(self):
        graph = SemanticGraph()
        graph.add_token("test", 1.0)
        graph.add_edge("a", "b", 1.0)
        data = graph.to_dict()
        graph2 = SemanticGraph.from_dict(data)
        self.assertEqual(graph2.nodes["test"], 1.0)
        self.assertEqual(graph2.edges["a"]["b"], 1.0)


class TestEpisodicMemory(unittest.TestCase):
    
    def test_add_episode(self):
        memory = EpisodicMemory(max_episodes=10)
        memory.add(1, "user input", "system output", notable=False)
        self.assertEqual(len(memory.episodes), 1)
        self.assertEqual(memory.episodes[0].turn, 1)
    
    def test_max_episodes(self):
        memory = EpisodicMemory(max_episodes=5)
        for i in range(10):
            memory.add(i, f"input{i}", f"output{i}")
        self.assertEqual(len(memory.episodes), 5)
        # Should have kept the last 5
        self.assertEqual(memory.episodes[0].turn, 5)
    
    def test_get_recent(self):
        memory = EpisodicMemory()
        for i in range(10):
            memory.add(i, f"input{i}", f"output{i}")
        recent = memory.get_recent(3)
        self.assertEqual(len(recent), 3)
        self.assertEqual(recent[-1].turn, 9)
    
    def test_search(self):
        memory = EpisodicMemory()
        memory.add(1, "hello world", "test output")
        memory.add(2, "foo bar", "hello again")
        results = memory.search("hello")
        self.assertEqual(len(results), 2)
    
    def test_serialization(self):
        memory = EpisodicMemory()
        memory.add(1, "input", "output", notable=True)
        data = memory.to_dict()
        memory2 = EpisodicMemory.from_dict(data)
        self.assertEqual(len(memory2.episodes), 1)
        self.assertTrue(memory2.episodes[0].notable)


if __name__ == "__main__":
    unittest.main()
