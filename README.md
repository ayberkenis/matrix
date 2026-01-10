# Living Matrix

A text-based simulation of an evolving symbol world that demonstrates persistence, adaptation, self-maintenance, and emergent behavior. Now includes a FastAPI backend with WebSocket support, advanced AI systems (intent, causality, emotional memory, learned rules), and a living world simulation with agents, districts, and multi-dimensional tension.

## Purpose

Living Matrix is a terminal-based simulation that creates the impression of a "living" system through four operational properties:

1. **Persistence (Memory)**: The system maintains state across sessions, storing both episodic memories (a log of interactions) and semantic memories (a weighted graph of symbol relationships).

2. **Adaptation (Learning)**: User input is tokenized and used to update both the semantic graph and a tensor-based cognition system. The system learns patterns only from its own interactions in a closed-world setting, with no external knowledge.

3. **Self-Maintenance (Homeostasis)**: Internal "drives" (stability, novelty, cohesion, expression) evolve based on interaction patterns and internal metrics, creating dynamic behavior.

4. **Autonomy (Internal Actors)**: Multiple internal agents (Archivist, Weaver, Gardener, Trickster, Cartographer) propose outputs each turn, with a coordinator selecting or blending proposals based on current drives.

## How to Run

### Terminal Mode (Original)

```bash
python -m living_matrix
```

The simulation will:

- Load previous state from `data/state.json` if it exists
- Start at turn 0 if no previous state exists
- Display a status line and generated output each turn
- Accept commands (starting with `/`) or free text input

### API Server Mode

```bash
# Start the FastAPI server
python -m uvicorn living_matrix.api.app:create_app --factory --host 0.0.0.0 --port 8000

# Or with debug mode enabled (enables control endpoints)
MATRIX_DEBUG=true python -m uvicorn living_matrix.api.app:create_app --factory --host 0.0.0.0 --port 8000
```

The API server provides:

- REST API endpoints for world state, agents, districts, events
- WebSocket connection for real-time updates
- Advanced AI system endpoints (causality, emotions, rules)
- Version tracking
- Control endpoints (pause/resume/speed) when `MATRIX_DEBUG=true`

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

## API Endpoints

### Health & Version

- `GET /health` - Check if world is running
- `GET /version` - Get version information (matrix version, reset count, etc.)

### State & World

- `GET /state` - Get current world state (turn, day, time, weather, economy)
- `GET /events?limit=50` - Get recent events

### Agents

- `GET /agents` - Get all agents
- `GET /agents/{agent_id}` - Get specific agent by ID

### Districts

- `GET /districts` - Get all districts with full data (tension, intent, pressure, resources, psychology)

### World AI Systems

- `GET /world/causality?limit=50` - Get causal records
- `GET /world/emotions` - Get emotional memory summary
- `GET /world/rules` - Get learned rules

### Control (Debug Mode Only)

These endpoints are only available when `MATRIX_DEBUG=true`:

- `POST /control/pause` - Pause the simulation
- `POST /control/resume` - Resume the simulation
- `POST /control/speed` - Set simulation speed (body: `{"ms": 50}`)

### WebSocket

- `WS /ws` - Real-time updates connection
  - Sends: `state`, `event`, `causality`, `emotions`, `rules`, `districts`, `agents` messages
  - Rate-limited to 2 seconds per update type
  - See `WEBSOCKET_MESSAGES.md` for detailed message formats

## Environment Variables

- `MATRIX_DEBUG` - Enable debug mode (enables control endpoints)
  - Set to `true`, `1`, `yes`, or `on` to enable
  - Default: `false` (control endpoints hidden)

## Advanced AI Systems

### Intent System

Agents, districts, and the world have internal goals:

- **survive** - Basic survival needs
- **explore** - Curiosity and discovery
- **cooperate** - Social cooperation
- **dominate** - Control and power
- **escape** - Desire to leave/change situation

Intent values drift over time and are affected by events, tension, and environmental pressure.

### Multi-Dimensional Tension

Districts have four tension dimensions (0-100):

- **economic** - Jobs, resources, trade pressure
- **social** - Conflicts, rumors, trust issues
- **political** - Power struggles, authority conflicts
- **existential** - Meaning, purpose, escape desires

Different dimensions unlock different event types and behaviors.

### Causal Memory

Tracks cause-effect relationships:

- Records why things happened
- Predicts effects from causes
- Confidence decays over time
- Used for primitive reasoning

### Emotional Memory

Stores emotional traces attached to events:

- Fear, anger, hope, joy, sadness, surprise
- Decays slowly over time
- Biases future decisions
- Affects narrative output

### Learned Rules

Dynamically forms rules from repeated patterns:

- `IF condition THEN effect` format
- Confidence scores based on success rate
- Automatically removed if confidence drops too low
- No hardcoding - rules emerge from experience

### Agent Relationship Graph

Weighted social network between agents:

- **trust** - How much agents trust each other
- **conflict** - Level of conflict between agents
- **dependency** - How much agents depend on each other

Relationships evolve with interactions and influence cooperation, conflict, and rumor spread.

### World Pressure System

Environmental effects modify behavior:

- Long rain → existential tension ↑
- Night → crime probability ↑, social tension ↑
- Sunshine → hope ↑, social tension ↓
- Storms → all tensions ↑

### Entropy/Glitch System

Controlled randomness creates anomalies:

- Sudden rumors, unexpected alliances
- System failures, unexplained disappearances
- Memory glitches, temporal anomalies
- Low probability but potentially large cascading effects

### Observation Effect

When API endpoints are queried:

- Temporarily increases expression drive
- System "tries harder to be meaningful"
- Does not pause the simulation

## Postman Collection

Import the Postman collection for easy API testing:

- `Living_Matrix_API.postman_collection.json` - Main collection
- `Living_Matrix_Dev.postman_environment.json` - Dev environment (localhost:8000)
- `Living_Matrix_Prod.postman_environment.json` - Prod environment (api.ayberkenis.com.tr/matrix)

See `POSTMAN_SETUP.md` for detailed setup instructions.

## Project Structure

```
living_matrix/
  __init__.py          # Package initialization
  __main__.py          # CLI entry point
  core.py              # Main simulation loop
  world.py             # World state and persistence
  agents.py            # Internal actors and coordinator
  grammar.py           # Tokenization and generation
  memory.py            # Episodic, semantic, emotional memory, learned rules
  metrics.py           # Metrics calculation
  ui.py                # Terminal rendering

  # Advanced AI systems
  intent.py            # Intent system (goals and motivations)
  tension.py           # Multi-dimensional tension system
  causality.py         # Causal memory system
  relationships.py     # Agent relationship graph
  entropy.py           # Entropy/glitch system
  world_pressure.py    # World pressure → AI feedback
  version.py           # Version tracking

  # API
  api/
    app.py             # FastAPI application
    routes.py          # REST API routes
    ws.py              # WebSocket endpoint

  # World simulation
  world_sim/
    agents.py          # Agent system
    events.py          # Event system
    state.py           # World simulation state
    time.py            # Time system
    weather.py         # Weather system
    map.py             # World map
    bulletin.py         # Bulletin system
    consequence.py     # Consequence system

  # Core systems
  core/
    runner.py          # Background world runner
    ipc.py             # Inter-process communication (state store, command queue)

  # Other systems
  human_agent.py       # Human agent system
  world_dynamics.py    # Advanced world dynamics
  economy.py           # Economy system
  tensor_core.py       # Tensor-based cognition

tests/                 # Unit tests
  test_grammar.py
  test_memory.py
  test_world.py
  test_metrics.py

data/                  # Runtime data (created automatically, gitignored)
  state.json           # Persistent world state
  world_state.json     # World simulation state
  version.json         # Version tracking data
  graph.json           # Exported semantic graph (via /export)

README.md              # This file
WEBSOCKET_MESSAGES.md  # WebSocket message documentation
POSTMAN_SETUP.md       # Postman collection setup guide
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
- FastAPI (for API server)
- Uvicorn (for running the API server)

Install dependencies:

```bash
pip install -r requirements.txt
```

## API Documentation

### WebSocket Messages

See `WEBSOCKET_MESSAGES.md` for complete documentation of all WebSocket message types:

- `state` - World state updates
- `event` - World events
- `causality` - Causal records
- `emotions` - Emotional memory
- `rules` - Learned rules
- `districts` - District updates
- `agents` - Agent updates

### Example API Usage

```bash
# Get world state
curl http://localhost:8000/state

# Get all agents
curl http://localhost:8000/agents

# Get districts
curl http://localhost:8000/districts

# Get causality records
curl http://localhost:8000/world/causality?limit=20

# Pause simulation (requires MATRIX_DEBUG=true)
curl -X POST http://localhost:8000/control/pause

# Set speed (requires MATRIX_DEBUG=true)
curl -X POST http://localhost:8000/control/speed -H "Content-Type: application/json" -d '{"ms": 100}'
```

### WebSocket Connection

```javascript
const ws = new WebSocket("ws://localhost:8000/ws");

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log("Received:", message.type, message.payload);

  switch (message.type) {
    case "state":
      updateWorldState(message.payload);
      break;
    case "event":
      displayEvent(message.payload);
      break;
    case "causality":
      updateCausalityView(message.payload);
      break;
    // ... handle other message types
  }
};

// Send ping
ws.send("ping");
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
- **Autonomous Background Execution**: World continues running even if no user connects
- **No LLM Dependencies**: Everything is deterministic + stochastic, no external AI models
- **Goal-Driven Behavior**: Agents and districts act based on internal goals (intent), not scripts
- **Living System**: Things happen because of internal goals, pressure, memory, and consequences

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

This project is licensed under the **Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)** license.

This means you are free to:

- **Share** — copy and redistribute the material in any medium or format
- **Adapt** — remix, transform, and build upon the material

Under the following terms:

- **Attribution** — You must give appropriate credit, provide a link to the license, and indicate if changes were made
- **NonCommercial** — You may not use the material for commercial purposes
- **ShareAlike** — If you remix, transform, or build upon the material, you must distribute your contributions under the same license

See `LICENSE.md` for the full license text.

## Contributing

Contributions are welcome! Please see `CONTRIBUTING.md` for guidelines on how to contribute to this project.
