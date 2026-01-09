"""Episodic and semantic memory management."""

from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json


@dataclass
class Episode:
    """A single episodic memory entry."""
    turn: int
    timestamp: str
    user_input: str
    system_output: str
    notable: bool = False  # Marked as notable event


@dataclass
class SemanticGraph:
    """Semantic memory: weighted graph of tokens and relationships."""
    nodes: Dict[str, float] = field(default_factory=dict)  # token -> weight
    edges: Dict[str, Dict[str, float]] = field(default_factory=dict)  # token -> {neighbor -> weight}
    
    def add_token(self, token: str, weight: float = 1.0):
        """Add or update a token node."""
        self.nodes[token] = self.nodes.get(token, 0.0) + weight
    
    def add_edge(self, token1: str, token2: str, weight: float = 1.0):
        """Add or update an edge between two tokens."""
        if token1 not in self.edges:
            self.edges[token1] = {}
        self.edges[token1][token2] = self.edges[token1].get(token2, 0.0) + weight
    
    def get_neighbors(self, token: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """Get top neighbors of a token by edge weight."""
        if token not in self.edges:
            return []
        neighbors = list(self.edges[token].items())
        neighbors.sort(key=lambda x: x[1], reverse=True)
        return neighbors[:top_k]
    
    def get_cluster(self, token: str, depth: int = 2, top_k: int = 20) -> List[str]:
        """Get a cluster of related tokens via breadth-first traversal."""
        visited = set()
        cluster = []
        queue = [(token, 0)]
        visited.add(token)
        
        while queue and len(cluster) < top_k:
            current, current_depth = queue.pop(0)
            if current_depth < depth:
                if current in self.edges:
                    neighbors = self.get_neighbors(current, top_k=top_k)
                    for neighbor, weight in neighbors:
                        if neighbor not in visited:
                            visited.add(neighbor)
                            cluster.append(neighbor)
                            queue.append((neighbor, current_depth + 1))
        
        return cluster
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "nodes": self.nodes,
            "edges": self.edges
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "SemanticGraph":
        """Deserialize from dictionary."""
        graph = cls()
        graph.nodes = data.get("nodes", {})
        graph.edges = data.get("edges", {})
        return graph


class EpisodicMemory:
    """Rolling log of episodic memories."""
    
    def __init__(self, max_episodes: int = 1000):
        self.episodes: List[Episode] = []
        self.max_episodes = max_episodes
    
    def add(self, turn: int, user_input: str, system_output: str, notable: bool = False):
        """Add a new episode."""
        episode = Episode(
            turn=turn,
            timestamp=datetime.now().isoformat(),
            user_input=user_input,
            system_output=system_output,
            notable=notable
        )
        self.episodes.append(episode)
        
        # Trim if over limit
        if len(self.episodes) > self.max_episodes:
            self.episodes = self.episodes[-self.max_episodes:]
    
    def get_recent(self, n: int = 10) -> List[Episode]:
        """Get the most recent N episodes."""
        return self.episodes[-n:] if len(self.episodes) > n else self.episodes
    
    def get_notable(self) -> List[Episode]:
        """Get all notable episodes."""
        return [e for e in self.episodes if e.notable]
    
    def search(self, query: str) -> List[Episode]:
        """Search episodes by text content (simple substring match)."""
        query_lower = query.lower()
        return [
            e for e in self.episodes
            if query_lower in e.user_input.lower() or query_lower in e.system_output.lower()
        ]
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "episodes": [
                {
                    "turn": e.turn,
                    "timestamp": e.timestamp,
                    "user_input": e.user_input,
                    "system_output": e.system_output,
                    "notable": e.notable
                }
                for e in self.episodes
            ]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "EpisodicMemory":
        """Deserialize from dictionary."""
        memory = cls()
        for ep_data in data.get("episodes", []):
            episode = Episode(
                turn=ep_data["turn"],
                timestamp=ep_data["timestamp"],
                user_input=ep_data["user_input"],
                system_output=ep_data["system_output"],
                notable=ep_data.get("notable", False)
            )
            memory.episodes.append(episode)
        return memory
