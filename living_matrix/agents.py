"""Internal agents that propose outputs each turn."""

import random
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

from .grammar import generate_from_graph, remix_phrase, apply_grammar_template, GRAMMAR_TEMPLATES, tokenize
from .memory import SemanticGraph, EpisodicMemory
from .dataclasses import Drives
from .tensor_core import TensorCognition
from .constants.agents_constants import (
    MIN_TOKEN_LENGTH, DEFAULT_TOKEN_LENGTH, TOKEN_LENGTH_MULTIPLIER, MAX_TOKEN_LENGTH,
    ARCHIVIST_RECENT_EPISODES, ARCHIVIST_MUTATION_RATE_BASE, ARCHIVIST_MUTATION_RATE_MULTIPLIER,
    ARCHIVIST_CONFIDENCE_BASE, ARCHIVIST_CONFIDENCE_STABILITY_MULTIPLIER,
    WEAVER_FALLBACK_RECENT_EPISODES, WEAVER_FALLBACK_MAX_TOKENS, WEAVER_FALLBACK_CONFIDENCE,
    WEAVER_COHESION_THRESHOLD, WEAVER_TEMPERATURE_BASE, WEAVER_TEMPERATURE_COHESION_MULTIPLIER,
    WEAVER_CONFIDENCE_BASE, WEAVER_CONFIDENCE_COHESION_MULTIPLIER, WEAVER_TEMPLATE_CHANCE,
    GARDENER_CLUSTER_DEPTH, GARDENER_CLUSTER_TOP_K, GARDENER_MIN_CLUSTER_SIZE,
    GARDENER_MAX_TOKENS, GARDENER_TEMPLATE_CHANCE, GARDENER_MIN_TOKENS_FOR_TEMPLATE,
    GARDENER_FALLBACK_RECENT_EPISODES, GARDENER_FALLBACK_TOKENS_PER_EPISODE,
    GARDENER_FALLBACK_MIN_TOKENS, GARDENER_TEMPLATE_CHANCE_FALLBACK,
    GARDENER_CONFIDENCE_BASE, GARDENER_CONFIDENCE_COHESION_MULTIPLIER,
    TRICKSTER_LENGTH_BASE, TRICKSTER_LENGTH_MULTIPLIER, TRICKSTER_TEMPERATURE,
    TRICKSTER_RANDOM_WORD_CHANCE, TRICKSTER_CONFIDENCE_BASE, TRICKSTER_CONFIDENCE_NOVELTY_MULTIPLIER,
    CARTOGRAPHER_NEIGHBOR_COUNT, CARTOGRAPHER_RECENT_EPISODES, CARTOGRAPHER_TOKENS_PER_EPISODE,
    CARTOGRAPHER_MIN_TOKENS, CARTOGRAPHER_MAX_TOKENS, CARTOGRAPHER_CONFIDENCE_BASE,
    CARTOGRAPHER_CONFIDENCE_COHESION_MULTIPLIER, CARTOGRAPHER_FALLBACK_SAMPLE_SIZE,
    COORDINATOR_DRIVE_ALIGNMENT_BASE, COORDINATOR_DRIVE_ALIGNMENT_MULTIPLIER
)


@dataclass
class Proposal:
    """An agent's proposed output."""
    text: str
    tokens: List[str]
    style: str
    agent_name: str
    confidence: float = 1.0


class Agent:
    """Base class for internal agents."""
    
    def __init__(self, name: str, style: str):
        self.name = name
        self.style = style
    
    def propose(
        self,
        graph: SemanticGraph,
        memory: EpisodicMemory,
        drives: Drives,
        turn: int,
        tensor_cognition: Optional[TensorCognition] = None
    ) -> Proposal:
        """Generate a proposal. Override in subclasses."""
        return Proposal(
            text="",
            tokens=[],
            style=self.style,
            agent_name=self.name,
            confidence=0.0
        )


class Archivist(Agent):
    """Remixes past phrases from episodic memory."""
    
    def __init__(self):
        super().__init__("Archivist", "remix")
    
    def propose(
        self,
        graph: SemanticGraph,
        memory: EpisodicMemory,
        drives: Drives,
        turn: int,
        tensor_cognition: Optional[TensorCognition] = None
    ) -> Proposal:
        recent = memory.get_recent(ARCHIVIST_RECENT_EPISODES)
        if not recent:
            return Proposal("", [], self.style, self.name, 0.0)
        
        # Pick a random recent output
        episode = random.choice(recent)
        phrase = episode.system_output or episode.user_input
        
        if not phrase:
            return Proposal("", [], self.style, self.name, 0.0)
        
        # Remix with mutation rate based on novelty drive
        mutation_rate = ARCHIVIST_MUTATION_RATE_BASE + ARCHIVIST_MUTATION_RATE_MULTIPLIER * drives.novelty
        remixed = remix_phrase(phrase, graph.edges, mutation_rate)
        
        tokens = tokenize(remixed)
        confidence = ARCHIVIST_CONFIDENCE_BASE + ARCHIVIST_CONFIDENCE_STABILITY_MULTIPLIER * drives.stability
        
        return Proposal(
            text=remixed,
            tokens=tokens,
            style=self.style,
            agent_name=self.name,
            confidence=confidence
        )


class Weaver(Agent):
    """Creates new phrases via graph walks."""
    
    def __init__(self):
        super().__init__("Weaver", "generative")
    
    def propose(
        self,
        graph: SemanticGraph,
        memory: EpisodicMemory,
        drives: Drives,
        turn: int,
        tensor_cognition: Optional[TensorCognition] = None
    ) -> Proposal:
        # Fallback if no graph: use episodic memory
        if not graph.nodes:
            recent = memory.get_recent(WEAVER_FALLBACK_RECENT_EPISODES)
            if recent:
                episode = random.choice(recent)
                phrase = episode.system_output or episode.user_input
                if phrase:
                    tokens = tokenize(phrase)
                    if tokens:
                        text = " ".join(tokens[:min(WEAVER_FALLBACK_MAX_TOKENS, len(tokens))])
                        return Proposal(text, tokens[:min(MAX_TOKEN_LENGTH, len(tokens))], self.style, self.name, WEAVER_FALLBACK_CONFIDENCE)
            return Proposal("", [], self.style, self.name, 0.0)
        
        # Length based on expression drive (minimum 4 tokens)
        length = max(MIN_TOKEN_LENGTH, DEFAULT_TOKEN_LENGTH + int(TOKEN_LENGTH_MULTIPLIER * drives.expression))
        temperature = WEAVER_TEMPERATURE_BASE - WEAVER_TEMPERATURE_COHESION_MULTIPLIER * drives.cohesion  # Lower temp = more cohesive
        
        # Start from a high-weight node if cohesion is high
        start_token = None
        if drives.cohesion > WEAVER_COHESION_THRESHOLD and graph.nodes:
            sorted_nodes = sorted(graph.nodes.items(), key=lambda x: x[1], reverse=True)
            if sorted_nodes:
                start_token = sorted_nodes[0][0]
        
        # Try tensor-based generation if available (AI-driven)
        tokens = []
        if tensor_cognition:
            graph_dict = {"nodes": graph.nodes, "edges": graph.edges}
            drives_list = [drives.stability, drives.novelty, drives.cohesion, drives.expression]
            # Get metrics from coordinator context
            novelty_score = getattr(self, '_novelty_score', 0.0)
            diversity = getattr(self, '_diversity', 0.5)
            coherence = getattr(self, '_coherence', 0.5)
            tensor_tokens = tensor_cognition.generate_from_state(
                graph_dict,
                num_tokens=length,
                temperature=temperature,
                drives=drives_list,
                novelty_score=novelty_score,
                diversity=diversity,
                coherence=coherence
            )
            if tensor_tokens and len(tensor_tokens) >= 3:
                tokens = tensor_tokens
        
        # Fallback to graph-based generation
        if not tokens or len(tokens) < 3:
            tokens = generate_from_graph(graph.edges, start_token, length, temperature)
        
        # Fallback: if generation failed, use nodes directly
        if not tokens or len(tokens) < 3:
            if graph.nodes:
                node_list = list(graph.nodes.keys())
                tokens = random.sample(node_list, min(length, len(node_list)))
                # Repeat to reach minimum length
                while len(tokens) < MIN_TOKEN_LENGTH and node_list:
                    tokens.append(random.choice(node_list))
        
        if not tokens:
            return Proposal("", [], self.style, self.name, 0.0)
        
        # Ensure minimum length
        tokens = tokens[:min(MAX_TOKEN_LENGTH, max(MIN_TOKEN_LENGTH, len(tokens)))]
        
        # Apply template sometimes
        if len(tokens) >= 3 and random.random() < WEAVER_TEMPLATE_CHANCE and GRAMMAR_TEMPLATES:
            template = random.choice(GRAMMAR_TEMPLATES)
            text = apply_grammar_template(tokens, template)
        else:
            text = " ".join(tokens)
        
        confidence = WEAVER_CONFIDENCE_BASE + WEAVER_CONFIDENCE_COHESION_MULTIPLIER * drives.cohesion
        
        return Proposal(
            text=text,
            tokens=tokens,
            style=self.style,
            agent_name=self.name,
            confidence=confidence
        )


class Gardener(Agent):
    """Focuses on clusters and relationships."""
    
    def __init__(self):
        super().__init__("Gardener", "analytical")
    
    def propose(
        self,
        graph: SemanticGraph,
        memory: EpisodicMemory,
        drives: Drives,
        turn: int,
        tensor_cognition: Optional[TensorCognition] = None
    ) -> Proposal:
        if not graph.nodes:
            return Proposal("", [], self.style, self.name, 0.0)
        
        # Pick a central token
        central = random.choice(list(graph.nodes.keys()))
        cluster = graph.get_cluster(central, depth=GARDENER_CLUSTER_DEPTH, top_k=GARDENER_CLUSTER_TOP_K)
        
        # Always produce multi-token output (never "stands alone")
        if cluster and len(cluster) >= GARDENER_MIN_CLUSTER_SIZE:
            # Use cluster tokens
            tokens = [central] + cluster[:min(GARDENER_MAX_TOKENS, len(cluster))]
            # Apply template or create descriptive phrase
            if random.random() < GARDENER_TEMPLATE_CHANCE and len(tokens) >= GARDENER_MIN_TOKENS_FOR_TEMPLATE:
                template = random.choice([
                    "{0} connects {1} {2}",
                    "{0} links {1} through {2}",
                    "around {0} gather {1} {2}",
                ])
                text = template.format(tokens[0], tokens[1], tokens[2] if len(tokens) > 2 else tokens[1])
            else:
                text = " ".join(tokens[:min(6, len(tokens))])
        else:
            # Fallback: use recent episodic tokens or generate walk
                if graph.edges:
                    # Generate a walk from central token
                    tokens = generate_from_graph(graph.edges, central, length=random.randint(GARDENER_FALLBACK_MIN_TOKENS, GARDENER_MAX_TOKENS), temperature=1.5)
                    if not tokens:
                        tokens = [central]
                else:
                    tokens = [central]
                
                # Get additional tokens from recent memory
                recent = memory.get_recent(GARDENER_FALLBACK_RECENT_EPISODES)
                for ep in recent:
                    ep_tokens = tokenize(ep.system_output + " " + ep.user_input)
                    tokens.extend(ep_tokens[:GARDENER_FALLBACK_TOKENS_PER_EPISODE])
                    if len(tokens) >= GARDENER_FALLBACK_MIN_TOKENS:
                        break
                
                tokens = tokens[:min(GARDENER_MAX_TOKENS, len(tokens))]
                
                # Apply template
                if len(tokens) >= GARDENER_MIN_TOKENS_FOR_TEMPLATE and random.random() < GARDENER_TEMPLATE_CHANCE_FALLBACK:
                    template = random.choice(GRAMMAR_TEMPLATES)
                    text = apply_grammar_template(tokens, template)
                else:
                    text = " ".join(tokens)
        
        confidence = GARDENER_CONFIDENCE_BASE + GARDENER_CONFIDENCE_COHESION_MULTIPLIER * drives.cohesion
        
        return Proposal(
            text=text,
            tokens=tokens[:min(12, len(tokens))],
            style=self.style,
            agent_name=self.name,
            confidence=confidence
        )


class Trickster(Agent):
    """Introduces randomness and disruption."""
    
    def __init__(self):
        super().__init__("Trickster", "chaotic")
    
    def propose(
        self,
        graph: SemanticGraph,
        memory: EpisodicMemory,
        drives: Drives,
        turn: int,
        tensor_cognition: Optional[TensorCognition] = None
    ) -> Proposal:
        # Minimum length 4 tokens
        length = max(MIN_TOKEN_LENGTH, TRICKSTER_LENGTH_BASE + int(TRICKSTER_LENGTH_MULTIPLIER * drives.novelty))
        
        if graph.edges:
            # High temperature walk
            tokens = generate_from_graph(graph.edges, None, length, temperature=TRICKSTER_TEMPERATURE)
        else:
            tokens = []
        
        # Fallback: use nodes directly
        if not tokens or len(tokens) < 3:
            if graph.nodes:
                node_list = list(graph.nodes.keys())
                tokens = random.sample(node_list, min(length, len(node_list)))
                while len(tokens) < MIN_TOKEN_LENGTH and node_list:
                    tokens.append(random.choice(node_list))
            else:
                return Proposal("", [], self.style, self.name, 0.0)
        
        # Sometimes add random words
        if random.random() < TRICKSTER_RANDOM_WORD_CHANCE:
            tokens.append("shift")
            tokens.append("flux")
        
        tokens = tokens[:min(MAX_TOKEN_LENGTH, len(tokens))]
        text = " ".join(tokens)
        confidence = TRICKSTER_CONFIDENCE_BASE + TRICKSTER_CONFIDENCE_NOVELTY_MULTIPLIER * drives.novelty
        
        return Proposal(
            text=text,
            tokens=tokens,
            style=self.style,
            agent_name=self.name,
            confidence=confidence
        )


class Cartographer(Agent):
    """Maps relationships between concepts."""
    
    def __init__(self):
        super().__init__("Cartographer", "poetic")
    
    def propose(
        self,
        graph: SemanticGraph,
        memory: EpisodicMemory,
        drives: Drives,
        turn: int,
        tensor_cognition: Optional[TensorCognition] = None
    ) -> Proposal:
        # Find edges or use nodes
        all_edges = []
        for token1, neighbors in graph.edges.items():
            for token2, weight in neighbors.items():
                all_edges.append((token1, token2, weight))
        
        if all_edges:
            all_edges.sort(key=lambda x: x[2], reverse=True)
            token1, token2, weight = all_edges[0]
            tokens = [token1, token2]
            
            # Expand with neighbors or recent memory
            if token1 in graph.edges:
                neighbors = list(graph.edges[token1].keys())[:CARTOGRAPHER_NEIGHBOR_COUNT]
                tokens.extend(neighbors)
            elif token2 in graph.edges:
                neighbors = list(graph.edges[token2].keys())[:CARTOGRAPHER_NEIGHBOR_COUNT]
                tokens.extend(neighbors)
            
            # Get more from recent memory if needed
            if len(tokens) < CARTOGRAPHER_MIN_TOKENS:
                recent = memory.get_recent(CARTOGRAPHER_RECENT_EPISODES)
                for ep in recent:
                    ep_tokens = tokenize(ep.system_output + " " + ep.user_input)
                    tokens.extend(ep_tokens[:CARTOGRAPHER_TOKENS_PER_EPISODE])
                    if len(tokens) >= CARTOGRAPHER_MIN_TOKENS:
                        break
            
            tokens = tokens[:min(CARTOGRAPHER_MAX_TOKENS, len(tokens))]
            
            # Create poetic description
            if len(tokens) >= 3:
                templates = [
                    "{0} maps to {1} through {2}",
                    "the path from {0} to {1} reveals {2}",
                    "{0} connects with {1} where {2} emerges",
                    "between {0} and {1} flows {2}",
                ]
                template = random.choice(templates)
                text = template.format(tokens[0], tokens[1], tokens[2] if len(tokens) > 2 else tokens[1])
            else:
                templates = [
                    f"{tokens[0]} maps to {tokens[1]}",
                    f"the path from {tokens[0]} to {tokens[1]}",
                    f"{tokens[0]} connects with {tokens[1]}",
                ]
                text = random.choice(templates)
        elif graph.nodes:
            # Fallback: use nodes
            node_list = list(graph.nodes.keys())
            tokens = random.sample(node_list, min(CARTOGRAPHER_FALLBACK_SAMPLE_SIZE, len(node_list)))
            if len(tokens) >= GARDENER_MIN_TOKENS_FOR_TEMPLATE:
                template = random.choice(GRAMMAR_TEMPLATES)
                text = apply_grammar_template(tokens, template)
            else:
                text = " ".join(tokens)
        else:
            return Proposal("", [], self.style, self.name, 0.0)
        
        tokens = tokens[:min(MAX_TOKEN_LENGTH, len(tokens))]
        confidence = CARTOGRAPHER_CONFIDENCE_BASE + CARTOGRAPHER_CONFIDENCE_COHESION_MULTIPLIER * drives.cohesion
        
        return Proposal(
            text=text,
            tokens=tokens,
            style=self.style,
            agent_name=self.name,
            confidence=confidence
        )


class Coordinator:
    """Selects or blends agent proposals."""
    
    def __init__(self):
        self.agents: List[Agent] = [
            Archivist(),
            Weaver(),
            Gardener(),
            Trickster(),
            Cartographer()
        ]
    
    def select_output(
        self,
        graph: SemanticGraph,
        memory: EpisodicMemory,
        drives: Drives,
        turn: int,
        tensor_cognition: Optional[TensorCognition] = None,
        diversity: float = 0.5,
        coherence: float = 0.5,
        novelty_score: float = 0.0
    ) -> Tuple[str, List[str], str]:
        """
        Select or blend proposals from agents.
        
        Returns:
            Tuple of (output_text, tokens, agent_name)
        """
        # Store metrics for agents to access
        self._novelty_score = novelty_score
        self._diversity = diversity
        self._coherence = coherence
        
        # Get proposals from all agents
        proposals = [
            agent.propose(graph, memory, drives, turn, tensor_cognition)
            for agent in self.agents
        ]
        
        # Filter out empty proposals
        proposals = [p for p in proposals if p.text and p.confidence > 0.0]
        
        if not proposals:
            return ("", [], "none")
        
        # Weight by confidence and drives
        weights = []
        for prop in proposals:
            weight = prop.confidence
            
            # Adjust by drive alignment
            if prop.agent_name == "Archivist":
                weight *= (COORDINATOR_DRIVE_ALIGNMENT_BASE + COORDINATOR_DRIVE_ALIGNMENT_MULTIPLIER * drives.stability)
            elif prop.agent_name == "Weaver":
                weight *= (COORDINATOR_DRIVE_ALIGNMENT_BASE + COORDINATOR_DRIVE_ALIGNMENT_MULTIPLIER * drives.cohesion)
            elif prop.agent_name == "Trickster":
                weight *= (COORDINATOR_DRIVE_ALIGNMENT_BASE + COORDINATOR_DRIVE_ALIGNMENT_MULTIPLIER * drives.novelty)
            elif prop.agent_name == "Gardener":
                weight *= (COORDINATOR_DRIVE_ALIGNMENT_BASE + COORDINATOR_DRIVE_ALIGNMENT_MULTIPLIER * drives.cohesion)
            elif prop.agent_name == "Cartographer":
                weight *= (COORDINATOR_DRIVE_ALIGNMENT_BASE + COORDINATOR_DRIVE_ALIGNMENT_MULTIPLIER * drives.expression)
            
            weights.append(weight)
        
        # Weighted random selection
        total_weight = sum(weights)
        if total_weight == 0:
            selected = random.choice(proposals)
        else:
            r = random.random() * total_weight
            cumulative = 0.0
            for i, weight in enumerate(weights):
                cumulative += weight
                if r <= cumulative:
                    selected = proposals[i]
                    break
            else:
                selected = proposals[-1]
        
        return (selected.text, selected.tokens, selected.agent_name)
