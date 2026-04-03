#!/usr/bin/env python3
"""
Memory-Aware Tools - Agent Integration

Purpose: Provide agent instructions for using memory-aware patterns
This follows White Roger's skill-based integration approach
"""

import os
import sys
import json
from datetime import datetime

# Kill switch
MEMORY_CONTRACT_ENABLED = os.getenv('MEMORY_CONTRACT_ENABLED', 'true')

# Import our memory contract hooks
try:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from pre_action_memory import pre_action_memory_search, pre_action_recall
    from post_decision_memory import post_decision_memory_persistence
    from compliance_tracker import get_compliance_status
    from config_loader import get_config
    
    config = get_config()
    print("[Memory Contract] Hooks and config loaded successfully")
    
except ImportError as e:
    print(f"[Memory Contract ERROR] Could not load hooks: {e}")
    # Create fallback functions for graceful degradation
    def pre_action_memory_search(context):
        print(f"[Memory Contract WARNING] Pre-action search unavailable: {context.get('tool')}")
        return []
    
    def pre_action_recall(query, domain=None, limit=3):
        print(f"[Memory Contract WARNING] Explicit recall unavailable for: {query[:50]}...")
        return ""
    
    def post_decision_memory_persistence(decision, outcome, metadata):
        print(f"[Memory Contract WARNING] Post-decision write unavailable: {decision[:50]}...")
        return {"status": "fallback"}
    
    def get_compliance_status():
        return {"status": "unavailable", "message": "Compliance tracker not loaded"}
    
    config = None

def should_use_memory_contract():
    """Check if Memory Contract should be used"""
    if MEMORY_CONTRACT_ENABLED.lower() != 'true':
        return False
    
    # Check if kill switch file exists
    kill_switch_file = config.get('kill_switch_file') if config else None
    if kill_switch_file and os.path.exists(kill_switch_file):
        print(f"[Memory Contract] DISABLED - kill switch file exists: {kill_switch_file}")
        return False
    
    return True

def get_memory_context_for_tool(tool_name, **kwargs):
    """Create context for memory search based on tool and parameters"""
    context = {
        "tool": tool_name,
        "timestamp": datetime.now().isoformat(),
        "parameters": kwargs
    }
    
    # Add tool-specific context
    if tool_name == "exec":
        context["command"] = kwargs.get('command', '')
        context["purpose"] = "command execution"
    elif tool_name == "write":
        context["file"] = kwargs.get('path', '')
        context["purpose"] = "file write"
    elif tool_name == "edit":
        context["file"] = kwargs.get('path', '')
        context["purpose"] = "file edit"
    elif tool_name == "browser":
        context["action"] = kwargs.get('action', '')
        context["purpose"] = "browser interaction"
    elif tool_name == "message":
        context["action"] = kwargs.get('action', '')
        context["purpose"] = "messaging"
    
    return context

def create_decision_text(tool_name, **kwargs):
    """Create decision text for memory persistence"""
    if tool_name == "exec":
        return f"Executed command: {kwargs.get('command', '')[:100]}"
    elif tool_name == "write":
        return f"Wrote to file: {kwargs.get('path', '')}"
    elif tool_name == "edit":
        return f"Edited file: {kwargs.get('path', '')}"
    elif tool_name == "browser":
        return f"Browser action: {kwargs.get('action', '')}"
    elif tool_name == "message":
        return f"Message action: {kwargs.get('action', '')}"
    else:
        return f"Used tool: {tool_name}"

# Agent Instruction Functions
# These are what the agent calls when following the skill instructions

def before_tool_use(tool_name, **kwargs):
    """
    Agent calls this BEFORE using any tool
    
    Follows White Roger's skill instruction:
    "Before executing any significant action, search for relevant context"
    """
    if not should_use_memory_contract():
        print(f"[Memory Contract] Skipping pre-action search (disabled)")
        return []
    
    try:
        # Create context for memory search
        context = get_memory_context_for_tool(tool_name, **kwargs)
        
        print(f"[Memory Contract] Pre-action search for {tool_name}...")
        results = pre_action_memory_search(context)
        
        if results:
            print(f"[Memory Contract] Found {len(results)} relevant memory entries")
            for i, r in enumerate(results[:3]):  # Show top 3
                title = r.get('title', 'Untitled')
                summary = r.get('summary', '')[:80]
                print(f"  {i+1}. {title}: {summary}...")
        else:
            print(f"[Memory Contract] No relevant memory found")
        
        return results
        
    except Exception as e:
        print(f"[Memory Contract ERROR] Pre-action search failed: {e}")
        return []  # Graceful degradation - don't block execution

def after_tool_use(tool_name, result, **kwargs):
    """
    Agent calls this AFTER using any tool
    
    Follows White Roger's skill instruction:
    "After completing significant actions, record the decision and outcome"
    """
    if not should_use_memory_contract():
        print(f"[Memory Contract] Skipping post-decision persistence (disabled)")
        return {"status": "skipped"}
    
    try:
        # Create decision text
        decision = create_decision_text(tool_name, **kwargs)
        
        # Determine outcome
        if isinstance(result, dict):
            outcome = result.get('status', 'unknown')
        else:
            outcome = str(type(result))
        
        # Create metadata
        metadata = {
            "tool": tool_name,
            "parameters": kwargs,
            "result_type": type(result).__name__,
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"[Memory Contract] Post-decision persistence for {tool_name}...")
        persistence_result = post_decision_memory_persistence(
            decision=decision,
            outcome=outcome,
            metadata=metadata
        )
        
        print(f"[Memory Contract] Decision recorded: {decision[:50]}...")
        return persistence_result
        
    except Exception as e:
        print(f"[Memory Contract ERROR] Post-decision persistence failed: {e}")
        return {"status": "error", "error": str(e)}

def check_compliance():
    """
    Agent calls this to check compliance status
    
    Follows White Roger's skill instruction:
    "To view compliance, call get_compliance_status()"
    """
    try:
        status = get_compliance_status()
        return status
    except Exception as e:
        print(f"[Memory Contract ERROR] Compliance check failed: {e}")
        return {"status": "error", "error": str(e)}

# =============================================================================
# OPENCLAW TOOL EXPOSURE (2026-04-03 spec)
# =============================================================================

"""
The pre_action_recall function is exposed as an OpenClaw tool for explicit use:

Tool Name: memory_recall
Description: Retrieve relevant memories from Roger's memory store
Parameters:
  - query (string): Search query
  - domain (string, optional): Filter by domain (architecture, trade, memory-system, agent-ops, project, episodic)
  - limit (integer, optional): Max results, default 3, max 5

Usage from agent:
  result = pre_action_recall("dynasty trade Bijan Robinson", domain="trade", limit=3)
  # Returns formatted memory context string for injection

This is integrated into the hook system via:
  - pre_action_memory.py: pre_action_recall() function
  - cognitive_memory.py: pre_action_recall() semantic wrapper
  - memory_aware_tools.py: before_tool_use() calls pre_action_recall automatically
"""

def explicit_recall(query: str, domain: str = None, limit: int = 3) -> str:
    """
    Explicit recall function for agent to call directly.
    Use this for intentional memory lookups.
    
    Args:
        query: Search query string
        domain: Optional domain filter
        limit: Max results (default 3, max 5)
    
    Returns:
        Formatted memory context string
    """
    return pre_action_recall(query, domain=domain, limit=limit)


# =============================================================================
# EXAMPLE USAGE PATTERNS
# =============================================================================

# Example usage patterns for the agent
def example_agent_workflow():
    """
    Example of how agent should use Memory Contract
    
    This demonstrates the pattern from White Roger's skill draft
    """
    print("\n" + "="*60)
    print("Memory Contract Agent Workflow Example")
    print("="*60)
    
    # Example 1: Before deploying
    print("\n1. Before deploying:")
    context = {
        "tool": "exec",
        "command": "git push origin main",
        "user_request": "Deploy the Dynastydroid backend"
    }
    
    # Agent calls pre-action search
    results = before_tool_use("exec", command="git push origin main")
    
    if results:
        print("   Reviewing relevant memory before deployment...")
        for r in results[:2]:
            print(f"   - {r.get('title', 'Untitled')}")
    
    # Agent executes the actual tool (OpenClaw handles this)
    print("\n2. Executing deployment (OpenClaw handles tool call)...")
    # result = exec(command="git push origin main")  # OpenClaw would call this
    
    # Agent calls post-decision persistence
    print("\n3. After deployment:")
    after_tool_use(
        "exec",
        result={"status": "success", "output": "Deployment completed"},
        command="git push origin main"
    )
    
    # Check compliance
    print("\n4. Checking compliance:")
    compliance = check_compliance()
    if isinstance(compliance, dict) and 'daily_metrics' in compliance:
        metrics = compliance['daily_metrics']
        print(f"   Today's searches: {metrics.get('pre_action_searches', 0)}")
        print(f"   Today's writes: {metrics.get('post_decision_writes', 0)}")
    
    print("\n" + "="*60)
    print("Workflow complete - Memory Contract integrated!")
    print("="*60)

if __name__ == "__main__":
    # Test the implementation
    example_agent_workflow()