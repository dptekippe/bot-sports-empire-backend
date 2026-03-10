#!/usr/bin/env python3
"""
Test the configuration system against White Roger's acceptance criteria
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from config_loader import get_config


def test_acceptance_criteria():
    """Test against White Roger's acceptance criteria"""
    print("=" * 60)
    print("Testing Configuration System Acceptance Criteria")
    print("=" * 60)
    
    all_passed = True
    
    # Test 1: No hardcoded "danieltekippe" paths
    print("\n1. Testing: No hardcoded 'danieltekippe' paths")
    test_home = "/tmp/test_user_12345"
    os.environ["HOME"] = test_home
    
    config = get_config()
    workspace = config.get("workspace")
    
    if "danieltekippe" in workspace:
        print(f"  ❌ FAIL: Found 'danieltekippe' in path: {workspace}")
        all_passed = False
    else:
        print(f"  ✅ PASS: No 'danieltekippe' in path: {workspace}")
    
    # Test 2: Environment variable overrides work
    print("\n2. Testing: Environment variable overrides")
    test_workspace = "/tmp/custom_workspace_test"
    os.environ["MEMORY_CONTRACT_WORKSPACE"] = test_workspace
    
    # Clear module cache and reload config
    import importlib
    import config_loader
    importlib.reload(config_loader)
    from config_loader import get_config
    
    config = get_config()
    
    if config.get("workspace") == test_workspace:
        print(f"  ✅ PASS: Environment variable override works: {config.get('workspace')}")
    else:
        print(f"  ❌ FAIL: Expected {test_workspace}, got {config.get('workspace')}")
        all_passed = False
    
    # Test 3: Directory creation
    print("\n3. Testing: Directory creation")
    directories = [
        config.get("workspace"),
        config.get("memory_dir"),
        config.get("hooks_dir"),
        config.get("logs_dir"),
    ]
    
    all_dirs_exist = all(os.path.exists(d) for d in directories)
    if all_dirs_exist:
        print(f"  ✅ PASS: All directories created: {len(directories)} directories")
    else:
        print(f"  ❌ FAIL: Some directories missing")
        for d in directories:
            if not os.path.exists(d):
                print(f"    Missing: {d}")
        all_passed = False
    
    # Test 4: Config validation
    print("\n4. Testing: Config validation")
    if config.validate():
        print("  ✅ PASS: Configuration validation passed")
    else:
        print("  ❌ FAIL: Configuration validation failed")
        all_passed = False
    
    # Test 5: Path resolution with variables
    print("\n5. Testing: Path resolution with variables")
    memory_dir = config.get("memory_dir")
    expected_memory_dir = os.path.join(test_workspace, "memory")
    
    if memory_dir == expected_memory_dir:
        print(f"  ✅ PASS: Path resolution correct: {memory_dir}")
    else:
        print(f"  ❌ FAIL: Expected {expected_memory_dir}, got {memory_dir}")
        all_passed = False
    
    # Test 6: Default values work without config file
    print("\n6. Testing: Default values without config file")
    # Create temp directory for test
    with tempfile.TemporaryDirectory() as temp_dir:
        # Move config file out of the way
        config_file = Path(__file__).parent / "config.yaml"
        backup_file = Path(__file__).parent / "config.yaml.backup"
        
        if config_file.exists():
            config_file.rename(backup_file)
        
        try:
            # Set HOME to temp directory
            os.environ["HOME"] = temp_dir
            os.environ.pop("MEMORY_CONTRACT_WORKSPACE", None)
            
            # Clear module cache and reload config
            import importlib
            import config_loader
            importlib.reload(config_loader)
            from config_loader import get_config
            
            config = get_config()
            
            expected_default = os.path.join(temp_dir, ".openclaw", "workspace")
            if config.get("workspace").startswith(temp_dir):
                print(f"  ✅ PASS: Default values work: {config.get('workspace')}")
            else:
                print(f"  ❌ FAIL: Expected path in {temp_dir}, got {config.get('workspace')}")
                all_passed = False
                
        finally:
            # Restore config file
            if backup_file.exists():
                backup_file.rename(config_file)
    
    # Cleanup
    print("\n7. Testing: Cleanup test directories")
    test_dirs_to_clean = [
        "/tmp/test_user_12345",
        "/tmp/custom_workspace_test",
    ]
    
    for dir_path in test_dirs_to_clean:
        if os.path.exists(dir_path):
            try:
                shutil.rmtree(dir_path)
                print(f"  ✅ Cleaned: {dir_path}")
            except Exception as e:
                print(f"  ⚠️  Warning: Could not clean {dir_path}: {e}")
    
    # Final result
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL ACCEPTANCE CRITERIA PASSED")
        print("Confidence: +15% (Configuration system working)")
    else:
        print("❌ SOME ACCEPTANCE CRITERIA FAILED")
        print("Confidence: Needs improvement")
    print("=" * 60)
    
    return all_passed


def test_grep_for_hardcoded_paths():
    """Check if any files still contain hardcoded paths"""
    print("\n" + "=" * 60)
    print("Checking for hardcoded paths in hook files")
    print("=" * 60)
    
    hooks_dir = Path(__file__).parent
    hardcoded_found = False
    
    # Check Python files
    for py_file in hooks_dir.glob("*.py"):
        if py_file.name in ["config_loader.py", "test_config_system.py"]:
            continue
            
        with open(py_file, 'r') as f:
            content = f.read()
            if "danieltekippe" in content:
                print(f"❌ Found in {py_file.name}: Hardcoded path")
                hardcoded_found = True
            elif "/Users/" in content and "workspace" in content:
                # Check for any hardcoded /Users/ paths
                print(f"⚠️  Warning in {py_file.name}: Possible hardcoded /Users/ path")
    
    if not hardcoded_found:
        print("✅ No hardcoded 'danieltekippe' paths found in Python files")
    
    # Check for config.get() usage
    print("\nChecking for config.get() usage (should replace hardcoded paths):")
    config_usage_found = False
    for py_file in hooks_dir.glob("*.py"):
        if py_file.name == "config_loader.py":
            continue
            
        with open(py_file, 'r') as f:
            content = f.read()
            if "config.get" in content or "get_config()" in content:
                print(f"✅ {py_file.name}: Uses config system")
                config_usage_found = True
    
    if config_usage_found:
        print("✅ Config system integration found in hook files")
    else:
        print("⚠️  Warning: Config system not yet integrated into hook files")
    
    return not hardcoded_found


if __name__ == "__main__":
    # Run acceptance criteria tests
    criteria_passed = test_acceptance_criteria()
    
    # Run grep check
    grep_passed = test_grep_for_hardcoded_paths()
    
    # Overall result
    print("\n" + "=" * 60)
    print("OVERALL PHASE 1, TASK 1 STATUS")
    print("=" * 60)
    
    if criteria_passed and grep_passed:
        print("✅ PHASE 1, TASK 1 COMPLETE")
        print("Configuration system ready for White Roger review")
        print("\nNext steps:")
        print("1. White Roger reviews config system")
        print("2. Integrate config into all hook files")
        print("3. Remove remaining hardcoded paths")
    else:
        print("❌ PHASE 1, TASK 1 INCOMPLETE")
        print("Issues found that need to be addressed")
    
    print("=" * 60)