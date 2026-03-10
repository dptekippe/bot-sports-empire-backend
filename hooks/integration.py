#!/usr/bin/env python3
"""
OpenClaw Integration for Memory Contract

Purpose: Integrate Memory Contract hooks with OpenClaw tools
Features: Gradual rollout, kill switch, monitoring
"""

import os
import sys
import json
import datetime
from typing import Dict, Any, Callable

# Configuration
MEMORY_CONTRACT_ENABLED = os.environ.get('MEMORY_CONTRACT_ENABLED', 'true').lower() == 'true'
TOOLS_TO_WRAP = ['exec']  # Start with exec only (gradual rollout)

# Import hooks
try:
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from tool_wrappers import wrap_tool_call
    from session_validation import validate_memory_capture
    from compliance_tracker import run_compliance_update
    
    HOOKS_AVAILABLE = True
except ImportError as e:
    print(f"[Memory Contract WARNING] Could not import hooks: {e}")
    HOOKS_AVAILABLE = False

def is_memory_contract_enabled() -> bool:
    """Check if memory contract is enabled"""
    if not MEMORY_CONTRACT_ENABLED:
        print("[Memory Contract] DISABLED via environment variable")
        return False
    
    if not HOOKS_AVAILABLE:
        print("[Memory Contract] DISABLED - hooks not available")
        return False
    
    return True

def patch_openclaw_tools():
    """
    Patch OpenClaw tools to include memory contract behavior
    
    This function should be called early in OpenClaw initialization
    """
    if not is_memory_contract_enabled():
        print("[Memory Contract] Not patching tools - disabled")
        return
    
    print(f"[Memory Contract] Patching tools: {TOOLS_TO_WRAP}")
    
    try:
        # Try to import OpenClaw tools
        # Note: This depends on OpenClaw's internal structure
        # We'll need to adapt based on actual OpenClaw implementation
        
        # For now, create a demonstration of how patching would work
        print("[Memory Contract] Tool patching demonstration:")
        print("  - In production, this would replace openclaw.tools.exec")
        print("  - With wrapped version that includes memory contract")
        print("  - Starting with exec tool only (gradual rollout)")
        
        # Create a test to verify the concept works
        test_memory_contract_integration()
        
    except ImportError as e:
        print(f"[Memory Contract ERROR] Could not import OpenClaw tools: {e}")
        print("  This is expected if running outside OpenClaw context")
        print("  Integration will happen when OpenClaw loads this module")

def test_memory_contract_integration():
    """Test that memory contract integration works"""
    print("\n[Memory Contract] Running integration test...")
    
    # Test 1: Validate memory capture
    print("  Test 1: Running validate_memory_capture()...")
    validation_result = validate_memory_capture()
    if validation_result.get('overall_status') == 'PASS':
        print("  ✓ Validation passed")
    else:
        print(f"  ✗ Validation failed: {validation_result.get('overall_status')}")
    
    # Test 2: Run compliance update
    print("  Test 2: Running compliance update...")
    compliance_result = run_compliance_update()
    if compliance_result.get('overall_status') == 'high':
        print("  ✓ Compliance metrics updated")
    else:
        print(f"  ✗ Compliance low: {compliance_result.get('overall_status')}")
    
    # Test 3: Check if hooks are working
    print("  Test 3: Checking hook logs...")
    from config_loader import get_config
    config = get_config()
    log_files = [
        config.get('search_log'),
        config.get('write_log'),
        config.get('validation_log')
    ]
    
    for log_file in log_files:
        # TODO: Agent should use OpenClaw read tool to check log files
        # Example: read(path=log_file) if exists
        print(f"  [TODO] Would check log file: {os.path.basename(log_file)}")
    
    print("[Memory Contract] Integration test complete")

def create_kill_switch():
    """Create kill switch file to disable memory contract"""
    kill_switch_file = config.get("kill_switch_file")
    
    # TODO: Agent should use OpenClaw write tool to create kill switch
    # Example: write(path=kill_switch_file, content=kill_switch_content)
    kill_switch_content = f"""# Memory Contract Kill Switch
# Created: {datetime.datetime.now().isoformat()}
# Delete this file to re-enable Memory Contract
# Or set MEMORY_CONTRACT_ENABLED=false environment variable
"""
    print(f"[TODO] Would create kill switch at {kill_switch_file}")
    print("  Memory Contract would be disabled on next restart")

def remove_kill_switch():
    """Remove kill switch file to re-enable memory contract"""
    kill_switch_file = config.get("kill_switch_file")
    
    if os.path.exists(kill_switch_file):
        os.remove(kill_switch_file)
        print(f"[Memory Contract] Kill switch removed: {kill_switch_file}")
        print("  Memory Contract will be enabled on next restart")
    else:
        print(f"[Memory Contract] No kill switch found")

def check_kill_switch() -> bool:
    """Check if kill switch is active"""
    kill_switch_file = config.get("kill_switch_file")
    env_disabled = os.environ.get('MEMORY_CONTRACT_ENABLED', 'true').lower() == 'false'
    
    file_exists = os.path.exists(kill_switch_file)
    
    if file_exists or env_disabled:
        print(f"[Memory Contract] Kill switch active: file={file_exists}, env={env_disabled}")
        return True
    
    return False

def get_integration_status() -> Dict:
    """Get current integration status"""
    return {
        "timestamp": datetime.datetime.now().isoformat(),
        "enabled": is_memory_contract_enabled() and not check_kill_switch(),
        "hooks_available": HOOKS_AVAILABLE,
        "tools_wrapped": TOOLS_TO_WRAP,
        "kill_switch_active": check_kill_switch(),
        "environment_variable": os.environ.get('MEMORY_CONTRACT_ENABLED', 'true'),
        "files": {
            "hooks_directory": os.path.exists(config.get('hooks_dir')),
            "compliance_file": os.path.exists(config.get('compliance_file')),
            "kill_switch_file": os.path.exists(config.get('kill_switch_file'))
        }
    }

# Main execution
if __name__ == "__main__":
    print("=" * 60)
    print("Memory Contract Integration Module")
    print("=" * 60)
    
    # Check status
    status = get_integration_status()
    print(f"Status: {'ENABLED' if status['enabled'] else 'DISABLED'}")
    print(f"Hooks available: {status['hooks_available']}")
    print(f"Tools to wrap: {status['tools_wrapped']}")
    print(f"Kill switch: {'ACTIVE' if status['kill_switch_active'] else 'INACTIVE'}")
    
    # Show file status
    print("\nFile Status:")
    for file_name, exists in status['files'].items():
        print(f"  {file_name}: {'✓' if exists else '✗'}")
    
    # Test if enabled
    if status['enabled']:
        print("\n[Memory Contract] Running integration test...")
        test_memory_contract_integration()
    else:
        print("\n[Memory Contract] Integration disabled")
        if status['kill_switch_active']:
            print("  Kill switch is active")
            print(f"  Remove {config.get('kill_switch_file')} to enable")
        if status['environment_variable'] == 'false':
            print("  Environment variable MEMORY_CONTRACT_ENABLED=false")
            print("  Set to 'true' to enable")
    
    print("\nCommands:")
    print("  python3 integration.py              - Check status")
    print("  python3 integration.py --kill       - Create kill switch")
    print("  python3 integration.py --enable     - Remove kill switch")
    print("  python3 integration.py --test       - Run integration test")
    
    # Handle command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--kill':
            create_kill_switch()
        elif sys.argv[1] == '--enable':
            remove_kill_switch()
        elif sys.argv[1] == '--test':
            test_memory_contract_integration()
        elif sys.argv[1] == '--status':
            print(json.dumps(status, indent=2))
from config_loader import get_config
config = get_config()