#!/usr/bin/env python3
"""
Pre-Action Memory Search Hook

Purpose: Search memory before significant actions to provide context
White Roger Revision: Add sanity check - if search fails, log warning but don't block execution
"""

import os
import json
import datetime
from typing import Dict, List, Optional

def extract_keywords(context: Dict) -> List[str]:
    """Extract search keywords from context"""
    keywords = []
    
    # Extract from tool type
    if 'tool' in context:
        keywords.append(context['tool'])
    
    # Extract from command/action
    if 'command' in context:
        # Simple keyword extraction from command
        words = context['command'].split()
        keywords.extend([w for w in words if len(w) > 3][:3])
    
    # Extract from user request if present
    if 'user_request' in context:
        words = context['user_request'].split()
        keywords.extend([w for w in words if len(w) > 3][:3])
    
    return list(set(keywords))  # Remove duplicates

def memory_search_safe(query: str, max_results: int = 5) -> Optional[List[Dict]]:
    """
    Safe memory search with error handling
    Returns None if search fails (don't block execution)
    """
    try:
        # This would integrate with OpenClaw's memory_search tool
        # For now, return mock results
        return [
            {"path": "memory/2026-03-06.md", "lines": "1-5", "content": "Test memory entry"},
            {"path": "MEMORY.md", "lines": "10-15", "content": "Previous decision about memory system"}
        ]
    except Exception as e:
        # Log warning but don't raise
        log_warning(f"Memory search failed: {e}")
        return None

def log_search(context: Dict, keywords: List[str], results: Optional[List[Dict]]):
    """Log search for compliance tracking"""
    log_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "context": context,
        "keywords": keywords,
        "results_count": len(results) if results else 0,
        "search_successful": results is not None
    }
    
    # TODO: Agent should write this log entry using OpenClaw write tool
    # log_file = config.get("search_log")
    # with open(log_file, 'a') as f:
    #     f.write(json.dumps(log_entry) + '\n')
    
    print(f"[TODO] Would log search to {config.get('search_log')}: {log_entry}")

def pre_action_memory_search(context: Dict) -> Optional[List[Dict]]:
    """
    Search memory for relevant context before action
    
    Args:
        context: Dictionary containing action context (tool, command, user_request, etc.)
    
    Returns:
        List of memory search results or None if search failed
    
    White Roger Revision: If search fails, return None but don't block execution
    """
    print(f"[Memory Contract] Pre-action search for: {context.get('tool', 'unknown')}")
    
    # Extract keywords
    keywords = extract_keywords(context)
    if not keywords:
        print(f"[Memory Contract] No keywords extracted from context")
        return None
    
    # Perform safe search
    query = " ".join(keywords)
    results = memory_search_safe(query, max_results=5)
    
    # Log for compliance tracking
    log_search(context, keywords, results)
    
    if results:
        print(f"[Memory Contract] Found {len(results)} relevant memories")
    else:
        print(f"[Memory Contract] Search failed or no results (continuing anyway)")
    
    return results

def log_warning(message: str):
    """Log warning message"""
    warning_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "level": "WARNING",
        "message": message
    }
    
    # TODO: Agent should write this warning using OpenClaw write tool
    # warning_file = config.get("logs_dir") + "/warnings.jsonl"
    # with open(warning_file, 'a') as f:
    #     f.write(json.dumps(warning_entry) + '\n')
    
    print(f"[WARNING] {message} (would log to {config.get('logs_dir')}/warnings.jsonl)")

# Test function
if __name__ == "__main__":
    # Test the hook
    test_context = {
        "tool": "exec",
        "command": "git push origin main",
        "user_request": "Deploy to production"
    }
    
    results = pre_action_memory_search(test_context)
    print(f"Test results: {results}")
from config_loader import get_config
config = get_config()