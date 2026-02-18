SHELL := bash
# =============================================================================
# Template Pipeline: Redpanda + Flink + Iceberg + dbt
# =============================================================================
# TODO: Update the header comment with your pipeline number and domain name.
# TODO: Search-and-replace DOMAIN → your domain (e.g., stock_ticks, orders, iot)
# =============================================================================

COMPOSE = docker compose
FLINK_SQL_CLIENT = MSYS_NO_PATHCONV=1 $(COMPOSE) exec -T flink-jobmanager /opt/flink/bin/sql-client.sh embedded

.PHONY: help up down generate create-topics process process-bronze process-silver \
        process-streaming dbt-build dbt-test dbt-docs benchmark logs status \
        clean ps restart check-lag health \
        compact-silver expire-snapshots vacuum maintain

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# =============================================================================
# Lifecycle
# =============================================================================

up: ## Start all infrastructure services
	$(COMPOSE) up -d
	@echo ""
	@echo "=== Template Pipeline: Redpanda + Flink + Iceberg ==="
	@echo "Redpanda Kafka API: localhost:19092"
	@echo "Redpanda Console:   http://localhost:8085"
	@echo "Flink Dashboard:    http://localhost:8081"
	@echo "MinIO Console:      http://localhost:9001  (minioadmin/minioadmin)"
	@echo ""
	@echo "Next steps:"
	@echo "  make create-topics   # Create Redpanda topics"
	@echo "  make generate        # Produce events to Redpanda"
	@echo "  make process         # Submit Flink SQL batch jobs"
	@echo "  make dbt-build       # Run dbt transformations"

down: ## Stop all services and remove volumes
	$(COMPOSE) --profile generator --profile dbt down -v
	@echo "Pipeline stopped and volumes removed."

clean: ## Stop everything and prune all related resources
	$(COMPOSE) --profile generator --profile dbt down -v --remove-orphans
	docker network rm pXX-pipeline-net 2>/dev/null || true  # TODO: replace XX
	@echo "Pipeline fully cleaned."

restart: ## Restart all services
	$(MAKE) down
	$(MAKE) up

# =============================================================================
# Topic Management
# =============================================================================

create-topics: ## Create Redpanda topics (primary + Dead Letter Queue)
	$(COMPOSE) exec redpanda rpk topic create DOMAIN.raw_events \
		--brokers localhost:9092 \
		--partitions 3 \
		--replicas 1 \
		--topic-config retention.ms=259200000 \
		--topic-config cleanup.policy=delete || true
	$(COMPOSE) exec redpanda rpk topic create DOMAIN.raw_events.dlq \
		--brokers localhost:9092 \
		--partitions 1 \
		--replicas 1 \
		--topic-config retention.ms=604800000 \
		--topic-config cleanup.policy=delete || true
	@$(COMPOSE) exec redpanda rpk topic list --brokers localhost:9092
	@echo "Topics created: DOMAIN.raw_events (3 partitions) + DOMAIN.raw_events.dlq (DLQ, 7-day retention)."

# =============================================================================
# Data Generation
# =============================================================================

generate: ## Produce events to Redpanda (burst mode — all data as fast as possible)
	MSYS_NO_PATHCONV=1 $(COMPOSE) run --rm data-generator
	@echo "Data generation complete."

generate-limited: ## Produce limited events for testing (10k)
	MSYS_NO_PATHCONV=1 $(COMPOSE) run --rm -e MAX_EVENTS=10000 data-generator
	@echo "Limited data generation complete (10k events)."

# =============================================================================
# Flink SQL Processing
# =============================================================================

process: process-bronze process-silver ## Submit all Flink SQL jobs (Bronze + Silver)
	@echo "All Flink SQL jobs complete."

process-bronze: ## Submit Bronze layer Flink SQL jobs (batch mode)
	@echo "=== Bronze: Redpanda → Iceberg ==="
	$(FLINK_SQL_CLIENT) -i /opt/flink/sql/00-init.sql -f /opt/flink/sql/05-bronze.sql
	@echo "Bronze layer complete."

process-silver: ## Submit Silver layer Flink SQL jobs (batch mode)
	@echo "=== Silver: Bronze → Cleaned Iceberg ==="
	$(FLINK_SQL_CLIENT) -i /opt/flink/sql/00-init.sql -f /opt/flink/sql/06-silver.sql
	@echo "Silver layer complete."

process-streaming: ## Start continuous streaming Bronze job (runs indefinitely)
	@echo "=== Streaming Bronze: Redpanda → Iceberg (continuous) ==="
	@echo "NOTE: This job runs indefinitely. Cancel with Ctrl+C or kill the Flink job."
	$(FLINK_SQL_CLIENT) -i /opt/flink/sql/00-init-streaming.sql -f /opt/flink/sql/07-streaming-bronze.sql

# =============================================================================
# dbt Transformations
# =============================================================================

dbt-build: ## Run dbt build (full-refresh) on Iceberg Silver data
	MSYS_NO_PATHCONV=1 $(COMPOSE) run --rm --entrypoint /bin/sh dbt -c "dbt deps --profiles-dir . && dbt build --full-refresh --profiles-dir ."
	@echo "dbt build complete."

dbt-test: ## Run dbt tests only
	MSYS_NO_PATHCONV=1 $(COMPOSE) run --rm dbt test --profiles-dir .

dbt-docs: ## Generate dbt documentation
	MSYS_NO_PATHCONV=1 $(COMPOSE) run --rm dbt docs generate --profiles-dir .

# =============================================================================
# Benchmark (Full End-to-End)
# =============================================================================
# Measures total wall-clock time from cold start to dbt build complete.
# Sequence: down → up → create-topics → generate → (sleep) → process → (sleep) → dbt-build → down
#
# sleep 15 (after up): allow services to stabilize before submitting SQL
# sleep 10 (after generate): allow Flink to catch up with Redpanda lag
# sleep 15 (after process): allow Iceberg metadata commits to finalize
#   without this, dbt may see 0 rows from iceberg_scan() on a just-written table

benchmark: ## Full end-to-end benchmark: down → up → topics → generate → process → dbt → down
	@echo "============================================================"
	@echo "  Template Pipeline Benchmark"
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
	echo "Waiting for Iceberg metadata commits to finalize..." && \
	sleep 15 && \
	$(MAKE) dbt-build && \
	END_TIME=$$(date +%s) && \
	ELAPSED=$$((END_TIME - START_TIME)) && \
	echo "" && \
	echo "============================================================" && \
	echo "  BENCHMARK COMPLETE" && \
	echo "  Total elapsed: $${ELAPSED}s" && \
	echo "============================================================" && \
	mkdir -p benchmark_results && \
	echo "{\"pipeline\": \"template-DOMAIN\", \"elapsed_seconds\": $$ELAPSED, \"timestamp\": \"$$(date -Iseconds)\"}" > benchmark_results/latest.json && \
	echo "Results saved to benchmark_results/latest.json" && \
	$(MAKE) down

# =============================================================================
# Observability
# =============================================================================

logs: ## Tail logs from all services
	$(COMPOSE) logs -f --tail=100

logs-redpanda: ## Tail Redpanda logs
	$(COMPOSE) logs -f redpanda

logs-flink: ## Tail Flink JobManager logs
	$(COMPOSE) logs -f flink-jobmanager

logs-flink-tm: ## Tail Flink TaskManager logs
	$(COMPOSE) logs -f flink-taskmanager

status: ## Show service status
	@echo "=== Pipeline: Service Status ==="
	$(COMPOSE) ps
	@echo ""
	@echo "=== Redpanda Topics ==="
	$(COMPOSE) exec redpanda rpk topic list --brokers localhost:9092 2>/dev/null || echo "(Redpanda not running)"
	@echo ""
	@echo "=== Flink Jobs ==="
	@curl -s http://localhost:8081/jobs/overview 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "(Flink not running)"

ps: ## Show running containers
	$(COMPOSE) ps

# =============================================================================
# Health & Diagnostics
# =============================================================================

health: ## Quick health check of all services
	@echo "=== Pipeline: Health Check ==="
	@echo -n "Redpanda:         " && $(COMPOSE) exec -T redpanda \
	    rpk cluster health --brokers localhost:9092 2>/dev/null | grep -q "Healthy" \
	    && echo "OK" || echo "FAIL"
	@echo -n "Flink Dashboard:  " && curl -sf http://localhost:8081/overview > /dev/null 2>&1 \
	    && echo "OK" || echo "FAIL"
	@echo -n "MinIO:            " && curl -sf http://localhost:9000/minio/health/live > /dev/null 2>&1 \
	    && echo "OK" || echo "FAIL"
	@echo -n "Redpanda Console: " && curl -sf http://localhost:8085 > /dev/null 2>&1 \
	    && echo "OK" || echo "FAIL"

check-lag: ## Show Redpanda consumer group lag and DLQ status
	$(COMPOSE) exec redpanda rpk group describe flink-consumer --brokers localhost:9092
	@echo ""
	@$(COMPOSE) exec -T redpanda rpk topic consume DOMAIN.raw_events.dlq \
	    --brokers localhost:9092 --num 1 2>/dev/null \
	    && echo "DLQ has messages - investigate!" || echo "DLQ: empty (OK)"

# =============================================================================
# Iceberg Maintenance (run periodically in production)
# =============================================================================
# compact-silver:   merge many small Parquet files into larger 128MB files
#                   → improves dbt and analytical query scan performance
# expire-snapshots: remove Iceberg snapshot history older than 7 days
#                   → keeps MinIO clean; you retain the ability to time-travel
# vacuum:           delete orphan data files not referenced by any snapshot
#                   → recovers storage from failed writes / aborted jobs
# maintain:         runs compact-silver + expire-snapshots together

compact-silver: ## Compact Silver Iceberg files to target 128MB file size
	@echo "=== Compacting Silver Iceberg table ==="
	$(FLINK_SQL_CLIENT) -i /opt/flink/sql/00-init.sql <<'EOF'
	CALL iceberg_catalog.system.rewrite_data_files(
	    table => 'silver.cleaned_events',
	    options => map['target-file-size-bytes', '134217728',
	                   'min-file-size-threshold', '33554432']
	);
	EOF
	@echo "Silver compaction complete."

expire-snapshots: ## Expire Iceberg snapshots older than 7 days
	@echo "=== Expiring old Iceberg snapshots ==="
	$(FLINK_SQL_CLIENT) -i /opt/flink/sql/00-init.sql <<'EOF'
	CALL iceberg_catalog.system.expire_snapshots(
	    table => 'silver.cleaned_events',
	    older_than => TIMESTAMPADD(DAY, -7, NOW())
	);
	CALL iceberg_catalog.system.expire_snapshots(
	    table => 'bronze.raw_events',
	    older_than => TIMESTAMPADD(DAY, -7, NOW())
	);
	EOF
	@echo "Snapshot expiry complete."

vacuum: ## Remove orphan files from Iceberg warehouse (run weekly)
	@echo "=== Removing orphan Iceberg files ==="
	$(FLINK_SQL_CLIENT) -i /opt/flink/sql/00-init.sql <<'EOF'
	CALL iceberg_catalog.system.remove_orphan_files(
	    table => 'silver.cleaned_events',
	    older_than => TIMESTAMPADD(DAY, -7, NOW())
	);
	EOF
	@echo "Vacuum complete."

maintain: compact-silver expire-snapshots ## Run all routine Iceberg maintenance
