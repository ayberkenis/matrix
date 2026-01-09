"""Metrics for measuring system state: diversity, coherence, novelty."""

from typing import List, Dict, Set
from collections import deque


def calculate_diversity(tokens: List[str], window_size: int = 100) -> float:
    """
    Calculate diversity: unique tokens / total tokens in recent window.
    
    Args:
        tokens: List of recent tokens
        window_size: Size of window to consider
        
    Returns:
        Diversity score (0.0-1.0)
    """
    if not tokens:
        return 0.0
    
    window = tokens[-window_size:] if len(tokens) > window_size else tokens
    unique = len(set(window))
    total = len(window)
    
    return unique / total if total > 0 else 0.0


def calculate_coherence(
    tokens: List[str],
    graph: Dict[str, Dict[str, float]],
    window_size: int = 20
) -> float:
    """
    Calculate coherence: average edge weight among tokens in recent window.
    
    Args:
        tokens: List of recent tokens
        graph: Semantic graph
        window_size: Size of window to consider
        
    Returns:
        Coherence score (0.0-1.0, normalized)
    """
    if not tokens or not graph:
        return 0.0
    
    window = tokens[-window_size:] if len(tokens) > window_size else tokens
    if len(window) < 2:
        return 0.0
    
    total_weight = 0.0
    count = 0
    
    for i in range(len(window) - 1):
        token1 = window[i]
        token2 = window[i + 1]
        
        if token1 in graph and token2 in graph[token1]:
            weight = graph[token1][token2]
            total_weight += weight
            count += 1
    
    if count == 0:
        return 0.0
    
    avg_weight = total_weight / count
    
    # Normalize to 0-1 range (assuming max weight is around 10-20)
    # Use a sigmoid-like normalization
    normalized = min(1.0, avg_weight / 10.0)
    return normalized


def calculate_novelty(
    tokens: List[str],
    recent_history: Set[str],
    window_size: int = 50
) -> float:
    """
    Calculate novelty: fraction of tokens not seen in recent history.
    
    Args:
        tokens: Current tokens to evaluate
        recent_history: Set of tokens seen recently
        window_size: Size of history window (for context)
        
    Returns:
        Novelty score (0.0-1.0)
    """
    if not tokens:
        return 0.0
    
    window = tokens[-window_size:] if len(tokens) > window_size else tokens
    if not window:
        return 0.0
    
    novel_count = sum(1 for t in window if t not in recent_history)
    return novel_count / len(window) if window else 0.0


class MetricsTracker:
    """Tracks metrics over time with rolling windows."""
    
    def __init__(self, token_window: int = 200, history_window: int = 100, artifact_window: int = 25):
        self.token_window = token_window
        self.history_window = history_window
        self.artifact_window = artifact_window  # K=25 turns for novelty
        self.recent_tokens: deque = deque(maxlen=token_window)
        self.recent_history: Set[str] = set()
        self.history_queue: deque = deque(maxlen=history_window)
        # Artifact-based window for novelty (last K turns' artifacts)
        # Each entry is a list of tokens from one artifact
        self.recent_artifact_tokens: deque = deque(maxlen=artifact_window)  # Last K turns
    
    def add_tokens(self, tokens: List[str]):
        """Add new tokens to tracking."""
        for token in tokens:
            self.recent_tokens.append(token)
            self.history_queue.append(token)
            self.recent_history.add(token)
        
        # Trim history set if queue is full
        if len(self.history_queue) >= self.history_window:
            # Remove oldest tokens from set
            while len(self.history_queue) > self.history_window:
                old_token = self.history_queue.popleft()
                # Only remove if it's not in recent tokens
                if old_token not in self.recent_tokens:
                    self.recent_history.discard(old_token)
    
    def add_artifact_tokens(self, tokens: List[str]):
        """
        Add artifact tokens to novelty tracking window.
        Stores the entire artifact as one entry (last K turns).
        """
        if tokens:
            self.recent_artifact_tokens.append(tokens.copy())
    
    def get_diversity(self) -> float:
        """Get current diversity score."""
        return calculate_diversity(list(self.recent_tokens), self.token_window)
    
    def get_coherence(self, graph: Dict[str, Dict[str, float]]) -> float:
        """Get current coherence score."""
        return calculate_coherence(list(self.recent_tokens), graph, self.token_window)
    
    def get_novelty(self, current_artifact_tokens: List[str]) -> float:
        """
        Get novelty score based on artifact tokens not in recent artifact window.
        
        Args:
            current_artifact_tokens: Tokens from current artifact
            
        Returns:
            Novelty score (0.0-1.0)
        """
        if not current_artifact_tokens:
            return 0.0
        
        # Create set of tokens from last K turns' artifacts
        recent_artifact_set = set()
        for artifact_tokens in self.recent_artifact_tokens:
            recent_artifact_set.update(artifact_tokens)
        
        # Count novel tokens (tokens not seen in recent artifacts)
        novel_tokens = [t for t in current_artifact_tokens if t not in recent_artifact_set]
        novel_count = len(novel_tokens)
        
        return novel_count / len(current_artifact_tokens) if current_artifact_tokens else 0.0
    
    def get_novel_tokens(self, current_artifact_tokens: List[str]) -> List[str]:
        """
        Get list of novel tokens in current artifact (for debug output).
        
        Args:
            current_artifact_tokens: Tokens from current artifact
            
        Returns:
            List of novel tokens
        """
        if not current_artifact_tokens:
            return []
        
        # Create set of tokens from last K turns' artifacts
        recent_artifact_set = set()
        for artifact_tokens in self.recent_artifact_tokens:
            recent_artifact_set.update(artifact_tokens)
        
        # Return novel tokens
        return [t for t in current_artifact_tokens if t not in recent_artifact_set]
    
    def reset(self):
        """Reset all tracking."""
        self.recent_tokens.clear()
        self.recent_history.clear()
        self.history_queue.clear()
        self.recent_artifact_tokens.clear()