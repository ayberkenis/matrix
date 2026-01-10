"""World state and persistence management."""

import json
import os
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass, field, asdict
import random

from .memory import SemanticGraph, EpisodicMemory
from .grammar import tokenize
from .tensor_core import TensorCognition


@dataclass
class Drives:
    """Internal drives that influence behavior."""
    stability: float = 0.5  # Prefers repeating coherent motifs
    novelty: float = 0.5    # Prefers introducing new symbols
    cohesion: float = 0.5   # Prefers tightening clusters/relationships
    expression: float = 0.5 # Prefers producing longer/structured output
    
    def normalize(self):
        """Ensure all drives are in [0, 1] range."""
        self.stability = max(0.0, min(1.0, self.stability))
        self.novelty = max(0.0, min(1.0, self.novelty))
        self.cohesion = max(0.0, min(1.0, self.cohesion))
        self.expression = max(0.0, min(1.0, self.expression))
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "stability": self.stability,
            "novelty": self.novelty,
            "cohesion": self.cohesion,
            "expression": self.expression
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Drives":
        """Deserialize from dictionary."""
        return cls(
            stability=data.get("stability", 0.5),
            novelty=data.get("novelty", 0.5),
            cohesion=data.get("cohesion", 0.5),
            expression=data.get("expression", 0.5)
        )


@dataclass
class WorldState:
    """Complete world state."""
    turn: int = 0
    seed: int = 42
    drives: Drives = field(default_factory=Drives)
    semantic_graph: SemanticGraph = field(default_factory=SemanticGraph)
    episodic_memory: EpisodicMemory = field(default_factory=EpisodicMemory)
    last_stimulus_turn: int = 0
    last_stimulus_length: int = 0
    last_stimulus_tensor: Optional[List[float]] = None  # Persisted stimulus motif tensor
    stimulus_decay_factor: float = 0.85  # Decay per turn
    silence_mode: bool = False  # Suppress visible output
    primordial_lexicon_initialized: bool = False  # Flag to ensure lexicon seeded only once
    
    # Species continuity pressure (SYSTEM 11)
    population_pressure: float = 0.0  # 0..1 (pressure to reproduce)
    extinction_risk: float = 0.0  # 0..1 (risk of species extinction)
    turns_since_last_birth: int = 0  # Track turns without births
    world_state: str = "alive"  # "alive" or "dead_world" (SYSTEM 15)
    
    # SYSTEM D: Generational trauma/memory
    generational_trauma: float = 0.0  # Accumulates from deaths, reduces conflict, increases cooperation
    deaths_last_50_turns: int = 0  # Track recent deaths for trauma calculation
    
    # POPULATION COMPRESSION: Global population metrics
    total_population: int = 0  # active_agents + child_pools across all districts
    active_agents: int = 0  # Total active agents (adults)
    total_child_pool: int = 0  # Total children in compressed pools
    civilization_phase: str = "survival"  # survival, growth, stable, strain, decline
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        result = {
            "turn": self.turn,
            "seed": self.seed,
            "drives": self.drives.to_dict(),
            "semantic_graph": self.semantic_graph.to_dict(),
            "episodic_memory": self.episodic_memory.to_dict(),
            "last_stimulus_turn": self.last_stimulus_turn,
            "last_stimulus_length": self.last_stimulus_length,
            "last_stimulus_tensor": self.last_stimulus_tensor,
            "stimulus_decay_factor": self.stimulus_decay_factor,
            "silence_mode": self.silence_mode,
            "primordial_lexicon_initialized": self.primordial_lexicon_initialized
        }
        if self.tensor_cognition:
            result["tensor_cognition"] = self.tensor_cognition.to_dict()
        return result
    
    @classmethod
    def from_dict(cls, data: dict) -> "WorldState":
        """Deserialize from dictionary."""
        from .memory import SemanticGraph, EpisodicMemory
        
        state = cls()
        state.turn = data.get("turn", 0)
        state.seed = data.get("seed", 42)
        state.drives = Drives.from_dict(data.get("drives", {}))
        state.semantic_graph = SemanticGraph.from_dict(data.get("semantic_graph", {}))
        state.episodic_memory = EpisodicMemory.from_dict(data.get("episodic_memory", {}))
        state.last_stimulus_turn = data.get("last_stimulus_turn", 0)
        state.last_stimulus_length = data.get("last_stimulus_length", 0)
        state.last_stimulus_tensor = data.get("last_stimulus_tensor", None)
        state.stimulus_decay_factor = data.get("stimulus_decay_factor", 0.85)
        state.silence_mode = data.get("silence_mode", False)
        state.primordial_lexicon_initialized = data.get("primordial_lexicon_initialized", False)
        
        # Restore tensor cognition if present
        if "tensor_cognition" in data:
            state.tensor_cognition = TensorCognition.from_dict(data["tensor_cognition"])
        else:
            # Initialize new tensor cognition
            state.tensor_cognition = TensorCognition(seed=state.seed)
        
        return state


class World:
    """Manages world state and persistence."""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.state_file = self.data_dir / "state.json"
        self.backup_file = self.data_dir / "state.json.bak"
        self.state: Optional[WorldState] = None
    
    def load(self) -> WorldState:
        """Load world state from disk, or create new if missing."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.state = WorldState.from_dict(data)
                # Initialize primordial lexicon if not already done
                if not self.state.primordial_lexicon_initialized and self.state.tensor_cognition:
                    self.state.tensor_cognition.initialize_primordial_lexicon()
                    self.state.primordial_lexicon_initialized = True
                # Restore RNG state if possible
                random.seed(self.state.seed)
                return self.state
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                # Corrupted file, try backup
                if self.backup_file.exists():
                    try:
                        with open(self.backup_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        self.state = WorldState.from_dict(data)
                        # Initialize primordial lexicon if not already done
                        if not self.state.primordial_lexicon_initialized and self.state.tensor_cognition:
                            self.state.tensor_cognition.initialize_primordial_lexicon()
                            self.state.primordial_lexicon_initialized = True
                        random.seed(self.state.seed)
                        return self.state
                    except:
                        pass
                # Both failed, start fresh
                print(f"Warning: Could not load state ({e}), starting fresh.")
        
        # Create new state
        self.state = WorldState()
        # Initialize tensor cognition
        self.state.tensor_cognition = TensorCognition(seed=self.state.seed)
        # Initialize primordial lexicon (only on fresh state)
        if not self.state.primordial_lexicon_initialized:
            self.state.tensor_cognition.initialize_primordial_lexicon()
            self.state.primordial_lexicon_initialized = True
        random.seed(self.state.seed)
        return self.state
    
    def save(self):
        """
        Save world state to PostgreSQL (fire-and-forget).
        
        This method does NOT block. Errors are logged but not propagated.
        """
        if self.state is None:
            return
        
        # Write to PostgreSQL asynchronously
        try:
            from .persistence.snapshot_writer import write_snapshot
            write_snapshot(self.state.turn, self.state.to_dict())
        except Exception as e:
            # Log error but don't propagate - simulation must continue
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error saving world state: {e}", exc_info=True)
    
    def update_graph_from_tokens(self, tokens: List[str], weight_multiplier: float = 1.0):
        """
        Update semantic graph from tokens with sliding window edges.
        
        Args:
            tokens: List of tokens to process
            weight_multiplier: Multiplier for edge weights (e.g., 0.3 for artifacts)
        """
        if not tokens or not self.state:
            return
        
        # Update node weights
        for token in tokens:
            self.state.semantic_graph.add_token(token, weight=1.0 * weight_multiplier)
        
        # Create edges with sliding window (size 2-4)
        for window_size in range(2, min(5, len(tokens) + 1)):
            for i in range(len(tokens) - window_size + 1):
                window_tokens = tokens[i:i+window_size]
                # Connect all pairs in window
                for j in range(len(window_tokens) - 1):
                    token1 = window_tokens[j]
                    token2 = window_tokens[j + 1]
                    # Weight decreases with distance
                    edge_weight = weight_multiplier / (j + 1)
                    self.state.semantic_graph.add_edge(token1, token2, weight=edge_weight)
                    # Add reverse edge (undirected)
                    self.state.semantic_graph.add_edge(token2, token1, weight=edge_weight * 0.5)
        
        # Handle single token case: connect to recent tokens from episodic memory
        if len(tokens) == 1 and self.state.episodic_memory.episodes:
            single_token = tokens[0]
            # Get tokens from last few episodes
            recent = self.state.episodic_memory.get_recent(5)
            context_tokens = set()
            for ep in recent:
                ep_tokens = tokenize(ep.system_output + " " + ep.user_input)
                context_tokens.update(ep_tokens)
            
            # Connect single token to context tokens
            for ctx_token in context_tokens:
                if ctx_token != single_token:
                    self.state.semantic_graph.add_edge(single_token, ctx_token, weight=0.3 * weight_multiplier)
                    self.state.semantic_graph.add_edge(ctx_token, single_token, weight=0.15 * weight_multiplier)
    
    def process_input(self, user_input: str):
        """Process user input: tokenize and update semantic graph and tensor cognition."""
        if not user_input or not self.state:
            return
        
        tokens = tokenize(user_input)
        if not tokens:
            return
        
        # Update graph with full weight (1.0) for user input
        self.update_graph_from_tokens(tokens, weight_multiplier=1.0)
        
        # Update tensor cognition
        if self.state.tensor_cognition:
            drives = [
                self.state.drives.stability,
                self.state.drives.novelty,
                self.state.drives.cohesion,
                self.state.drives.expression
            ]
            self.state.tensor_cognition.update_from_interaction(tokens, weight=1.0, drives=drives)
        
        # Update stimulus tracking
        self.state.last_stimulus_turn = self.state.turn
        self.state.last_stimulus_length = len(user_input)
    
    def process_artifact(self, artifact_tokens: List[str]):
        """Process generated artifact: update graph and tensor cognition (closed loop learning)."""
        if not artifact_tokens or not self.state:
            return
        
        # Update graph with reduced weight (0.3) for artifacts
        self.update_graph_from_tokens(artifact_tokens, weight_multiplier=0.3)
        
        # Update tensor cognition with reduced weight
        if self.state.tensor_cognition:
            drives = [
                self.state.drives.stability,
                self.state.drives.novelty,
                self.state.drives.cohesion,
                self.state.drives.expression
            ]
            self.state.tensor_cognition.update_from_interaction(artifact_tokens, weight=0.3, drives=drives)
    
    def update_drives(
        self,
        diversity: float,
        coherence: float,
        novelty: float,
        interaction_intensity: float
    ):
        """Update drives based on metrics and interaction, with homeostasis and coupling."""
        if not self.state:
            return
        
        d = self.state.drives
        turns_since_stimulus = self.state.turn - self.state.last_stimulus_turn
        
        # Homeostasis: drift toward midpoint (0.5) to prevent saturation
        homeostasis_rate = 0.02
        d.stability += homeostasis_rate * (0.5 - d.stability)
        d.novelty += homeostasis_rate * (0.5 - d.novelty)
        d.cohesion += homeostasis_rate * (0.5 - d.cohesion)
        d.expression += homeostasis_rate * (0.5 - d.expression)
        
        # Calculate deltas with caps
        max_delta = 0.05
        
        # Stability: increases with coherence, decreases with novelty
        stability_delta = 0.1 * (coherence - novelty) - 0.05 * (1.0 - interaction_intensity)
        stability_delta = max(-max_delta, min(max_delta, stability_delta))
        d.stability += stability_delta
        
        # Novelty: increases when diversity/novelty are low, decreases with stability
        novelty_delta = 0.1 * (1.0 - diversity) + 0.1 * (1.0 - novelty) - 0.05 * d.stability
        novelty_delta = max(-max_delta, min(max_delta, novelty_delta))
        d.novelty += novelty_delta
        
        # Cohesion: increases with coherence, decreases with time since stimulus
        cohesion_delta = 0.1 * coherence - 0.02 * min(turns_since_stimulus / 10.0, 1.0)
        cohesion_delta = max(-max_delta, min(max_delta, cohesion_delta))
        d.cohesion += cohesion_delta
        
        # Expression: increases with interaction intensity, decreases with stability
        expression_delta = 0.1 * interaction_intensity - 0.05 * d.stability
        expression_delta = max(-max_delta, min(max_delta, expression_delta))
        d.expression += expression_delta
        
        # Coupling rules to prevent collapse
        if d.stability > 0.85 and novelty < 0.15:
            d.novelty = min(1.0, d.novelty + 0.05)
            d.expression = min(1.0, d.expression + 0.03)
        
        if coherence > 0.90 and diversity < 0.20:
            d.cohesion = max(0.0, d.cohesion - 0.04)
        
        # Normalize
        d.normalize()
    
    def advance_turn(self):
        """Advance turn counter."""
        if self.state:
            self.state.turn += 1
    
    def reset(self):
        """Reset world to initial state."""
        old_seed = self.state.seed if self.state else 42
        self.state = WorldState(seed=old_seed)
        # Initialize tensor cognition
        self.state.tensor_cognition = TensorCognition(seed=old_seed)
        random.seed(self.state.seed)
    
    def set_seed(self, seed: int):
        """Set RNG seed."""
        if self.state:
            self.state.seed = seed
        random.seed(seed)
    
    def lexicon_sprout(self, novelty_drive: float):
        """
        Introduce new tokens when graph is sparse and novelty drive is high.
        Connects them to recent motifs.
        
        Args:
            novelty_drive: Current novelty drive value (0.0-1.0)
        """
        if not self.state:
            return
        
        # Only sprout if novelty is high and graph is sparse
        num_edges = sum(len(neighbors) for neighbors in self.state.semantic_graph.edges.values())
        if novelty_drive < 0.6 or num_edges >= 10:
            return
        
        # Seed lexicon: neutral nature/shape/time/texture words
        seed_lexicon = [
            "flow", "shift", "pattern", "form", "shape", "texture", "surface",
            "depth", "light", "shadow", "moment", "cycle", "rhythm", "pulse",
            "wave", "current", "stream", "path", "trace", "mark", "sign",
            "grain", "edge", "center", "field", "space", "place", "point"
        ]
        
        # Pick 1-3 tokens from seed lexicon
        num_sprouts = random.randint(1, 3)
        new_tokens = random.sample(seed_lexicon, min(num_sprouts, len(seed_lexicon)))
        
        # Connect to recent tokens from graph
        if self.state.semantic_graph.nodes:
            recent_tokens = list(self.state.semantic_graph.nodes.keys())
            # Weight by node weight, take top 5
            sorted_tokens = sorted(recent_tokens, 
                                  key=lambda t: self.state.semantic_graph.nodes.get(t, 0.0),
                                  reverse=True)[:5]
            
            for new_token in new_tokens:
                # Add token with small weight
                self.state.semantic_graph.add_token(new_token, weight=0.5)
                
                # Connect to recent motifs
                for recent_token in sorted_tokens:
                    if recent_token != new_token:
                        self.state.semantic_graph.add_edge(new_token, recent_token, weight=0.2)
                        self.state.semantic_graph.add_edge(recent_token, new_token, weight=0.1)