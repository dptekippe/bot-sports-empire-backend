#!/usr/bin/env python3
"""
Session Validation Hook

Purpose: Validate memory capture at session end and periodically
"""

import os
import json
import datetime
from typing import Dict, List, Tuple

def check_todays_memory_exists() -> Dict:
    """Check if today's memory file exists"""
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    memory_file = os.path.join(config.get("memory_dir"), f"{today}.md")
    
    exists = os.path.exists(memory_file)
    
    return {
        "check": "today_memory_exists",
        "status": "PASS" if exists else "FAIL",
        "details": {"file": memory_file, "exists": exists}
    }

def check_memory_file_not_empty() -> Dict:
    """Check if today's memory file has content"""
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    memory_file = os.path.join(config.get("memory_dir"), f"{today}.md")
    
    if not os.path.exists(memory_file):
        return {
            "check": "memory_file_not_empty",
            "status": "FAIL",
            "details": {"file": memory_file, "error": "File does not exist"}
        }
    
    # TODO: Agent should use OpenClaw read tool to check memory file
    # Example: read(path=memory_file)
    print(f"[TODO] Would read memory file: {memory_file}")
    content = ""  # Placeholder
    
    # Count non-empty lines (excluding headers and whitespace)
    lines = [line.strip() for line in content.split('\n') if line.strip()]
    non_header_lines = [line for line in lines if not line.startswith('#')]
    
    has_content = len(non_header_lines) > 10  # White Roger's criteria: >10 lines
    
    return {
        "check": "memory_file_not_empty",
        "status": "PASS" if has_content else "FAIL",
        "details": {
            "file": memory_file,
            "total_lines": len(lines),
            "content_lines": len(non_header_lines),
            "has_content": has_content
        }
    }

def check_decisions_log_updated() -> Dict:
    """Check if decisions log has been updated recently"""
    decisions_file = config.get("decisions_file")
    
    if not os.path.exists(decisions_file):
        return {
            "check": "decisions_log_updated",
            "status": "FAIL",
            "details": {"file": decisions_file, "error": "File does not exist"}
        }
    
    # Check modification time
    mod_time = os.path.getmtime(decisions_file)
    mod_datetime = datetime.datetime.fromtimestamp(mod_time)
    time_diff = datetime.datetime.now() - mod_datetime
    
    # Consider updated if modified within last 24 hours
    recently_updated = time_diff.total_seconds() < 24 * 3600
    
    return {
        "check": "decisions_log_updated",
        "status": "PASS" if recently_updated else "WARN",
        "details": {
            "file": decisions_file,
            "last_modified": mod_datetime.isoformat(),
            "hours_since_mod": time_diff.total_seconds() / 3600,
            "recently_updated": recently_updated
        }
    }

def check_search_logs_populated() -> Dict:
    """Check if search logs have entries from today"""
    search_log = config.get("search_log")
    
    if not os.path.exists(search_log):
        return {
            "check": "search_logs_populated",
            "status": "FAIL",
            "details": {"file": search_log, "error": "File does not exist"}
        }
    
    today = datetime.datetime.now().strftime('%Y-%m-%d')
    today_searches = 0
    
    try:
        # TODO: Agent should use OpenClaw read tool to check search log
        # Example: read(path=search_log) then parse lines
        print(f"[TODO] Would read search log: {search_log}")
        # For now, assume no searches
        today_searches = 0
    except Exception as e:
        return {
            "check": "search_logs_populated",
            "status": "ERROR",
            "details": {"file": search_log, "error": str(e)}
        }
    
    # White Roger's criteria: ≥1 search per active session
    # For now, check if we have any searches today
    has_searches = today_searches > 0
    
    return {
        "check": "search_logs_populated",
        "status": "PASS" if has_searches else "WARN",
        "details": {
            "file": search_log,
            "today_searches": today_searches,
            "has_searches": has_searches
        }
    }

def check_backup_synced() -> Dict:
    """Check if git backup is recent"""
    # For now, check if workspace has .git directory
    git_dir = os.path.join(config.get("workspace"), ".git")
    
    git_exists = os.path.exists(git_dir)
    
    # White Roger's criteria: last commit <6 hours ago
    # This is a simplified check - in production would check actual commit times
    return {
        "check": "backup_synced",
        "status": "PASS" if git_exists else "WARN",
        "details": {
            "git_exists": git_exists,
            "note": "Full commit time check not implemented yet"
        }
    }

def generate_validation_report(checks: List[Dict]) -> Dict:
    """Generate a validation report from check results"""
    total_checks = len(checks)
    pass_count = sum(1 for check in checks if check['status'] == 'PASS')
    fail_count = sum(1 for check in checks if check['status'] == 'FAIL')
    warn_count = sum(1 for check in checks if check['status'] == 'WARN')
    error_count = sum(1 for check in checks if check['status'] == 'ERROR')
    
    overall_status = "PASS" if fail_count == 0 and error_count == 0 else "FAIL"
    
    report = {
        "timestamp": datetime.datetime.now().isoformat(),
        "overall_status": overall_status,
        "summary": {
            "total_checks": total_checks,
            "pass": pass_count,
            "fail": fail_count,
            "warn": warn_count,
            "error": error_count
        },
        "checks": checks,
        "recommendations": []
    }
    
    # Generate recommendations based on failures
    for check in checks:
        if check['status'] in ['FAIL', 'ERROR']:
            if check['check'] == 'today_memory_exists':
                report['recommendations'].append("Create today's memory file")
            elif check['check'] == 'memory_file_not_empty':
                report['recommendations'].append("Add content to memory file")
            elif check['check'] == 'decisions_log_updated':
                report['recommendations'].append("Update decisions log with recent decisions")
            elif check['check'] == 'search_logs_populated':
                report['recommendations'].append("Ensure pre-action memory searches are being performed")
    
    return report

def check_log_rotation() -> Dict:
    """Check if log rotation is working"""
    try:
        from log_rotation_standalone import run_log_rotation_if_enabled
        
        # Run log rotation
        rotation_result = run_log_rotation_if_enabled()
        
        if rotation_result.get("status") == "disabled":
            return {
                "check": "log_rotation",
                "status": "WARN",
                "details": {
                    "message": "Log rotation disabled in config",
                    "result": rotation_result
                }
            }
        elif rotation_result.get("status") == "error":
            return {
                "check": "log_rotation",
                "status": "FAIL",
                "details": {
                    "message": "Log rotation failed",
                    "error": rotation_result.get("error"),
                    "result": rotation_result
                }
            }
        else:
            # Log rotation ran successfully
            counts = rotation_result.get("counts", {})
            return {
                "check": "log_rotation",
                "status": "PASS",
                "details": {
                    "message": "Log rotation completed successfully",
                    "result": rotation_result,
                    "summary": f"Processed: {counts.get('total_processed', 0)}, "
                              f"Deleted: {counts.get('deleted', 0)}, "
                              f"Compressed: {counts.get('compressed', 0)}"
                }
            }
            
    except Exception as e:
        return {
            "check": "log_rotation",
            "status": "ERROR",
            "details": {
                "message": "Log rotation check failed",
                "error": str(e)
            }
        }

def send_alert(message: str):
    """Send alert for critical failures"""
    alert_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "level": "ALERT",
        "message": message
    }
    
    alert_file = config.get("alert_log")
    # TODO: Agent should use OpenClaw write tool to log alert
    # Example: write(path=alert_file, content=json.dumps(alert_entry) + '\n', append=True)
    print(f"[TODO] Would write alert to {alert_file}: {alert_entry}")
    
    print(f"[ALERT] {message}")

def validate_memory_capture() -> Dict:
    """
    Validate memory system is functioning
    
    Returns:
        Validation report dictionary
    """
    print("[Memory Contract] Running memory validation...")
    
    # Run all checks
    checks = [
        check_todays_memory_exists(),
        check_memory_file_not_empty(),
        check_decisions_log_updated(),
        check_search_logs_populated(),
        check_backup_synced(),
        check_log_rotation()  # NEW: Log rotation check
    ]
    
    # Generate validation report
    report = generate_validation_report(checks)
    
    # Alert if failures
    if report['overall_status'] == 'FAIL':
        alert_msg = f"Memory validation failed: {report['summary']['fail']} failures, {report['summary']['error']} errors"
        send_alert(alert_msg)
    
    # Log validation result
    validation_file = config.get("validation_log")
    # TODO: Agent should use OpenClaw write tool to log validation
    # Example: write(path=validation_file, content=json.dumps(report) + '\n', append=True)
    print(f"[TODO] Would write validation to {validation_file}: {report['overall_status']}")
    
    print(f"[Memory Contract] Validation complete: {report['overall_status']}")
    print(f"  Pass: {report['summary']['pass']}, Fail: {report['summary']['fail']}, Warn: {report['summary']['warn']}")
    
    return report

# Test function
if __name__ == "__main__":
    # Test the validation
    report = validate_memory_capture()
    print(f"Validation report: {json.dumps(report, indent=2)}")
from config_loader import get_config
config = get_config()