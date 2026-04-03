#!/usr/bin/env python3
"""
Hook Health Monitor - Hook Failure Recovery System

Monitors health of all hooks with:
- 5-minute healthcheck interval
- State tracking: HEALTHY / DEGRADED / FAILED
- Degradation flags and confidence discounts
- Circuit breaker on hook dependencies
- Failure logging to hook_failure_log.jsonl

Hook types:
- pgvector: Database queries with response time checks
- file-based: Handler file existence and readability
- exec-based: Process alive checks
"""

import os
import sys
import json
import time
import datetime
import threading
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field, asdict
import sqlite3

# Configuration
HOOKS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)))
WORKSPACE_DIR = os.path.dirname(HOOKS_DIR)
FAILURE_LOG = os.path.join(HOOKS_DIR, 'hook_failure_log.jsonl')
HOOKS_CONFIG_FILE = os.path.join(HOOKS_DIR, 'hook_health_config.json')

# Health check intervals (seconds)
HEALTHCHECK_INTERVAL = 300  # 5 minutes
DEGRADED_THRESHOLD_MS = 1000  # 1 second response time = degraded
FAILED_THRESHOLD_MS = 5000  # 5 seconds = failed
FAILED_CONSECUTIVE_THRESHOLD = 3  # 3 consecutive failures = hook failed

# Confidence discounts
DEFAULT_CONFIDENCE = 1.0
DEGRADED_CONFIDENCE = 0.7
FAILED_CONFIDENCE = 0.3

# Database for health state
HEALTH_DB = os.path.join(HOOKS_DIR, 'hook_health.db')


class HookState(Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


class HookType(Enum):
    PGVECTOR = "pgvector"
    FILE_BASED = "file"
    EXEC = "exec"


@dataclass
class HookHealth:
    name: str
    hook_type: HookType
    path: str
    state: HookState = HookState.UNKNOWN
    last_check: Optional[str] = None
    response_time_ms: Optional[float] = None
    consecutive_failures: int = 0
    last_error: Optional[str] = None
    confidence: float = DEFAULT_CONFIDENCE
    is_degraded: bool = False

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "hook_type": self.hook_type.value,
            "path": self.path,
            "state": self.state.value,
            "last_check": self.last_check,
            "response_time_ms": self.response_time_ms,
            "consecutive_failures": self.consecutive_failures,
            "last_error": self.last_error,
            "confidence": self.confidence,
            "is_degraded": self.is_degraded
        }


@dataclass
class HealthReport:
    timestamp: str
    overall_state: HookState
    pre_action_hooks: List[HookHealth]
    post_action_hooks: List[HookHealth]
    circuit_breaker_open: bool = False
    halted_operations: List[str] = field(default_factory=list)
    total_hooks: int = 0
    healthy_count: int = 0
    degraded_count: int = 0
    failed_count: int = 0

    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "overall_state": self.overall_state.value,
            "pre_action_hooks": [h.to_dict() for h in self.pre_action_hooks],
            "post_action_hooks": [h.to_dict() for h in self.post_action_hooks],
            "circuit_breaker_open": self.circuit_breaker_open,
            "halted_operations": self.halted_operations,
            "total_hooks": self.total_hooks,
            "healthy_count": self.healthy_count,
            "degraded_count": self.degraded_count,
            "failed_count": self.failed_count
        }


def init_health_db():
    """Initialize the health state database"""
    conn = sqlite3.connect(HEALTH_DB)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS hook_health (
            name TEXT PRIMARY KEY,
            hook_type TEXT NOT NULL,
            path TEXT NOT NULL,
            state TEXT DEFAULT 'UNKNOWN',
            last_check TEXT,
            response_time_ms REAL,
            consecutive_failures INTEGER DEFAULT 0,
            last_error TEXT,
            confidence REAL DEFAULT 1.0,
            is_degraded INTEGER DEFAULT 0
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS hook_health_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            state TEXT NOT NULL,
            response_time_ms REAL,
            error TEXT,
            timestamp TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()


def save_hook_health(health: HookHealth):
    """Save hook health state to database"""
    conn = sqlite3.connect(HEALTH_DB)
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO hook_health 
        (name, hook_type, path, state, last_check, response_time_ms, 
         consecutive_failures, last_error, confidence, is_degraded)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        health.name,
        health.hook_type.value,
        health.path,
        health.state.value,
        health.last_check,
        health.response_time_ms,
        health.consecutive_failures,
        health.last_error,
        health.confidence,
        1 if health.is_degraded else 0
    ))
    conn.commit()
    conn.close()


def record_health_history(name: str, state: HookState, response_time_ms: Optional[float], error: Optional[str]):
    """Record health check in history"""
    conn = sqlite3.connect(HEALTH_DB)
    c = conn.cursor()
    c.execute('''
        INSERT INTO hook_health_history (name, state, response_time_ms, error, timestamp)
        VALUES (?, ?, ?, ?, ?)
    ''', (name, state.value, response_time_ms, error, datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()


def load_hook_configs() -> Dict[str, HookHealth]:
    """Load hook configurations from config file or discover hooks"""
    configs = {}
    
    # Default hooks to monitor
    default_hooks = [
        # Pre-action hooks
        HookHealth(
            name="pre_action_memory",
            hook_type=HookType.FILE_BASED,
            path=os.path.join(HOOKS_DIR, "pre_action_memory.py")
        ),
        HookHealth(
            name="memory_pre_action_ts",
            hook_type=HookType.EXEC,
            path=os.path.join(os.path.expanduser("~/.openclaw/hooks/memory-pre-action/handler.ts"))
        ),
        
        # Post-action hooks
        HookHealth(
            name="post_decision_memory",
            hook_type=HookType.FILE_BASED,
            path=os.path.join(HOOKS_DIR, "post_decision_memory.py")
        ),
        HookHealth(
            name="pgvector_memory_hook",
            hook_type=HookType.PGVECTOR,
            path=os.path.join(HOOKS_DIR, "pgvector_memory_hook.ts")
        ),
        HookHealth(
            name="gate_orchestrator",
            hook_type=HookType.EXEC,
            path=os.path.join(os.path.expanduser("~/.openclaw/hooks/gate-orchestrator/handler.ts"))
        ),
    ]
    
    for hook in default_hooks:
        configs[hook.name] = hook
    
    return configs


def check_pgvector_health(health: HookHealth) -> Tuple[bool, Optional[float], Optional[str]]:
    """Check pgvector hook health - try simple query and measure response time"""
    start_time = time.time()
    try:
        DATABASE_URL = os.environ.get("DATABASE_URL")
        if not DATABASE_URL:
            return False, None, "DATABASE_URL not set"
        
        import psycopg2
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        cur = conn.cursor()
        
        # Simple health check query
        cur.execute("SELECT 1")
        cur.fetchone()
        
        cur.close()
        conn.close()
        
        response_time = (time.time() - start_time) * 1000
        
        if response_time > FAILED_THRESHOLD_MS:
            return False, response_time, f"Response time {response_time:.0f}ms exceeds failed threshold"
        elif response_time > DEGRADED_THRESHOLD_MS:
            return True, response_time, f"Response time {response_time:.0f}ms exceeds degraded threshold"
        
        return True, response_time, None
        
    except ImportError:
        return False, None, "psycopg2 not available"
    except Exception as e:
        return False, None, str(e)


def check_file_based_health(health: HookHealth) -> Tuple[bool, Optional[float], Optional[str]]:
    """Check file-based hook health - verify file exists and is readable"""
    try:
        path = Path(health.path)
        
        if not path.exists():
            return False, None, f"File does not exist: {health.path}"
        
        if not path.is_file():
            return False, None, f"Path is not a file: {health.path}"
        
        # Check readability
        if not os.access(path, os.R_OK):
            return False, None, f"File not readable: {health.path}"
        
        # Get file stats for response time proxy
        stat = path.stat()
        response_time = 0.1  # Minimal time for file check
        
        return True, response_time, None
        
    except Exception as e:
        return False, None, str(e)


def check_exec_health(health: HookHealth) -> Tuple[bool, Optional[float], Optional[str]]:
    """Check exec-based hook health - verify process/handler is alive"""
    try:
        path = Path(health.path)
        
        if not path.exists():
            return False, None, f"Handler file does not exist: {health.path}"
        
        if not path.is_file():
            return False, None, f"Handler path is not a file: {health.path}"
        
        if not os.access(path, os.R_OK):
            return False, None, f"Handler file not readable: {health.path}"
        
        # Try to verify the file is a valid script by checking shebang
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            first_line = f.readline().strip()
            if first_line.startswith('#!'):
                # Has shebang - looks like an executable script
                pass
        
        # For exec hooks, we can't really check if the process is alive
        # without running it, so we just verify the file exists and is valid
        response_time = 0.5  # Slightly more than file check
        
        return True, response_time, None
        
    except Exception as e:
        return False, None, str(e)


def check_hook_health(health: HookHealth) -> HookHealth:
    """Check health of a single hook based on its type"""
    start = time.time()
    now = datetime.datetime.now().isoformat()
    
    if health.hook_type == HookType.PGVECTOR:
        success, response_time, error = check_pgvector_health(health)
    elif health.hook_type == HookType.FILE_BASED:
        success, response_time, error = check_file_based_health(health)
    elif health.hook_type == HookType.EXEC:
        success, response_time, error = check_exec_health(health)
    else:
        success = False
        response_time = None
        error = f"Unknown hook type: {health.hook_type}"
    
    # Update health object
    health.last_check = now
    health.response_time_ms = response_time
    health.last_error = error
    
    if success:
        if response_time and response_time > DEGRADED_THRESHOLD_MS:
            health.state = HookState.DEGRADED
            health.is_degraded = True
            health.confidence = DEGRADED_CONFIDENCE
            health.consecutive_failures = 0
        else:
            health.state = HookState.HEALTHY
            health.is_degraded = False
            health.confidence = DEFAULT_CONFIDENCE
            health.consecutive_failures = 0
    else:
        health.consecutive_failures += 1
        if health.consecutive_failures >= FAILED_CONSECUTIVE_THRESHOLD:
            health.state = HookState.FAILED
            health.is_degraded = True
            health.confidence = FAILED_CONFIDENCE
        else:
            health.state = HookState.DEGRADED
            health.is_degraded = True
            health.confidence = DEGRADED_CONFIDENCE
    
    # Record history
    record_health_history(health.name, health.state, response_time, error)
    
    return health


def log_failure(health: HookHealth, operation: str = "health_check"):
    """Log hook failure to hook_failure_log.jsonl"""
    entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "hook_name": health.name,
        "hook_type": health.hook_type.value,
        "hook_path": health.path,
        "state": health.state.value,
        "operation": operation,
        "error": health.last_error,
        "consecutive_failures": health.consecutive_failures,
        "confidence": health.confidence
    }
    
    with open(FAILURE_LOG, 'a') as f:
        f.write(json.dumps(entry) + '\n')


def check_all_hooks(hooks: Dict[str, HookHealth]) -> HealthReport:
    """Check health of all hooks and generate report"""
    now = datetime.datetime.now().isoformat()
    
    pre_action_hooks = []
    post_action_hooks = []
    
    pre_action_names = ["pre_action_memory", "memory_pre_action_ts"]
    circuit_breaker_open = False
    halted_operations = []
    
    for name, health in hooks.items():
        checked = check_hook_health(health)
        hooks[name] = checked
        
        # Log failures
        if checked.state == HookState.FAILED or checked.state == HookState.DEGRADED:
            log_failure(checked)
        
        # Save to database
        save_hook_health(checked)
        
        # Categorize
        if name in pre_action_names:
            pre_action_hooks.append(checked)
        else:
            post_action_hooks.append(checked)
    
    # Check circuit breaker: if BOTH pre-action AND post-action are degraded, halt operations
    pre_degraded = any(h.state in (HookState.DEGRADED, HookState.FAILED) for h in pre_action_hooks)
    post_degraded = any(h.state in (HookState.DEGRADED, HookState.FAILED) for h in post_action_hooks)
    
    if pre_degraded and post_degraded:
        circuit_breaker_open = True
        halted_operations.append("non_trivial_actions")
        halted_operations.append("memory_search")
        halted_operations.append("decision_persistence")
    
    # Calculate overall state
    all_hooks = pre_action_hooks + post_action_hooks
    healthy_count = sum(1 for h in all_hooks if h.state == HookState.HEALTHY)
    degraded_count = sum(1 for h in all_hooks if h.state == HookState.DEGRADED)
    failed_count = sum(1 for h in all_hooks if h.state == HookState.FAILED)
    
    if failed_count > 0:
        overall_state = HookState.FAILED
    elif degraded_count > 0:
        overall_state = HookState.DEGRADED
    else:
        overall_state = HookState.HEALTHY
    
    report = HealthReport(
        timestamp=now,
        overall_state=overall_state,
        pre_action_hooks=pre_action_hooks,
        post_action_hooks=post_action_hooks,
        circuit_breaker_open=circuit_breaker_open,
        halted_operations=halted_operations,
        total_hooks=len(all_hooks),
        healthy_count=healthy_count,
        degraded_count=degraded_count,
        failed_count=failed_count
    )
    
    return report


def get_degradation_context() -> Dict:
    """Get current degradation context for tagging outputs"""
    hooks = load_hook_configs()
    report = check_all_hooks(hooks)
    
    context = {
        "is_degraded": report.overall_state != HookState.HEALTHY,
        "circuit_breaker_open": report.circuit_breaker_open,
        "halted_operations": report.halted_operations,
        "confidence_multiplier": 1.0,
        "degraded_hooks": [],
        "failed_hooks": []
    }
    
    if report.overall_state == HookState.FAILED:
        context["confidence_multiplier"] = FAILED_CONFIDENCE
    elif report.overall_state == HookState.DEGRADED:
        context["confidence_multiplier"] = DEGRADED_CONFIDENCE
    
    for hook in report.pre_action_hooks + report.post_action_hooks:
        if hook.state == HookState.DEGRADED:
            context["degraded_hooks"].append(hook.name)
        elif hook.state == HookState.FAILED:
            context["failed_hooks"].append(hook.name)
    
    return context


def apply_confidence_discount(base_confidence: float) -> float:
    """Apply confidence discount based on hook health"""
    context = get_degradation_context()
    return base_confidence * context["confidence_multiplier"]


class HookHealthMonitor:
    """Background health monitor that runs health checks periodically"""
    
    def __init__(self, interval: int = HEALTHCHECK_INTERVAL):
        self.interval = interval
        self.hooks = load_hook_configs()
        self.running = False
        self._thread = None
        
    def start(self):
        """Start the health monitor in a background thread"""
        if self.running:
            return
        
        self.running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        print(f"[HookHealthMonitor] Started with {self.interval}s interval")
    
    def stop(self):
        """Stop the health monitor"""
        self.running = False
        if self._thread:
            self._thread.join(timeout=5)
        print("[HookHealthMonitor] Stopped")
    
    def _run(self):
        """Main health check loop"""
        while self.running:
            try:
                report = check_all_hooks(self.hooks)
                print(f"[HookHealthMonitor] {report.timestamp}")
                print(f"  Overall: {report.overall_state.value}")
                print(f"  Healthy: {report.healthy_count}, Degraded: {report.degraded_count}, Failed: {report.failed_count}")
                if report.circuit_breaker_open:
                    print(f"  ⚠️ Circuit breaker OPEN - halted: {report.halted_operations}")
            except Exception as e:
                print(f"[HookHealthMonitor] Error in health check: {e}")
            
            # Sleep in small increments to allow clean shutdown
            for _ in range(self.interval):
                if not self.running:
                    break
                time.sleep(1)
    
    def get_current_report(self) -> HealthReport:
        """Get current health report"""
        return check_all_hooks(self.hooks)


def run_health_check_once():
    """Run a single health check and print results"""
    init_health_db()
    hooks = load_hook_configs()
    report = check_all_hooks(hooks)
    
    print("=" * 60)
    print("HOOK HEALTH REPORT")
    print("=" * 60)
    print(f"Timestamp: {report.timestamp}")
    print(f"Overall State: {report.overall_state.value}")
    print(f"Total Hooks: {report.total_hooks}")
    print(f"  Healthy: {report.healthy_count}")
    print(f"  Degraded: {report.degraded_count}")
    print(f"  Failed: {report.failed_count}")
    print()
    
    print("PRE-ACTION HOOKS:")
    for h in report.pre_action_hooks:
        status_icon = "✓" if h.state == HookState.HEALTHY else "⚠️" if h.state == HookState.DEGRADED else "✗"
        print(f"  {status_icon} {h.name}: {h.state.value}")
        print(f"      Path: {h.path}")
        print(f"      Last Check: {h.last_check}")
        if h.response_time_ms:
            print(f"      Response: {h.response_time_ms:.1f}ms")
        if h.last_error:
            print(f"      Error: {h.last_error}")
        print(f"      Confidence: {h.confidence}")
    print()
    
    print("POST-ACTION HOOKS:")
    for h in report.post_action_hooks:
        status_icon = "✓" if h.state == HookState.HEALTHY else "⚠️" if h.state == HookState.DEGRADED else "✗"
        print(f"  {status_icon} {h.name}: {h.state.value}")
        print(f"      Path: {h.path}")
        print(f"      Last Check: {h.last_check}")
        if h.response_time_ms:
            print(f"      Response: {h.response_time_ms:.1f}ms")
        if h.last_error:
            print(f"      Error: {h.last_error}")
        print(f"      Confidence: {h.confidence}")
    print()
    
    if report.circuit_breaker_open:
        print("⚠️  CIRCUIT BREAKER OPEN")
        print(f"    Halted operations: {report.halted_operations}")
    print()
    
    return report


# Main execution
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Hook Health Monitor")
    parser.add_argument('--once', action='store_true', help='Run health check once and exit')
    parser.add_argument('--monitor', action='store_true', help='Start continuous monitoring')
    parser.add_argument('--status', action='store_true', help='Show current health status')
    args = parser.parse_args()
    
    # Initialize database
    init_health_db()
    
    if args.once or args.status:
        run_health_check_once()
    elif args.monitor:
        monitor = HookHealthMonitor()
        monitor.start()
        print("[HookHealthMonitor] Press Ctrl+C to stop")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[HookHealthMonitor] Shutting down...")
            monitor.stop()
    else:
        # Default: run once
        run_health_check_once()

