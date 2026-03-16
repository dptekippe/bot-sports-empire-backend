#!/usr/bin/env zsh
# ============================================================
# install-factcheck-swarm.sh
# Single-file installer for the factcheck-swarm OpenClaw hook
#
# Usage (from anywhere):
#   chmod +x install-factcheck-swarm.sh
#   ./install-factcheck-swarm.sh
#
# What it does:
#   1. Creates ~/.openclaw/hooks/factcheck-swarm/
#   2. Writes HOOK.yaml (both hooks: factcheck-pre + review-swarm)
#   3. Writes tests.json (4 test cases)
#   4. Registers hook:  openclaw hook add ...
#   5. Runs test suite: openclaw test factcheck-swarm ...
# ============================================================

set -e

HOOK_DIR="$HOME/.openclaw/hooks/factcheck-swarm"

echo ""
echo "══════════════════════════════════════════════════"
echo "  factcheck-swarm  OpenClaw Hook Installer"
echo "══════════════════════════════════════════════════"
echo ""

# ── Step 1: Create directory ────────────────────────────────
echo "→ Creating hook directory: $HOOK_DIR"
mkdir -p "$HOOK_DIR"

# ── Step 2: Write HOOK.yaml ─────────────────────────────────
echo "→ Writing HOOK.yaml"
cat > "$HOOK_DIR/HOOK.yaml" << 'HOOK_EOF'
# ============================================================
# factcheck-swarm  —  OpenClaw Hook for Roger
# ============================================================
# Two-pass accuracy gate:
#   PRE-ACTION   → recency check → darwin-swarm validation
#   POST-RESPONSE → critique     → pgvector error-pattern learning
# No external tools. No web calls. Internal reasoning only.
# ============================================================

name: factcheck-swarm
version: 1.0.0
description: >
  Pre-action factual staleness gate with darwin-swarm consensus validation.
  Post-response critique loop writes error patterns to pgvector for
  continuous accuracy improvement. Internal reasoning only — no web/tools.

metadata:
  openclaw:
    emoji: 🔬
    schema_version: "1.0"
    local_only: true

# ──────────────────────────────────────────────────────────────
# HOOK 1 — PRE-ACTION FACTCHECK
# ──────────────────────────────────────────────────────────────
hooks:
  - name: factcheck-pre
    type: pre_action
    priority: 900
    trigger:
      pattern: "/(player|team|contract|price|news|2026|latest|current|today|update)/i"
      event: message:received

    timeout: 8000
    fallback: inject_warning

    pipeline:

      # ── STEP 1: pgvector recency query ──────────────────────
      - id: recency_check
        type: pgvector_query
        description: Query memories table for stale facts about the matched entity
        sql: |
          SELECT
            1 - (embedding <=> query_embedding)   AS similarity,
            NOW() - created_at                    AS age,
            content,
            metadata->>'source'                   AS source,
            metadata->>'project'                  AS project,
            CASE
              WHEN NOW() - created_at < INTERVAL '7 days'   THEN 1.00
              WHEN NOW() - created_at < INTERVAL '30 days'  THEN 0.85
              WHEN NOW() - created_at < INTERVAL '60 days'  THEN 0.70
              WHEN NOW() - created_at < INTERVAL '90 days'  THEN 0.50
              ELSE                                                0.25
            END                                   AS recency_score
          FROM memories
          WHERE content ILIKE '%' || $match || '%'
            AND created_at < NOW() - INTERVAL '60 days'
          ORDER BY recency_score DESC, similarity DESC
          LIMIT 5;
        inputs:
          match: "{{trigger.match}}"
          query_embedding: "{{embed(trigger.match)}}"
        outputs:
          recency_score: "{{rows[0].recency_score | default(0.0)}}"
          context_snips: "{{rows[*].content | slice(0,3)}}"

      # ── STEP 2: conditional darwin-swarm dispatch ────────────
      - id: swarm_validate
        type: conditional
        condition: "{{recency_score}} < 0.75"
        description: Only fire the swarm when staleness is detected
        on_true:

          # ── 2a: call darwin-swarm ──────────────────────────
          - id: darwin_dispatch
            type: hook_call
            target: darwin-swarm
            description: >
              8-agent evolutionary swarm validates the flagged claim using
              only conversation context + internal memory. No external calls.
            input:
              task: "validate_fact {{trigger.match}} {{context_snips}}"
              domain: factcheck
              data:
                match: "{{trigger.match}}"
                context_snips: "{{context_snips}}"
                recency_score: "{{recency_score}}"
                now_iso: "{{now_iso}}"
              agent_weight_overrides:
                Aggressive-Upside:    0.20
                Value-Floor:          0.25
                Contrarian-AntiADP:   0.30
                Auditor-Accuracy:     0.15
                Auditor-Context:      0.10
            outputs:
              swarm_consensus: "{{output.confidence}}"
              linked_insights: "{{output.top3 | slice(0,3) | format_bullets}}"
              evo_summary: "{{output.evo_summary}}"

          # ── 2b: inject verified context block ─────────────
          - id: context_inject
            type: message_inject
            position: before_assistant
            content: |
              ━━━ FACTCHECK GATE ━━━
              VERIFIED {{now_iso}}
              recency_score={{recency_score | round(2)}}  swarm_consensus={{swarm_consensus | round(2)}}
              ──
              {{linked_insights}}
              ━━━━━━━━━━━━━━━━━━━━━

        on_false:
          - id: fresh_stamp
            type: message_inject
            position: before_assistant
            content: |
              ━━━ FACTCHECK GATE ━━━
              FRESH {{now_iso}}  recency_score={{recency_score | round(2)}} ✓
              ━━━━━━━━━━━━━━━━━━━━━

      # ── STEP 3: fallback warning on pgvector failure ────────
      - id: stale_fallback
        type: message_inject
        position: before_assistant
        trigger_on: fallback
        content: |
          ⚠️ Stale data risk (recency_score < 0.75). Manual verification recommended.

    output_schema:
      recency_score:    { type: number,  minimum: 0.0, maximum: 1.0 }
      swarm_consensus:  { type: number,  minimum: 0.0, maximum: 1.0 }
      linked_insights:  { type: array,   maxItems: 3,  items: { type: string } }
      verified_stamp:   { type: string }

# ──────────────────────────────────────────────────────────────
# HOOK 2 — POST-RESPONSE REVIEW SWARM
# ──────────────────────────────────────────────────────────────
  - name: review-swarm
    type: post_response
    priority: 800
    trigger:
      event: message:sent

    timeout: 10000
    fallback: skip_continue

    pipeline:

      # ── STEP 1: darwin-swarm critique ──────────────────────
      - id: critique_dispatch
        type: hook_call
        target: darwin-swarm
        description: >
          Full-context critique of the just-sent response.
          Scores accuracy, flags reasoning errors. Internal only.
        input:
          task: "critique_response {{full_context}}"
          domain: self_review
          data:
            full_context: "{{session.full_context}}"
            assistant_response: "{{session.last_response}}"
            factcheck_stamp: "{{session.factcheck_stamp | default('none')}}"
        outputs:
          critique_score: "{{output.confidence}}"
          low_score_reason: "{{output.evo_summary}}"
          critique_top3: "{{output.top3}}"

      # ── STEP 2: write error pattern on low consensus ────────
      - id: error_pattern_write
        type: conditional
        condition: "{{critique_score}} < 0.80"
        on_true:
          - id: pgvector_upsert
            type: pgvector_upsert
            description: Persist the error pattern for future recency/bias detection
            table: memories
            record:
              content: "error_pattern: {{low_score_reason}}"
              metadata:
                type: error_pattern
                critique_score: "{{critique_score}}"
                trigger_match: "{{session.trigger_match | default('unknown')}}"
                project: factcheck
                source: review-swarm
                importance: 8
              embedding: "{{embed(low_score_reason)}}"

      # ── STEP 3: emit learning signal ───────────────────────
      - id: fitness_emit
        type: event_emit
        event: session:learning
        payload:
          fitness_delta: "{{critique_score}}"
          evo_summary: "{{low_score_reason}}"
          linked_insights: "{{critique_top3 | slice(0,3) | format_bullets}}"
          timestamp: "{{now_iso}}"

    output_schema:
      critique_score:   { type: number,  minimum: 0.0, maximum: 1.0 }
      low_score_reason: { type: string }
      fitness_delta:    { type: number }

# ──────────────────────────────────────────────────────────────
# GLOBAL CONFIG
# ──────────────────────────────────────────────────────────────
config:
  memory: true
  memory_schema:
    table: memories
    embedding_col: embedding
    content_col: content
    metadata_cols: [type, project, source, importance, critique_score]
  local_only: true
  parallel_agents: true
  memory_atomic: true
  per_hook_timeout: 2000
  swarm_weights:
    ceiling:  0.20
    floor:    0.25
    recency:  0.30
    weapons:  0.15
    oline:    0.10
HOOK_EOF

# ── Step 3: Write tests.json ────────────────────────────────
echo "→ Writing tests.json"
cat > "$HOOK_DIR/tests.json" << 'TESTS_EOF'
[
  {
    "test_id": "T1_kyler_murray_value",
    "description": "Player value — Vikings trade + Jefferson synergy",
    "input": {
      "message": "What is Kyler Murray's dynasty value right now?",
      "trigger_match": "player"
    },
    "expect": {
      "recency_score": 0.50,
      "swarm_fires": true,
      "swarm_consensus_min": 0.85,
      "linked_insight_keywords": ["Vikings", "Jefferson", "target share"]
    }
  },
  {
    "test_id": "T2_burrow_dynasty",
    "description": "Dynasty hold 2026 — O-line improvement",
    "input": {
      "message": "Is Burrow a dynasty hold into 2026 given the Bengals O-line improvements?",
      "trigger_match": "2026"
    },
    "expect": {
      "recency_score": 0.70,
      "swarm_fires": true,
      "swarm_consensus_min": 0.88,
      "linked_insight_keywords": ["O-line", "sack rate", "PFF grade"]
    }
  },
  {
    "test_id": "T3_oil_prices_today",
    "description": "Commodity price — Brent crude + geopolitics (high staleness)",
    "input": {
      "message": "What are oil prices today? Brent crude and geopolitical factors?",
      "trigger_match": "today"
    },
    "expect": {
      "recency_score": 0.25,
      "swarm_fires": true,
      "swarm_consensus_max": 0.75,
      "fallback_fires": true,
      "error_pattern_written": true
    }
  },
  {
    "test_id": "T4_render_pricing",
    "description": "Infra cost — Render pricing vs AWS SES",
    "input": {
      "message": "Has Render's pricing changed? Comparing against my AWS SES costs.",
      "trigger_match": "price"
    },
    "expect": {
      "recency_score": 0.70,
      "swarm_fires": true,
      "swarm_consensus_min": 0.80,
      "error_pattern_written": false,
      "linked_insight_keywords": ["starter", "SES", "stable"]
    }
  }
]
TESTS_EOF

# ── Step 4: Register with OpenClaw ──────────────────────────
echo "→ Registering hook with OpenClaw"
openclaw hook add "$HOOK_DIR/HOOK.yaml"

# ── Step 5: Confirm both hooks are listed ───────────────────
echo ""
echo "→ Registered hooks:"
openclaw hooks list | grep -E "factcheck|review-swarm"

# ── Step 6: Run test suite ──────────────────────────────────
echo ""
echo "══════════════════════════════════════════════════"
echo "  Running test suite"
echo "══════════════════════════════════════════════════"
echo ""

echo "── T1: Kyler Murray value (player trigger) ──"
openclaw test factcheck-swarm '{"message":"What is Kyler Murray'\''s dynasty value right now?","trigger_match":"player"}'

echo ""
echo "── T2: Burrow dynasty 2026 (2026 trigger) ──"
openclaw test factcheck-swarm '{"message":"Is Burrow a dynasty hold into 2026?","trigger_match":"2026"}'

echo ""
echo "── T3: Oil prices today (today trigger) ──"
openclaw test factcheck-swarm '{"message":"What are oil prices today?","trigger_match":"today"}'

echo ""
echo "── T4: Render pricing (price trigger) ──"
openclaw test factcheck-swarm '{"message":"Has Render'\''s pricing changed vs my AWS SES costs?","trigger_match":"price"}'

# ── Done ────────────────────────────────────────────────────
echo ""
echo "══════════════════════════════════════════════════"
echo "  ✅ factcheck-swarm installed"
echo ""
echo "  factcheck-pre   priority 900  pre_action"
echo "  review-swarm    priority 800  post_response"
echo ""
echo "  Hook dir:  $HOOK_DIR"
echo "  Logs:      openclaw hooks logs factcheck-swarm --tail 50"
echo "             openclaw hooks logs review-swarm --tail 20"
echo "══════════════════════════════════════════════════"
