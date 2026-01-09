"""Tensor-based cognition layer for Living Matrix.

This module implements a closed-world AI system using PyTorch tensors.
The system learns patterns only from its own interactions, with no external knowledge.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import List, Dict, Optional, Tuple
import random


class TokenEmbedding(nn.Module):
    """Learnable embeddings for tokens in the world's vocabulary."""
    
    def __init__(self, vocab_size: int, embedding_dim: int = 64, seed: int = 42):
        """
        Initialize token embeddings.
        
        Args:
            vocab_size: Maximum vocabulary size (will grow dynamically)
            embedding_dim: Dimension of embedding vectors
            seed: Random seed for initialization
        """
        super().__init__()
        self.embedding_dim = embedding_dim
        self.vocab_size = vocab_size
        
        # Initialize embeddings with small random values
        torch.manual_seed(seed)
        self.embedding = nn.Embedding(vocab_size, embedding_dim)
        # Initialize with small random values
        nn.init.normal_(self.embedding.weight, mean=0.0, std=0.1)
    
    def forward(self, token_ids: torch.Tensor) -> torch.Tensor:
        """
        Get embeddings for token IDs.
        
        Args:
            token_ids: Tensor of token IDs, shape [batch_size] or [seq_len]
            
        Returns:
            Embeddings, shape [batch_size, embedding_dim] or [seq_len, embedding_dim]
        """
        return self.embedding(token_ids)


class MotifEncoder(nn.Module):
    """Encodes sequences of tokens into motif tensors (internal representations)."""
    
    def __init__(self, embedding_dim: int = 64, hidden_dim: int = 128):
        """
        Initialize motif encoder.
        
        Args:
            embedding_dim: Dimension of token embeddings
            hidden_dim: Hidden dimension for encoding
        """
        super().__init__()
        self.embedding_dim = embedding_dim
        self.hidden_dim = hidden_dim
        
        # Gated pooling mechanism
        self.gate = nn.Sequential(
            nn.Linear(embedding_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, embedding_dim),
            nn.Sigmoid()
        )
        
        # Projection to motif space
        self.projection = nn.Linear(embedding_dim, embedding_dim)
    
    def forward(self, embeddings: torch.Tensor) -> torch.Tensor:
        """
        Encode a sequence of embeddings into a single motif tensor.
        
        Args:
            embeddings: Token embeddings, shape [seq_len, embedding_dim]
            
        Returns:
            Motif tensor, shape [embedding_dim]
        """
        if embeddings.shape[0] == 0:
            # Empty sequence - return zero vector
            return torch.zeros(self.embedding_dim)
        
        # Compute gated mean pooling
        gates = self.gate(embeddings)  # [seq_len, embedding_dim]
        gated_embeddings = embeddings * gates  # [seq_len, embedding_dim]
        pooled = gated_embeddings.mean(dim=0)  # [embedding_dim]
        
        # Project to motif space
        motif = self.projection(pooled)  # [embedding_dim]
        
        return motif


class TensorCognition:
    """Main tensor-based cognition system."""
    
    def __init__(
        self,
        embedding_dim: int = 64,
        hidden_dim: int = 128,
        vocab_size: int = 10000,
        seed: int = 42
    ):
        """
        Initialize tensor cognition system.
        
        Args:
            embedding_dim: Dimension of token embeddings
            hidden_dim: Hidden dimension for encoder
            vocab_size: Maximum vocabulary size
            seed: Random seed
        """
        self.embedding_dim = embedding_dim
        self.hidden_dim = hidden_dim
        self.vocab_size = vocab_size
        self.seed = seed
        self.learning_frozen = False
        
        # Detect and set device (GPU if available, else CPU)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Token to ID mapping (grows dynamically)
        self.token_to_id: Dict[str, int] = {}
        self.id_to_token: Dict[int, str] = {}
        self.next_id = 0
        
        # Special tokens
        self.UNK_ID = 0
        self.token_to_id["<UNK>"] = self.UNK_ID
        self.id_to_token[self.UNK_ID] = "<UNK>"
        self.next_id = 1
        
        # Initialize modules
        torch.manual_seed(seed)
        self.embeddings = TokenEmbedding(vocab_size, embedding_dim, seed)
        self.encoder = MotifEncoder(embedding_dim, hidden_dim)
        
        # Move modules to device
        self.embeddings = self.embeddings.to(self.device)
        self.encoder = self.encoder.to(self.device)
        
        # Multi-state world tensors (prevent vector lock)
        self.state_core = (torch.randn(embedding_dim, device=self.device) * 0.1)  # Slow-changing
        self.state_flux = (torch.randn(embedding_dim, device=self.device) * 0.1)  # Fast-changing
        
        # Online learning parameters
        self.learning_rate = 0.01
        self.embedding_update_rate = 0.001  # Smaller for embeddings
        
        # Anti-repetition tracking
        from collections import deque
        self.recent_motifs: deque = deque(maxlen=10)  # Last 10 selected motif keys
        self.recent_ngrams: set = set()  # 2-grams and 3-grams from last 10 artifacts
        
        # Internal thought: motif registry for blending
        self.motif_registry: deque = deque(maxlen=20)  # Last 20 motif tensors (for internal blending)
        
        # Primordial lexicon (abstract tokens for autonomous speech)
        self.primordial_lexicon: List[str] = []
        self._last_internal_tokens: List[str] = []  # Track last internal thought tokens
    
    def initialize_primordial_lexicon(self):
        """
        Initialize primordial lexicon with abstract tokens.
        Called only once on fresh state.
        """
        primordial_tokens = [
            "flow", "form", "cycle", "drift", "echo", "trace",
            "pattern", "emerge", "dissolve",
            "between", "within", "toward", "away",
            "shift", "gather", "scatter", "fold", "unfold"
        ]
        
        for token in primordial_tokens:
            # Get or create token ID (this creates the embedding)
            token_id = self.get_token_id(token)
            # Token starts with low weight (no edges yet)
            # Relationships will emerge through interaction
        
        self.primordial_lexicon = primordial_tokens.copy()
    
    def get_token_id(self, token: str) -> int:
        """
        Get or create ID for a token.
        
        Args:
            token: Token string
            
        Returns:
            Token ID
        """
        if token in self.token_to_id:
            return self.token_to_id[token]
        
        # Add new token
        if self.next_id >= self.vocab_size:
            # Vocabulary full - use UNK
            return self.UNK_ID
        
        token_id = self.next_id
        self.token_to_id[token] = token_id
        self.id_to_token[token_id] = token
        self.next_id += 1
        
        return token_id
    
    def tokens_to_ids(self, tokens: List[str]) -> List[int]:
        """Convert list of tokens to IDs."""
        return [self.get_token_id(t) for t in tokens]
    
    def ids_to_tokens(self, token_ids: List[int]) -> List[str]:
        """Convert list of IDs to tokens."""
        return [self.id_to_token.get(id, "<UNK>") for id in token_ids]
    
    def encode_motif(self, tokens: List[str]) -> torch.Tensor:
        """
        Encode a sequence of tokens into a motif tensor.
        
        Args:
            tokens: List of token strings
            
        Returns:
            Motif tensor
        """
        if not tokens:
            return torch.zeros(self.embedding_dim, device=self.device)
        
        # Convert to IDs
        token_ids = self.tokens_to_ids(tokens)
        token_ids_tensor = torch.tensor(token_ids, dtype=torch.long, device=self.device)
        
        # Get embeddings
        with torch.no_grad():
            embeddings = self.embeddings(token_ids_tensor)  # [seq_len, embedding_dim]
            motif = self.encoder(embeddings)  # [embedding_dim]
        
        return motif
    
    def get_world_state(self, stability: float) -> torch.Tensor:
        """
        Get the combined world state tensor, weighted by stability.
        Args:
            stability: Current stability drive value (0.0-1.0)
        Returns:
            Combined world state tensor
        """
        alpha = stability  # Use stability directly as alpha
        combined_state = alpha * self.state_core + (1.0 - alpha) * self.state_flux
        return F.normalize(combined_state, p=2, dim=0)
    
    def generate_internal_motif(
        self,
        novelty_drive: float = 0.5,
        stability: float = 0.5
    ) -> torch.Tensor:
        """
        Generate an internal motif tensor without generating text.
        Used for autonomous thought cycles.
        
        Sources:
        1. Perturbations of recent motifs
        2. Blends of older motifs
        3. Projections from state_flux
        
        Args:
            novelty_drive: Novelty drive (0.0-1.0) - higher = more exploration
            stability: Stability drive (0.0-1.0) - higher = more conservative
            
        Returns:
            Internal motif tensor (not converted to text)
        """
        torch.manual_seed(self.seed + hash((novelty_drive, stability)) % 1000)
        
        # Strategy selection based on novelty
        if novelty_drive > 0.6 and len(self.motif_registry) >= 2:
            # High novelty: blend two older motifs
            idx1 = random.randint(0, min(5, len(self.motif_registry) - 1))
            idx2 = random.randint(0, min(5, len(self.motif_registry) - 1))
            while idx2 == idx1:
                idx2 = random.randint(0, min(5, len(self.motif_registry) - 1))
            
            motif1 = self.motif_registry[-1 - idx1]
            motif2 = self.motif_registry[-1 - idx2]
            blend_ratio = 0.3 + 0.4 * random.random()
            internal_motif = blend_ratio * motif1 + (1.0 - blend_ratio) * motif2
            self._last_internal_tokens = []  # No tokens for pure motif blending
            
        elif len(self.motif_registry) > 0:
            # Medium novelty: perturb recent motif
            recent_motif = self.motif_registry[-1]
            perturbation = torch.randn(self.embedding_dim) * (0.05 + 0.1 * novelty_drive)
            internal_motif = recent_motif + perturbation
            self._last_internal_tokens = []  # No tokens for pure motif perturbation
            
        else:
            # Low novelty or empty registry: sample from primordial lexicon + state_flux
            if self.primordial_lexicon:
                # Sample 2-4 DISTINCT tokens from primordial lexicon
                num_samples = min(random.randint(2, 4), len(self.primordial_lexicon))
                sampled_tokens = random.sample(self.primordial_lexicon, num_samples)
                # Encode them into a motif
                lexicon_motif = self.encode_motif(sampled_tokens)
                # Blend with state_flux projection
                blend_ratio = 0.4 + 0.3 * random.random()
                internal_motif = blend_ratio * lexicon_motif + (1.0 - blend_ratio) * self.state_flux
                
                # Return sampled tokens so caller can create graph edges
                self._last_internal_tokens = sampled_tokens
            else:
                # Fallback: project from state_flux
                internal_motif = self.state_flux.clone()
                # Add small orthogonal noise
                noise = torch.randn(self.embedding_dim, device=self.device) * (0.02 + 0.03 * novelty_drive)
                # Make noise orthogonal to state_flux
                noise = noise - (noise @ self.state_flux) * self.state_flux
                internal_motif = internal_motif + noise
                self._last_internal_tokens = []  # No tokens for pure noise
        
        # Normalize
        internal_motif = F.normalize(internal_motif, p=2, dim=0)
        
        # Register for future blending
        self.motif_registry.append(internal_motif.clone().detach())
        
        return internal_motif
    
    def update_from_internal_motif(
        self,
        motif: torch.Tensor,
        weight: float = 0.1,
        drives: Optional[List[float]] = None
    ):
        """
        Update cognition from an internal motif (not from text tokens).
        Used for autonomous thought cycles.
        
        Args:
            motif: Internal motif tensor
            weight: Learning weight (smaller than external interactions)
            drives: Optional [stability, novelty, cohesion, expression]
        """
        if self.learning_frozen:
            return
        
        # Modulate by drives if provided
        if drives:
            drive_scale = 0.5 + 0.5 * (drives[1] - drives[0])  # Novelty - stability
            weight *= drive_scale
        
        # Update multi-state tensors (smaller updates for internal thoughts)
        core_lr = 0.01 * weight  # Half the rate of external interactions
        self.state_core = (1.0 - core_lr) * self.state_core + core_lr * motif
        self.state_core = F.normalize(self.state_core, p=2, dim=0)
        
        flux_lr = 0.10 * weight  # Half the rate of external interactions
        self.state_flux = (1.0 - flux_lr) * self.state_flux + flux_lr * motif
        self.state_flux = F.normalize(self.state_flux, p=2, dim=0)
    
    def inject_latent_novelty(
        self,
        novelty_drive: float = 0.5
    ):
        """
        Inject controlled novelty when novelty_score is low.
        Adds small orthogonal noise to state_flux or samples low-weight tokens.
        
        Args:
            novelty_drive: Novelty drive (0.0-1.0) - scales magnitude
        """
        if self.learning_frozen:
            return
        
        # Sample 1-2 low-weight tokens if vocabulary exists
        if len(self.token_to_id) > 2:
            # Get random token IDs (excluding UNK)
            available_ids = [id for id in self.id_to_token.keys() if id != self.UNK_ID]
            if available_ids:
                num_samples = min(2, len(available_ids))
                sample_ids = random.sample(available_ids, num_samples)
                ids_tensor = torch.tensor(sample_ids, dtype=torch.long)
                
                with torch.no_grad():
                    sample_embeddings = self.embeddings(ids_tensor)
                    # Average them
                    novelty_vector = sample_embeddings.mean(dim=0)
                    # Scale by novelty drive
                    novelty_vector = novelty_vector * (0.01 + 0.02 * novelty_drive)
                    
                    # Add to state_flux only
                    self.state_flux = F.normalize(self.state_flux + novelty_vector, p=2, dim=0)
        else:
            # Fallback: add small orthogonal noise
            torch.manual_seed(self.seed + hash(novelty_drive) % 1000)
            noise = torch.randn(self.embedding_dim, device=self.device) * (0.01 + 0.01 * novelty_drive)
            # Make orthogonal to state_flux
            noise = noise - (noise @ self.state_flux) * self.state_flux
            self.state_flux = F.normalize(self.state_flux + noise, p=2, dim=0)
    
    def update_from_interaction(
        self,
        tokens: List[str],
        weight: float = 1.0,
        drives: Optional[List[float]] = None
    ):
        """
        Update cognition from an interaction (user input or artifact).
        Uses local online learning, not backprop over datasets.
        
        Args:
            tokens: List of tokens from interaction
            weight: Learning weight (1.0 for user input, 0.3 for artifacts)
            drives: Optional [stability, novelty, cohesion, expression] to modulate learning
        """
        if not tokens or self.learning_frozen:
            return
        
        # Encode motif
        motif = self.encode_motif(tokens)
        
        # Modulate by drives if provided
        if drives:
            # Drives as tensor: [stability, novelty, cohesion, expression]
            drive_scale = 0.5 + 0.5 * (drives[1] - drives[0])  # Novelty - stability
            weight *= drive_scale
        
        # Update multi-state tensors
        # state_core: slow-changing (0.98 retention)
        core_lr = 0.02 * weight
        self.state_core = (1.0 - core_lr) * self.state_core + core_lr * motif
        self.state_core = F.normalize(self.state_core, p=2, dim=0)
        
        # state_flux: fast-changing (0.80 retention)
        flux_lr = 0.20 * weight
        self.state_flux = (1.0 - flux_lr) * self.state_flux + flux_lr * motif
        self.state_flux = F.normalize(self.state_flux, p=2, dim=0)
        
        # Optional: small local update to embeddings for involved tokens
        if not self.learning_frozen and weight > 0.5:  # Only for significant interactions
            token_ids = self.tokens_to_ids(tokens)
            if token_ids:
                token_ids_tensor = torch.tensor(token_ids, dtype=torch.long, device=self.device)
                
                # Get current embeddings
                current_embeddings = self.embeddings(token_ids_tensor)
                
                # Target: move embeddings toward combined world state
                world_state = self.get_world_state(stability=0.5)
                target = world_state.unsqueeze(0).expand_as(current_embeddings)
                
                # Small gradient step (local update)
                with torch.enable_grad():
                    embeddings = self.embeddings(token_ids_tensor)
                    loss = F.mse_loss(embeddings.mean(dim=0), target.mean(dim=0))
                    loss.backward()
                    
                    # Update only involved embeddings (very small step)
                    with torch.no_grad():
                        for idx in token_ids:
                            if idx < self.embeddings.embedding.weight.shape[0]:
                                grad = self.embeddings.embedding.weight.grad[idx]
                                if grad is not None:
                                    self.embeddings.embedding.weight[idx] -= (
                                        self.embedding_update_rate * grad
                                    )
                    
                    # Zero gradients
                    self.embeddings.embedding.weight.grad.zero_()
    
    def generate_candidates(
        self,
        graph: Dict[str, Dict[str, float]],
        num_candidates: int = 5,
        candidate_length: int = 8
    ) -> List[List[str]]:
        """
        Generate candidate phrases using graph-based methods.
        
        Args:
            graph: Semantic graph edges
            num_candidates: Number of candidates to generate
            candidate_length: Length of each candidate
            
        Returns:
            List of candidate token sequences
        """
        candidates = []
        
        if not graph.get("edges"):
            return candidates
        
        edges = graph["edges"]
        nodes = list(edges.keys()) if edges else []
        
        for _ in range(num_candidates):
            if not nodes:
                break
            
            # Random walk on graph
            start = random.choice(nodes)
            candidate = [start]
            
            for _ in range(candidate_length - 1):
                if start in edges and edges[start]:
                    neighbors = list(edges[start].keys())
                    weights = [edges[start][n] for n in neighbors]
                    total = sum(weights)
                    if total > 0:
                        r = random.random() * total
                        cumulative = 0.0
                        for neighbor, weight in zip(neighbors, weights):
                            cumulative += weight
                            if r <= cumulative:
                                candidate.append(neighbor)
                                start = neighbor
                                break
                        else:
                            break
                    else:
                        break
                else:
                    break
            
            if len(candidate) >= 3:
                candidates.append(candidate)
        
        return candidates
    
    def _get_motif_key(self, tokens: List[str]) -> str:
        """Get normalized motif key for repetition tracking."""
        # Normalize: take 3-7 token window, sorted for stability
        window = tokens[:min(7, len(tokens))]
        if len(window) < 3:
            return " ".join(sorted(window))
        return " ".join(sorted(window[:3] + window[-2:]))
    
    def _get_ngrams(self, tokens: List[str]) -> List[Tuple[str, ...]]:
        """Extract 2-grams and 3-grams from tokens."""
        ngrams = []
        for n in [2, 3]:
            for i in range(len(tokens) - n + 1):
                ngrams.append(tuple(tokens[i:i+n]))
        return ngrams
    
    def score_candidate(
        self,
        candidate: List[str],
        world_state: torch.Tensor,
        novelty_penalty: float = 0.1,
        cohesion_bonus: float = 0.1
    ) -> Tuple[float, float]:
        """
        Score a candidate phrase by similarity to world state.
        
        Args:
            candidate: List of tokens
            world_state: Current world state tensor
            novelty_penalty: Penalty for being too similar (encourages diversity)
            cohesion_bonus: Bonus for internal coherence
            
        Returns:
            Score (higher is better)
        """
        motif = self.encode_motif(candidate)
        
        # Cosine similarity to world state
        similarity = F.cosine_similarity(
            motif.unsqueeze(0),
            world_state.unsqueeze(0),
            dim=1
        ).item()
        
        # Novelty penalty (encourage some diversity)
        novelty_score = 1.0 - abs(similarity)
        
        # Cohesion bonus (internal coherence of candidate)
        cohesion = 0.0
        if len(candidate) > 1:
            # Check if tokens are related in embedding space
            token_ids = self.tokens_to_ids(candidate)
            if len(token_ids) > 1:
                ids_tensor = torch.tensor(token_ids, dtype=torch.long, device=self.device)
                with torch.no_grad():
                    embeds = self.embeddings(ids_tensor)
                    # Average pairwise similarity
                    similarities = []
                    for i in range(len(embeds) - 1):
                        sim = F.cosine_similarity(
                            embeds[i:i+1],
                            embeds[i+1:i+2],
                            dim=1
                        ).item()
                        similarities.append(sim)
                    if similarities:
                        cohesion = sum(similarities) / len(similarities)
        
        # Repetition penalty
        motif_key = self._get_motif_key(candidate)
        motif_penalty = 0.3 if motif_key in self.recent_motifs else 0.0
        
        candidate_ngrams = set(self._get_ngrams(candidate))
        overlapping_ngrams = candidate_ngrams.intersection(self.recent_ngrams)
        ngram_penalty = min(0.3, 0.02 * len(overlapping_ngrams))
        
        total_repetition_penalty = motif_penalty + ngram_penalty
        
        # Combined score
        base_score = similarity + cohesion_bonus * cohesion - novelty_penalty * (1.0 - novelty_score)
        final_score = base_score - total_repetition_penalty
        
        return (final_score, total_repetition_penalty)
    
    def generate_from_state(
        self,
        graph: Dict[str, Dict[str, float]],
        num_tokens: int = 8,
        temperature: float = 1.0,
        drives: Optional[List[float]] = None,
        novelty_score: float = 0.0,
        diversity: float = 0.5,
        coherence: float = 0.5
    ) -> List[str]:
        """
        Generate tokens based on world state tensor and graph.
        Uses AI-driven candidate scoring instead of pure random walks.
        
        Args:
            graph: Semantic graph for candidate generation
            num_tokens: Number of tokens to generate
            temperature: Sampling temperature
            drives: Optional [stability, novelty, cohesion, expression]
            novelty_score: Current novelty metric
            diversity: Current diversity metric
            coherence: Current coherence metric
            
        Returns:
            List of generated token strings
        """
        # Dynamic temperature based on metrics (exploration schedule)
        base_temperature = 1.0
        if novelty_score < 0.15:
            base_temperature += 0.2
        if diversity < 0.2:
            base_temperature += 0.2
        if coherence < 0.25:
            base_temperature -= 0.1
        effective_temperature = max(0.7, min(1.6, base_temperature * temperature))
        
        # Adjust parameters based on drives
        novelty_penalty = 0.1
        cohesion_bonus = 0.1
        stability = 0.5
        if drives:
            novelty_penalty = 0.05 + 0.15 * drives[1]  # Novelty drive
            cohesion_bonus = 0.05 + 0.15 * drives[2]  # Cohesion drive
            stability = drives[0]  # Stability drive
        
        # Get world state (alpha-weighted core + flux)
        world_state = self.get_world_state(stability=stability)
        
        # Add controlled noise to state_flux if stuck
        if novelty_score < 0.15:
            torch.manual_seed(self.seed + hash(tuple(world_state.tolist())) % 1000)
            noise = torch.randn(self.embedding_dim, device=self.device) * 0.01
            self.state_flux = F.normalize(self.state_flux + noise, p=2, dim=0)
            world_state = self.get_world_state(stability=stability)
        
        # Generate candidates
        candidates = self.generate_candidates(
            graph,
            num_candidates=10,
            candidate_length=num_tokens
        )
        
        if not candidates:
            # Fallback: use graph nodes
            if graph.get("nodes"):
                nodes = list(graph["nodes"].keys())
                return random.sample(nodes, min(num_tokens, len(nodes)))
            return []
        
        # Score candidates
        scored = []
        for candidate in candidates:
            score, rep_penalty = self.score_candidate(
                candidate,
                world_state,
                novelty_penalty=novelty_penalty,
                cohesion_bonus=cohesion_bonus
            )
            scored.append((score, rep_penalty, candidate))
        
        # Sort by score
        scored.sort(key=lambda x: x[0], reverse=True)
        
        # Select using temperature-based sampling
        if effective_temperature > 0 and len(scored) > 1:
            # Softmax over top candidates
            top_k = min(5, len(scored))
            top_candidates = scored[:top_k]
            scores = [s[0] for s in top_candidates]
            scores_tensor = torch.tensor(scores) / effective_temperature
            probs = F.softmax(scores_tensor, dim=0)
            torch.manual_seed(self.seed + hash(tuple(scores)) % 1000)
            idx = torch.multinomial(probs, 1).item()
            selected = top_candidates[idx][2]
        else:
            selected = scored[0][2]
        
        # Update repetition tracking
        motif_key = self._get_motif_key(selected)
        self.recent_motifs.append(motif_key)
        selected_ngrams = self._get_ngrams(selected)
        self.recent_ngrams.update(selected_ngrams)
        # Keep only last 10 artifacts' ngrams (approximate)
        if len(self.recent_ngrams) > 100:
            # Trim oldest (simple approach: clear and rebuild from recent motifs)
            self.recent_ngrams = set()
            for m in list(self.recent_motifs)[-5:]:  # Last 5 motifs
                tokens = m.split()
                self.recent_ngrams.update(self._get_ngrams(tokens))
        
        return selected[:num_tokens]
    
    def get_tensor_stats(self, temperature: float = 1.0) -> Dict[str, float]:
        """Get statistics about tensor state."""
        return {
            "state_core_norm": float(self.state_core.norm().item()),
            "state_flux_norm": float(self.state_flux.norm().item()),
            "vocab_size": len(self.token_to_id),
            "embedding_dim": self.embedding_dim,
            "temperature": temperature
        }
    
    def get_nearest_neighbors(self, token: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """
        Get nearest neighbor tokens in embedding space.
        
        Args:
            token: Query token
            top_k: Number of neighbors to return
            
        Returns:
            List of (token, similarity) tuples
        """
        if token not in self.token_to_id:
            return []
        
        token_id = self.token_to_id[token]
        token_embedding = self.embeddings.embedding.weight[token_id].detach()
        
        # Compute similarities to all other tokens
        all_embeddings = self.embeddings.embedding.weight.detach()
        similarities = F.cosine_similarity(
            token_embedding.unsqueeze(0),
            all_embeddings,
            dim=1
        )
        
        # Get top k (excluding self)
        top_similarities, top_indices = torch.topk(similarities, min(top_k + 1, len(similarities)))
        
        neighbors = []
        for sim, idx in zip(top_similarities, top_indices):
            idx_item = idx.item()
            if idx_item != token_id and idx_item in self.id_to_token:
                neighbors.append((self.id_to_token[idx_item], float(sim.item())))
        
        return neighbors[:top_k]
    
    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "token_to_id": self.token_to_id,
            "id_to_token": {str(k): v for k, v in self.id_to_token.items()},
            "next_id": self.next_id,
            "embedding_dim": self.embedding_dim,
            "hidden_dim": self.hidden_dim,
            "vocab_size": self.vocab_size,
            "seed": self.seed,
            "learning_rate": self.learning_rate,
            "learning_frozen": self.learning_frozen,
            "state_core": self.state_core.tolist(),
            "state_flux": self.state_flux.tolist(),
            "recent_motifs": list(self.recent_motifs),
            "recent_ngrams": [list(ng) if isinstance(ng, tuple) else ng for ng in self.recent_ngrams],
            "motif_registry": [m.tolist() for m in self.motif_registry],
            "primordial_lexicon": self.primordial_lexicon,
            "embeddings_weight": self.embeddings.embedding.weight.detach().tolist(),
            "encoder_gate_0_weight": self.encoder.gate[0].weight.detach().tolist(),
            "encoder_gate_0_bias": self.encoder.gate[0].bias.detach().tolist(),
            "encoder_gate_2_weight": self.encoder.gate[2].weight.detach().tolist(),
            "encoder_gate_2_bias": self.encoder.gate[2].bias.detach().tolist(),
            "encoder_projection_weight": self.encoder.projection.weight.detach().tolist(),
            "encoder_projection_bias": self.encoder.projection.bias.detach().tolist(),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "TensorCognition":
        """Deserialize from dictionary."""
        obj = cls(
            embedding_dim=data.get("embedding_dim", 64),
            hidden_dim=data.get("hidden_dim", 128),
            vocab_size=data.get("vocab_size", 10000),
            seed=data.get("seed", 42)
        )
        
        obj.token_to_id = data.get("token_to_id", {})
        obj.id_to_token = {int(k): v for k, v in data.get("id_to_token", {}).items()}
        obj.next_id = data.get("next_id", 1)
        obj.learning_rate = data.get("learning_rate", 0.01)
        obj.learning_frozen = data.get("learning_frozen", False)
        
        # Restore multi-state tensors
        if "state_core" in data:
            obj.state_core = torch.tensor(data["state_core"], dtype=torch.float32)
        if "state_flux" in data:
            obj.state_flux = torch.tensor(data["state_flux"], dtype=torch.float32)
        
        # Restore repetition tracking
        if "recent_motifs" in data:
            from collections import deque
            obj.recent_motifs = deque(data["recent_motifs"], maxlen=10)
        if "recent_ngrams" in data:
            # Convert list items to tuples (n-grams are tuples, but JSON stores them as lists)
            ngrams_list = data["recent_ngrams"]
            if ngrams_list and isinstance(ngrams_list[0], list):
                # Convert lists to tuples for hashability
                obj.recent_ngrams = {tuple(ng) if isinstance(ng, list) else ng for ng in ngrams_list}
            else:
                # Already tuples or strings
                obj.recent_ngrams = set(ngrams_list)
        if "motif_registry" in data:
            obj.motif_registry = deque(
                [torch.tensor(m, dtype=torch.float32, device=obj.device) for m in data["motif_registry"]],
                maxlen=20
            )
        if "primordial_lexicon" in data:
            obj.primordial_lexicon = data["primordial_lexicon"]
        
        # Restore model weights
        if "embeddings_weight" in data:
            obj.embeddings.embedding.weight.data = torch.tensor(data["embeddings_weight"], device=obj.device)
        
        if "encoder_gate_0_weight" in data:
            obj.encoder.gate[0].weight.data = torch.tensor(data["encoder_gate_0_weight"], device=obj.device)
            obj.encoder.gate[0].bias.data = torch.tensor(data["encoder_gate_0_bias"], device=obj.device)
            obj.encoder.gate[2].weight.data = torch.tensor(data["encoder_gate_2_weight"], device=obj.device)
            obj.encoder.gate[2].bias.data = torch.tensor(data["encoder_gate_2_bias"], device=obj.device)
            obj.encoder.projection.weight.data = torch.tensor(data["encoder_projection_weight"], device=obj.device)
            obj.encoder.projection.bias.data = torch.tensor(data["encoder_projection_bias"], device=obj.device)
        
        return obj
