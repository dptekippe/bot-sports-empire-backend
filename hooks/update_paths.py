#!/usr/bin/env python3
"""
Update hardcoded paths to use config system
"""

import os
import re
from pathlib import Path

# Mapping of hardcoded paths to config keys
PATH_MAPPINGS = {
    # File: (regex_pattern, replacement_template)
    "pre_action_memory.py": [
        (r'"/Users/danieltekippe/.openclaw/workspace/hooks/warnings\.jsonl"', 
         'config.get("logs_dir") + "/warnings.jsonl"'),
        (r'"/Users/danieltekippe/.openclaw/workspace/memory/\{today\}\.md"',
         'os.path.join(config.get("memory_dir"), f"{today}.md")'),
    ],
    "post_decision_memory.py": [
        (r'memory_dir = "/Users/danieltekippe/.openclaw/workspace/memory"',
         'memory_dir = config.get("memory_dir")'),
        (r'"/Users/danieltekippe/.openclaw/workspace/DECISIONS\.md"',
         'config.get("decisions_file")'),
    ],
    "session_validation.py": [
        (r'"/Users/danieltekippe/.openclaw/workspace/memory/\{today\}\.md"',
         'os.path.join(config.get("memory_dir"), f"{today}.md")'),
        (r'"/Users/danieltekippe/.openclaw/workspace/DECISIONS\.md"',
         'config.get("decisions_file")'),
        (r'"/Users/danieltekippe/.openclaw/workspace/hooks/search_log\.jsonl"',
         'config.get("search_log")'),
        (r'"/Users/danieltekippe/.openclaw/workspace/hooks/write_log\.jsonl"',
         'config.get("write_log")'),
        (r'"/Users/danieltekippe/.openclaw/workspace/hooks/validation_log\.jsonl"',
         'config.get("validation_log")'),
        (r'"/Users/danieltekippe/.openclaw/workspace/hooks/errors\.jsonl"',
         'config.get("error_log")'),
        (r'"/Users/danieltekippe/.openclaw/workspace/hooks/alerts\.jsonl"',
         'config.get("alert_log")'),
        (r'"/Users/danieltekippe/.openclaw/workspace/\.git"',
         'os.path.join(config.get("workspace"), ".git")'),
    ],
    "compliance_tracker.py": [
        (r'"/Users/danieltekippe/.openclaw/workspace/memory_contract_compliance\.json"',
         'config.get("compliance_file")'),
        (r'"/Users/danieltekippe/.openclaw/workspace/hooks/search_log\.jsonl"',
         'config.get("search_log")'),
        (r'"/Users/danieltekippe/.openclaw/workspace/hooks/write_log\.jsonl"',
         'config.get("write_log")'),
        (r'"/Users/danieltekippe/.openclaw/workspace/hooks/validation_log\.jsonl"',
         'config.get("validation_log")'),
    ],
    "memory_aware_tools.py": [
        (r'"/Users/danieltekippe/.openclaw/workspace/hooks"',
         'config.get("hooks_dir")'),
    ],
    "integration.py": [
        (r'"/Users/danieltekippe/.openclaw/workspace/DISABLE_MEMORY_CONTRACT"',
         'config.get("kill_switch_file")'),
    ],
}

# Common imports to add
CONFIG_IMPORT = "from config_loader import get_config\n"
OS_IMPORT = "import os\n"

def update_file(file_path):
    """Update a single file to use config system"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    original_content = content
    file_name = Path(file_path).name
    
    # Add imports if needed
    if "from config_loader import get_config" not in content:
        # Find where to insert import (after other imports)
        lines = content.split('\n')
        import_end = 0
        for i, line in enumerate(lines):
            if line.strip() and not (line.startswith('import ') or line.startswith('from ')):
                import_end = i
                break
        
        if import_end == 0:
            import_end = len(lines)
        
        lines.insert(import_end, CONFIG_IMPORT.strip())
        content = '\n'.join(lines)
    
    if "import os" not in content and "os.path" in PATH_MAPPINGS.get(file_name, []):
        lines = content.split('\n')
        import_end = 0
        for i, line in enumerate(lines):
            if line.strip() and not (line.startswith('import ') or line.startswith('from ')):
                import_end = i
                break
        
        if import_end == 0:
            import_end = len(lines)
        
        lines.insert(import_end, OS_IMPORT.strip())
        content = '\n'.join(lines)
    
    # Add config = get_config() after imports if not present
    if "config = get_config()" not in content:
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if "from config_loader import get_config" in line:
                # Insert config = get_config() after a blank line or at end of imports
                insert_point = i + 1
                while insert_point < len(lines) and (lines[insert_point].startswith('import ') or 
                                                     lines[insert_point].startswith('from ')):
                    insert_point += 1
                lines.insert(insert_point, "config = get_config()")
                break
        content = '\n'.join(lines)
    
    # Apply path replacements
    if file_name in PATH_MAPPINGS:
        for pattern, replacement in PATH_MAPPINGS[file_name]:
            # Check if pattern exists
            if re.search(pattern, content):
                content = re.sub(pattern, replacement, content)
                print(f"  Replaced: {pattern[:50]}...")
    
    # Write back if changed
    if content != original_content:
        with open(file_path, 'w') as f:
            f.write(content)
        return True
    else:
        return False

def check_hardcoded_paths(file_path):
    """Check if file contains hardcoded paths"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    file_name = Path(file_path).name
    issues = []
    
    # Check for danieltekippe
    if "danieltekippe" in content:
        issues.append("Contains 'danieltekippe'")
    
    # Check for hardcoded /Users/ paths
    if "/Users/" in content and "workspace" in content:
        issues.append("Contains hardcoded /Users/ path")
    
    # Check for config usage
    uses_config = "config.get" in content or "get_config()" in content
    
    return issues, uses_config

def main():
    hooks_dir = Path(__file__).parent
    updated_files = []
    
    print("Updating hook files to use config system...")
    print("=" * 60)
    
    # First, check current state
    print("\nCurrent state (before update):")
    for py_file in hooks_dir.glob("*.py"):
        if py_file.name in ["config_loader.py", "test_config_system.py", "update_paths.py"]:
            continue
        
        issues, uses_config = check_hardcoded_paths(py_file)
        if issues:
            print(f"❌ {py_file.name}: {', '.join(issues)}")
        elif uses_config:
            print(f"✅ {py_file.name}: Already uses config system")
        else:
            print(f"⚠️  {py_file.name}: No hardcoded paths, but doesn't use config")
    
    # Update files
    print("\n\nUpdating files...")
    for py_file in hooks_dir.glob("*.py"):
        if py_file.name in ["config_loader.py", "test_config_system.py", "update_paths.py"]:
            continue
        
        print(f"\nProcessing: {py_file.name}")
        if update_file(py_file):
            updated_files.append(py_file.name)
            print(f"  ✅ Updated")
        else:
            print(f"  ⚠️  No changes needed")
    
    # Check final state
    print("\n\nFinal state (after update):")
    all_good = True
    for py_file in hooks_dir.glob("*.py"):
        if py_file.name in ["config_loader.py", "test_config_system.py", "update_paths.py"]:
            continue
        
        issues, uses_config = check_hardcoded_paths(py_file)
        if issues:
            print(f"❌ {py_file.name}: {', '.join(issues)}")
            all_good = False
        elif uses_config:
            print(f"✅ {py_file.name}: Uses config system")
        else:
            print(f"⚠️  {py_file.name}: Check needed")
            all_good = False
    
    print("\n" + "=" * 60)
    if all_good:
        print("✅ ALL FILES UPDATED SUCCESSFULLY")
        print(f"Updated {len(updated_files)} files: {', '.join(updated_files)}")
    else:
        print("❌ SOME FILES STILL HAVE ISSUES")
        print("Manual review needed")
    
    # Run grep test
    print("\n" + "=" * 60)
    print("Running grep test for hardcoded paths...")
    os.system(f"cd {hooks_dir} && grep -r 'danieltekippe' *.py 2>/dev/null | grep -v test_config_system | grep -v update_paths || echo 'No hardcoded paths found'")
    
    return all_good

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)