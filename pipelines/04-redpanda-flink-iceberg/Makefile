SHELL := bash
# =============================================================================
# Pipeline 04: Redpanda + Flink + Iceberg
# =============================================================================
# Makefile for orchestrating the complete streaming pipeline lifecycle.
# Fork of Pipeline 01 with Redpanda replacing Kafka + Schema Registry.
# =============================================================================

COMPOSE = docker compose
FLINK_SQL_CLIENT = MSYS_NO_PATHCONV=1 $(COMPOSE) exec -T flink-jobmanager /opt/flink/bin/sql-client.sh embedded

.PHONY: help up down generate create-topics process process-bronze process-silver \
        process-streaming dbt-build benchmark logs status clean ps restart

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# =============================================================================
# Lifecycle
# =============================================================================

up: ## Start all infrastructure services
	$(COMPOSE) up -d
	@echo ""
	@echo "=== Pipeline 04: Redpanda + Flink + Iceberg ==="
	@echo "Redpanda Kafka API: localhost:19092"
	@echo "Schema Registry:    http://localhost:18081"
	@echo "Pandaproxy:         http://localhost:18082"
	@echo "Redpanda Admin:     http://localhost:9644"
	@echo "Flink Dashboard:    http://localhost:8081"
	@echo "MinIO Console:      http://localhost:9001  (minioadmin/minioadmin)"
	@echo ""
	@echo "Next steps:"
	@echo "  make create-topics   # Create Redpanda topics"
	@echo "  make generate        # Produce taxi events to Redpanda"
	@echo "  make process         # Submit Flink SQL jobs"
	@echo "  make dbt-build       # Run dbt transformations"

down: ## Stop all services and remove volumes
	$(COMPOSE) --profile generator --profile dbt down -v
	@echo "Pipeline 04 stopped and volumes removed."

clean: ## Stop everything and prune all related resources
	$(COMPOSE) --profile generator --profile dbt down -v --remove-orphans
	docker network rm p04-pipeline-net 2>/dev/null || true
	@echo "Pipeline 04 fully cleaned."

restart: ## Restart all services
	$(MAKE) down
	$(MAKE) up

# =============================================================================
# Topic Management
# =============================================================================

create-topics: ## Create Redpanda topics (primary + Dead Letter Queue)
	$(COMPOSE) exec redpanda rpk topic create taxi.raw_trips \
		--brokers localhost:9092 \
		--partitions 3 \
		--replicas 1 \
		--topic-config retention.ms=259200000 \
		--topic-config cleanup.policy=delete || true
	$(COMPOSE) exec redpanda rpk topic create taxi.raw_trips.dlq \
		--brokers localhost:9092 \
		--partitions 1 \
		--replicas 1 \
		--topic-config retention.ms=604800000 \
		--topic-config cleanup.policy=delete || true
	@$(COMPOSE) exec redpanda rpk topic list --brokers localhost:9092
	@echo "Topics created: taxi.raw_trips (3 partitions) + taxi.raw_trips.dlq (DLQ, 7-day retention)."

# =============================================================================
# Data Generation
# =============================================================================

generate: ## Produce taxi trip events to Redpanda (burst mode)
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

process-streaming: ## Start continuous streaming Bronze job (Redpanda → Iceberg, runs indefinitely)
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
# Benchmark (Full E2E)
# =============================================================================

benchmark: ## Full end-to-end benchmark: down -> up → topics → generate → process → dbt → down
	@echo "============================================================"
	@echo "  Pipeline 04 Benchmark: Redpanda + Flink + Iceberg"
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
	echo "{\"pipeline\": \"04-redpanda-flink-iceberg\", \"elapsed_seconds\": $$ELAPSED, \"timestamp\": \"$$(date -Iseconds)\"}" > benchmark_results/latest.json && \
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
	@echo "=== Pipeline 04: Service Status ==="
	$(COMPOSE) ps
	@echo ""
	@echo "=== Redpanda Topics ==="
	$(COMPOSE) exec redpanda rpk topic list --brokers localhost:9092 2>/dev/null || echo "(Redpanda not running)"
	@echo ""
	@echo "=== Flink Jobs ==="
	@curl -s http://localhost:8081/jobs/overview 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "(Flink not running)"

ps: ## Show running containers
	$(COMPOSE) ps
