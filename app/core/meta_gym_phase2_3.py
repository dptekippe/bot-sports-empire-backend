"""
Meta-gym Phase 2 & 3 Implementation

Phase 2: Telemetry Aggregation + Health Score
- Reads telemetry.jsonl
- Computes per-session health score (0-100)
- Aggregates across sessions

Phase 3: Thompson Sampling for Hook Optimization
- Multi-armed bandit for hook selection
- Learns which hook combinations improve outcomes
- Beta priors for domain weights

Usage:
    python meta_gym_phase2_3.py --phase 2     # Compute health scores
    python meta_gym_phase2_3.py --phase 3     # Run Thompson Sampling
    python meta_gym_phase2_3.py --status      # Show current state
"""
import json
import sqlite3
import math
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import os

META_GYM_DIR = Path.home() / ".openclaw" / "hooks" / "meta-gym"
TELEMETRY_FILE = META_GYM_DIR / "telemetry.jsonl"
HEALTH_DB = Path.home() / ".openclaw" / "hooks" / "meta-gym" / "health_scores.db"
HOOK_SELECTION_DB = Path.home() / ".openclaw" / "hooks" / "meta-gym" / "hook_selection.db"

# Hook effectiveness weights (Phase 1 outputs)
HOOK_WEIGHTS = {
    "biascheck-gym": 0.15,
    "doubttrigger-gym": 0.15,
    "echochamber": 0.15,
    "mcts-reflection": 0.20,
    "scout-veto": 0.15,
    "futureself": 0.10,
    "hook-effectiveness": 0.10,
}

# Domain-specific hook configurations
DOMAIN_HOOK_CONFIGS = {
    "fantasy_football": {
        "enabled": ["mcts-reflection", "biascheck-gym", "scout-veto"],
        "weights": {"mcts-reflection": 0.3, "biascheck-gym": 0.2, "scout-veto": 0.2, "echochamber": 0.15, "doubttrigger-gym": 0.15}
    },
    "technical": {
        "enabled": ["mcts-reflection", "hook-effectiveness", "scout-veto"],
        "weights": {"mcts-reflection": 0.35, "hook-effectiveness": 0.25, "scout-veto": 0.2, "biascheck-gym": 0.1, "doubttrigger-gym": 0.1}
    },
    "general": {
        "enabled": list(HOOK_WEIGHTS.keys()),
        "weights": HOOK_WEIGHTS
    }
}


def init_health_db():
    """Initialize health score database."""
    HEALTH_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(HEALTH_DB))
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS health_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            timestamp TEXT,
            domain TEXT,
            unified_score REAL,
            hook_scores TEXT,
            telemetry_entries INTEGER,
            features TEXT
        )
    """)
    conn.commit()
    conn.close()


def init_hook_selection_db():
    """Initialize hook selection database for Thompson Sampling."""
    HOOK_SELECTION_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(HOOK_SELECTION_DB))
    c = conn.cursor()
    
    # Thompson Sampling state per domain
    c.execute("""
        CREATE TABLE IF NOT EXISTS thompson_state (
            domain TEXT PRIMARY KEY,
            hook_name TEXT,
            alpha REAL DEFAULT 1.0,
            beta REAL DEFAULT 1.0,
            selections INTEGER DEFAULT 0,
            successes INTEGER DEFAULT 0
        )
    """)
    
    # Hook selection log
    c.execute("""
        CREATE TABLE IF NOT EXISTS selection_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            domain TEXT,
            selected_hook TEXT,
            reward REAL,
            thompson_sample REAL
        )
    """)
    
    conn.commit()
    conn.close()


def read_telemetry() -> List[Dict]:
    """Read telemetry entries from JSONL file."""
    if not TELEMETRY_FILE.exists():
        return []
    
    entries = []
    with open(TELEMETRY_FILE) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return entries


def compute_health_score(telemetry_entries: List[Dict]) -> Tuple[float, Dict]:
    """
    Compute unified health score (0-100) from telemetry.
    
    Returns (unified_score, hook_scores_dict).
    """
    if not telemetry_entries:
        return 50.0, {}
    
    hook_scores = {}
    
    # Aggregate scores per hook
    for entry in telemetry_entries:
        hook_name = entry.get("hook_name", "unknown")
        score = entry.get("score", 0.5)  # Default 0.5 if not present
        
        if hook_name not in hook_scores:
            hook_scores[hook_name] = []
        hook_scores[hook_name].append(score)
    
    # Compute weighted average
    weighted_sum = 0.0
    total_weight = 0.0
    
    for hook, weight in HOOK_WEIGHTS.items():
        if hook in hook_scores:
            avg_score = sum(hook_scores[hook]) / len(hook_scores[hook])
            hook_scores[hook] = avg_score
            weighted_sum += avg_score * weight
            total_weight += weight
        else:
            hook_scores[hook] = 0.0
    
    unified_score = (weighted_sum / total_weight * 100) if total_weight > 0 else 50.0
    
    # Clamp to 0-100
    unified_score = max(0.0, min(100.0, unified_score))
    
    return unified_score, hook_scores


def aggregate_telemetry_by_session(telemetry: List[Dict]) -> Dict[str, List[Dict]]:
    """Group telemetry by session."""
    sessions = defaultdict(list)
    for entry in telemetry:
        session_id = entry.get("session_id", "unknown")
        sessions[session_id].append(entry)
    return dict(sessions)


def compute_phase2_health_scores():
    """Phase 2: Aggregate telemetry and compute health scores."""
    print(f"\n{'='*60}")
    print(f" META-GYM PHASE 2: HEALTH SCORE COMPUTATION")
    print(f"{'='*60}\n")
    
    telemetry = read_telemetry()
    print(f"Total telemetry entries: {len(telemetry)}")
    
    if not telemetry:
        print("No telemetry data yet. Hooks need to fire first.")
        return
    
    # Initialize DB
    init_health_db()
    
    # Group by session
    sessions = aggregate_telemetry_by_session(telemetry)
    print(f"Sessions: {len(sessions)}")
    
    conn = sqlite3.connect(str(HEALTH_DB))
    
    for session_id, entries in sessions.items():
        unified_score, hook_scores = compute_health_score(entries)
        
        # Get domain from entries
        domain = "general"
        for entry in entries:
            if "domain" in entry:
                domain = entry["domain"]
                break
        
        # Store in DB
        c = conn.cursor()
        c.execute("""
            INSERT INTO health_scores (session_id, timestamp, domain, unified_score, hook_scores, telemetry_entries, features)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            datetime.now().isoformat(),
            domain,
            unified_score,
            json.dumps(hook_scores),
            len(entries),
            json.dumps({k: v for k, v in hook_scores.items()})
        ))
        
        print(f"  Session {session_id[:8]}... | Domain: {domain} | Score: {unified_score:.1f}")
    
    conn.commit()
    conn.close()
    
    print(f"\nStored {len(sessions)} health scores in database")
    print(f"{'='*60}\n")


def thompson_sample(alpha: float, beta: float) -> float:
    """Sample from Beta distribution using Thompson Sampling."""
    import random
    import math
    
    # Using J. M. Chambers' method for Beta distribution
    if alpha <= 0 or beta <= 0:
        return 0.5
    
    # Gamma samples
    def gamma_sample(shape):
        if shape < 1:
            return gamma_sample(shape + 1) * random.random() ** (1.0 / shape)
        else:
            import math
            shape -= 1
            c = shape * math.log(shape) - math.lgamma(shape + 1)
            return math.exp(c - shape + shape * math.log(random.random() + 1e-10))
    
    x = gamma_sample(alpha)
    y = gamma_sample(beta)
    return x / (x + y)


def select_hook_thompson(domain: str, available_hooks: List[str]) -> Tuple[str, float]:
    """
    Thompson Sampling: Select best hook based on historical performance.
    
    Returns (selected_hook, sample_value).
    """
    init_hook_selection_db()
    conn = sqlite3.connect(str(HOOK_SELECTION_DB))
    c = conn.cursor()
    
    best_hook = available_hooks[0] if available_hooks else None
    best_sample = -1.0
    
    for hook in available_hooks:
        c.execute(
            "SELECT alpha, beta FROM thompson_state WHERE domain=? AND hook_name=?",
            (domain, hook)
        )
        row = c.fetchone()
        
        if row:
            alpha, beta = row
        else:
            # Initialize with non-informative prior
            alpha, beta = 1.0, 1.0
            c.execute(
                "INSERT INTO thompson_state (domain, hook_name, alpha, beta) VALUES (?, ?, ?, ?)",
                (domain, hook, alpha, beta)
            )
        
        sample = thompson_sample(alpha, beta)
        
        if sample > best_sample:
            best_sample = sample
            best_hook = hook
    
    conn.commit()
    conn.close()
    
    return best_hook, best_sample


def update_thompson_state(domain: str, hook_name: str, reward: float):
    """
    Update Thompson Sampling state after observing reward.
    
    Reward: 1.0 = success, 0.0 = failure
    """
    init_hook_selection_db()
    conn = sqlite3.connect(str(HOOK_SELECTION_DB))
    c = conn.cursor()
    
    # Get current state
    c.execute(
        "SELECT alpha, beta FROM thompson_state WHERE domain=? AND hook_name=?",
        (domain, hook_name)
    )
    row = c.fetchone()
    
    if row:
        alpha, beta = row
        
        # Update with new reward (sequential update)
        new_alpha = alpha + reward
        new_beta = beta + (1 - reward)
        
        c.execute(
            "UPDATE thompson_state SET alpha=?, beta=?, selections=selections+1, successes=successes+? WHERE domain=? AND hook_name=?",
            (new_alpha, new_beta, reward, domain, hook_name)
        )
    
    # Log selection
    c.execute(
        "INSERT INTO selection_log (timestamp, domain, selected_hook, reward, thompson_sample) VALUES (?, ?, ?, ?, ?)",
        (datetime.now().isoformat(), domain, hook_name, reward, reward)
    )
    
    conn.commit()
    conn.close()


def run_phase3_thompson_sampling():
    """Phase 3: Thompson Sampling for hook optimization."""
    print(f"\n{'='*60}")
    print(f" META-GYM PHASE 3: THOMPSON SAMPLING")
    print(f"{'='*60}\n")
    
    # Get health scores from recent sessions
    init_health_db()
    conn = sqlite3.connect(str(HEALTH_DB))
    c = conn.cursor()
    
    c.execute("""
        SELECT session_id, domain, unified_score 
        FROM health_scores 
        ORDER BY timestamp DESC 
        LIMIT 20
    """)
    
    sessions = c.fetchall()
    conn.close()
    
    if not sessions:
        print("No health scores yet. Run Phase 2 first.")
        return
    
    print(f"Recent sessions: {len(sessions)}")
    
    # Initialize Thompson Sampling for each domain
    domains_seen = set()
    for session_id, domain, score in sessions:
        domains_seen.add(domain)
        
        # Use health score as reward signal
        # Higher score = better = reward 1, Lower = reward 0
        threshold = 70.0
        reward = 1.0 if score >= threshold else 0.0
        
        # Get config for this domain
        config = DOMAIN_HOOK_CONFIGS.get(domain, DOMAIN_HOOK_CONFIGS["general"])
        hooks = config["enabled"]
        
        # Update each hook (simplified: update all hooks based on outcome)
        for hook in hooks:
            update_thompson_state(domain, hook, reward)
        
        print(f"  Domain: {domain} | Score: {score:.1f} | Reward: {reward:.1f}")
    
    print(f"\nThompson Sampling state updated for {len(domains_seen)} domains")
    
    # Show current recommendations
    print(f"\nCurrent Hook Recommendations:")
    for domain in domains_seen:
        config = DOMAIN_HOOK_CONFIGS.get(domain, DOMAIN_HOOK_CONFIGS["general"])
        hooks = config["enabled"]
        
        selected, sample = select_hook_thompson(domain, hooks)
        print(f"  {domain}: {selected} (sample={sample:.3f})")
    
    print(f"{'='*60}\n")


def show_status():
    """Show current meta-gym status."""
    print(f"\n{'='*60}")
    print(f" META-GYM STATUS")
    print(f"{'='*60}")
    
    telemetry = read_telemetry()
    print(f"\nTelemetry entries: {len(telemetry)}")
    
    # Health scores
    if HEALTH_DB.exists():
        conn = sqlite3.connect(str(HEALTH_DB))
        c = conn.cursor()
        c.execute("SELECT COUNT(*), AVG(unified_score) FROM health_scores")
        count, avg = c.fetchone()
        print(f"Health scores: {count} (avg: {avg:.1f if avg else 0:.1f})")
        conn.close()
    
    # Thompson Sampling state
    if HOOK_SELECTION_DB.exists():
        conn = sqlite3.connect(str(HOOK_SELECTION_DB))
        c = conn.cursor()
        c.execute("SELECT COUNT(DISTINCT domain) FROM thompson_state")
        domains = c.fetchone()[0]
        print(f"Thompson Sampling domains: {domains}")
        conn.close()
    
    print(f"{'='*60}\n")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Meta-gym Phase 2 & 3")
    parser.add_argument("--phase", type=int, choices=[2, 3], help="Run specific phase")
    parser.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--domain", type=str, default="general", help="Domain for hook selection")
    parser.add_argument("--hook", type=str, help="Hook name for update")
    parser.add_argument("--reward", type=float, help="Reward (0-1) for update")
    
    args = parser.parse_args()
    
    if args.status:
        show_status()
    elif args.phase == 2:
        compute_phase2_health_scores()
    elif args.phase == 3:
        run_phase3_thompson_sampling()
    else:
        # Default: show status
        show_status()
        print("Run with --phase 2 or --phase 3")
