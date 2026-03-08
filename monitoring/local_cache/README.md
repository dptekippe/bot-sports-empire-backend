# Local Monitoring Cache

## Purpose
Local storage for monitoring data before GitHub sync. Provides:
1. **GitHub fallback** - Monitoring works even if GitHub unavailable
2. **Data persistence** - Monitoring data survives between sessions
3. **Recovery source** - Can restore monitoring state if needed
4. **Performance** - Faster than GitHub for frequent updates

## Structure
```
local_cache/
├── system_health.json      # Current system status (updated every 30m)
├── job_history/            # Cron job execution logs
│   ├── subconscious.json   # Subconscious job history
│   ├── muscle_memory.json  # Muscle memory job history
│   └── meta_monitoring.json # Monitoring system itself
├── alerts/                 # Active and historical alerts
│   ├── active.json        # Currently active alerts
│   └── archive/           # Resolved alerts (by date)
├── validation/            # Output quality validation results
│   ├── soul_validation.json
│   └── skills_validation.json
└── metrics/               # Effectiveness measurements
    ├── learning_velocity.json
    └── system_reliability.json
```

## Data Flow
1. **Monitoring agent** collects data
2. **Data stored locally** in cache (immediate)
3. **Attempt GitHub sync** (async, retry on failure)
4. **If GitHub fails:** Data remains in local cache
5. **If GitHub succeeds:** Local cache remains as backup

## Recovery Protocol
If monitoring system detects GitHub sync failures:
1. Continue storing data locally
2. Log sync failures
3. Alert after 3 consecutive failures
4. Attempt recovery every hour
5. Manual intervention if >24 hours offline

## Maintenance
- **Auto-clean:** Old data archived after 30 days
- **Size limits:** 100MB max, oldest data purged first
- **Integrity checks:** Daily validation of cache structure
- **Backup:** Included in regular workspace backups

**Last updated:** 2026-03-07 by Black Roger