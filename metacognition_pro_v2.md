# Roger Metacognition Pro v2.0 (Universal CFR Reasoning)

## Protocol (Any Domain)
Input → TRIGGER → STATE → CONF → ALTS → SANITY → TOOL → COMMIT → ACTION

---

### TRIGGER DETECTION
Domains: [code, deploy, api, draft, plan, debug, optimize]
→ Extract RL State Vector

### STATE ENCODING (Abstracted)
[RL State] Domain: {domain} | Risk_Bias: {bias}% | Mem_Match: {n}

Examples:
- deploy: 15% Week1 fail (n=47)
- code: 8% bug rate (n=120)
- api: 22% rate-limit (n=89)
- draft: 120% ADP variance (n=500)

---

### 1. INFO CONFIDENCE (Variance-Adjusted)
```
conf = 50% + mem_hits*20% - risk_bias*30% + holdout*10%
```

[Conf] {conf:.0f}% (n={sample}, bias={risk_bias}%)

---

### 2. ALTERNATIVE VIEWS (Universal Regret)
Top-3 actions → regret_delta = value(alt) - value(selected)

Domain value functions:
- Draft: vorp(alt_player)
- Deploy: uptime(alt_config)
- Code: bug_rate(alt_arch)
- API: success_rate(alt_endpoint)

[CFR] Rejected "{alt2}": +{delta:.1f} risk/cost

---

### 3. SANITY CHECK (Holdout Validation)
```
holdout_bias = test_set_error_rate()
```

[Sanity] Holdout: {bias:.1f}% ({test_n} samples)

---

### 4. TOOL JUSTIFICATION (ROI Quantified)
```
tool_roi = risk_reduction / (cost * (1-conf))
```

[Tool] {tool}: {delta:.1f} risk/cost (conf {conf}%)

---

### 5. MEMORY COMMIT (Threshold-Gated)
Commit if regret_delta > threshold OR mem_match < 0.85:
```
pgvector: "{domain}: {insight} (n={episodes}, delta={delta:.1f}%)"
```

[Mem] {insight}

---

### 6. ACTION EXECUTION
[Action] {action}

[Trace] State→Conf→CFR→Sanity→Tool→Mem→Action

---

## Domain Config (openclaw.json)
```json
{
  "metacognition_pro_v2": {
    "risk_bias": {
      "deploy": 0.15,
      "code": 0.08,
      "api": 0.22,
      "draft": 1.20,
      "debug": 0.35
    },
    "value_functions": {
      "deploy": "uptime_pct",
      "draft": "vorp",
      "code": "-bug_rate",
      "api": "success_rate"
    }
  }
}
```

---

## Universal Examples

### 1. DEPLOY
```
[State] Domain: deploy | Risk: 15% | Mem: n=47
[Conf] 65% (n=47, bias=15%)
[CFR] Rejected "staging": +22% uptime
[Sanity] Holdout: 8% (n=12)
[Tool] rollback: +15% recovery (conf 65%)
[Mem] Deploy: Always stage first (n=47, delta=22%)
[Action] Deploy to staging → monitor 5min → prod
```

### 2. CODE
```
[State] Domain: code | Risk: 8% | Mem: n=120
[Conf] 82% (n=120, bias=8%)
[CFR] Rejected "async": +15% bug risk
[Sanity] Holdout: 5% (n=30)
[Tool] TypeScript: +12% safety (conf 82%)
[Mem] Code: Sync > async for I/O (n=120, delta=15%)
[Action] Use sync with error handling
```

### 3. API
```
[State] Domain: api | Risk: 22% | Mem: n=89
[Conf] 58% (n=89, bias=22%)
[CFR] Rejected "batch": +35% throughput
[Sanity] Holdout: 18% (n=22)
[Tool] Retry + backoff: +40% success (conf 58%)
[Mem] API: Rate-limit → exponential backoff (n=89, delta=40%)
[Action] GET with retry (3x, exp backoff)
```

### 4. DRAFT (Applied to DynastyDroid)
```
[State] Domain: draft | Risk: 120% | Mem: n=500
[Conf] 35% (n=500, bias=120%)
[CFR] Rejected "Bowers TE": +28% vorp vs ADP
[Sanity] Holdout: 65% bias (multi-year)
[Tool] VORP calc: +15% edge (conf 35%)
[Mem] Draft: Rookie TE in Rounds 10-14 = 68% hit (n=500, delta=28%)
[Action] Draft Bijan RB at 1.02
```

---

## Deployment Checklist
- [x] metacognition_pro_v2.md created
- [ ] openclaw.json updated with domain config
- [ ] Gateway restart
- [ ] Test 3 domains (TUI)
- [ ] Verify pgvector namespace="universal_insights"

---

## Test Outputs (TBD)
1. "Deploy Render service?"
2. "Optimize this Python loop?"
3. "1.05 superflex pick?"
