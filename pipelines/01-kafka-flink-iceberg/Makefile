SHELL := bash
# =============================================================================
# Pipeline 01: Kafka + Flink + Iceberg (Production-Grade Template)
# =============================================================================
# Makefile for orchestrating the complete streaming pipeline lifecycle.
# =============================================================================

COMPOSE = docker compose
FLINK_SQL_CLIENT = MSYS_NO_PATHCONV=1 $(COMPOSE) exec -T flink-jobmanager /opt/flink/bin/sql-client.sh embedded

.PHONY: help up down generate create-topics process process-bronze process-silver \
        dbt-build benchmark logs status clean ps restart check-lag health \
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
	@echo "=== Pipeline 01: Kafka + Flink + Iceberg ==="
	@echo "Kafka:            localhost:9092"
	@echo "Flink Dashboard:  http://localhost:8083"
	@echo "MinIO Console:    http://localhost:9001  (minioadmin/minioadmin)"
	@echo ""
	@echo "Next steps:"
	@echo "  make create-topics   # Create Kafka topics"
	@echo "  make generate        # Produce taxi events to Kafka"
	@echo "  make process         # Submit Flink SQL jobs"
	@echo "  make dbt-build       # Run dbt transformations"

down: ## Stop all services and remove volumes
	$(COMPOSE) --profile generator --profile dbt --profile lakekeeper down -v
	@echo "Pipeline 01 stopped and volumes removed."

clean: ## Stop everything and prune all related resources
	$(COMPOSE) --profile generator --profile dbt --profile lakekeeper down -v --remove-orphans
	docker network rm p01-pipeline-net 2>/dev/null || true
	@echo "Pipeline 01 fully cleaned."

restart: ## Restart all services
	$(MAKE) down
	$(MAKE) up

# =============================================================================
# Topic Management
# =============================================================================

create-topics: ## Create Kafka topics (raw + DLQ)
	$(COMPOSE) exec kafka /bin/bash /opt/kafka/scripts/create-topics.sh

# =============================================================================
# Data Generation
# =============================================================================

generate: ## Produce taxi trip events to Kafka (burst mode)
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
	@echo "=== Bronze: Kafka → Iceberg ==="
	$(FLINK_SQL_CLIENT) -i /opt/flink/sql/00-init.sql -f /opt/flink/sql/05-bronze.sql
	@echo "Bronze layer complete."

process-silver: ## Submit Silver layer Flink SQL jobs (batch mode)
	@echo "=== Silver: Bronze → Cleaned Iceberg ==="
	$(FLINK_SQL_CLIENT) -i /opt/flink/sql/00-init.sql -f /opt/flink/sql/06-silver.sql
	@echo "Silver layer complete."

process-streaming: ## Start continuous streaming Bronze job
	@echo "=== Streaming Bronze: Kafka → Iceberg (continuous) ==="
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
# Benchmark (Full E2E)
# =============================================================================

benchmark: ## Full end-to-end benchmark: down -> up → topics → generate → process → dbt → down
	@echo "============================================================"
	@echo "  Pipeline 01 Benchmark: Kafka + Flink + Iceberg"
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
	echo "{\"pipeline\": \"01-kafka-flink-iceberg\", \"elapsed_seconds\": $$ELAPSED, \"timestamp\": \"$$(date -Iseconds)\"}" > benchmark_results/latest.json && \
	echo "Results saved to benchmark_results/latest.json" && \
	$(MAKE) down

# =============================================================================
# Observability
# =============================================================================

logs: ## Tail logs from all services
	$(COMPOSE) logs -f --tail=100

logs-kafka: ## Tail Kafka logs
	$(COMPOSE) logs -f kafka

logs-flink: ## Tail Flink JobManager logs
	$(COMPOSE) logs -f flink-jobmanager

logs-flink-tm: ## Tail Flink TaskManager logs
	$(COMPOSE) logs -f flink-taskmanager

status: ## Show service status
	@echo "=== Pipeline 01: Service Status ==="
	$(COMPOSE) ps
	@echo ""
	@echo "=== Kafka Topics ==="
	$(COMPOSE) exec kafka /opt/kafka/bin/kafka-topics.sh \
		--bootstrap-server localhost:9092 --list 2>/dev/null || echo "(Kafka not running)"
	@echo ""
	@echo "=== Flink Jobs ==="
	@curl -s http://localhost:8083/jobs/overview 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "(Flink not running)"

ps: ## Show running containers
	$(COMPOSE) ps

# =============================================================================
# Health & Diagnostics
# =============================================================================

health: ## Quick health check of all services
	@echo "=== Pipeline 01: Health Check ==="
	@echo -n "Kafka:           " && $(COMPOSE) exec -T kafka /opt/kafka/bin/kafka-broker-api-versions.sh --bootstrap-server localhost:9092 > /dev/null 2>&1 && echo "OK" || echo "FAIL"
	@echo -n "MinIO:           " && curl -sf http://localhost:9000/minio/health/live > /dev/null 2>&1 && echo "OK" || echo "FAIL"
	@echo -n "Flink Dashboard: " && curl -sf http://localhost:8083/overview > /dev/null 2>&1 && echo "OK" || echo "FAIL"

check-lag: ## Show Kafka consumer group lag
	$(COMPOSE) exec kafka /opt/kafka/bin/kafka-consumer-groups.sh \
		--bootstrap-server localhost:9092 \
		--describe --group flink-consumer 2>/dev/null || echo "(No active consumer group 'flink-consumer')"

# =============================================================================
# Iceberg Maintenance (run periodically in production)
# =============================================================================

compact-silver: ## Compact Silver Iceberg files to target 128MB file size
	@echo "=== Compacting Silver Iceberg table ==="
	$(FLINK_SQL_CLIENT) -i /opt/flink/sql/00-init.sql <<'EOF'
	CALL iceberg_catalog.system.rewrite_data_files(
	    table => 'silver.cleaned_trips',
	    options => map['target-file-size-bytes', '134217728',
	                   'min-file-size-threshold', '33554432']
	);
	EOF
	@echo "Silver compaction complete."

expire-snapshots: ## Expire Iceberg snapshots older than 7 days
	@echo "=== Expiring old Iceberg snapshots ==="
	$(FLINK_SQL_CLIENT) -i /opt/flink/sql/00-init.sql <<'EOF'
	CALL iceberg_catalog.system.expire_snapshots(
	    table => 'silver.cleaned_trips',
	    older_than => TIMESTAMPADD(DAY, -7, NOW())
	);
	CALL iceberg_catalog.system.expire_snapshots(
	    table => 'bronze.raw_trips',
	    older_than => TIMESTAMPADD(DAY, -7, NOW())
	);
	EOF
	@echo "Snapshot expiry complete."

vacuum: ## Remove orphan files from Iceberg warehouse (run weekly)
	@echo "=== Removing orphan Iceberg files ==="
	$(FLINK_SQL_CLIENT) -i /opt/flink/sql/00-init.sql <<'EOF'
	CALL iceberg_catalog.system.remove_orphan_files(
	    table => 'silver.cleaned_trips',
	    older_than => TIMESTAMPADD(DAY, -7, NOW())
	);
	EOF
	@echo "Vacuum complete."

maintain: compact-silver expire-snapshots ## Run all routine Iceberg maintenance

# =============================================================================
# Lakekeeper REST Catalog (opt-in)
# =============================================================================

up-lakekeeper: ## Start with Lakekeeper REST catalog
	$(COMPOSE) --profile lakekeeper up -d
	@echo ""
	@echo "=== Pipeline 01: Kafka + Flink + Iceberg (Lakekeeper REST Catalog) ==="
	@echo "Lakekeeper UI:    http://localhost:8181"
	@echo "Flink Dashboard:  http://localhost:8083"
	@echo ""
	@echo "Use 'make process-rest' to run Flink SQL with REST catalog"

process-rest: process-bronze-rest process-silver-rest ## Submit Flink SQL via REST catalog
	@echo "All Flink SQL jobs complete (REST catalog)."

process-bronze-rest: ## Submit Bronze layer via REST catalog
	@echo "=== Bronze: Kafka → Iceberg (REST catalog) ==="
	$(FLINK_SQL_CLIENT) -i /opt/flink/sql/00-init-rest.sql -f /opt/flink/sql/05-bronze.sql
	@echo "Bronze layer complete."

process-silver-rest: ## Submit Silver layer via REST catalog
	@echo "=== Silver: Bronze → Cleaned Iceberg (REST catalog) ==="
	$(FLINK_SQL_CLIENT) -i /opt/flink/sql/00-init-rest.sql -f /opt/flink/sql/06-silver.sql
	@echo "Silver layer complete."
