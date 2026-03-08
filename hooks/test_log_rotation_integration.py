#!/usr/bin/env python3
"""
Test log rotation integration end-to-end
"""

import os
import sys
import tempfile
import json
import time
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

print("=" * 60)
print("Log Rotation Integration Test")
print("=" * 60)

# Create test workspace
with tempfile.TemporaryDirectory() as temp_dir:
    os.environ["MEMORY_CONTRACT_WORKSPACE"] = temp_dir
    
    # Clear module cache
    import importlib
    import config_loader
    importlib.reload(config_loader)
    from config_loader import get_config
    
    config = get_config()
    
    print(f"Test workspace: {temp_dir}")
    print(f"Logs directory: {config.get('logs_dir')}")
    
    # Create logs directory
    logs_dir = config.get("logs_dir")
    os.makedirs(logs_dir, exist_ok=True)
    
    # Create test log files with different ages
    print("\nCreating test log files...")
    
    test_files = [
        ("recent_search.jsonl", 1),    # 1 day old - should be kept
        ("old_write.jsonl", 35),       # 35 days old - should be deleted
        ("medium_validation.jsonl", 10), # 10 days old - should be compressed
        ("very_old_error.jsonl", 60),  # 60 days old - should be deleted
    ]
    
    for filename, days_old in test_files:
        filepath = os.path.join(logs_dir, filename)
        with open(filepath, 'w') as f:
            for i in range(5):
                f.write(json.dumps({
                    "timestamp": "2026-03-06T00:00:00",
                    "file": filename,
                    "entry": i,
                    "test": True
                }) + "\n")
        
        # Set file modification time
        old_time = time.time() - (days_old * 24 * 60 * 60)
        os.utime(filepath, (old_time, old_time))
        
        print(f"  Created: {filename} ({days_old} days old)")
    
    # List files before rotation
    print("\nFiles before rotation:")
    for f in Path(logs_dir).glob("*"):
        print(f"  {f.name} ({f.stat().st_size} bytes)")
    
    # Run log rotation
    print("\nRunning log rotation...")
    from log_rotation_standalone import run_log_rotation_if_enabled
    result = run_log_rotation_if_enabled()
    
    print(f"\nRotation result: {json.dumps(result, indent=2)}")
    
    # List files after rotation
    print("\nFiles after rotation:")
    for f in Path(logs_dir).glob("*"):
        print(f"  {f.name} ({f.stat().st_size} bytes)")
    
    # Verify results
    print("\n" + "=" * 60)
    print("Verification Results")
    print("=" * 60)
    
    all_passed = True
    
    # Check deleted files
    deleted = result.get("results", {}).get("deleted", [])
    expected_deleted = ["old_write.jsonl", "very_old_error.jsonl"]
    
    for expected in expected_deleted:
        if expected in deleted:
            print(f"✅ {expected} correctly deleted (>30 days)")
        else:
            print(f"❌ {expected} should have been deleted")
            all_passed = False
    
    # Check compressed files
    compressed = result.get("results", {}).get("compressed", [])
    expected_compressed = ["medium_validation.jsonl"]
    
    for expected in expected_compressed:
        if expected in compressed:
            print(f"✅ {expected} correctly compressed (>7 days)")
            # Check .gz file exists
            gz_file = Path(logs_dir) / f"{expected}.gz"
            if gz_file.exists():
                print(f"  ✅ Compressed file created: {gz_file.name}")
            else:
                print(f"  ❌ Compressed file not found")
                all_passed = False
        else:
            print(f"❌ {expected} should have been compressed")
            all_passed = False
    
    # Check kept files
    kept = result.get("results", {}).get("kept", [])
    expected_kept = ["recent_search.jsonl"]
    
    for expected in expected_kept:
        if expected in kept:
            print(f"✅ {expected} correctly kept (<7 days)")
            # Check file still exists
            file = Path(logs_dir) / expected
            if file.exists():
                print(f"  ✅ File still exists: {file.name}")
            else:
                print(f"  ❌ File missing")
                all_passed = False
        else:
            print(f"❌ {expected} should have been kept")
            all_passed = False
    
    # Check rotation log was created
    rotation_log = Path(logs_dir) / "rotation_log.jsonl"
    if rotation_log.exists():
        print(f"✅ Rotation log created: {rotation_log.name}")
        with open(rotation_log, 'r') as f:
            log_entries = [json.loads(line) for line in f]
        print(f"  📊 Log entries: {len(log_entries)}")
    else:
        print(f"❌ Rotation log not created")
        all_passed = False
    
    # Test integration with session validation
    print("\n" + "=" * 60)
    print("Testing Session Validation Integration")
    print("=" * 60)
    
    try:
        from session_validation import validate_memory_capture
        
        # Run validation (which should include log rotation check)
        print("Running session validation (includes log rotation check)...")
        validation_report = validate_memory_capture()
        
        # Check if log rotation check was included
        log_rotation_checks = [
            check for check in validation_report.get("checks", [])
            if check.get("check") == "log_rotation"
        ]
        
        if log_rotation_checks:
            log_check = log_rotation_checks[0]
            print(f"✅ Log rotation check included in validation")
            print(f"  Status: {log_check.get('status')}")
            print(f"  Message: {log_check.get('details', {}).get('message', 'N/A')}")
            
            if log_check.get("status") == "PASS":
                print(f"  ✅ Log rotation passed validation")
            else:
                print(f"  ❌ Log rotation failed validation")
                all_passed = False
        else:
            print(f"❌ Log rotation check not found in validation")
            all_passed = False
            
    except Exception as e:
        print(f"❌ Error testing validation integration: {e}")
        import traceback
        traceback.print_exc()
        all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ LOG ROTATION INTEGRATION TEST PASSED")
        print("Log rotation is fully implemented and integrated")
        print("\nSummary:")
        print("- Standalone rotation function: ✅ Implemented")
        print("- Session validation integration: ✅ Working")
        print("- File deletion/compression: ✅ Working")
        print("- Rotation logging: ✅ Working")
    else:
        print("❌ LOG ROTATION INTEGRATION TEST FAILED")
    
    print("=" * 60)

if __name__ == "__main__":
    success = test_log_rotation_integration()
    exit(0 if success else 1)