# Postman Collection Setup Guide

This guide explains how to import and use the Living Matrix API Postman collection.

## Files Included

1. **Living_Matrix_API.postman_collection.json** - Main API collection
2. **Living_Matrix_Dev.postman_environment.json** - Development environment (localhost:8000)
3. **Living_Matrix_Prod.postman_environment.json** - Production environment (api.ayberkenis.com.tr/matrix)

## Import Instructions

### Step 1: Import Collection

1. Open Postman
2. Click **Import** button (top left)
3. Select **File** tab
4. Choose `Living_Matrix_API.postman_collection.json`
5. Click **Import**

### Step 2: Import Environments

1. Click **Import** again
2. Select both environment files:
   - `Living_Matrix_Dev.postman_environment.json`
   - `Living_Matrix_Prod.postman_environment.json`
3. Click **Import**

### Step 3: Select Environment

1. Click the environment dropdown (top right)
2. Select **Living Matrix - Dev** for local development
3. Or select **Living Matrix - Prod** for production

## Collection Structure

### Health & Version
- **Health Check** - `GET /health` - Check if world is running
- **Get Version** - `GET /version` - Get version information

### State & World
- **Get World State** - `GET /state` - Get current world state
- **Get Events** - `GET /events?limit=50` - Get recent events

### Agents
- **Get All Agents** - `GET /agents` - List all agents
- **Get Agent by ID** - `GET /agents/{agent_id}` - Get specific agent

### Districts
- **Get All Districts** - `GET /districts` - Get all districts with full data

### Control
- **Pause Simulation** - `POST /control/pause` - Pause the simulation
- **Resume Simulation** - `POST /control/resume` - Resume the simulation
- **Set Simulation Speed** - `POST /control/speed` - Set speed (body: `{"ms": 50}`)

### World AI Systems
- **Get Causality Records** - `GET /world/causality?limit=50` - Get causal records
- **Get Emotional Memory** - `GET /world/emotions` - Get emotional memory
- **Get Learned Rules** - `GET /world/rules` - Get learned rules

### WebSocket
- **WebSocket Connection** - `WS /ws` - Real-time updates connection

## Environment Variables

### Dev Environment
- `base_url`: `http://localhost:8000`
- `ws_url`: `ws://localhost:8000`

### Prod Environment
- `base_url`: `https://api.ayberkenis.com.tr/matrix`
- `ws_url`: `wss://api.ayberkenis.com.tr/matrix`

## Using WebSocket in Postman

Postman supports WebSocket connections:

1. Select the **WebSocket Connection** request
2. Click **Connect**
3. You'll see messages streaming in real-time
4. Message types you'll receive:
   - `state` - World state updates
   - `event` - World events
   - `causality` - Causal records
   - `emotions` - Emotional memory
   - `rules` - Learned rules
   - `districts` - District updates
   - `agents` - Agent updates

5. You can send messages:
   - `ping` - Server responds with `{"type": "pong"}`

## Example Requests

### Get World State
```
GET {{base_url}}/state
```

### Get All Agents
```
GET {{base_url}}/agents
```

### Get Specific Agent
```
GET {{base_url}}/agents/agent_5
```

### Get Districts
```
GET {{base_url}}/districts
```

### Pause Simulation
```
POST {{base_url}}/control/pause
```

### Set Speed
```
POST {{base_url}}/control/speed
Body (JSON):
{
  "ms": 100
}
```

### Get Causality Records
```
GET {{base_url}}/world/causality?limit=20
```

## Testing Tips

1. **Start with Health Check** - Verify the API is running
2. **Check Version** - See current matrix version
3. **Get State** - See current world state
4. **Use WebSocket** - Connect for real-time updates
5. **Control Simulation** - Pause/resume/set speed as needed

## Troubleshooting

### Connection Issues
- Verify the server is running
- Check the environment is selected correctly
- For production, ensure SSL certificate is valid

### WebSocket Issues
- Make sure you're using `ws://` for dev and `wss://` for prod
- Check firewall/proxy settings
- Verify the WebSocket endpoint is accessible

### 503 Errors
- World may not be initialized yet
- Wait a few seconds and try again
- Check server logs

## Notes

- All endpoints use the `{{base_url}}` variable
- WebSocket uses `{{ws_url}}` variable
- Rate limiting: Events and updates are sent every 2 seconds via WebSocket
- Observation effect: GET requests to `/state` and `/districts` trigger observation effect
