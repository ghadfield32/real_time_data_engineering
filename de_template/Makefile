SHELL := bash
# =============================================================================
# de_template: Dual-Broker Data Pipeline Template
# =============================================================================
# Four configuration axes (set in .env):
#   BROKER  = redpanda | kafka
#   CATALOG = hadoop   | rest
#   STORAGE = minio    | aws_s3 | gcs | azure
#   MODE    = batch    | streaming_bronze
#
# Quick start:
#   cp .env.example .env
#   make print-config
#   make up
#   make create-topics
#   make generate-limited
#   make process
#   make validate
# =============================================================================

# Load .env if it exists (exports all vars)
ifneq (,$(wildcard .env))
    include .env
    export
endif

# --- Axis defaults (overridable from shell: make up BROKER=kafka) ---
BROKER   ?= redpanda
CATALOG  ?= hadoop
STORAGE  ?= minio
MODE     ?= batch

# GNU make reads .env via `include` as a makefile fragment.
# Lines like "BROKER=redpanda  # comment" leave trailing whitespace in the value.
# Trailing whitespace breaks ifeq comparisons ("redpanda  " != "redpanda").
# $(strip ...) removes leading/trailing whitespace from all four axes.
BROKER   := $(strip $(BROKER))
CATALOG  := $(strip $(CATALOG))
STORAGE  := $(strip $(STORAGE))
MODE     := $(strip $(MODE))

# --- Data directory (host-side, passed to docker compose via environment) ---
# Absolute path is used so Docker Compose gets an unambiguous bind mount source
# regardless of which directory docker compose resolves relative paths from.
# Default: repo-root data/ (one level up from de_template/)
# Override in .env or shell: HOST_DATA_DIR=/your/absolute/path
HOST_DATA_DIR ?= $(abspath $(CURDIR)/../data)
export HOST_DATA_DIR

# --- Compose file assembly based on axes ---
COMPOSE_FILES := -f infra/base.yml

ifeq ($(BROKER),redpanda)
    COMPOSE_FILES += -f infra/broker.redpanda.yml
else
    COMPOSE_FILES += -f infra/broker.kafka.yml
endif

ifeq ($(STORAGE),minio)
    COMPOSE_FILES += -f infra/storage.minio.yml
endif

COMPOSE          = docker compose $(COMPOSE_FILES)
FLINK_SQL_CLIENT = MSYS_NO_PATHCONV=1 $(COMPOSE) exec -T flink-jobmanager /opt/flink/bin/sql-client.sh embedded

.PHONY: help print-config validate-config \
        up down clean restart \
        build-sql show-sql \
        create-topics \
        generate generate-limited \
        process process-bronze process-silver process-streaming \
        wait-for-silver \
        dbt-build dbt-test dbt-docs \
        validate health check-lag \
        benchmark \
        flink-jobs flink-cancel flink-restart-streaming \
        compact-silver expire-snapshots vacuum maintain \
        logs logs-broker logs-flink logs-flink-tm status ps

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-22s\033[0m %s\n", $$1, $$2}'

debug-env: ## Show raw variable values with [brackets] to expose whitespace/path issues
	@echo "=== de_template: Raw Variable Debug ==="
	@echo "BROKER        = [$(BROKER)]"
	@echo "CATALOG       = [$(CATALOG)]"
	@echo "STORAGE       = [$(STORAGE)]"
	@echo "MODE          = [$(MODE)]"
	@echo "COMPOSE_FILES = [$(COMPOSE_FILES)]"
	@echo "HOST_DATA_DIR = [$(HOST_DATA_DIR)]"
	@echo "DATA_PATH     = [$(DATA_PATH)]"
	@echo "TOPIC         = [$(TOPIC)]"
	@echo "WAREHOUSE     = [$(WAREHOUSE)]"

# =============================================================================
# Configuration
# =============================================================================

print-config: ## Echo all resolved configuration axes
	@echo "=== de_template: Resolved Configuration ==="
	@echo "BROKER   = $(BROKER)"
	@echo "CATALOG  = $(CATALOG)"
	@echo "STORAGE  = $(STORAGE)"
	@echo "MODE     = $(MODE)"
	@echo "TOPIC    = $(TOPIC)"
	@echo "DLQ_TOPIC= $(DLQ_TOPIC)"
	@echo "DLQ_MAX  = $(DLQ_MAX)"
	@echo "WAREHOUSE= $(WAREHOUSE)"
	@echo "S3_ENDPOINT (Flink)  = $(S3_ENDPOINT)"
	@echo "DUCKDB_S3_ENDPOINT   = $(DUCKDB_S3_ENDPOINT)"
	@echo "DATA_PATH= $(DATA_PATH)"
	@echo "MAX_EVENTS= $(MAX_EVENTS)"

validate-config: ## Fail on incompatible configuration combinations
ifeq ($(CATALOG),rest)
	@echo "CATALOG=rest: verifying catalog.rest-lakekeeper.yml is valid..."
	@$(COMPOSE) --profile catalog-rest config --quiet 2>/dev/null \
		|| (echo "ERROR: CATALOG=rest config invalid — check infra/catalog.rest-lakekeeper.yml" && exit 1)
endif
ifeq ($(STORAGE),minio)
	@[ -n "$(MINIO_ROOT_USER)" ] \
		|| (echo "ERROR: MINIO_ROOT_USER not set in .env" && exit 1)
	@[ -n "$(MINIO_ROOT_PASSWORD)" ] \
		|| (echo "ERROR: MINIO_ROOT_PASSWORD not set in .env" && exit 1)
	@[ -n "$(S3_ENDPOINT)" ] \
		|| (echo "ERROR: STORAGE=minio requires S3_ENDPOINT in .env (e.g. http://minio:9000)" && exit 1)
	@[ "$(S3_PATH_STYLE)" = "true" ] \
		|| (echo "WARN: STORAGE=minio should have S3_PATH_STYLE=true in .env")
endif
ifeq ($(STORAGE),aws_s3)
	@echo "$(S3_ENDPOINT)" | grep -qi "minio" \
		&& echo "WARN: STORAGE=aws_s3 but S3_ENDPOINT contains 'minio' — did you mean STORAGE=minio?" \
		|| true
endif
	@[ -n "$(TOPIC)" ] \
		|| (echo "ERROR: TOPIC not set in .env" && exit 1)
	@[ -n "$(WAREHOUSE)" ] \
		|| (echo "ERROR: WAREHOUSE not set in .env" && exit 1)
	@# Verify data file exists on the host before starting containers
	@DATA_FILE="$(HOST_DATA_DIR)/$(notdir $(DATA_PATH))"; \
	    [ -f "$$DATA_FILE" ] \
	    || (echo "ERROR: Parquet file not found: $$DATA_FILE" \
	        && echo "  HOST_DATA_DIR = $(HOST_DATA_DIR)" \
	        && echo "  DATA_PATH     = $(DATA_PATH)" \
	        && echo "  Place your parquet file at $$DATA_FILE" \
	        && echo "  or set HOST_DATA_DIR in .env to its parent directory." \
	        && exit 1)
	@echo "Config OK: BROKER=[$(BROKER)] CATALOG=[$(CATALOG)] STORAGE=[$(STORAGE)] MODE=[$(MODE)]"
	@echo "Data file: $(HOST_DATA_DIR)/$(notdir $(DATA_PATH))"

# =============================================================================
# Lifecycle
# =============================================================================

up: validate-config build-sql ## Start all infrastructure services
	$(COMPOSE) up -d
	@echo ""
	@echo "=== de_template: $(BROKER) + Flink + Iceberg ==="
	@echo "Flink Dashboard:    http://localhost:8081"
ifeq ($(STORAGE),minio)
	@echo "MinIO Console:      http://localhost:9001  ($(MINIO_ROOT_USER)/$(MINIO_ROOT_PASSWORD))"
endif
ifeq ($(BROKER),redpanda)
	@echo "Redpanda Console:   http://localhost:8085"
endif
	@echo ""
	@echo "Next steps:"
	@echo "  make create-topics    → Create Kafka topics"
	@echo "  make generate-limited → Produce 10k test events"
	@echo "  make process          → Submit Flink SQL batch jobs"
	@echo "  make validate         → Run 4-stage smoke test"

down: ## Stop all services and remove volumes
	$(COMPOSE) --profile generator --profile dbt --profile catalog-rest down -v
	@echo "Pipeline stopped and volumes removed."

clean: ## Stop everything and prune all related resources
	$(COMPOSE) --profile generator --profile dbt --profile catalog-rest down -v --remove-orphans
	rm -rf build/
	@echo "Pipeline fully cleaned."

restart: ## Restart all services
	$(MAKE) down
	$(MAKE) up

# =============================================================================
# SQL Template Rendering
# =============================================================================

build-sql: ## Render SQL + conf templates → build/sql/ + build/conf/ (strict)
	@mkdir -p build/sql build/conf
	@BROKER="$(BROKER)" CATALOG="$(CATALOG)" STORAGE="$(STORAGE)" MODE="$(MODE)" \
	    TOPIC="$(TOPIC)" DLQ_TOPIC="$(DLQ_TOPIC)" \
	    WAREHOUSE="$(WAREHOUSE)" S3_ENDPOINT="$(S3_ENDPOINT)" \
	    S3_USE_SSL="$(S3_USE_SSL)" S3_PATH_STYLE="$(S3_PATH_STYLE)" \
	    AWS_ACCESS_KEY_ID="$(AWS_ACCESS_KEY_ID)" \
	    AWS_SECRET_ACCESS_KEY="$(AWS_SECRET_ACCESS_KEY)" \
	    python3 scripts/render_sql.py

show-sql: ## Print rendered SQL files and the active config axes
	@echo "=== Active config: BROKER=$(BROKER) CATALOG=$(CATALOG) STORAGE=$(STORAGE) MODE=$(MODE) ==="
	@echo ""
	@for f in build/sql/*.sql build/conf/*.xml; do \
	    [ -f "$$f" ] || continue; \
	    echo "━━━ $$f ━━━"; \
	    cat "$$f"; \
	    echo ""; \
	done

# =============================================================================
# Topic Management
# =============================================================================

create-topics: ## Create broker topics (primary + Dead Letter Queue)
ifeq ($(BROKER),redpanda)
	$(COMPOSE) exec broker rpk topic create $(TOPIC) \
		--brokers localhost:9092 \
		--partitions 3 \
		--replicas 1 \
		--topic-config retention.ms=259200000 \
		--topic-config cleanup.policy=delete || true
	$(COMPOSE) exec broker rpk topic create $(DLQ_TOPIC) \
		--brokers localhost:9092 \
		--partitions 1 \
		--replicas 1 \
		--topic-config retention.ms=604800000 \
		--topic-config cleanup.policy=delete || true
	@$(COMPOSE) exec broker rpk topic list --brokers localhost:9092
else
	$(COMPOSE) exec broker /opt/kafka/bin/kafka-topics.sh \
		--create --if-not-exists \
		--bootstrap-server localhost:9092 \
		--topic $(TOPIC) \
		--partitions 3 \
		--replication-factor 1 \
		--config retention.ms=259200000 \
		--config cleanup.policy=delete
	$(COMPOSE) exec broker /opt/kafka/bin/kafka-topics.sh \
		--create --if-not-exists \
		--bootstrap-server localhost:9092 \
		--topic $(DLQ_TOPIC) \
		--partitions 1 \
		--replication-factor 1 \
		--config retention.ms=604800000 \
		--config cleanup.policy=delete
	@$(COMPOSE) exec broker /opt/kafka/bin/kafka-topics.sh \
		--list --bootstrap-server localhost:9092
endif
	@echo "Topics created: $(TOPIC) (3 partitions) + $(DLQ_TOPIC) (DLQ, 7-day retention)"

# =============================================================================
# Data Generation
# =============================================================================

generate: ## Produce all events to broker (burst mode)
	MSYS_NO_PATHCONV=1 $(COMPOSE) run --rm data-generator
	@echo "Data generation complete."

generate-limited: ## Produce 10k events for testing (smoke test)
	MSYS_NO_PATHCONV=1 $(COMPOSE) run --rm -e MAX_EVENTS=10000 data-generator
	@echo "Limited data generation complete (10k events)."

# =============================================================================
# Flink SQL Processing
# =============================================================================

process: process-bronze process-silver ## Submit all Flink SQL batch jobs (Bronze + Silver)
	@echo "All Flink SQL batch jobs complete."

process-bronze: ## Submit Bronze layer Flink SQL jobs (batch: Kafka → Iceberg)
	@echo "=== Bronze: $(BROKER) → Iceberg ==="
	$(FLINK_SQL_CLIENT) \
	    -i /opt/flink/sql/00_catalog.sql \
	    -f /opt/flink/sql/05_bronze_batch.sql
	@echo "Bronze layer complete."

process-silver: ## Submit Silver layer Flink SQL jobs (batch: Bronze → Cleaned Iceberg)
	@echo "=== Silver: Bronze → Cleaned Iceberg ==="
	$(FLINK_SQL_CLIENT) \
	    -i /opt/flink/sql/00_catalog.sql \
	    -f /opt/flink/sql/06_silver.sql
	@echo "Silver layer complete."

process-streaming: ## Start continuous streaming Bronze job (runs indefinitely)
	@echo "=== Streaming Bronze: $(BROKER) → Iceberg (continuous) ==="
	@echo "NOTE: This job runs indefinitely. Cancel from Flink Dashboard or Ctrl+C."
	$(FLINK_SQL_CLIENT) \
	    -i /opt/flink/sql/00_catalog.sql \
	    -f /opt/flink/sql/07_bronze_streaming.sql

# =============================================================================
# Wait Gate (replaces sleep 15)
# =============================================================================

wait-for-silver: ## Poll Silver table via iceberg_scan until rows > 0 (90s timeout)
	MSYS_NO_PATHCONV=1 $(COMPOSE) run --rm \
	    --entrypoint python3 dbt \
	    /scripts/wait_for_iceberg.py
	@echo "Silver table ready."

# =============================================================================
# dbt Transformations
# =============================================================================

dbt-build: ## Run dbt build (full-refresh) on Iceberg Silver data
	MSYS_NO_PATHCONV=1 $(COMPOSE) run --rm \
	    --entrypoint /bin/sh dbt \
	    -c "dbt deps --profiles-dir . && dbt build --full-refresh --profiles-dir ."
	@echo "dbt build complete."

dbt-test: ## Run dbt tests only
	MSYS_NO_PATHCONV=1 $(COMPOSE) run --rm \
	    --entrypoint /bin/sh dbt \
	    -c "dbt test --profiles-dir ."

dbt-docs: ## Generate dbt documentation
	MSYS_NO_PATHCONV=1 $(COMPOSE) run --rm \
	    --entrypoint /bin/sh dbt \
	    -c "dbt docs generate --profiles-dir ."

# =============================================================================
# Validation (4-stage smoke test)
# =============================================================================

validate: ## Run 4-stage smoke test: health + Flink jobs + row counts + dbt test
	@BROKER="$(BROKER)" MODE="$(MODE)" STORAGE="$(STORAGE)" \
	    CATALOG="$(CATALOG)" DLQ_TOPIC="$(DLQ_TOPIC)" DLQ_MAX="$(DLQ_MAX)" \
	    WAREHOUSE="$(WAREHOUSE)" \
	    DUCKDB_S3_ENDPOINT="$(DUCKDB_S3_ENDPOINT)" \
	    DUCKDB_S3_USE_SSL="$(DUCKDB_S3_USE_SSL)" \
	    AWS_ACCESS_KEY_ID="$(AWS_ACCESS_KEY_ID)" \
	    AWS_SECRET_ACCESS_KEY="$(AWS_SECRET_ACCESS_KEY)" \
	    COMPOSE_FILES="$(COMPOSE_FILES)" \
	    bash scripts/validate.sh

health: ## Quick health check of all services
	@echo "=== de_template: Health Check (BROKER=$(BROKER)) ==="
ifeq ($(BROKER),redpanda)
	@echo -n "Redpanda:         " && $(COMPOSE) exec -T broker \
	    rpk cluster health 2>/dev/null | grep -qE 'Healthy:.+true' \
	    && echo "OK" || echo "FAIL"
	@echo -n "Redpanda Console: " && curl -sf http://localhost:8085 > /dev/null 2>&1 \
	    && echo "OK" || echo "FAIL"
else
	@echo -n "Kafka:            " && $(COMPOSE) exec -T broker \
	    /opt/kafka/bin/kafka-topics.sh --list --bootstrap-server localhost:9092 \
	    > /dev/null 2>&1 && echo "OK" || echo "FAIL"
endif
	@echo -n "Flink Dashboard:  " && curl -sf http://localhost:8081/overview > /dev/null 2>&1 \
	    && echo "OK" || echo "FAIL"
ifeq ($(STORAGE),minio)
	@echo -n "MinIO:            " && curl -sf http://localhost:9000/minio/health/live \
	    > /dev/null 2>&1 && echo "OK" || echo "FAIL"
endif

check-lag: ## Show consumer group lag and DLQ status
ifeq ($(BROKER),redpanda)
	$(COMPOSE) exec broker rpk group describe flink-consumer --brokers localhost:9092
	@echo ""
	@$(COMPOSE) exec -T broker rpk topic consume $(DLQ_TOPIC) \
	    --brokers localhost:9092 --num 1 2>/dev/null \
	    && echo "DLQ has messages - investigate!" || echo "DLQ: empty (OK)"
else
	$(COMPOSE) exec broker /opt/kafka/bin/kafka-consumer-groups.sh \
	    --bootstrap-server localhost:9092 --describe --group flink-consumer
	@echo ""
	@$(COMPOSE) exec -T broker /opt/kafka/bin/kafka-console-consumer.sh \
	    --bootstrap-server localhost:9092 --topic $(DLQ_TOPIC) \
	    --from-beginning --max-messages 1 --timeout-ms 3000 2>/dev/null \
	    && echo "DLQ has messages - investigate!" || echo "DLQ: empty (OK)"
endif

# =============================================================================
# Benchmark (Full End-to-End)
# =============================================================================

benchmark: ## Full benchmark: down → up → topics → generate → process → validate → down
	@echo "============================================================"
	@echo "  de_template Benchmark"
	@echo "  BROKER=$(BROKER)  MODE=$(MODE)"
	@echo "============================================================"
	@START_TIME=$$(date +%s) && \
	$(MAKE) down 2>/dev/null || true && \
	$(MAKE) up && \
	echo "Waiting for services to stabilize..." && \
	sleep 15 && \
	$(MAKE) create-topics && \
	$(MAKE) generate-limited && \
	echo "Waiting for Flink processing to catch up..." && \
	sleep 10 && \
	$(MAKE) process && \
	$(MAKE) wait-for-silver && \
	$(MAKE) dbt-build && \
	END_TIME=$$(date +%s) && \
	ELAPSED=$$((END_TIME - START_TIME)) && \
	echo "" && \
	echo "============================================================" && \
	echo "  BENCHMARK COMPLETE" && \
	echo "  Total elapsed: $${ELAPSED}s" && \
	echo "============================================================" && \
	mkdir -p benchmark_results && \
	echo "{\"broker\": \"$(BROKER)\", \"mode\": \"$(MODE)\", \"elapsed_seconds\": $$ELAPSED, \"timestamp\": \"$$(date -Iseconds)\"}" \
	    > benchmark_results/latest.json && \
	echo "Results saved to benchmark_results/latest.json" && \
	$(MAKE) down

# =============================================================================
# Flink Job Lifecycle (streaming operational control)
# =============================================================================

flink-jobs: ## List all Flink jobs with state + restart count
	@echo "=== Flink Jobs ==="
	@curl -s http://localhost:8081/jobs/overview 2>/dev/null | \
	    python3 -c "import json,sys; d=json.load(sys.stdin); jobs=d.get('jobs',[]); [print('  (no jobs)') for _ in [1] if not jobs] or [print(f'  {j[\"jid\"][:8]}...  state={j[\"state\"]:<10}  name={j[\"name\"]}') for j in jobs]" \
	    2>/dev/null || echo "  (Flink not running)"

flink-cancel: ## Cancel a Flink job by ID: make flink-cancel JOB=<job-id>
ifndef JOB
	@echo "Usage: make flink-cancel JOB=<job-id>"
	@echo "Get job IDs with: make flink-jobs"
	@exit 1
endif
	@echo "Cancelling Flink job: $(JOB)"
	curl -sf -XPATCH "http://localhost:8081/jobs/$(JOB)?mode=cancel" \
	    && echo "Job $(JOB) cancelled." \
	    || echo "Cancel failed — check job ID with: make flink-jobs"

flink-restart-streaming: ## Cancel all RUNNING streaming jobs then start fresh Bronze
	@echo "=== Cancelling all RUNNING Flink jobs ==="
	@RUNNING=$$(curl -s http://localhost:8081/jobs/overview 2>/dev/null | \
	    python3 -c "import json,sys; \
	        d=json.load(sys.stdin); \
	        print(' '.join(j['jid'] for j in d.get('jobs',[]) if j['state']=='RUNNING'))" \
	    2>/dev/null || echo ""); \
	if [ -n "$$RUNNING" ]; then \
	    for jid in $$RUNNING; do \
	        echo "  Cancelling $$jid ..."; \
	        curl -sf -XPATCH "http://localhost:8081/jobs/$$jid?mode=cancel" > /dev/null; \
	    done; \
	    sleep 3; \
	else \
	    echo "  No RUNNING jobs found."; \
	fi
	$(MAKE) process-streaming

# =============================================================================
# Iceberg Maintenance (run periodically in production)
# =============================================================================

compact-silver: ## Compact Silver Iceberg files to target 128MB
	@bash scripts/iceberg_maintenance.sh compact-silver \
	    SQL_CLIENT="$(FLINK_SQL_CLIENT)"

expire-snapshots: ## Expire Iceberg snapshots older than 7 days
	@bash scripts/iceberg_maintenance.sh expire-snapshots \
	    SQL_CLIENT="$(FLINK_SQL_CLIENT)"

vacuum: ## Remove orphan Iceberg files (run weekly)
	@bash scripts/iceberg_maintenance.sh vacuum \
	    SQL_CLIENT="$(FLINK_SQL_CLIENT)"

maintain: compact-silver expire-snapshots ## Run all routine Iceberg maintenance

# =============================================================================
# Observability
# =============================================================================

logs: ## Tail logs from all services
	$(COMPOSE) logs -f --tail=100

logs-broker: ## Tail broker (Redpanda/Kafka) logs
	$(COMPOSE) logs -f broker

logs-flink: ## Tail Flink JobManager logs
	$(COMPOSE) logs -f flink-jobmanager

logs-flink-tm: ## Tail Flink TaskManager logs
	$(COMPOSE) logs -f flink-taskmanager

status: ## Show service status and Flink job list
	@echo "=== de_template: Service Status ==="
	$(COMPOSE) ps
	@echo ""
	@echo "=== Flink Jobs ==="
	@curl -s http://localhost:8081/jobs/overview 2>/dev/null | \
	    python3 -m json.tool 2>/dev/null || echo "(Flink not running)"

ps: ## Show running containers
	$(COMPOSE) ps
