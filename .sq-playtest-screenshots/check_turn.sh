#!/usr/bin/env bash
# 59-8 per-turn OTEL verification. Usage: check_turn.sh <round>  (no round = latest round summary)
DB="postgresql://slabgorb@localhost:5432/sidequest"
SID=883
R="${1:-}"
RFILT=""
if [ -n "$R" ]; then RFILT="AND round=$R"; fi

echo "===== ROUND ${R:-<all>} — session $SID ====="

echo "--- intent_router.decompose (classification + latency_ms) ---"
psql "$DB" -tAF'|' -c "
  SELECT round,
         payload_json::jsonb->>'classification',
         payload_json::jsonb->>'dispatch_count',
         payload_json::jsonb->>'latency_ms',
         payload_json::jsonb->>'degraded'
  FROM turn_telemetry
  WHERE session_id=$SID AND event_type='intent_router.decompose' $RFILT
  ORDER BY round, seq;"

echo "--- intent_router.subsystem (per-dispatch engagement) ---"
psql "$DB" -tAF'|' -c "
  SELECT round,
         payload_json::jsonb->>'subsystem',
         payload_json::jsonb->>'key',
         payload_json::jsonb->>'engaged',
         left(coalesce(payload_json::jsonb->>'error',''),60)
  FROM turn_telemetry
  WHERE session_id=$SID AND event_type='intent_router.subsystem' $RFILT
  ORDER BY round, seq;"

echo "--- confrontation.* + encounter events ---"
psql "$DB" -tAF'|' -c "
  SELECT round, event_type, left(payload_json,120)
  FROM turn_telemetry
  WHERE session_id=$SID AND (event_type LIKE 'confrontation%' OR event_type LIKE '%encounter%') $RFILT
  ORDER BY round, seq;"

echo "--- ENCOUNTER events table (encounter_events endpoint source) ---"
psql "$DB" -tAF'|' -c "
  SELECT seq, kind, left(payload_json,100)
  FROM events
  WHERE session_id=$SID AND kind LIKE 'ENCOUNTER%'
  ORDER BY seq;"

echo "--- LIE-DETECTOR: dispatch_engagement.*.mismatch (MUST be empty) ---"
psql "$DB" -tAF'|' -c "
  SELECT round, event_type, left(payload_json,150)
  FROM turn_telemetry
  WHERE session_id=$SID AND event_type LIKE 'dispatch_engagement%mismatch%' $RFILT
  ORDER BY round, seq;"

echo "--- validation_warning / subsystem errors ---"
psql "$DB" -tAF'|' -c "
  SELECT round, component, event_type, left(payload_json,140)
  FROM turn_telemetry
  WHERE session_id=$SID AND (event_type LIKE '%warning%' OR event_type LIKE '%error%' OR event_type LIKE '%failed%' OR event_type LIKE '%mismatch%') $RFILT
  ORDER BY round, seq;"
echo "===== end round ${R:-<all>} ====="
