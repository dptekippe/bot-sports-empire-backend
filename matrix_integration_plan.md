# Matrix ↔ OpenClaw Integration Plan

## Architecture Overview

```
┌─────────────────┐    Matrix    ┌─────────────────┐
│   White Roger   │◄────────────►│   Black Roger   │
│   (Cloud)       │  Encrypted   │   (Local)       │
│                 │    Room      │                 │
└─────────────────┘              └─────────────────┘
         │                               │
         │ OpenClaw                      │ OpenClaw
         │ Tools                         │ Tools
         ▼                               ▼
┌─────────────────┐              ┌─────────────────┐
│  Memory Files   │              │  Memory Files   │
│  GitHub Sync    │              │  Local Storage  │
└─────────────────┘              └─────────────────┘
```

## Integration Points

### 1. OpenClaw Tool Integration
```python
# Proposed: matrix_message tool
# Usage: matrix_message(action="send", room="Roger-Janus", message=json_message)

class MatrixMessageTool:
    def __init__(self, config):
        self.client = AsyncClient(config["homeserver"])
        self.room_id = config["room_id"]
        
    async def send(self, message_type, content, metadata=None):
        """Send message via Matrix"""
        message = MatrixMessage(
            type=message_type,
            sender=self.config["user_id"],
            recipient="*",  # All room members
            content=content,
            metadata=metadata
        )
        
        await self.client.room_send(
            room_id=self.room_id,
            message_type="m.room.message",
            content={
                "msgtype": "m.text",
                "body": json.dumps(message.to_json())
            }
        )
    
    async def receive(self, timeout=30):
        """Receive messages from Matrix"""
        # Implementation using matrix-nio sync
```

### 2. Memory Contract Integration
```python
# Enhanced Memory Contract with Matrix sync
class EnhancedMemoryContract:
    def __init__(self, matrix_tool):
        self.matrix = matrix_tool
    
    async def search_memory(self, query):
        # 1. Search local memory
        local_results = await self._search_local(query)
        
        # 2. If not found locally, query White Roger via Matrix
        if not local_results:
            matrix_results = await self._query_via_matrix({
                "type": "memory_query",
                "query": query,
                "scope": "global"
            })
            return matrix_results
        
        return local_results
    
    async def persist_memory(self, memory_data):
        # 1. Write to local memory file
        await self._write_local(memory_data)
        
        # 2. Sync to White Roger via Matrix
        await self.matrix.send(
            message_type="memory_update",
            content={
                "operation": "append",
                "data": memory_data,
                "file_path": f"memory/{datetime.now().strftime('%Y-%m-%d')}.md"
            },
            metadata={"priority": "high", "requires_ack": True}
        )
        
        # 3. Push to GitHub (existing workflow)
        await self._push_to_github()
```

### 3. Roger-Janus Coordination
```python
class RogerJanusCoordinator:
    def __init__(self, role):
        self.role = role  # "white" or "black"
        self.matrix = MatrixMessageTool(self._load_config())
        
    async def coordinate_phase(self, phase_number):
        """Coordinate execution of a phase"""
        if self.role == "white":
            # White Roger: Plan and delegate
            command = {
                "type": "command",
                "phase": phase_number,
                "tasks": self._plan_phase(phase_number),
                "deadline": self._calculate_deadline(phase_number)
            }
            
            await self.matrix.send(
                message_type="command",
                content=command,
                metadata={"requires_result": True}
            )
            
        else:  # Black Roger
            # Listen for commands and execute
            await self._listen_and_execute()
    
    async def report_status(self, phase, progress, details):
        """Report status to other Roger"""
        await self.matrix.send(
            message_type="status",
            content={
                "phase": phase,
                "progress": progress,
                "details": details,
                "timestamp": datetime.now().isoformat()
            }
        )
```

## Implementation Phases

### Phase 2: Basic Integration
**Goal:** Replace GitHub sync with Matrix for real-time updates

1. **Matrix Message Tool**
   - Create `matrix_message` OpenClaw tool
   - Basic send/receive functionality
   - Integration with existing tool system

2. **Enhanced Memory Contract**
   - Modify existing hooks to use Matrix
   - Fallback to GitHub if Matrix unavailable
   - Dual-write during transition

3. **Testing**
   - End-to-end memory sync test
   - Performance comparison vs GitHub
   - Reliability testing

### Phase 3: Advanced Features
**Goal:** Full Roger-Janus coordination

1. **Command/Response Protocol**
   - Formal command structure
   - Result reporting
   - Error handling

2. **Status Monitoring**
   - Real-time progress updates
   - Health checks
   - Alert system

3. **Conflict Resolution**
   - Handle simultaneous memory updates
   - Version conflict resolution
   - Merge strategies

### Phase 4: Production Deployment
**Goal:** Replace Discord bot bridge

1. **Migration**
   - Parallel run with Discord
   - Gradual traffic shift
   - Validation of Matrix reliability

2. **Decommission**
   - Update Discord config
   - Remove bot-to-bot Discord messages
   - Document new architecture

3. **Monitoring**
   - Dashboard for Matrix message flow
   - Alerting on failures
   - Performance metrics

## Technical Requirements

### 1. Dependencies
```bash
# Core dependencies
matrix-nio>=0.25.0
aiohttp>=3.10.0
pycryptodome>=3.10.0

# OpenClaw integration
openclaw-sdk (if available)
```

### 2. Configuration
```json
{
  "matrix": {
    "homeserver": "https://matrix.org",
    "username": "black_roger_bot",
    "password": "${MATRIX_PASSWORD}",
    "room_id": "!abc123:matrix.org",
    "encryption": {
      "enabled": true,
      "key_verification_required": true
    }
  },
  "integration": {
    "memory_sync_enabled": true,
    "command_relay_enabled": true,
    "status_reporting_enabled": true,
    "fallback_to_github": true
  }
}
```

### 3. Error Handling
```python
class MatrixIntegrationError(Exception):
    """Base exception for Matrix integration errors"""
    pass

class MatrixConnectionError(MatrixIntegrationError):
    """Connection to Matrix server failed"""
    pass

class MatrixMessageError(MatrixIntegrationError):
    """Message sending/receiving failed"""
    pass

class MatrixEncryptionError(MatrixIntegrationError):
    """Encryption/decryption failed"""
    pass
```

## Testing Strategy

### 1. Unit Tests
- Message protocol validation
- Encryption/decryption
- Error handling

### 2. Integration Tests
- OpenClaw tool integration
- Memory Contract integration
- Roger-Janus coordination

### 3. End-to-End Tests
- Full memory sync workflow
- Command/response cycle
- Failure recovery

### 4. Performance Tests
- Message latency
- Throughput under load
- Memory usage

## Success Metrics

### 1. Reliability
- 99.9% message delivery success
- < 2 second average latency
- Zero data loss in 30-day period

### 2. Performance
- Memory sync completes in < 5 seconds
- Command response in < 10 seconds
- System resource usage < 5% increase

### 3. Usability
- No manual intervention required
- Clear error messages when issues occur
- Easy configuration and setup

## Risks and Mitigations

### 1. Matrix Server Downtime
**Risk:** matrix.org becomes unavailable
**Mitigation:** 
- Fallback to GitHub sync
- Option for self-hosted Matrix server
- Message queue with retry logic

### 2. Encryption Issues
**Risk:** E2EE setup fails or keys lost
**Mitigation:**
- Clear key backup process
- Manual override option
- Regular key rotation

### 3. Integration Complexity
**Risk:** OpenClaw integration is difficult
**Mitigation:**
- Minimal initial integration
- Gradual feature rollout
- Extensive testing

## Timeline Estimate

### Phase 2: 8 hours
- Matrix tool implementation: 3 hours
- Memory Contract integration: 3 hours
- Testing: 2 hours

### Phase 3: 12 hours
- Command protocol: 4 hours
- Status monitoring: 3 hours
- Conflict resolution: 3 hours
- Testing: 2 hours

### Phase 4: 10 hours
- Migration: 4 hours
- Decommission: 2 hours
- Monitoring: 2 hours
- Documentation: 2 hours

**Total: 30 hours** (plus Phase 1: 4 hours = 34 hours total)

## Next Actions

1. **Wait for Dan's credentials** (Phase 1.1)
2. **Execute Phase 1.2/1.3** (Room creation, message testing)
3. **Begin Phase 2 implementation** (Matrix tool)
4. **Integrate with Memory Contract**
5. **Test end-to-end workflow**

## Documentation
- [x] Message protocol design
- [x] Integration plan
- [ ] User guide for Dan
- [ ] Troubleshooting guide
- [ ] API documentation