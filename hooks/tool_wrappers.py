#!/usr/bin/env python3
"""
Tool Wrappers for Memory Contract Integration

Purpose: Wrap OpenClaw tool calls to inject memory contract behavior
"""

import sys
import os
import json
import datetime
from typing import Dict, Any, Callable

# Add hooks directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from pre_action_memory import pre_action_memory_search
    from post_decision_memory import post_decision_memory_persistence
    from session_validation import validate_memory_capture
    from compliance_tracker import run_compliance_update
except ImportError as e:
    print(f"[Memory Contract WARNING] Could not import hooks: {e}")
    # Define fallback functions
    def pre_action_memory_search(context):
        print(f"[Memory Contract] Pre-action search disabled: {context.get('tool', 'unknown')}")
        return None
    
    def post_decision_memory_persistence(decision, outcome, metadata):
        print(f"[Memory Contract] Post-decision write disabled: {decision[:50]}...")
        return {"status": "disabled"}
    
    def validate_memory_capture():
        print("[Memory Contract] Validation disabled")
        return {"overall_status": "DISABLED"}
    
    def run_compliance_update():
        return {"overall_status": "DISABLED"}

def wrap_tool_call(original_tool: Callable, tool_name: str) -> Callable:
    """
    Create a wrapped version of a tool that includes memory contract behavior
    
    Args:
        original_tool: The original tool function to wrap
        tool_name: Name of the tool (exec, write, edit, browser, etc.)
    
    Returns:
        Wrapped tool function with memory contract integration
    
    Note: This is a guidance function - agents should implement the pattern
    but OpenClaw tools are called directly, not through Python wrappers
    """
    def wrapped_tool(**kwargs):
        # TODO: Agents should implement this pattern manually:
        # 1. Call pre_action_memory_search() for guidance
        # 2. Make actual OpenClaw tool call (exec, write, etc.)
        # 3. Call post_decision_memory_persistence() to record
        
        print(f"[TODO] Tool wrapper for {tool_name} - agents should implement pattern manually")
        print(f"  Context: {kwargs}")
        
        # For now, just call the original tool
        return original_tool(**kwargs)
    
    return wrapped_tool

def should_record_decision(tool_name: str, kwargs: Dict, result: Any) -> bool:
    """
    Determine if a tool execution should be recorded as a decision
    
    Some tools are just queries or reads, not decisions
    """
    # Always record these tools
    if tool_name in ['write', 'edit', 'exec', 'browser', 'message']:
        return True
    
    # Record read/edit if it modifies content
    if tool_name == 'read' and 'edit' in str(kwargs.get('path', '')):
        return True
    
    # Default: don't record
    return False

def create_decision_description(tool_name: str, kwargs: Dict, result: Any) -> str:
    """Create a human-readable description of the decision"""
    if tool_name == 'exec':
        command = kwargs.get('command', '')
        return f"Executed command: {command[:100]}"
    
    elif tool_name == 'write':
        path = kwargs.get('path', '')
        content_preview = kwargs.get('content', '')[:50]
        return f"Wrote to {path}: {content_preview}..."
    
    elif tool_name == 'edit':
        path = kwargs.get('path', '')
        return f"Edited file: {path}"
    
    elif tool_name == 'browser':
        action = kwargs.get('action', '')
        url = kwargs.get('targetUrl', '')
        return f"Browser action: {action} {url}"
    
    elif tool_name == 'message':
        action = kwargs.get('action', '')
        channel = kwargs.get('channel', '')
        return f"Message action: {action} on {channel}"
    
    else:
        return f"{tool_name} execution with kwargs: {str(kwargs)[:100]}"

def create_outcome_description(result: Any) -> str:
    """Create a human-readable description of the outcome"""
    if isinstance(result, dict):
        if 'status' in result:
            status = result['status']
            if status == 'success':
                return "Success"
            elif status == 'error':
                return f"Error: {result.get('error', 'Unknown error')}"
        
        # Try to extract meaningful info
        keys = list(result.keys())
        return f"Result with keys: {', '.join(keys[:3])}"
    
    elif isinstance(result, str):
        return result[:200]
    
    else:
        return str(result)[:200]

def sanitize_kwargs(kwargs: Dict) -> Dict:
    """Sanitize kwargs for logging (remove sensitive data)"""
    sanitized = {}
    
    for key, value in kwargs.items():
        if key in ['password', 'token', 'secret', 'key', 'auth']:
            sanitized[key] = '***REDACTED***'
        elif isinstance(value, str) and len(value) > 100:
            sanitized[key] = value[:100] + '...'
        else:
            sanitized[key] = value
    
    return sanitized

def summarize_result(result: Any) -> Dict:
    """Create a summary of the result for metadata"""
    if isinstance(result, dict):
        summary = {}
        
        # Copy basic fields
        for key in ['status', 'ok', 'success']:
            if key in result:
                summary[key] = result[key]
        
        # Add result-specific fields
        if 'messageId' in result:
            summary['messageId'] = result['messageId']
        if 'channelId' in result:
            summary['channelId'] = result['channelId']
        if 'output' in result:
            summary['output_length'] = len(str(result['output']))
        
        return summary
    
    return {"type": type(result).__name__, "str_length": len(str(result))}

def run_periodic_validation():
    """Run periodic validation (to be called by cron)"""
    print("[Memory Contract] Running periodic validation...")
    
    # Run validation
    validation_report = validate_memory_capture()
    
    # Update compliance metrics
    compliance_report = run_compliance_update()
    
    # Check if we need to alert
    if validation_report.get('overall_status') == 'FAIL':
        print("[Memory Contract ALERT] Validation failed!")
    
    return {
        "validation": validation_report,
        "compliance": compliance_report,
        "timestamp": datetime.datetime.now().isoformat()
    }

# Test the wrappers
if __name__ == "__main__":
    print("Testing tool wrappers...")
    
    # TODO: This is a test stub - agents should test with real OpenClaw tools
    print("[TODO] Test stub - agents should test with real OpenClaw tool integration")
    
    # Test periodic validation
    validation_result = run_periodic_validation()
    print(f"Validation result: {json.dumps(validation_result, indent=2)}")
from config_loader import get_config
config = get_config()