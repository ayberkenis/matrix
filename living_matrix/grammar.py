"""Tokenization and phrase generation utilities."""

import re
import random
from typing import List, Dict, Set, Tuple


# Minimal stopword list - only articles, pronouns, very common glue words
# Removed "now" as it's meaningful in context
STOPWORDS: Set[str] = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "are", "were", "been",
    "be", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "must", "can", "this", "that",
    "these", "those", "i", "you", "he", "she", "it", "we", "they", "me",
    "him", "her", "us", "them", "my", "your", "his", "her", "its", "our",
    "their", "what", "which", "who", "whom", "whose", "where", "when",
    "why", "how", "all", "each", "every", "both", "few", "more", "most",
    "other", "some", "such", "no", "nor", "not", "only", "own", "same",
    "so", "than", "too", "very", "just"
}


def tokenize(text: str) -> List[str]:
    """
    Tokenize text into lowercase word tokens, filtering stopwords.
    Keeps tokens of length >= 2 (not >= 4) to preserve meaningful short words.
    
    Args:
        text: Input text string
        
    Returns:
        List of token strings
    """
    # Extract alphanumeric sequences
    tokens = re.findall(r'\b[a-z0-9]+\b', text.lower())
    # Filter stopwords and keep tokens of length >= 2
    return [t for t in tokens if t not in STOPWORDS and len(t) >= 2]


def extract_phrases(text: str, min_length: int = 2, max_length: int = 5) -> List[Tuple[str, ...]]:
    """
    Extract n-gram phrases from text.
    
    Args:
        text: Input text
        min_length: Minimum phrase length
        max_length: Maximum phrase length
        
    Returns:
        List of phrase tuples
    """
    tokens = tokenize(text)
    phrases = []
    for n in range(min_length, min(max_length + 1, len(tokens) + 1)):
        for i in range(len(tokens) - n + 1):
            phrases.append(tuple(tokens[i:i+n]))
    return phrases


def generate_from_graph(
    graph: Dict[str, Dict[str, float]],
    start_token: str = None,
    length: int = 10,
    temperature: float = 1.0
) -> List[str]:
    """
    Generate a sequence of tokens via weighted random walk on semantic graph.
    
    Args:
        graph: Semantic graph {token: {neighbor: weight}}
        start_token: Starting token (random if None)
        length: Desired sequence length
        temperature: Sampling temperature (higher = more random)
        
    Returns:
        List of generated tokens
    """
    if not graph:
        return []
    
    tokens = []
    current = start_token
    
    if current is None or current not in graph:
        # Pick random starting token weighted by node weight
        candidates = list(graph.keys())
        if not candidates:
            return []
        current = random.choice(candidates)
    
    tokens.append(current)
    
    for _ in range(length - 1):
        if current not in graph or not graph[current]:
            # Dead end, pick random
            candidates = list(graph.keys())
            if not candidates:
                break
            current = random.choice(candidates)
            tokens.append(current)
            continue
        
        # Get neighbors with weights
        neighbors = graph[current]
        if not neighbors:
            break
        
        # Apply temperature
        weights = {k: v ** (1.0 / temperature) for k, v in neighbors.items()}
        total = sum(weights.values())
        if total == 0:
            break
        
        # Weighted random choice
        r = random.random() * total
        cumulative = 0.0
        for neighbor, weight in weights.items():
            cumulative += weight
            if r <= cumulative:
                current = neighbor
                tokens.append(current)
                break
    
    return tokens


def remix_phrase(phrase: str, graph: Dict[str, Dict[str, float]], mutation_rate: float = 0.2) -> str:
    """
    Mutate a phrase by replacing some tokens with graph neighbors.
    
    Args:
        phrase: Original phrase
        graph: Semantic graph
        mutation_rate: Fraction of tokens to mutate (0.0-1.0)
        
    Returns:
        Mutated phrase string
    """
    tokens = tokenize(phrase)
    if not tokens:
        return phrase
    
    num_mutations = max(1, int(len(tokens) * mutation_rate))
    indices_to_mutate = random.sample(range(len(tokens)), min(num_mutations, len(tokens)))
    
    result = tokens.copy()
    for idx in indices_to_mutate:
        token = result[idx]
        if token in graph and graph[token]:
            # Replace with a neighbor
            neighbors = list(graph[token].keys())
            if neighbors:
                result[idx] = random.choice(neighbors)
    
    return " ".join(result)


def apply_grammar_template(tokens: List[str], template: str = None) -> str:
    """
    Apply a simple grammar template to tokens.
    
    Args:
        tokens: List of tokens
        template: Template string with {0}, {1}, etc. placeholders
        
    Returns:
        Formatted string
    """
    if not tokens:
        return ""
    
    if template is None:
        # Default: just join with spaces
        return " ".join(tokens)
    
    # Fill template with tokens (cycling if needed)
    result = template
    for i in range(len(tokens)):
        result = result.replace(f"{{{i}}}", tokens[i], 1)
    
    # Fill remaining placeholders with random tokens
    remaining = re.findall(r'\{(\d+)\}', result)
    for placeholder in remaining:
        idx = int(placeholder)
        if idx < len(tokens):
            result = result.replace(f"{{{idx}}}", tokens[idx % len(tokens)])
        else:
            result = result.replace(f"{{{idx}}}", random.choice(tokens) if tokens else "")
    
    return result


# Grammar templates for generation
GRAMMAR_TEMPLATES = [
    "{0} becomes {1} when {2}",
    "{0} and {1} converge",
    "where {0} meets {1}, {2} emerges",
    "{0} shifts toward {1}",
    "{1} reflects {0}",
    "{0} transforms into {1}",
    "the pattern of {0} and {1}",
    "{0} resonates with {1}",
    "{0} flows into {1}",
    "{1} echoes {0}",
]
