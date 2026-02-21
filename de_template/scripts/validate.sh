#!/bin/bash
# =============================================================================
# validate.sh — 4-Stage Smoke Test for de_template
# =============================================================================
# Called by: make validate
# Environment vars injected by Makefile (BROKER, MODE, STORAGE, etc.)
#
# Stage 1: Infrastructure health (BROKER-aware, Flink, MinIO)
# Stage 2: Flink job state (batch: FINISHED >= 2 | streaming: RUNNING >= 1)
# Stage 3: Row counts (data-derived: bronze >= 0.95*N, silver <= bronze, DLQ <= DLQ_MAX)
# Stage 4: dbt test (all model tests pass)
# =============================================================================
set -euo pipefail

BROKER="${BROKER:-redpanda}"
MODE="${MODE:-batch}"
STORAGE="${STORAGE:-minio}"
DLQ_TOPIC="${DLQ_TOPIC:-taxi.raw_trips.dlq}"
DLQ_MAX="${DLQ_MAX:-0}"

PASS=0
FAIL=0
TOTAL=0

pass() {
    echo "  [PASS] $1"
    PASS=$((PASS + 1))
    TOTAL=$((TOTAL + 1))
}

fail() {
    echo "  [FAIL] $1"
    FAIL=$((FAIL + 1))
    TOTAL=$((TOTAL + 1))
}

section() {
    echo ""
    echo "━━━ Stage $1: $2 ━━━"
}

build_compose() {
    local cmd="docker compose -f infra/base.yml"
    if [ "$BROKER" = "redpanda" ]; then
        cmd="$cmd -f infra/broker.redpanda.yml"
    else
        cmd="$cmd -f infra/broker.kafka.yml"
    fi
    if [ "$STORAGE" = "minio" ]; then
        cmd="$cmd -f infra/storage.minio.yml"
    fi
    echo "$cmd"
}

COMPOSE=$(build_compose)

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "  de_template: 4-Stage Smoke Test"
echo "  BROKER=$(echo $BROKER | tr '[:lower:]' '[:upper:]')  MODE=$(echo $MODE | tr '[:lower:]' '[:upper:]')  STORAGE=$(echo $STORAGE | tr '[:lower:]' '[:upper:]')"
echo "╚══════════════════════════════════════════════════════════╝"

# =============================================================================
# Stage 1: Infrastructure Health
# =============================================================================
section 1 "Infrastructure Health"

if [ "$BROKER" = "redpanda" ]; then
    # rpk v25+: --brokers flag removed from rpk cluster health; reads from node config.
    # grep -E 'Healthy:.+true' checks the value (not just the key name).
    if $COMPOSE exec -T broker rpk cluster health 2>/dev/null | grep -qE 'Healthy:.+true'; then
        pass "Redpanda: healthy"
    else
        fail "Redpanda: not healthy (rpk cluster health failed)"
    fi
else
    if $COMPOSE exec -T broker /opt/kafka/bin/kafka-topics.sh \
        --list --bootstrap-server localhost:9092 > /dev/null 2>&1; then
        pass "Kafka: healthy (topic list OK)"
    else
        fail "Kafka: not healthy (kafka-topics.sh --list failed)"
    fi
fi

if curl -sf http://localhost:8081/overview > /dev/null 2>&1; then
    pass "Flink Dashboard: reachable"
else
    fail "Flink Dashboard: not reachable (http://localhost:8081)"
fi

if [ "$STORAGE" = "minio" ]; then
    if curl -sf http://localhost:9000/minio/health/live > /dev/null 2>&1; then
        pass "MinIO: healthy"
    else
        fail "MinIO: not healthy (http://localhost:9000/minio/health/live)"
    fi
fi

# =============================================================================
# Stage 2: Flink Job State
# =============================================================================
section 2 "Flink Job State"

JOBS_JSON=$(curl -s http://localhost:8081/jobs/overview 2>/dev/null || echo '{"jobs":[]}')
FINISHED=$(echo "$JOBS_JSON" | python3 -c "
import json,sys
d=json.load(sys.stdin)
print(sum(1 for j in d.get('jobs',[]) if j.get('state')=='FINISHED'))
" 2>/dev/null || echo "0")
RUNNING=$(echo "$JOBS_JSON" | python3 -c "
import json,sys
d=json.load(sys.stdin)
print(sum(1 for j in d.get('jobs',[]) if j.get('state')=='RUNNING'))
" 2>/dev/null || echo "0")

if [ "$MODE" = "streaming_bronze" ]; then
    if [ "$RUNNING" -ge 1 ]; then
        pass "Flink streaming: $RUNNING job(s) RUNNING"
    else
        fail "Flink streaming: expected >=1 RUNNING job, found $RUNNING (check Dashboard → Jobs)"
    fi

    # Streaming stability: check restart count on each RUNNING job
    RUNNING_IDS=$(echo "$JOBS_JSON" | python3 -c "
import json,sys
d=json.load(sys.stdin)
print(' '.join(j['jid'] for j in d.get('jobs',[]) if j.get('state')=='RUNNING'))
" 2>/dev/null || echo "")
    for jid in $RUNNING_IDS; do
        RESTARTS=$(curl -s "http://localhost:8081/jobs/${jid}" 2>/dev/null | \
            python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('numRestarts',0))" \
            2>/dev/null || echo "0")
        if [ "${RESTARTS:-0}" -eq 0 ]; then
            pass "Flink job ${jid:0:8}...: 0 restarts (stable)"
        else
            fail "Flink job ${jid:0:8}...: $RESTARTS restart(s) — job is unstable, check TM logs"
        fi
    done
else
    if [ "$FINISHED" -ge 2 ]; then
        pass "Flink batch: $FINISHED job(s) FINISHED (bronze + silver)"
    else
        fail "Flink batch: expected >=2 FINISHED jobs, found $FINISHED (check Dashboard → Jobs)"
    fi
fi

# =============================================================================
# Stage 3: Row Counts (data-derived from generator metrics)
# =============================================================================
section 3 "Row Counts"

# Read events_produced from generator metrics volume
# Note: docker compose run always works for services with profiles (no --profile needed)
EVENTS_PRODUCED=$(
    $COMPOSE run --rm --no-deps \
        --entrypoint python3 \
        dbt - <<'PYEOF' 2>/dev/null
import json, sys, os
try:
    with open('/metrics/latest.json') as f:
        data = json.load(f)
    print(data.get('events', 0))
except Exception as e:
    print(0)
PYEOF
)
EVENTS_PRODUCED=$(echo "$EVENTS_PRODUCED" | tr -d '[:space:]')

if [ -z "$EVENTS_PRODUCED" ] || [ "$EVENTS_PRODUCED" = "0" ]; then
    echo "  [WARN] Could not read generator metrics (METRICS_PATH=/metrics/latest.json)"
    echo "         Run 'make generate-limited' before validate to enable count checks."
    EVENTS_PRODUCED=0
else
    echo "  Events produced (from generator): $EVENTS_PRODUCED"
fi

# Get bronze and silver counts via DuckDB iceberg_scan inside dbt container
COUNT_RESULT=$(
    $COMPOSE run --rm --no-deps \
        --entrypoint python3 \
        dbt /scripts/wait_for_iceberg.py 2>/dev/null
    $COMPOSE run --rm --no-deps \
        --entrypoint python3 \
        dbt - <<'PYEOF' 2>/dev/null
import duckdb, os, sys

endpoint = os.environ.get('DUCKDB_S3_ENDPOINT', 'minio:9000')
key = os.environ.get('AWS_ACCESS_KEY_ID', 'minioadmin')
secret = os.environ.get('AWS_SECRET_ACCESS_KEY', 'minioadmin')
use_ssl = os.environ.get('DUCKDB_S3_USE_SSL', 'false').lower() == 'true'

def count(path):
    con = duckdb.connect()
    try:
        con.execute("INSTALL iceberg; INSTALL httpfs; LOAD iceberg; LOAD httpfs;")
        con.execute(f"SET s3_endpoint='{endpoint}';")
        con.execute(f"SET s3_access_key_id='{key}';")
        con.execute(f"SET s3_secret_access_key='{secret}';")
        con.execute(f"SET s3_use_ssl={'true' if use_ssl else 'false'};")
        con.execute("SET s3_url_style='path';")
        r = con.execute(f"SELECT COUNT(*) FROM iceberg_scan('{path}', allow_moved_paths=true)").fetchone()
        return r[0] if r else 0
    except Exception as e:
        return -1
    finally:
        con.close()

bronze = count('s3://warehouse/bronze/raw_trips')
silver = count('s3://warehouse/silver/cleaned_trips')
print(f"BRONZE={bronze}")
print(f"SILVER={silver}")
PYEOF
)

BRONZE=$(echo "$COUNT_RESULT" | grep 'BRONZE=' | cut -d= -f2 | tr -d '[:space:]')
SILVER=$(echo "$COUNT_RESULT" | grep 'SILVER=' | cut -d= -f2 | tr -d '[:space:]')
BRONZE="${BRONZE:-0}"
SILVER="${SILVER:-0}"

echo "  Bronze rows: $BRONZE"
echo "  Silver rows: $SILVER"

# Bronze completeness check (>= 95% of produced events)
if [ "$EVENTS_PRODUCED" -gt 0 ]; then
    THRESHOLD=$(echo "scale=0; $EVENTS_PRODUCED * 95 / 100" | bc)
    if [ "$BRONZE" -ge "$THRESHOLD" ]; then
        pass "Bronze completeness: $BRONZE >= 95% of $EVENTS_PRODUCED produced"
    else
        fail "Bronze completeness: $BRONZE < 95% of $EVENTS_PRODUCED (threshold: $THRESHOLD)"
    fi
else
    if [ "$BRONZE" -gt 0 ]; then
        pass "Bronze has rows: $BRONZE (generator metrics unavailable for % check)"
    else
        fail "Bronze is empty (0 rows)"
    fi
fi

# Silver <= bronze (dedup can only reduce, never exceed)
if [ "$SILVER" -le "$BRONZE" ] && [ "$SILVER" -gt 0 ]; then
    pass "Silver rows ($SILVER) <= bronze ($BRONZE) and > 0"
elif [ "$SILVER" -eq 0 ]; then
    fail "Silver is empty (0 rows) — check Flink silver job logs"
else
    fail "Silver ($SILVER) > bronze ($BRONZE) — impossible, investigate"
fi

# Iceberg metadata health: verify Silver table has committed snapshot metadata
# An iceberg_scan() returning rows already proves metadata exists, but this
# check explicitly confirms the metadata/ folder (catches partial commits).
ICEBERG_META=$(
    $COMPOSE run --rm --no-deps \
        --entrypoint python3 \
        dbt - <<'PYEOF' 2>/dev/null
import duckdb, os, sys

endpoint = os.environ.get('DUCKDB_S3_ENDPOINT', 'minio:9000')
key = os.environ.get('AWS_ACCESS_KEY_ID', 'minioadmin')
secret = os.environ.get('AWS_SECRET_ACCESS_KEY', 'minioadmin')
use_ssl = os.environ.get('DUCKDB_S3_USE_SSL', 'false').lower() == 'true'

con = duckdb.connect()
try:
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute(f"SET s3_endpoint='{endpoint}';")
    con.execute(f"SET s3_access_key_id='{key}';")
    con.execute(f"SET s3_secret_access_key='{secret}';")
    con.execute(f"SET s3_use_ssl={'true' if use_ssl else 'false'};")
    con.execute("SET s3_url_style='path';")
    r = con.execute(
        "SELECT count(*) FROM glob("
        "'s3://warehouse/silver/cleaned_trips/metadata/*.json')"
    ).fetchone()
    print(r[0] if r else 0)
except Exception:
    print(0)
finally:
    con.close()
PYEOF
)
ICEBERG_META=$(echo "$ICEBERG_META" | tr -d '[:space:]')
if [ "${ICEBERG_META:-0}" -gt 0 ]; then
    pass "Iceberg metadata: $ICEBERG_META snapshot file(s) committed"
else
    fail "Iceberg metadata: no snapshot metadata found in silver/cleaned_trips/metadata/"
fi

# DLQ check
DLQ_COUNT=0
if [ "$BROKER" = "redpanda" ]; then
    DLQ_COUNT=$(
        $COMPOSE exec -T broker rpk topic consume "$DLQ_TOPIC" \
            --brokers localhost:9092 --num 9999 --timeout 3s 2>/dev/null \
            | wc -l || echo 0
    )
else
    DLQ_COUNT=$(
        $COMPOSE exec -T broker /opt/kafka/bin/kafka-console-consumer.sh \
            --bootstrap-server localhost:9092 --topic "$DLQ_TOPIC" \
            --from-beginning --timeout-ms 3000 2>/dev/null \
            | wc -l || echo 0
    )
fi
DLQ_COUNT=$(echo "$DLQ_COUNT" | tr -d '[:space:]')

if [ "$DLQ_COUNT" -le "$DLQ_MAX" ]; then
    pass "DLQ: $DLQ_COUNT messages (threshold: $DLQ_MAX)"
else
    fail "DLQ: $DLQ_COUNT messages exceeds DLQ_MAX=$DLQ_MAX — investigate parse errors"
fi

# =============================================================================
# Stage 4: dbt Test
# =============================================================================
section 4 "dbt Test"

DBT_EXIT=0
$COMPOSE run --rm --no-deps \
    --entrypoint /bin/sh \
    dbt -c "dbt test --profiles-dir . 2>&1" || DBT_EXIT=$?

if [ "$DBT_EXIT" -eq 0 ]; then
    pass "dbt test: all tests passed"
else
    fail "dbt test: one or more tests failed (exit code $DBT_EXIT)"
fi

# =============================================================================
# Summary
# =============================================================================
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "  Smoke Test Complete: $PASS/$TOTAL passed"
if [ "$FAIL" -gt 0 ]; then
    echo "  FAILED: $FAIL check(s) — see [FAIL] lines above"
    echo "╚══════════════════════════════════════════════════════════╝"
    exit 1
else
    echo "  All checks passed ✓"
    echo "╚══════════════════════════════════════════════════════════╝"
    exit 0
fi
