# WebSocket Message Examples

This document describes the WebSocket message types sent by the Living Matrix API.

All messages follow the format:

```json
{
  "type": "message_type",
  "payload": { ... }
}
```

## Message Types

### 1. `state` - World State Update

Sent when the world state changes (turn, day, time, weather, economy).

**Example:**

```json
{
  "type": "state",
  "payload": {
    "turn": 26130,
    "day": 15,
    "time": "14:30",
    "weather": "Clear skies, light breeze",
    "economy": {
      "total_food": 245.5,
      "total_credits": 1200.0,
      "average_tension": 35.2,
      "global_tension_index": 0.35,
      "district_count": 3,
      "hotspots": [
        { "district": "Central", "tension": 45.2 },
        { "district": "North", "tension": 38.5 }
      ],
      "active_events": ["food_shortage_wave", "trade_success"],
      "system_health": {
        "stability": "stable",
        "risk_level": "moderate"
      }
    }
  }
}
```

### 2. `event` - World Event

Sent when a new event occurs in the world (rate-limited to one per 2 seconds).

**Example:**

```json
{
  "type": "event",
  "payload": {
    "agent_id": "agent_5",
    "description": "AriKora trades for food at Market Square",
    "type": "market_trade",
    "turn": 26130
  }
}
```

### 3. `causality` - Causal Record Update

Sent when new causal records are created (rate-limited to one per 2 seconds).

**Example:**

```json
{
  "type": "causality",
  "payload": {
    "new_records": [
      {
        "cause": "event:food_shortage_wave",
        "effect": "Social tension increased in Central district",
        "confidence": 0.65,
        "duration": 3,
        "source": "region_central",
        "turn": 26128,
        "timestamp": "2024-01-15T14:30:00.123456"
      },
      {
        "cause": "event:aid_distribution",
        "effect": "Cooperation increased, trust improved",
        "confidence": 0.72,
        "duration": 1,
        "source": "region_north",
        "turn": 26129,
        "timestamp": "2024-01-15T14:30:15.234567"
      }
    ],
    "total_records": 142
  }
}
```

### 4. `emotions` - Emotional Memory Update

Sent when emotional memory summary changes (rate-limited to one per 2 seconds).

**Example:**

```json
{
  "type": "emotions",
  "payload": {
    "summary": {
      "fear": 0.15,
      "anger": 0.08,
      "hope": 0.22,
      "joy": 0.12,
      "sadness": 0.1,
      "surprise": 0.05
    },
    "recent_traces": [
      {
        "event": "Aid shipment arrives in Central district",
        "turn": 26128,
        "timestamp": "2024-01-15T14:29:45.123456",
        "fear": 0.0,
        "anger": 0.0,
        "hope": 0.4,
        "joy": 0.3,
        "sadness": 0.0,
        "surprise": 0.1,
        "dominant": "hope"
      },
      {
        "event": "Food shortage reported in North district",
        "turn": 26127,
        "timestamp": "2024-01-15T14:29:30.123456",
        "fear": 0.5,
        "anger": 0.2,
        "hope": -0.1,
        "joy": 0.0,
        "sadness": 0.3,
        "surprise": 0.1,
        "dominant": "fear"
      }
    ]
  }
}
```

### 5. `rules` - Learned Rules Update

Sent when new rules are learned (rate-limited to one per 2 seconds).

**Example:**

```json
{
  "type": "rules",
  "payload": {
    "new_rules": [
      {
        "condition": "food < 5 AND weather == 'rain'",
        "effect": "social_tension += 0.3",
        "confidence": 0.68,
        "matches": 12,
        "failures": 3,
        "turn_created": 26100,
        "last_matched": 26128,
        "success_rate": 0.8
      },
      {
        "condition": "economic_tension > 70",
        "effect": "escape_intent += 0.15",
        "confidence": 0.55,
        "matches": 8,
        "failures": 4,
        "turn_created": 26110,
        "last_matched": 26127,
        "success_rate": 0.67
      }
    ],
    "total_rules": 15
  }
}
```

### 6. `districts` - District Complete Update

Sent when any district data changes (tension, intent, pressure, resources, psychology) - rate-limited to one per 2 seconds.

**Example:**

```json
{
  "type": "districts",
  "payload": {
    "districts": [
      {
        "id": "region_central",
        "name": "Central",
        "tension": 30.25,
        "tension_multi": {
          "economic": 42.5,
          "social": 38.2,
          "political": 25.0,
          "existential": 15.3,
          "total": 121.0,
          "average": 30.25,
          "max_dimension": "economic"
        },
        "tension_trend": "increasing",
        "intent": {
          "survive": 0.65,
          "explore": 0.25,
          "cooperate": 0.45,
          "dominate": 0.15,
          "escape": 0.12
        },
        "pressure": {
          "food": 0.65,
          "jobs": 0.45,
          "weather": 0.2,
          "migration": 0.15,
          "rumor": 0.3,
          "inequality": 0.25
        },
        "resources": {
          "food_stock": 35.5,
          "jobs_available": 4
        },
        "psychology": {
          "trust": 0.45,
          "trauma": 0.25,
          "fatigue": 0.35
        },
        "risk_flags": ["high_food_pressure", "rising_social_tension"],
        "recent_events": [
          {
            "type": "food_shortage_wave",
            "severity": 0.65,
            "turn": 26128
          },
          {
            "type": "trade_success",
            "severity": 0.3,
            "turn": 26129
          }
        ]
      },
      {
        "id": "region_north",
        "name": "North",
        "tension": 20.125,
        "tension_multi": {
          "economic": 28.0,
          "social": 22.5,
          "political": 18.0,
          "existential": 12.0,
          "total": 80.5,
          "average": 20.125,
          "max_dimension": "economic"
        },
        "tension_trend": "stable",
        "intent": {
          "survive": 0.45,
          "explore": 0.35,
          "cooperate": 0.55,
          "dominate": 0.1,
          "escape": 0.08
        },
        "pressure": {
          "food": 0.3,
          "jobs": 0.25,
          "weather": 0.15,
          "migration": 0.1,
          "rumor": 0.2,
          "inequality": 0.15
        },
        "resources": {
          "food_stock": 58.2,
          "jobs_available": 6
        },
        "psychology": {
          "trust": 0.65,
          "trauma": 0.1,
          "fatigue": 0.2
        },
        "risk_flags": [],
        "recent_events": [
          {
            "type": "aid_distribution",
            "severity": 0.4,
            "turn": 26128
          }
        ]
      }
    ]
  }
}
```

### 7. `agents` - Agent Intent & Relationships Update

Sent when agent intents or relationships change (rate-limited to one per 2 seconds, limited to first 10 agents).

**Example:**

```json
{
  "type": "agents",
  "payload": {
    "agents": [
      {
        "id": "agent_5",
        "name": "AriKora",
        "intent": {
          "survive": 0.55,
          "explore": 0.3,
          "cooperate": 0.5,
          "dominate": 0.2,
          "escape": 0.1
        },
        "relationships": {
          "allies": [
            { "id": "agent_12", "trust": 0.75 },
            { "id": "agent_8", "trust": 0.68 }
          ],
          "enemies": [{ "id": "agent_3", "conflict": 0.65 }],
          "dependents": [{ "id": "agent_12", "dependency": 0.45 }]
        }
      },
      {
        "id": "agent_12",
        "name": "VexLume",
        "intent": {
          "survive": 0.6,
          "explore": 0.25,
          "cooperate": 0.65,
          "dominate": 0.15,
          "escape": 0.08
        },
        "relationships": {
          "allies": [
            { "id": "agent_5", "trust": 0.75 },
            { "id": "agent_8", "trust": 0.6 }
          ],
          "enemies": [],
          "dependents": [{ "id": "agent_5", "dependency": 0.4 }]
        }
      }
    ]
  }
}
```

## Rate Limiting

All update types (except `state`) are rate-limited to **one message per 2 seconds** to prevent overwhelming the client. The system uses a round-robin approach, sending one type of update per interval.

## Initial Snapshot

On connection, a full `state` message is sent immediately with complete data:

- All districts with full details
- All agents with full details
- Recent events
- Current economy state

## Client Messages

Clients can send:

- `"ping"` - Server responds with `{"type": "pong"}`

## Connection

Connect to: `ws://localhost:8000/ws`

Example JavaScript:

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
    case "emotions":
      updateEmotionsChart(message.payload);
      break;
    case "rules":
      updateRulesList(message.payload);
      break;
    case "districts":
      updateDistrictTensions(message.payload);
      break;
    case "agents":
      updateAgentIntents(message.payload);
      break;
  }
};
```
