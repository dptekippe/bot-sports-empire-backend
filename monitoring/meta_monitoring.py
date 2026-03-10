#!/usr/bin/env python3
"""
Meta-Monitoring Heartbeat
Monitors the monitoring system itself.
Runs every 30 minutes to ensure monitoring is working.
"""

import os
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Configuration
CONFIG = {
    "local_cache_path": "/Users/danieltekippe/.openclaw/workspace/monitoring/local_cache",
    "heartbeat_file": "meta_monitoring.json",
    "check_interval_minutes": 30,
    "alert_threshold_minutes": 45  # Alert if heartbeat missing for >45min
}

def check_monitoring_components():
    """Check if all monitoring components are working."""
    checks = {
        "local_cache": check_local_cache(),
        "system_health_file": check_system_health_file(),
        "monitoring_structure": check_monitoring_structure(),
        "recent_activity": check_recent_activity()
    }
    
    return checks

def check_local_cache():
    """Verify local cache directory exists and is writable."""
    cache_path = Path(CONFIG["local_cache_path"])
    
    if not cache_path.exists():
        return {"status": "failed", "reason": "Local cache directory not found"}
    
    # Test write permission
    test_file = cache_path / "test_write.tmp"
    try:
        test_file.write_text("test")
        test_file.unlink()
        return {"status": "operational"}
    except Exception as e:
        return {"status": "failed", "reason": f"Cannot write to cache: {str(e)}"}

def check_system_health_file():
    """Check if system health file exists and is valid JSON."""
    health_file = Path(CONFIG["local_cache_path"]) / "system_health.json"
    
    if not health_file.exists():
        return {"status": "failed", "reason": "System health file not found"}
    
    try:
        with open(health_file, 'r') as f:
            data = json.load(f)
        
        # Check timestamp is recent (within last hour)
        timestamp_str = data.get("timestamp", "")
        if timestamp_str:
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            age_minutes = (datetime.now(timezone.utc) - timestamp).total_seconds() / 60
            
            if age_minutes > 60:
                return {"status": "degraded", "reason": f"Health data stale ({age_minutes:.1f} minutes old)"}
        
        return {"status": "operational", "age_minutes": age_minutes}
    
    except json.JSONDecodeError as e:
        return {"status": "failed", "reason": f"Invalid JSON: {str(e)}"}
    except Exception as e:
        return {"status": "failed", "reason": f"Error reading file: {str(e)}"}

def check_monitoring_structure():
    """Verify monitoring directory structure."""
    required_dirs = [
        "local_cache",
        "local_cache/job_history",
        "local_cache/alerts",
        "local_cache/validation",
        "local_cache/metrics"
    ]
    
    base_path = Path("/Users/danieltekippe/.openclaw/workspace/monitoring")
    
    missing_dirs = []
    for dir_path in required_dirs:
        full_path = base_path / dir_path
        if not full_path.exists():
            missing_dirs.append(dir_path)
    
    if missing_dirs:
        return {"status": "degraded", "reason": f"Missing directories: {', '.join(missing_dirs)}"}
    
    return {"status": "operational"}

def check_recent_activity():
    """Check for recent monitoring activity."""
    # Look for recent files in local cache
    cache_path = Path(CONFIG["local_cache_path"])
    recent_files = []
    
    for file_path in cache_path.rglob("*.json"):
        if file_path.is_file():
            mtime = file_path.stat().st_mtime
            age_minutes = (time.time() - mtime) / 60
            
            if age_minutes < 60:  # Files updated in last hour
                recent_files.append({
                    "name": file_path.name,
                    "age_minutes": age_minutes
                })
    
    if not recent_files:
        return {"status": "degraded", "reason": "No recent monitoring activity"}
    
    return {"status": "operational", "recent_files": len(recent_files)}

def update_heartbeat(checks):
    """Update meta-monitoring heartbeat file."""
    now = datetime.now(timezone.utc)
    heartbeat_data = {
        "timestamp": now.isoformat().replace('+00:00', 'Z'),
        "overall_status": "operational",
        "checks": checks,
        "next_check": (now + timedelta(minutes=CONFIG["check_interval_minutes"])).isoformat().replace('+00:00', 'Z')
    }
    
    # Determine overall status
    all_operational = all(check["status"] == "operational" for check in checks.values())
    any_failed = any(check["status"] == "failed" for check in checks.values())
    
    if any_failed:
        heartbeat_data["overall_status"] = "failed"
    elif not all_operational:
        heartbeat_data["overall_status"] = "degraded"
    
    # Write heartbeat file
    heartbeat_path = Path(CONFIG["local_cache_path"]) / CONFIG["heartbeat_file"]
    with open(heartbeat_path, 'w') as f:
        json.dump(heartbeat_data, f, indent=2)
    
    return heartbeat_data

def check_previous_heartbeat():
    """Check if previous heartbeat was on time."""
    heartbeat_path = Path(CONFIG["local_cache_path"]) / CONFIG["heartbeat_file"]
    
    if not heartbeat_path.exists():
        return {"status": "first_run", "message": "No previous heartbeat found"}
    
    try:
        with open(heartbeat_path, 'r') as f:
            previous = json.load(f)
        
        prev_timestamp = datetime.fromisoformat(previous["timestamp"].replace('Z', '+00:00'))
        age_minutes = (datetime.now(timezone.utc) - prev_timestamp).total_seconds() / 60
        
        if age_minutes > CONFIG["alert_threshold_minutes"]:
            return {
                "status": "late",
                "age_minutes": age_minutes,
                "threshold": CONFIG["alert_threshold_minutes"]
            }
        
        return {
            "status": "on_time",
            "age_minutes": age_minutes
        }
    
    except Exception as e:
        return {"status": "error", "reason": str(e)}

def main():
    """Main meta-monitoring heartbeat function."""
    print("🔍 Meta-Monitoring Heartbeat Check")
    print(f"Time: {datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')}")
    
    # Check previous heartbeat
    prev_check = check_previous_heartbeat()
    print(f"Previous heartbeat: {prev_check['status']}")
    if prev_check.get('age_minutes'):
        print(f"  Age: {prev_check['age_minutes']:.1f} minutes")
    
    # Run component checks
    print("\nRunning component checks:")
    checks = check_monitoring_components()
    
    for component, result in checks.items():
        status_icon = "✅" if result["status"] == "operational" else "⚠️" if result["status"] == "degraded" else "❌"
        print(f"  {status_icon} {component}: {result['status']}")
        if "reason" in result:
            print(f"    Reason: {result['reason']}")
    
    # Update heartbeat
    heartbeat_data = update_heartbeat(checks)
    
    print(f"\n📊 Overall status: {heartbeat_data['overall_status'].upper()}")
    print(f"📝 Heartbeat updated: {heartbeat_data['timestamp']}")
    print(f"⏰ Next check: {heartbeat_data['next_check']}")
    
    # Return overall status for cron job
    return 0 if heartbeat_data["overall_status"] == "operational" else 1

if __name__ == "__main__":
    exit(main())