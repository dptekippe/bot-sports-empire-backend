#!/usr/bin/env python3
"""
Simple log rotation implementation
"""

import os
import glob
import gzip
import datetime
from pathlib import Path
from config_loader import get_config

config = get_config()

def rotate_logs_simple():
    """Simple log rotation implementation"""
    logs_dir = config.get("logs_dir")
    keep_days = config.get("log_rotation.keep_days", 30)
    
    if not os.path.exists(logs_dir):
        return {"status": "skipped", "reason": "logs_dir not found"}
    
    now = datetime.datetime.now()
    results = {
        "deleted": [],
        "compressed": [],
        "kept": []
    }
    
    # Find all JSONL files
    jsonl_files = glob.glob(os.path.join(logs_dir, "*.jsonl"))
    
    for file_path in jsonl_files:
        path = Path(file_path)
        stat = path.stat()
        file_age = now - datetime.datetime.fromtimestamp(stat.st_mtime)
        
        if file_age.days > keep_days:
            # Delete old files
            path.unlink()
            results["deleted"].append(path.name)
        elif file_age.days > 7:
            # Compress files older than 7 days
            gz_path = path.with_suffix('.jsonl.gz')
            with open(path, 'rb') as f_in:
                with gzip.open(gz_path, 'wb') as f_out:
                    f_out.write(f_in.read())
            path.unlink()
            results["compressed"].append(path.name)
        else:
            # Keep files
            results["kept"].append(path.name)
    
    results["status"] = "success"
    results["total_processed"] = len(jsonl_files)
    return results

if __name__ == "__main__":
    print("Running simple log rotation...")
    result = rotate_logs_simple()
    import json
    print(json.dumps(result, indent=2))