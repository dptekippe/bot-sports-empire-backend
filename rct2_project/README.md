# RCT2 RL Environment - Action Execution Implementation

## Overview

This document describes the implementation of action execution for the RCT2 RL environment, specifically focused on the `ridedemolish` action as a proof-of-concept.

## Architecture

```
Python Client (rct2_client.py)
        |
        v
TCP Connection (port 11752)
        |
        v
zmq_bridge.js (OpenRCT2 Plugin)
        |
        v
OpenRCT2 Game (Sweltering Heights scenario)
```

## Files Created

| File | Description |
|------|-------------|
| `rct2_project/zmq_bridge.js` | OpenRCT2 plugin that handles JSON-RPC over TCP |
| `rct2_client.py` | Full Python client with RCT2Client class |
| `rct2_action_tester.py` | Simple action tester script |
| `rct2_demolish_test.py` | Demolish action parameter format tester |
| `rct2_env.py` | Minimal Gymnasium-style RL environment wrapper |

## Message Protocol

### Request Format
```json
{"action": "action_name", "param1": value1, "param2": value2}
```

### Response Format
```json
{"status": "ok", "result": {"error": 0, "cost": 0, ...}}
```
or
```json
{"status": "error", "error": 1, "errorTitle": "...", "errorMessage": "..."}
```

## Implemented Actions

### Special Actions (Read-Only Queries)
These are handled specially by zmq_bridge.js and return early without calling `executeAction`:

| Action | Parameters | Description |
|--------|------------|-------------|
| `get_ride_info` | none | Returns list of all rides with details |
| `get_surface_height` | `x`, `y` | Returns terrain height at tile coordinates |
| `check_area_owned` | `x1`, `y1`, `x2`, `y2` | Checks if area is owned by park |

### Game Actions (executeAction passthrough)
All other actions are passed to OpenRCT2's `context.executeAction()`:

| Action | Parameters | Description |
|--------|------------|-------------|
| `pausetoggle` | none | Toggle game pause state |
| `ridedemolish` | `rideId` (or `id`) | Demolish a ride by ID |

## Testing the Demolish Action

### Quick Test
```bash
python rct2_action_tester.py
```

### Parameter Format Testing
```bash
python rct2_demolish_test.py
```

### Full RL Loop Test
```python
from rct2_env import RCT2Env

env = RCT2Env()
obs = env.reset()

# Demolish first ride
rides = obs['rides']
if rides:
    action = {"type": "demolish", "ride_id": rides[0]['id']}
    next_obs, reward, done, info = env.step(action)
    print(f"Reward: {reward}")

env.close()
```

## Key Findings

### Parameter Name Issue
OpenRCT2's `ridedemolish` action expects the ride ID as `id`, not `rideId`. The correct format is:
```json
{"action": "ridedemolish", "id": 0}
```

### Error Codes
- `error: 0` - Action succeeded
- `error: 1` - Action failed (generic)
- Other codes may indicate specific failures (no money, not owner, etc.)

### State API (Port 8081)
The user mentioned a State API on port 8081, but this is separate from the zmq_bridge (port 11752). The State API would provide park metrics (rating, cash, guests), while zmq_bridge provides ride information and action execution.

## Next Steps

1. **Verify demolish action** - Run the test scripts with OpenRCT2 running
2. **Add park metrics** - Implement `get_park_info` special action for state observation
3. **Expand action space** - Add more actions like `ridecreate`, `ridesetstatus`
4. **Implement reward function** - Connect park metrics to RL reward signal
5. **State API integration** - Connect to port 8081 for comprehensive state

## Installation

1. Copy `zmq_bridge.js` to OpenRCT2 plugin directory:
   - macOS: `~/Library/Application Support/OpenRCT2/plugin/`
   - Linux: `~/.config/OpenRCT2/plugin/`
   - Windows: `%APPDATA%\OpenRCT2\plugin\`

2. Start OpenRCT2 with the Sweltering Heights scenario

3. Run the Python test scripts:
   ```bash
   python rct2_action_tester.py
   ```

## Troubleshooting

### Connection Refused
- Verify OpenRCT2 is running with the plugin loaded
- Check the plugin console for "JSON Action Bridge: Server listening on port 11752"

### Action Returns Error
- Check OpenRCT2 console for detailed error messages
- Verify the ride ID exists
- Ensure game is not paused (some actions require unpaused game)

### Empty Response
- The connection may have been closed
- Check network connectivity
- Verify firewall settings