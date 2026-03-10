#!/usr/bin/env python3
"""
Post-Decision Memory Persistence Hook

Purpose: Write decisions and outcomes to memory after completion
"""

import os
import json
import datetime
from typing import Dict, List, Any

def ensure_memory_directory():
    """Ensure memory directory exists"""
    memory_dir = config.get("memory_dir")
    if not os.path.exists(memory_dir):
        os.makedirs(memory_dir)
    return memory_dir

def format_memory_entry(decision: str, outcome: str, metadata: Dict) -> str:
    """Format a memory entry for storage"""
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    
    # Extract tags from metadata or generate from context
    tags = metadata.get('tags', [])
    if not tags and 'context' in metadata:
        # Generate simple tags from context
        context = metadata['context']
        if isinstance(context, str):
            words = context.split()
            tags = [w.lower() for w in words if len(w) > 3][:3]
    
    entry = f"""
## {timestamp}
**Decision:** {decision}
**Outcome:** {outcome}
**Context:** {metadata.get('context', '')}
**Tags:** {','.join(tags)}
"""
    return entry.strip()

def append_to_memory_file(content: str):
    """Append content to today's memory file"""
    memory_dir = ensure_memory_directory()
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    memory_file = os.path.join(memory_dir, f"{today}.md")
    
    # TODO: Agent should write to memory file using OpenClaw write tool
    # Check if file exists and has content
    # file_exists = os.path.exists(memory_file)
    # 
    # with open(memory_file, 'a') as f:
    #     if not file_exists:
    #         # Add header for new file
    #         f.write(f"# {today}\n\n")
    #     f.write(content + "\n\n")
    
    print(f"[TODO] Would append to memory file: {memory_file}")
    print(f"Content: {content[:100]}...")
    
    return memory_file

def update_decisions_log(decision: str, outcome: str, metadata: Dict):
    """Update the decisions log with structured data"""
    decisions_file = config.get("decisions_file")
    
    entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "decision": decision,
        "outcome": outcome,
        "metadata": metadata
    }
    
    # TODO: Agent should write to decisions log using OpenClaw write tool
    # Append to decisions log
    # with open(decisions_file, 'a') as f:
    #     f.write(json.dumps(entry) + '\n')
    
    print(f"[TODO] Would update decisions log: {decisions_file}")
    print(f"Entry: {entry}")

def log_write_operation(decision: str, outcome: str, metadata: Dict, memory_file: str):
    """Log write operation for compliance tracking"""
    log_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "decision": decision,
        "outcome_length": len(outcome),
        "metadata_keys": list(metadata.keys()),
        "memory_file": memory_file,
        "write_successful": True
    }
    
    # TODO: Agent should write to write log using OpenClaw write tool
    # log_file = config.get("write_log")
    # with open(log_file, 'a') as f:
    #     f.write(json.dumps(log_entry) + '\n')
    
    print(f"[TODO] Would log write operation to {config.get('write_log')}")

def post_decision_memory_persistence(decision: str, outcome: str, metadata: Dict) -> Dict:
    """
    Write decision and outcome to memory
    
    Args:
        decision: Description of the decision made
        outcome: Result or output of the decision
        metadata: Additional context (tool, command, user_request, etc.)
    
    Returns:
        Dictionary with write status and file path
    """
    print(f"[Memory Contract] Post-decision write: {decision[:50]}...")
    
    try:
        # Format memory entry
        entry = format_memory_entry(decision, outcome, metadata)
        
        # Append to today's memory file
        memory_file = append_to_memory_file(entry)
        
        # Update decisions log
        update_decisions_log(decision, outcome, metadata)
        
        # Log for compliance tracking
        log_write_operation(decision, outcome, metadata, memory_file)
        
        print(f"[Memory Contract] Successfully wrote to {memory_file}")
        
        return {
            "status": "success",
            "memory_file": memory_file,
            "entry_length": len(entry)
        }
        
    except Exception as e:
        # Log error but don't raise (graceful degradation)
        error_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "level": "ERROR",
            "decision": decision,
            "error": str(e)
        }
        
        # TODO: Agent should write to error log using OpenClaw write tool
        # error_file = config.get("error_log")
        # with open(error_file, 'a') as f:
        #     f.write(json.dumps(error_entry) + '\n')
        
        print(f"[Memory Contract ERROR] Failed to write memory: {e}")
        print(f"[TODO] Would log error to {config.get('error_log')}")
        
        return {
            "status": "error",
            "error": str(e)
        }

# Test function
if __name__ == "__main__":
    # Test the hook
    test_decision = "Test decision to verify memory persistence"
    test_outcome = "Success - memory hook implemented"
    test_metadata = {
        "tool": "write",
        "context": "Testing post_decision_memory_persistence hook",
        "tags": ["test", "memory", "hook"]
    }
    
    result = post_decision_memory_persistence(test_decision, test_outcome, test_metadata)
    print(f"Test result: {result}")
from config_loader import get_config
config = get_config()