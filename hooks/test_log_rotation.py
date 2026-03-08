#!/usr/bin/env python3
"""
Test log rotation functionality
"""

import os
import sys
import tempfile
import json
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from compliance_tracker import ComplianceTracker
from config_loader import get_config

def test_log_rotation():
    """Test log rotation functionality"""
    print("=" * 60)
    print("Testing Log Rotation")
    print("=" * 60)
    
    # Create test directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Set test workspace
        os.environ["MEMORY_CONTRACT_WORKSPACE"] = temp_dir
        
        # Clear module cache and reload
        import importlib
        import config_loader
        importlib.reload(config_loader)
        from config_loader import get_config as get_config_fresh
        config = get_config_fresh()
        
        # Create tracker
        tracker = ComplianceTracker()
        
        # Create test log files
        logs_dir = config.get("logs_dir")
        os.makedirs(logs_dir, exist_ok=True)
        
        # Create some test log files
        test_logs = [
            ("test_search.jsonl", 5),  # 5 days old
            ("test_write.jsonl", 35),  # 35 days old (should be deleted)
            ("test_validation.jsonl", 10),  # 10 days old (should be compressed)
        ]
        
        for filename, days_old in test_logs:
            filepath = os.path.join(logs_dir, filename)
            with open(filepath, 'w') as f:
                f.write(json.dumps({"test": "data", "file": filename}) + "\n")
            
            # Set file modification time to days_old days ago
            import time
            old_time = time.time() - (days_old * 24 * 60 * 60)
            os.utime(filepath, (old_time, old_time))
            print(f"Created: {filename} ({days_old} days old)")
        
        # Run log rotation
        print("\nRunning log rotation...")
        result = tracker.run_log_rotation()
        
        print(f"\nRotation result: {json.dumps(result, indent=2)}")
        
        # Check results
        print("\nChecking results:")
        
        # List remaining files
        remaining_files = list(Path(logs_dir).glob("*"))
        print(f"Remaining files in logs directory: {len(remaining_files)}")
        for f in remaining_files:
            print(f"  {f.name}")
        
        # Verify expectations
        expected_deleted = ["test_write.jsonl"]  # 35 days old > 30 day limit
        expected_compressed = ["test_validation.jsonl"]  # 10 days old > 7 day compress threshold
        expected_kept = ["test_search.jsonl"]  # 5 days old < both thresholds
        
        all_passed = True
        
        # Check deleted file
        if "test_write.jsonl" in result.get("deleted", []):
            print("✅ test_write.jsonl correctly deleted (35 days old > 30 day limit)")
        else:
            print("❌ test_write.jsonl should have been deleted")
            all_passed = False
        
        # Check compressed file
        if "test_validation.jsonl" in result.get("compressed", []):
            print("✅ test_validation.jsonl correctly compressed (10 days old > 7 day threshold)")
            # Check that .gz file exists
            gz_file = Path(logs_dir) / "test_validation.jsonl.gz"
            if gz_file.exists():
                print("✅ Compressed file created: test_validation.jsonl.gz")
            else:
                print("❌ Compressed file not found")
                all_passed = False
        else:
            print("❌ test_validation.jsonl should have been compressed")
            all_passed = False
        
        # Check kept file
        search_file = Path(logs_dir) / "test_search.jsonl"
        if search_file.exists():
            print("✅ test_search.jsonl correctly kept (5 days old < all thresholds)")
        else:
            print("❌ test_search.jsonl should have been kept")
            all_passed = False
        
        print("\n" + "=" * 60)
        if all_passed:
            print("✅ LOG ROTATION TEST PASSED")
            print("Log rotation is properly implemented")
        else:
            print("❌ LOG ROTATION TEST FAILED")
            print("Issues found in log rotation implementation")
        
        print("=" * 60)
        
        return all_passed

if __name__ == "__main__":
    success = test_log_rotation()
    exit(0 if success else 1)