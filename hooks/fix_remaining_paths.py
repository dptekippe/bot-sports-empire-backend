#!/usr/bin/env python3
"""
Fix remaining hardcoded paths in hook files
"""

import os
import re
from pathlib import Path

def fix_file(file_path, patterns):
    """Fix hardcoded paths in a file"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    original = content
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)
    
    if content != original:
        with open(file_path, 'w') as f:
            f.write(content)
        return True
    return False

# Fix integration.py
integration_patterns = [
    (r"os\.path\.exists\('/Users/danieltekippe/\.openclaw/workspace/hooks'\)", 
     "os.path.exists(config.get('hooks_dir'))"),
    (r"os\.path\.exists\('/Users/danieltekippe/\.openclaw/workspace/memory_contract_compliance\.json'\)",
     "os.path.exists(config.get('compliance_file'))"),
    (r"os\.path\.exists\('/Users/danieltekippe/\.openclaw/workspace/DISABLE_MEMORY_CONTRACT'\)",
     "os.path.exists(config.get('kill_switch_file'))"),
]

# Fix memory_aware_tools.py
memory_aware_patterns = [
    (r"'/Users/danieltekippe/\.openclaw/workspace/hooks/search_log\.jsonl'",
     "config.get('search_log')"),
    (r"'/Users/danieltekippe/\.openclaw/workspace/hooks/write_log\.jsonl'",
     "config.get('write_log')"),
]

# Fix post_decision_memory.py
post_decision_patterns = [
    (r'log_file = "/Users/danieltekippe/\.openclaw/workspace/hooks/write_log\.jsonl"',
     'log_file = config.get("write_log")'),
    (r'error_file = "/Users/danieltekippe/\.openclaw/workspace/hooks/errors\.jsonl"',
     'error_file = config.get("error_log")'),
]

# Fix pre_action_memory.py
pre_action_patterns = [
    (r'log_file = "/Users/danieltekippe/\.openclaw/workspace/hooks/search_log\.jsonl"',
     'log_file = config.get("search_log")'),
]

def main():
    hooks_dir = Path(__file__).parent
    
    files_to_fix = [
        (hooks_dir / "integration.py", integration_patterns),
        (hooks_dir / "memory_aware_tools.py", memory_aware_patterns),
        (hooks_dir / "post_decision_memory.py", post_decision_patterns),
        (hooks_dir / "pre_action_memory.py", pre_action_patterns),
    ]
    
    print("Fixing remaining hardcoded paths...")
    print("=" * 60)
    
    for file_path, patterns in files_to_fix:
        if file_path.exists():
            print(f"\nFixing: {file_path.name}")
            if fix_file(file_path, patterns):
                print(f"  ✅ Fixed")
            else:
                print(f"  ⚠️  No changes needed")
        else:
            print(f"\n❌ File not found: {file_path.name}")
    
    # Verify fixes
    print("\n" + "=" * 60)
    print("Verifying fixes...")
    print("=" * 60)
    
    grep_result = os.popen(f"cd {hooks_dir} && grep -r 'danieltekippe' *.py 2>/dev/null | grep -v test_config_system | grep -v update_paths | grep -v fix_remaining_paths | grep -v config_loader").read()
    
    if grep_result.strip():
        print("❌ Still found hardcoded paths:")
        print(grep_result)
        return False
    else:
        print("✅ No hardcoded 'danieltekippe' paths found!")
        return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n" + "=" * 60)
        print("✅ ALL HARDCODED PATHS REMOVED")
        print("Phase 1, Task 2 complete!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ SOME PATHS REMAIN")
        print("Manual fixing needed")
        print("=" * 60)
    exit(0 if success else 1)