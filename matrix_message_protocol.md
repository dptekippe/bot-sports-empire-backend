# Matrix Message Protocol for Roger-to-Roger Communication

## Overview
Protocol for secure, reliable message exchange between White Roger and Black Roger via Matrix.

## Message Types

### 1. Text Message
```json
{
  "type": "text",
  "version": "1.0",
  "timestamp": "2026-03-07T12:00:00Z",
  "sender": "@white_roger_bot:matrix.org",
  "recipient": "@black_roger_bot:matrix.org",
  "content": {
    "body": "Hello from White Roger",
    "format": "plaintext"
  },
  "metadata": {
    "priority": "normal",
    "requires_ack": true,
    "message_id": "msg_1234567890"
  }
}
```

### 2. Memory Update
```json
{
  "type": "memory_update",
  "version": "1.0",
  "timestamp": "2026-03-07T12:00:00Z",
  "sender": "@black_roger_bot:matrix.org",
  "recipient": "@white_roger_bot:matrix.org",
  "content": {
    "memory_type": "daily",
    "file_path": "memory/2026-03-07.md",
    "operation": "append",
    "data": "## New memory entry\n- Something happened",
    "checksum": "sha256:abc123..."
  },
  "metadata": {
    "priority": "high",
    "requires_ack": true,
    "sync_required": true,
    "message_id": "mem_1234567890"
  }
}
```

### 3. Command Message
```json
{
  "type": "command",
  "version": "1.0",
  "timestamp": "2026-03-07T12:00:00Z",
  "sender": "@white_roger_bot:matrix.org",
  "recipient": "@black_roger_bot:matrix.org",
  "content": {
    "command": "execute_phase",
    "parameters": {
      "phase": "1.2",
      "action": "create_room"
    },
    "timeout_seconds": 300
  },
  "metadata": {
    "priority": "high",
    "requires_ack": true,
    "requires_result": true,
    "message_id": "cmd_1234567890"
  }
}
```

### 4. Status Update
```json
{
  "type": "status",
  "version": "1.0",
  "timestamp": "2026-03-07T12:00:00Z",
  "sender": "@black_roger_bot:matrix.org",
  "recipient": "@white_roger_bot:matrix.org",
  "content": {
    "status": "in_progress",
    "phase": "1.2",
    "progress": 75,
    "details": "Room creation script ready, waiting for credentials",
    "errors": []
  },
  "metadata": {
    "priority": "normal",
    "requires_ack": false,
    "message_id": "sta_1234567890"
  }
}
```

### 5. Acknowledgment
```json
{
  "type": "ack",
  "version": "1.0",
  "timestamp": "2026-03-07T12:00:00Z",
  "sender": "@white_roger_bot:matrix.org",
  "recipient": "@black_roger_bot:matrix.org",
  "content": {
    "original_message_id": "cmd_1234567890",
    "status": "received",
    "processed_at": "2026-03-07T12:00:05Z"
  },
  "metadata": {
    "priority": "low",
    "requires_ack": false,
    "message_id": "ack_1234567890"
  }
}
```

## Protocol Rules

### 1. Message ID Generation
- Format: `{type_prefix}_{timestamp}_{random}`
- Type prefixes: `msg_`, `mem_`, `cmd_`, `sta_`, `ack_`
- Must be unique per sender

### 2. Acknowledgment Requirements
- `requires_ack: true` → Recipient must send ack within 30 seconds
- `requires_result: true` → Recipient must send result message
- Missing acks trigger retry logic

### 3. Priority Levels
- `critical`: Immediate processing, retry every 10 seconds
- `high`: Process within 60 seconds, retry every 30 seconds  
- `normal`: Process within 5 minutes, retry every 2 minutes
- `low`: Process when possible, no retry

### 4. Retry Logic
- Max 3 retries per message
- Exponential backoff: 10s, 30s, 90s
- After max retries: log error, notify sender

### 5. Message Validation
All messages must:
1. Have valid JSON schema
2. Include required fields
3. Have valid timestamp (not in future, not too old)
4. Pass checksum verification (for memory updates)

## Implementation Notes

### Python Classes
```python
class MatrixMessage:
    def __init__(self, msg_type, sender, recipient, content, metadata=None):
        self.type = msg_type
        self.version = "1.0"
        self.timestamp = datetime.utcnow().isoformat() + "Z"
        self.sender = sender
        self.recipient = recipient
        self.content = content
        self.metadata = metadata or {}
        self.message_id = self._generate_id()
    
    def to_json(self):
        return {
            "type": self.type,
            "version": self.version,
            "timestamp": self.timestamp,
            "sender": self.sender,
            "recipient": self.recipient,
            "content": self.content,
            "metadata": self.metadata,
            "message_id": self.message_id
        }
    
    def _generate_id(self):
        prefix = {"text": "msg", "memory": "mem", "command": "cmd", 
                 "status": "sta", "ack": "ack"}[self.type]
        random_str = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8))
        return f"{prefix}_{int(time.time())}_{random_str}"
```

### Message Handler
```python
class MatrixMessageHandler:
    async def handle_message(self, raw_message):
        # Validate JSON
        message = self._validate_message(raw_message)
        
        # Route by type
        handlers = {
            "text": self._handle_text,
            "memory_update": self._handle_memory_update,
            "command": self._handle_command,
            "status": self._handle_status,
            "ack": self._handle_ack
        }
        
        handler = handlers.get(message["type"])
        if handler:
            await handler(message)
        else:
            await self._handle_unknown(message)
    
    async def send_message(self, message_obj):
        # Convert to JSON
        json_msg = message_obj.to_json()
        
        # Send via Matrix
        await self.matrix_client.room_send(
            room_id=self.room_id,
            message_type="m.room.message",
            content={
                "msgtype": "m.text",
                "body": json.dumps(json_msg),
                "format": "org.matrix.custom.json",
                "formatted_body": f"<pre><code>{json.dumps(json_msg, indent=2)}</code></pre>"
            }
        )
```

## Security Considerations

### 1. Encryption
- All rooms use end-to-end encryption (E2EE)
- Key verification required for first session
- Regular key rotation recommended

### 2. Authentication
- Validate sender matches claimed Matrix ID
- Reject messages from unauthorized users
- Log all message origins

### 3. Data Integrity
- Checksums for memory updates
- Timestamp validation
- Message ID uniqueness checking

## Testing Protocol

### Phase 1.3 Test Cases
1. **Basic text exchange**: White → Black → White
2. **Memory update**: Black sends memory, White acknowledges
3. **Command execution**: White sends command, Black executes and reports
4. **Error handling**: Malformed messages, timeouts, retries
5. **Performance**: Measure latency, throughput

### Success Criteria
- Message delivery < 2 seconds (95th percentile)
- 99.9% message integrity
- Zero data corruption
- Automatic recovery from disconnects

## Next Steps
1. Implement Python classes
2. Create test suite
3. Integrate with OpenClaw workflow
4. Deploy and monitor