"""Terminal UI rendering and formatting."""

from typing import Optional
from .world import Drives, WorldState
from .metrics import MetricsTracker


def format_status_line(
    turn: int,
    drives: Drives,
    diversity: float,
    coherence: float,
    novelty: float
) -> str:
    """Format the status line shown each turn."""
    return (
        f"[Turn {turn}] "
        f"stability:{drives.stability:.2f} "
        f"novelty:{drives.novelty:.2f} "
        f"cohesion:{drives.cohesion:.2f} "
        f"expression:{drives.expression:.2f} | "
        f"diversity:{diversity:.2f} "
        f"coherence:{coherence:.2f} "
        f"novelty:{novelty:.2f}"
    )


def format_output(text: str, agent_name: str = "") -> str:
    """Format the generated output text."""
    if not text:
        return ""
    
    # Simple formatting: capitalize first letter
    if text:
        text = text[0].upper() + text[1:] if len(text) > 1 else text.upper()
    
    # Add subtle agent indicator (optional, can be removed)
    if agent_name and agent_name != "none":
        return f"  {text}"
    
    return f"  {text}"


def print_help():
    """Print help message with available commands."""
    help_text = """
Available commands:
  /help              Show this help message
  /seed <int>        Set RNG seed
  /reset             Reset world (will ask for confirmation)
  /save              Force save current state
  /load              Reload state from disk
  /inspect token <word>  Show node and edges for a token
  /inspect cluster <word>  Show top related tokens (cluster)
  /drives            Print current drive values
  /step <n>          Advance n turns without user input
  /debug on|off      Enable/disable debug mode
  /tensor            Print tensor stats and similarity info
  /state             Summarize world state tensor
  /embed <token>     Show nearest neighbors in embedding space
  /freeze            Stop tensor learning temporarily
  /thaw              Resume tensor learning
  /silent            Suppress visible output (system continues thinking)
  /speak             Resume visible output
  /pulse             Force world bulletin and visible output now
  /status            Show drives + tensor stats without generating text
  /run               Start autopilot (world simulation)
  /pause             Pause autopilot
  /speed <ms>        Set tick delay in milliseconds (default 50)
  /device            Show current PyTorch device (CPU/CUDA)
  /auto [on|off]     Toggle autonomous mode (default: ON)
  /tick <n>          Advance world simulation by n turns
  /step <n>          Alias for /tick
  /time              Show current time
  /weather [all]     Show weather (add 'all' for per-region)
  /map               List regions and locations
  /where             Show current hotspots with crowd sizes
  /events            Show last 10 events
  /agents            Show agent summary by role
  /agent <id|name>   Show detailed agent information
  /follow <id|name>  Follow an agent in bulletins
  /unfollow          Stop following
  /export            Export semantic graph to data/graph.json
  /quit              Exit the simulation

You can also type free text as input (treated as stimulus).
"""
    print(help_text)


def print_drives(drives: Drives):
    """Print current drive values."""
    print(f"\nCurrent drives:")
    print(f"  Stability:  {drives.stability:.3f}")
    print(f"  Novelty:    {drives.novelty:.3f}")
    print(f"  Cohesion:   {drives.cohesion:.3f}")
    print(f"  Expression: {drives.expression:.3f}")
    print()


def print_inspect_token(word: str, graph):
    """Print inspection info for a token."""
    word_lower = word.lower()
    
    if word_lower not in graph.nodes:
        print(f"Token '{word}' not found in graph.")
        return
    
    weight = graph.nodes[word_lower]
    print(f"\nToken: {word_lower}")
    print(f"  Node weight: {weight:.2f}")
    
    if word_lower in graph.edges:
        neighbors = graph.get_neighbors(word_lower, top_k=10)
        if neighbors:
            print(f"  Top neighbors:")
            for neighbor, edge_weight in neighbors:
                print(f"    {neighbor}: {edge_weight:.2f}")
        else:
            print(f"  No neighbors")
    else:
        print(f"  No edges")
    print()


def print_inspect_cluster(word: str, graph):
    """Print cluster info for a token."""
    word_lower = word.lower()
    
    if word_lower not in graph.nodes:
        print(f"Token '{word}' not found in graph.")
        return
    
    cluster = graph.get_cluster(word_lower, depth=2, top_k=15)
    if cluster:
        print(f"\nCluster around '{word_lower}':")
        print(f"  {', '.join(cluster)}")
    else:
        print(f"No cluster found for '{word}'.")
    print()


def print_prompt():
    """Print the input prompt."""
    print("> ", end="", flush=True)


def print_tensor_stats(tensor_cognition, temperature: float = 1.0):
    """Print tensor statistics."""
    if not tensor_cognition:
        print("Tensor cognition not initialized.")
        return
    
    stats = tensor_cognition.get_tensor_stats(temperature=temperature)
    print(f"\nTensor Statistics:")
    print(f"  State core norm: {stats['state_core_norm']:.4f}")
    print(f"  State flux norm: {stats['state_flux_norm']:.4f}")
    print(f"  Temperature: {stats['temperature']:.2f}")
    print(f"  Vocabulary size: {stats['vocab_size']}")
    print(f"  Embedding dimension: {stats['embedding_dim']}")
    print(f"  Learning frozen: {tensor_cognition.learning_frozen}")
    print()


def print_world_state(tensor_cognition, stability: float = 0.5):
    """Print summary of world state tensors."""
    if not tensor_cognition:
        print("Tensor cognition not initialized.")
        return
    
    core = tensor_cognition.state_core
    flux = tensor_cognition.state_flux
    combined = tensor_cognition.get_world_state(stability=stability)
    
    print(f"\nWorld State Tensors:")
    print(f"  Core norm: {core.norm().item():.4f}")
    print(f"  Core mean: {core.mean().item():.4f}")
    print(f"  Core std: {core.std().item():.4f}")
    print(f"  Flux norm: {flux.norm().item():.4f}")
    print(f"  Flux mean: {flux.mean().item():.4f}")
    print(f"  Flux std: {flux.std().item():.4f}")
    print(f"  Combined (alpha={stability:.2f}) norm: {combined.norm().item():.4f}")
    print(f"  First 4 core values: {core[:4].tolist()}")
    print(f"  First 4 flux values: {flux[:4].tolist()}")
    print()


def print_embed_neighbors(tensor_cognition, token: str):
    """Print nearest neighbors for a token in embedding space."""
    if not tensor_cognition:
        print("Tensor cognition not initialized.")
        return
    
    neighbors = tensor_cognition.get_nearest_neighbors(token, top_k=10)
    if not neighbors:
        print(f"Token '{token}' not found or has no neighbors.")
        return
    
    print(f"\nNearest neighbors to '{token}' (embedding space):")
    for neighbor, similarity in neighbors:
        print(f"  {neighbor}: {similarity:.4f}")
    print()
