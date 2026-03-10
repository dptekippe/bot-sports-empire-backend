#!/usr/bin/env python3
"""
Agent-Level Memory Contract Integration

Purpose: Wrap tool calls at the agent level (Black Roger's level)
This is where we actually have control over tool execution
"""

import os
import sys
import json
import datetime
from typing import Dict, Any, Callable

# Kill switch from White Roger's specification
MEMORY_CONTRACT_ENABLED = os.getenv('MEMORY_CONTRACT_ENABLED', 'true')
if MEMORY_CONTRACT_ENABLED.lower() == 'false':
    print("[Memory Contract] DISABLED via environment variable")
    print("[Memory Contract] Using original tools (no wrapping)")
    # In production, we would skip the rest of this module
    sys.exit(0)

print("[Memory Contract] ENABLED - implementing agent-level wrapping")

# Import our hooks
try:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from pre_action_memory import pre_action_memory_search
    from post_decision_memory import post_decision_memory_persistence
    
    print("[Memory Contract] Hooks loaded successfully")
except ImportError as e:
    print(f"[Memory Contract ERROR] Could not load hooks: {e}")
    sys.exit(1)

class MemoryContractWrapper:
    """Wrapper class that adds memory contract behavior to tools"""
    
    def __init__(self):
        self.wrapped_tools = {}
        self.compliance_data = {
            "pre_action_searches": 0,
            "post_decision_writes": 0,
            "errors": 0,
            "start_time": datetime.datetime.now().isoformat()
        }
    
    def wrap_tool(self, tool_name: str, original_tool: Callable) -> Callable:
        """Wrap a tool with memory contract behavior"""
        
        def wrapped_tool(**kwargs):
            # Pre-action memory search
            context = {
                "tool": tool_name,
                "command": str(kwargs.get('command', kwargs.get('message', ''))),
                "timestamp": datetime.datetime.now().isoformat(),
                "kwargs_keys": list(kwargs.keys())
            }
            
            memory_results = pre_action_memory_search(context)
            self.compliance_data["pre_action_searches"] += 1
            
            # Execute original tool
            try:
                result = original_tool(**kwargs)
                
                # Determine if this was a decision worth recording
                if self.should_record_decision(tool_name, kwargs, result):
                    # Create decision description
                    decision = self.create_decision_description(tool_name, kwargs, result)
                    outcome = self.create_outcome_description(result)
                    
                    metadata = {
                        "tool": tool_name,
                        "kwargs": self.sanitize_kwargs(kwargs),
                        "result_summary": self.summarize_result(result),
                        "context": f"{tool_name} execution",
                        "tags": [tool_name, "execution"]
                    }
                    
                    # Post-decision memory persistence
                    write_result = post_decision_memory_persistence(decision, outcome, metadata)
                    self.compliance_data["post_decision_writes"] += 1
                    
                    if write_result.get('status') == 'error':
                        print(f"[Memory Contract ERROR] Failed to write memory: {write_result.get('error')}")
                        self.compliance_data["errors"] += 1
                
                return result
                
            except Exception as e:
                # Record failure
                decision = f"{tool_name} execution failed"
                outcome = f"Error: {str(e)}"
                metadata = {
                    "tool": tool_name,
                    "kwargs": self.sanitize_kwargs(kwargs),
                    "error": str(e),
                    "context": f"{tool_name} execution failed",
                    "tags": [tool_name, "error", "failure"]
                }
                
                post_decision_memory_persistence(decision, outcome, metadata)
                self.compliance_data["errors"] += 1
                
                # Re-raise
                raise
        
        # Store the wrapped tool
        self.wrapped_tools[tool_name] = wrapped_tool
        print(f"[Memory Contract] Wrapped tool: {tool_name}")
        
        return wrapped_tool
    
    def should_record_decision(self, tool_name: str, kwargs: Dict, result: Any) -> bool:
        """Determine if a tool execution should be recorded"""
        # Always record these tools
        if tool_name in ['exec', 'write', 'edit', 'browser', 'message']:
            return True
        
        # For read, only record if it's part of an edit operation
        if tool_name == 'read' and 'edit' in str(kwargs.get('path', '')):
            return True
        
        return False
    
    def create_decision_description(self, tool_name: str, kwargs: Dict, result: Any) -> str:
        """Create decision description"""
        if tool_name == 'exec':
            command = kwargs.get('command', '')
            return f"Executed: {command[:100]}"
        elif tool_name == 'write':
            path = kwargs.get('path', '')
            return f"Wrote to: {path}"
        elif tool_name == 'edit':
            path = kwargs.get('path', '')
            return f"Edited: {path}"
        elif tool_name == 'browser':
            action = kwargs.get('action', '')
            url = kwargs.get('targetUrl', '')
            return f"Browser: {action} {url}"
        elif tool_name == 'message':
            action = kwargs.get('action', '')
            return f"Message: {action}"
        else:
            return f"{tool_name}: {str(kwargs)[:100]}"
    
    def create_outcome_description(self, result: Any) -> str:
        """Create outcome description"""
        if isinstance(result, dict):
            if result.get('status') == 'success':
                return "Success"
            elif result.get('status') == 'error':
                return f"Error: {result.get('error', 'Unknown')}"
            else:
                return f"Result: {str(result)[:200]}"
        return str(result)[:200]
    
    def sanitize_kwargs(self, kwargs: Dict) -> Dict:
        """Sanitize kwargs for logging"""
        sanitized = {}
        for key, value in kwargs.items():
            if key in ['password', 'token', 'secret', 'key', 'auth']:
                sanitized[key] = '***REDACTED***'
            elif isinstance(value, str) and len(value) > 100:
                sanitized[key] = value[:100] + '...'
            else:
                sanitized[key] = value
        return sanitized
    
    def summarize_result(self, result: Any) -> Dict:
        """Summarize result for metadata"""
        if isinstance(result, dict):
            summary = {}
            for key in ['status', 'ok', 'success', 'messageId', 'channelId']:
                if key in result:
                    summary[key] = result[key]
            if 'output' in result:
                summary['output_length'] = len(str(result['output']))
            return summary
        return {"type": type(result).__name__}
    
    def get_compliance_report(self) -> Dict:
        """Get compliance report"""
        total_actions = self.compliance_data["pre_action_searches"]
        successful_writes = self.compliance_data["post_decision_writes"]
        errors = self.compliance_data["errors"]
        
        compliance_rate = (successful_writes / max(total_actions, 1)) * 100
        
        return {
            "timestamp": datetime.datetime.now().isoformat(),
            "compliance_rate": round(compliance_rate, 1),
            "metrics": self.compliance_data,
            "wrapped_tools": list(self.wrapped_tools.keys()),
            "status": "high" if compliance_rate >= 90 else "low"
        }

# Create global wrapper instance
memory_contract_wrapper = MemoryContractWrapper()

# Demonstration: How tools would be wrapped
def demonstrate_wrapping():
    """Demonstrate how tools would be wrapped"""
    print("\n[Memory Contract] Demonstration:")
    print("  In production, OpenClaw tools would be wrapped like:")
    print("  ")
    print("  # Original: exec(command='ls -la')")
    print("  # Wrapped: memory_contract_wrapper.wrap_tool('exec', original_exec)")
    print("  ")
    print("  The wrapped version would:")
    print("  1. Search memory before execution")
    print("  2. Execute the command")
    print("  3. Write decision to memory after")
    print("  4. Track compliance metrics")
    
    # Show what compliance would look like
    print("\n  Example compliance metrics:")
    report = memory_contract_wrapper.get_compliance_report()
    print(f"    Pre-action searches: {report['metrics']['pre_action_searches']}")
    print(f"    Post-decision writes: {report['metrics']['post_decision_writes']}")
    print(f"    Compliance rate: {report['compliance_rate']}%")
    print(f"    Status: {report['status']}")

# Main execution
if __name__ == "__main__":
    print("[Memory Contract] Agent-Level Integration Module")
    
    if MEMORY_CONTRACT_ENABLED.lower() != 'true':
        print("  Disabled via environment variable")
        sys.exit(0)
    
    demonstrate_wrapping()
    
    print("\n" + "="*60)
    print("Integration Status:")
    print("="*60)
    print(f"Memory Contract: {'ENABLED' if MEMORY_CONTRACT_ENABLED.lower() == 'true' else 'DISABLED'}")
    print(f"Hooks loaded: {'YES' if 'pre_action_memory' in sys.modules else 'NO'}")
    print(f"Wrapper ready: YES")
    
    print("\nTo use in production:")
    print("1. Import this module in your agent code")
    print("2. Wrap tools before using them:")
    print("   wrapped_exec = memory_contract_wrapper.wrap_tool('exec', original_exec)")
    print("3. Use wrapped_exec instead of original_exec")
    
    print("\nKill Switch:")
    print("  Set MEMORY_CONTRACT_ENABLED=false to disable")
from config_loader import get_config
config = get_config()