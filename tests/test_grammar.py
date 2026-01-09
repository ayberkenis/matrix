"""Tests for tokenization and grammar."""

import unittest
from living_matrix.grammar import tokenize, extract_phrases, generate_from_graph, remix_phrase


class TestTokenizer(unittest.TestCase):
    
    def test_tokenize_basic(self):
        text = "Hello world, this is a test!"
        tokens = tokenize(text)
        self.assertIn("hello", tokens)
        self.assertIn("world", tokens)
        self.assertIn("test", tokens)
        self.assertNotIn("this", tokens)  # stopword
        self.assertNotIn("is", tokens)    # stopword
    
    def test_tokenize_empty(self):
        tokens = tokenize("")
        self.assertEqual(tokens, [])
    
    def test_tokenize_punctuation(self):
        text = "test123, hello-world!"
        tokens = tokenize(text)
        self.assertIn("test123", tokens)
        self.assertIn("hello", tokens)
        self.assertIn("world", tokens)
    
    def test_tokenize_stability(self):
        # Same input should produce same output
        text = "The quick brown fox jumps over the lazy dog"
        tokens1 = tokenize(text)
        tokens2 = tokenize(text)
        self.assertEqual(tokens1, tokens2)
    
    def test_tokenize_now_not_stopword(self):
        # "now" should NOT be filtered as stopword
        text = "It rains now."
        tokens = tokenize(text)
        self.assertIn("rains", tokens)
        self.assertIn("now", tokens)
        self.assertNotIn("it", tokens)  # "it" is still a stopword
    
    def test_tokenize_help(self):
        # Short meaningful words should survive
        text = "help"
        tokens = tokenize(text)
        self.assertIn("help", tokens)
        self.assertEqual(len(tokens), 1)


class TestPhrases(unittest.TestCase):
    
    def test_extract_phrases(self):
        text = "hello world test"
        phrases = extract_phrases(text, min_length=2, max_length=3)
        self.assertGreater(len(phrases), 0)
        self.assertIn(("hello", "world"), phrases)


class TestGeneration(unittest.TestCase):
    
    def test_generate_from_graph(self):
        graph = {
            "a": {"b": 2.0, "c": 1.0},
            "b": {"c": 1.5},
            "c": {"a": 1.0}
        }
        sequence = generate_from_graph(graph, start_token="a", length=5)
        self.assertEqual(len(sequence), 5)
        self.assertEqual(sequence[0], "a")
    
    def test_generate_empty_graph(self):
        sequence = generate_from_graph({}, length=5)
        self.assertEqual(sequence, [])
    
    def test_remix_phrase(self):
        graph = {
            "hello": {"world": 1.0, "test": 0.5},
            "world": {"hello": 1.0}
        }
        phrase = "hello world test"
        remixed = remix_phrase(phrase, graph, mutation_rate=0.5)
        # Should still be a string
        self.assertIsInstance(remixed, str)
        self.assertGreater(len(remixed), 0)


if __name__ == "__main__":
    unittest.main()
