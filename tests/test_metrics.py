"""Tests for metrics calculation."""

import unittest
from living_matrix.metrics import calculate_diversity, calculate_coherence, calculate_novelty, MetricsTracker


class TestMetrics(unittest.TestCase):
    
    def test_diversity_all_unique(self):
        tokens = ["a", "b", "c", "d", "e"]
        diversity = calculate_diversity(tokens)
        self.assertEqual(diversity, 1.0)
    
    def test_diversity_all_same(self):
        tokens = ["a", "a", "a", "a", "a"]
        diversity = calculate_diversity(tokens)
        self.assertEqual(diversity, 0.2)  # 1 unique / 5 total
    
    def test_diversity_empty(self):
        diversity = calculate_diversity([])
        self.assertEqual(diversity, 0.0)
    
    def test_coherence(self):
        graph = {
            "a": {"b": 2.0, "c": 1.0},
            "b": {"c": 1.5}
        }
        tokens = ["a", "b", "c"]
        coherence = calculate_coherence(tokens, graph)
        self.assertGreater(coherence, 0.0)
        self.assertLessEqual(coherence, 1.0)
    
    def test_coherence_no_edges(self):
        graph = {}
        tokens = ["a", "b"]
        coherence = calculate_coherence(tokens, graph)
        self.assertEqual(coherence, 0.0)
    
    def test_novelty(self):
        tokens = ["new", "word", "here"]
        recent_history = {"old", "word", "there"}
        novelty = calculate_novelty(tokens, recent_history)
        self.assertGreater(novelty, 0.0)  # "new" and "here" are novel
        self.assertLessEqual(novelty, 1.0)


class TestMetricsTracker(unittest.TestCase):
    
    def test_add_tokens(self):
        tracker = MetricsTracker()
        tracker.add_tokens(["a", "b", "c"])
        self.assertEqual(len(tracker.recent_tokens), 3)
    
    def test_get_diversity(self):
        tracker = MetricsTracker()
        tracker.add_tokens(["a", "b", "c", "d", "e"])
        diversity = tracker.get_diversity()
        self.assertGreater(diversity, 0.0)
        self.assertLessEqual(diversity, 1.0)
    
    def test_get_coherence(self):
        tracker = MetricsTracker()
        tracker.add_tokens(["a", "b", "c"])
        graph = {
            "a": {"b": 1.0},
            "b": {"c": 1.0}
        }
        coherence = tracker.get_coherence(graph)
        self.assertGreaterEqual(coherence, 0.0)
        self.assertLessEqual(coherence, 1.0)
    
    def test_reset(self):
        tracker = MetricsTracker()
        tracker.add_tokens(["a", "b", "c"])
        tracker.reset()
        self.assertEqual(len(tracker.recent_tokens), 0)
        self.assertEqual(len(tracker.recent_history), 0)


if __name__ == "__main__":
    unittest.main()
