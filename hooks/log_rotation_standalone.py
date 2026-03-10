#!/usr/bin/env python3
"""
Standalone log rotation implementation
Called during validation and can be scheduled independently
"""

import os
import glob
import gzip
import datetime
import json
from pathlib import Path
from config_loader import get_config

config = get_config()

def rotate_logs():
    """
    Rotate log files based on config settings:
    - Delete files older than keep_days (default: 30)
    - Compress files older than compress_after_days (default: 7)
    - Keep newer files unchanged
    """
    try:
        logs_dir = config.get("logs_dir")
        keep_days = config.get("log_rotation.keep_days", 30)
        compress_after_days = config.get("log_rotation.compress_after_days", 7)
        
        if not os.path.exists(logs_dir):
            return {
                "status": "skipped", 
                "reason": "logs_dir not found",
                "logs_dir": logs_dir
            }
        
        # Ensure logs directory exists
        os.makedirs(logs_dir, exist_ok=True)
        
        now = datetime.datetime.now()
        jsonl_files = glob.glob(os.path.join(logs_dir, "*.jsonl"))
        
        deleted = []
        compressed = []
        kept = []
        errors = []
        
        for file_path in jsonl_files:
            try:
                path = Path(file_path)
                if not path.exists():
                    continue
                    
                stat = path.stat()
                file_age = now - datetime.datetime.fromtimestamp(stat.st_mtime)
                
                # Delete files older than keep_days
                if file_age.days > keep_days:
                    path.unlink()
                    deleted.append(path.name)
                
                # Compress files older than compress_after_days
                elif file_age.days > compress_after_days:
                    gz_path = path.with_suffix('.jsonl.gz')
                    with open(path, 'rb') as f_in:
                        with gzip.open(gz_path, 'wb') as f_out:
                            f_out.write(f_in.read())
                    path.unlink()
                    compressed.append(path.name)
                
                # Keep newer files
                else:
                    kept.append(path.name)
                    
            except Exception as e:
                errors.append(f"{path.name}: {str(e)}")
        
        result = {
            "status": "success",
            "timestamp": now.isoformat(),
            "config": {
                "logs_dir": logs_dir,
                "keep_days": keep_days,
                "compress_after_days": compress_after_days
            },
            "results": {
                "deleted": deleted,
                "compressed": compressed,
                "kept": kept,
                "errors": errors
            },
            "counts": {
                "total_processed": len(jsonl_files),
                "deleted": len(deleted),
                "compressed": len(compressed),
                "kept": len(kept),
                "errors": len(errors)
            }
        }
        
        # Log the rotation result
        log_rotation_result(result)
        
        return result
        
    except Exception as e:
        error_result = {
            "status": "error",
            "timestamp": datetime.datetime.now().isoformat(),
            "error": str(e)
        }
        log_rotation_result(error_result)
        return error_result

def log_rotation_result(result):
    """Log rotation results to rotation log file"""
    try:
        rotation_log = os.path.join(config.get("logs_dir"), "rotation_log.jsonl")
        with open(rotation_log, 'a') as f:
            f.write(json.dumps(result) + "\n")
    except:
        pass  # Don't fail if logging fails

def is_log_rotation_enabled():
    """Check if log rotation is enabled in config"""
    return config.get("features.enable_log_rotation", True)

def run_log_rotation_if_enabled():
    """Run log rotation only if enabled in config"""
    if not is_log_rotation_enabled():
        return {
            "status": "disabled",
            "reason": "log rotation disabled in config",
            "timestamp": datetime.datetime.now().isoformat()
        }
    
    return rotate_logs()

if __name__ == "__main__":
    print("Running standalone log rotation...")
    result = run_log_rotation_if_enabled()
    print(json.dumps(result, indent=2))