#!/usr/bin/env python3
"""
Compliance Tracker for Memory Contract

Purpose: Track and report compliance metrics for the Memory Contract system
"""

import os
import json
import datetime
import glob
import gzip
from typing import Dict, List
from pathlib import Path
from config_loader import get_config

config = get_config()

class ComplianceTracker:
    def __init__(self):
        self.compliance_file = config.get("compliance_file")
        self.initialize_compliance_file()
    
    def initialize_compliance_file(self):
        """Initialize compliance file if it doesn't exist"""
        if not os.path.exists(self.compliance_file):
            initial_data = {
                "created_at": datetime.datetime.now().isoformat(),
                "daily_metrics": {},
                "weekly_metrics": {},
                "alerts": [],
                "trends": {
                    "search_compliance": "unknown",
                    "write_compliance": "unknown",
                    "validation_success": "unknown"
                }
            }
            self.save_compliance_data(initial_data)
    
    def load_compliance_data(self) -> Dict:
        """Load compliance data from file"""
        # TODO: Agent should use OpenClaw read tool to load compliance data
        # Example: read(path=self.compliance_file)
        print(f"[TODO] Would load compliance data from {self.compliance_file}")
        
        # Return empty structure for now
        return {
            "daily_metrics": {},
            "weekly_metrics": {},
            "alerts": [],
            "trends": {}
        }
    
    def save_compliance_data(self, data: Dict):
        """Save compliance data to file"""
        # TODO: Agent should use OpenClaw write tool to save compliance data
        # Example: write(path=self.compliance_file, content=json.dumps(data, indent=2))
        print(f"[TODO] Would save compliance data to {self.compliance_file}: {json.dumps(data, indent=2)[:100]}...")
    
    def calculate_daily_metrics(self) -> Dict:
        """Calculate daily compliance metrics"""
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        
        # Count searches from search log
        search_log = config.get("search_log")
        today_searches = 0
        # TODO: Agent should use OpenClaw read tool to count searches
        # Example: read(path=search_log) then parse lines
        print(f"[TODO] Would count searches from {search_log}")
        
        # Count writes from write log
        write_log = config.get("write_log")
        today_writes = 0
        # TODO: Agent should use OpenClaw read tool to count writes
        # Example: read(path=write_log) then parse lines
        print(f"[TODO] Would count writes from {write_log}")
        
        # Count validations from validation log
        validation_log = config.get("validation_log")
        today_validations = 0
        today_validation_passes = 0
        # TODO: Agent should use OpenClaw read tool to count validations
        # Example: read(path=validation_log) then parse lines
        print(f"[TODO] Would count validations from {validation_log}")
        
        # Calculate compliance rates
        # For now, use simple thresholds
        search_compliance = "high" if today_searches >= 1 else "low"
        write_compliance = "high" if today_writes >= 1 else "low"
        validation_success_rate = today_validation_passes / max(today_validations, 1)
        validation_compliance = "high" if validation_success_rate >= 0.9 else "low"
        
        overall_compliance = "high" if all([
            search_compliance == "high",
            write_compliance == "high",
            validation_compliance == "high"
        ]) else "low"
        
        return {
            "date": today,
            "pre_action_searches": today_searches,
            "post_decision_writes": today_writes,
            "validation_runs": today_validations,
            "validation_passes": today_validation_passes,
            "compliance_rates": {
                "search": search_compliance,
                "write": write_compliance,
                "validation": validation_compliance,
                "overall": overall_compliance
            },
            "validation_success_rate": round(validation_success_rate * 100, 1)
        }
    
    def update_trends(self, daily_metrics: Dict):
        """Update trend analysis based on daily metrics"""
        data = self.load_compliance_data()
        
        # Simple trend analysis
        trends = data.get('trends', {})
        
        # Update search trend
        search_count = daily_metrics.get('pre_action_searches', 0)
        if 'previous_search_count' in trends:
            if search_count > trends['previous_search_count']:
                trends['search_compliance'] = "increasing"
            elif search_count < trends['previous_search_count']:
                trends['search_compliance'] = "decreasing"
            else:
                trends['search_compliance'] = "stable"
        trends['previous_search_count'] = search_count
        
        # Update write trend
        write_count = daily_metrics.get('post_decision_writes', 0)
        if 'previous_write_count' in trends:
            if write_count > trends['previous_write_count']:
                trends['write_compliance'] = "increasing"
            elif write_count < trends['previous_write_count']:
                trends['write_compliance'] = "decreasing"
            else:
                trends['write_compliance'] = "stable"
        trends['previous_write_count'] = write_count
        
        # Update validation trend
        validation_rate = daily_metrics.get('validation_success_rate', 0)
        if 'previous_validation_rate' in trends:
            if validation_rate > trends['previous_validation_rate']:
                trends['validation_success'] = "improving"
            elif validation_rate < trends['previous_validation_rate']:
                trends['validation_success'] = "declining"
            else:
                trends['validation_success'] = "stable"
        trends['previous_validation_rate'] = validation_rate
        
        data['trends'] = trends
        self.save_compliance_data(data)
    
    def add_alert(self, level: str, message: str):
        """Add an alert to the compliance tracker"""
        data = self.load_compliance_data()
        
        alert = {
            "timestamp": datetime.datetime.now().isoformat(),
            "level": level,  # INFO, WARNING, CRITICAL
            "message": message
        }
        
        data['alerts'].append(alert)
        
        # Keep only last 100 alerts
        if len(data['alerts']) > 100:
            data['alerts'] = data['alerts'][-100:]
        
        self.save_compliance_data(data)
    
    def update_daily_metrics(self):
        """Update daily compliance metrics"""
        data = self.load_compliance_data()
        
        # Calculate today's metrics
        daily_metrics = self.calculate_daily_metrics()
        today = daily_metrics['date']
        
        # Update daily metrics
        data['daily_metrics'][today] = daily_metrics
        
        # Update trends
        self.update_trends(daily_metrics)
        
        # Save updated data
        self.save_compliance_data(data)
        
        return daily_metrics
    
    def get_compliance_report(self) -> Dict:
        """Get current compliance report"""
        data = self.load_compliance_data()
        daily_metrics = self.calculate_daily_metrics()
        
        report = {
            "timestamp": datetime.datetime.now().isoformat(),
            "current_daily_metrics": daily_metrics,
            "trends": data.get('trends', {}),
            "recent_alerts": data.get('alerts', [])[-5:],  # Last 5 alerts
            "overall_status": daily_metrics['compliance_rates']['overall']
        }
        
        return report
    
    def rotate_logs(self):
        """Rotate and compress old log files based on config settings"""
        # TODO: Agent should implement log rotation using OpenClaw exec tool
        # This would involve shell commands for file operations
        logs_dir = config.get("logs_dir")
        keep_days = config.get("log_rotation.keep_days", 30)
        compress_after_days = config.get("log_rotation.compress_after_days", 7)
        
        print(f"[TODO] Would rotate logs in {logs_dir}, keep {keep_days} days, compress after {compress_after_days} days")
        
        # Return mock result for now
        return {
            "status": "todo",
            "deleted": [],
            "compressed": [],
            "kept": [],
            "total_processed": 0,
            "note": "Log rotation not implemented - agent should use OpenClaw exec tool"
        }
    
    def run_log_rotation(self):
        """Run log rotation if enabled in config"""
        if not config.get("features.enable_log_rotation", True):
            return {"status": "disabled", "reason": "log rotation disabled in config"}
        
        return self.rotate_logs()

def run_compliance_update():
    """Run compliance update and return report"""
    tracker = ComplianceTracker()
    
    # Run log rotation if enabled
    rotation_result = tracker.run_log_rotation()
    
    # Update metrics
    daily_metrics = tracker.update_daily_metrics()
    
    # Check for critical issues
    if daily_metrics['compliance_rates']['overall'] == 'low':
        tracker.add_alert(
            "WARNING",
            f"Low compliance detected: searches={daily_metrics['pre_action_searches']}, "
            f"writes={daily_metrics['post_decision_writes']}, "
            f"validation={daily_metrics['validation_success_rate']}%"
        )
    
    # Get and return report
    report = tracker.get_compliance_report()
    
    # Add log rotation result to report
    report['log_rotation'] = rotation_result
    
    return report

# Test function
if __name__ == "__main__":
    print("Running compliance tracker test...")
    
    # Initialize tracker
    tracker = ComplianceTracker()
    
    # Update metrics
    daily_metrics = tracker.update_daily_metrics()
    print(f"Daily metrics: {json.dumps(daily_metrics, indent=2)}")
    
    # Get report
    report = tracker.get_compliance_report()
    print(f"Compliance report: {json.dumps(report, indent=2)}")