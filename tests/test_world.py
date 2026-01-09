"""Tests for world state and persistence."""

import unittest
import tempfile
import shutil
from pathlib import Path
from living_matrix.world import World, WorldState, Drives
from living_matrix.grammar import tokenize


class TestDrives(unittest.TestCase):
    
    def test_normalize(self):
        drives = Drives(stability=1.5, novelty=-0.5, cohesion=0.7, expression=0.3)
        drives.normalize()
        self.assertLessEqual(drives.stability, 1.0)
        self.assertGreaterEqual(drives.stability, 0.0)
        self.assertLessEqual(drives.novelty, 1.0)
        self.assertGreaterEqual(drives.novelty, 0.0)
    
    def test_serialization(self):
        drives = Drives(stability=0.8, novelty=0.2, cohesion=0.6, expression=0.4)
        data = drives.to_dict()
        drives2 = Drives.from_dict(data)
        self.assertEqual(drives.stability, drives2.stability)
        self.assertEqual(drives.novelty, drives2.novelty)


class TestWorldState(unittest.TestCase):
    
    def test_serialization(self):
        state = WorldState(turn=42, seed=123)
        state.drives.stability = 0.8
        data = state.to_dict()
        state2 = WorldState.from_dict(data)
        self.assertEqual(state2.turn, 42)
        self.assertEqual(state2.seed, 123)
        self.assertEqual(state2.drives.stability, 0.8)


class TestWorld(unittest.TestCase):
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.world = World(data_dir=self.temp_dir)
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir)
    
    def test_load_new(self):
        state = self.world.load()
        self.assertIsNotNone(state)
        self.assertEqual(state.turn, 0)
    
    def test_save_load(self):
        state = self.world.load()
        state.turn = 10
        state.drives.stability = 0.9
        self.world.save()
        
        # Load again
        state2 = self.world.load()
        self.assertEqual(state2.turn, 10)
        self.assertEqual(state2.drives.stability, 0.9)
    
    def test_process_input(self):
        state = self.world.load()
        self.world.process_input("hello world test")
        self.assertIn("hello", state.semantic_graph.nodes)
        self.assertIn("world", state.semantic_graph.nodes)
        self.assertIn("test", state.semantic_graph.nodes)
        # Should have edges
        self.assertGreater(len(state.semantic_graph.edges), 0)
    
    def test_process_input_creates_edges(self):
        state = self.world.load()
        self.world.process_input("It rains now.")
        tokens = tokenize("It rains now.")
        # Should have at least "rains" and "now"
        self.assertIn("rains", state.semantic_graph.nodes)
        self.assertIn("now", state.semantic_graph.nodes)
        # Should have edges between tokens
        if "rains" in state.semantic_graph.edges:
            self.assertGreater(len(state.semantic_graph.edges["rains"]), 0)
    
    def test_process_artifact(self):
        state = self.world.load()
        # First add some input
        self.world.process_input("hello world")
        # Then process artifact with reduced weight
        artifact_tokens = ["hello", "world", "test"]
        self.world.process_artifact(artifact_tokens)
        # Should update graph
        self.assertIn("test", state.semantic_graph.nodes)
    
    def test_update_drives(self):
        state = self.world.load()
        initial_stability = state.drives.stability
        self.world.update_drives(diversity=0.5, coherence=0.7, novelty=0.3, interaction_intensity=0.6)
        # Drives should have changed
        state.drives.normalize()
        self.assertGreaterEqual(state.drives.stability, 0.0)
        self.assertLessEqual(state.drives.stability, 1.0)
    
    def test_reset(self):
        state = self.world.load()
        state.turn = 100
        self.world.reset()
        self.assertEqual(self.world.state.turn, 0)
        self.assertEqual(self.world.state.seed, state.seed)  # Seed preserved


if __name__ == "__main__":
    unittest.main()
