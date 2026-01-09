# Living Matrix

A text-based simulation of an evolving symbol world that demonstrates persistence, adaptation, self-maintenance, and emergent behavior.

## Purpose

Living Matrix is a terminal-based simulation that creates the impression of a "living" system through four operational properties:

1. **Persistence (Memory)**: The system maintains state across sessions, storing both episodic memories (a log of interactions) and semantic memories (a weighted graph of symbol relationships).

2. **Adaptation (Learning)**: User input is tokenized and used to update both the semantic graph and a tensor-based cognition system. The system learns patterns only from its own interactions in a closed-world setting, with no external knowledge.

3. **Self-Maintenance (Homeostasis)**: Internal "drives" (stability, novelty, cohesion, expression) evolve based on interaction patterns and internal metrics, creating dynamic behavior.

4. **Autonomy (Internal Actors)**: Multiple internal agents (Archivist, Weaver, Gardener, Trickster, Cartographer) propose outputs each turn, with a coordinator selecting or blending proposals based on current drives.

## How to Run

```bash
python -m living_matrix
```

The simulation will:
- Load previous state from `data/state.json` if it exists
- Start at turn 0 if no previous state exists
- Display a status line and generated output each turn
- Accept commands (starting with `/`) or free text input

## Commands

- `/help` - Show available commands
- `/seed <int>` - Set RNG seed for deterministic behavior
- `/reset` - Reset world (will ask for confirmation)
- `/save` - Force save current state
- `/load` - Reload state from disk
- `/inspect token <word>` - Show node and edges for a token
- `/inspect cluster <word>` - Show top related tokens (cluster)
- `/drives` - Print current drive values
- `/step <n>` - Advance n turns without user input
- `/tensor` - Print tensor stats and similarity info
- `/state` - Summarize world state tensor
- `/embed <token>` - Show nearest neighbors in embedding space
- `/freeze` - Stop tensor learning temporarily
- `/thaw` - Resume tensor learning
- `/export` - Export semantic graph to `data/graph.json`
- `/quit` - Exit the simulation

## How "Alive" is Defined

The simulation implements four properties that create the impression of a living system:

### 1. Persistence (Memory)

- **Episodic Memory**: A rolling log of turns, user inputs, system outputs, and notable events (bounded to 1000 episodes)
- **Semantic Memory**: A weighted graph where:
  - Nodes represent tokens (words) with weights indicating frequency
  - Edges represent co-occurrence relationships with weights indicating strength
- **State Persistence**: World state is saved to `data/state.json` every 10 turns and on exit

### 2. Adaptation (Learning)

- User input is tokenized (lowercase, alphanumeric, stopwords filtered)
- Tokens are added to the semantic graph with incremented weights
- Co-occurring tokens create/strengthen edges in the graph
- **Tensor-Based Learning**: 
  - Each token maps to a learnable embedding vector (64 dimensions)
  - Sequences are encoded into motif tensors representing internal patterns
  - World state tensor evolves through weighted moving averages
  - Embeddings update locally based on interactions (not batch training)
- Future generation uses hybrid approach:
  - **AI-driven**: Candidate phrases scored by similarity to world state tensor
  - **Graph-based**: Weighted random walks and phrase remixing as fallback
  - Grammar templates applied to generated sequences

### 3. Self-Maintenance (Homeostasis)

Four internal drives (each bounded 0.0-1.0) evolve each turn:

- **Stability**: Prefers repeating coherent motifs
  - Increases with coherence, decreases with novelty
- **Novelty**: Prefers introducing new symbols
  - Increases when diversity/novelty are low
- **Cohesion**: Prefers tightening clusters/relationships
  - Increases with coherence, decreases with time since stimulus
- **Expression**: Prefers producing longer/structured output
  - Increases with interaction intensity

Drives are updated based on:
- Current metrics (diversity, coherence, novelty)
- Interaction intensity (length of user input)
- Time since last strong stimulus

### 4. Autonomy (Internal Actors)

Five internal agents propose outputs each turn:

- **Archivist**: Remixes past phrases from episodic memory
- **Weaver**: Creates new phrases via graph walks
- **Gardener**: Focuses on clusters and relationships
- **Trickster**: Introduces randomness and disruption
- **Cartographer**: Maps relationships between concepts

A coordinator selects or blends proposals based on:
- Agent confidence scores
- Alignment with current drives
- Weighted random selection

## Metrics

The system tracks three metrics:

- **Diversity**: Unique tokens / total tokens in recent window
- **Coherence**: Average edge weight among tokens in recent output
- **Novelty**: Fraction of tokens not seen in recent history

These metrics influence drive updates and coordinator decisions.

## Example Session

```
Living Matrix initialized.
Type /help for commands, or enter text as stimulus.

> hello world
[Turn 0] stability:0.50 novelty:0.50 cohesion:0.50 expression:0.50 | diversity:0.00 coherence:0.00 novelty:0.00
  Hello world

> patterns emerge
[Turn 1] stability:0.55 novelty:0.45 cohesion:0.52 expression:0.51 | diversity:0.50 coherence:0.10 novelty:1.00
  Patterns emerge when hello meets world

> /drives
Current drives:
  Stability:  0.550
  Novelty:    0.450
  Cohesion:   0.520
  Expression: 0.510

> /step 5
[Turn 2] stability:0.60 novelty:0.40 cohesion:0.54 expression:0.48 | diversity:0.67 coherence:0.15 novelty:0.50
  Hello becomes world when patterns

[Turn 3] stability:0.65 novelty:0.35 cohesion:0.56 expression:0.46 | diversity:0.75 coherence:0.20 novelty:0.33
  World reflects patterns

[Turn 4] stability:0.70 novelty:0.30 cohesion:0.58 expression:0.44 | diversity:0.80 coherence:0.25 novelty:0.25
  The pattern of hello and world

[Turn 5] stability:0.75 novelty:0.25 cohesion:0.60 expression:0.42 | diversity:0.83 coherence:0.30 novelty:0.20
  Hello resonates with world

[Turn 6] stability:0.80 novelty:0.20 cohesion:0.62 expression:0.40 | diversity:0.86 coherence:0.35 novelty:0.17
  Where patterns meet world, hello emerges

> /inspect token hello
Token: hello
  Node weight: 2.00
  Top neighbors:
    world: 1.00
    patterns: 0.50

> /quit
State saved. Goodbye.
```

## Project Structure

```
living_matrix/
  __init__.py          # Package initialization
  __main__.py          # CLI entry point
  core.py              # Main simulation loop
  world.py             # World state and persistence
  agents.py            # Internal actors and coordinator
  grammar.py           # Tokenization and generation
  memory.py            # Episodic and semantic memory
  metrics.py           # Metrics calculation
  ui.py                # Terminal rendering

tests/                 # Unit tests
  test_grammar.py
  test_memory.py
  test_world.py
  test_metrics.py

data/                  # Runtime data (created automatically, gitignored)
  state.json           # Persistent world state
  graph.json           # Exported semantic graph (via /export)

README.md              # This file
```

## Testing

Run tests with:

```bash
python -m pytest tests/
```

Or with unittest:

```bash
python -m unittest discover tests
```

Tests cover:
- Tokenizer stability
- Semantic graph updates
- Drive update bounds
- Determinism under fixed seed
- Memory serialization

## Requirements

- Python 3.7+
- PyTorch 2.0+ (for tensor-based cognition)

Install dependencies:
```bash
pip install -r requirements.txt
```

## Design Notes

- The system is deterministic by default (seeded RNG) but allows seed changes
- State is saved every 10 turns automatically (including tensor weights)
- Episodic memory is bounded to prevent unbounded growth
- All drives are normalized to [0, 1] range each turn
- The simulation can run for thousands of turns without issues
- **Closed-World AI**: The tensor model has no external knowledge - it only learns patterns from interactions within the simulation
- **Hybrid Architecture**: Graph provides structural memory, tensors provide semantic cognition
- **Online Learning**: Updates happen incrementally through experience, not batch training
- **Ideal World Constraint**: System never invents real places, people, or technologies - only abstract concepts

## Why It Used to Get Stuck

Previous versions could get stuck in isolated states where:
- The semantic graph had mostly isolated nodes (no edges forming)
- Outputs degenerated to single-token messages like "Node X stands alone"
- Metrics stayed at 0.00 (coherence, novelty)
- Drives collapsed to extremes and stayed there

### Root Causes

1. **Over-aggressive tokenization**: "now" was filtered as a stopword, and useful short tokens were lost
2. **Insufficient edge creation**: Only adjacent pairs created edges, and single tokens had no connection mechanism
3. **No closed-loop learning**: Generated artifacts weren't fed back into the graph, so the system couldn't self-shape
4. **Sparse graph handling**: When graphs were sparse, agents had no fallback strategies
5. **Drive collapse**: No smoothing mechanism prevented drives from collapsing to 0 or 1

## How It Avoids Isolation Now

### A) Improved Tokenization
- Removed "now" from stopwords (it's meaningful in context)
- Keeps tokens of length >= 2 (not >= 4) to preserve short meaningful words
- Minimal stopword list (only articles, pronouns, very common glue words)

### B) Robust Graph Updates
- **Sliding window edges**: Creates edges for all pairs in windows of size 2-4, not just adjacent pairs
- **Single token handling**: When only one token is present, connects it to recent tokens from episodic memory
- **Weighted edges**: Edge weights decrease with distance in the window

### C) Closed-Loop Learning
- Generated artifacts are tokenized and fed back into the semantic graph
- Artifact learning uses reduced weight (0.3x multiplier) compared to user input
- This allows the system to self-shape and develop patterns autonomously

### D) Lexicon Sprout Mechanism
- When novelty drive is high (>0.6) and graph is sparse (<10 edges)
- Introduces 1-3 tokens from a curated seed lexicon (nature/shape/time/texture words)
- Connects them to recent motifs with small edge weights
- Prevents getting stuck with only a few tokens

### E) Multi-Token Artifacts
- All agents now guarantee minimum 3-4 tokens in output
- Fallback strategies: use episodic memory, generate walks, apply templates
- Never outputs "stands alone" messages (removed from Gardener agent)
- Uses grammar templates and remixing to create structured output

### F) Drive Smoothing
- Per-turn delta caps (max ±0.05) prevent sudden swings
- Drift toward midpoint (0.5) with 0.01 coefficient each turn
- Prevents permanent collapse to extremes
- Drives remain dynamic and responsive

### G) Sparse Graph Handling
- All agents have fallback strategies when graph is empty or sparse
- Use episodic memory tokens when graph edges are unavailable
- Generate minimum-length sequences even from isolated nodes
- Coordinator blends proposals to ensure output quality

## Testing

Run tests with:

```bash
python -m unittest discover tests
```

Tests now verify:
- Tokenization preserves "now" and "help"
- Edge formation from user input
- Artifact processing with reduced weights
- Drive smoothing prevents extremes
- Determinism under fixed seed

## License

This is a demonstration project. Use as you wish.
