SHELL := bash
# =============================================================================
# Pipeline 01: Kafka + Flink + Iceberg
# =============================================================================
# Makefile for orchestrating the complete streaming pipeline lifecycle.
# =============================================================================

COMPOSE = docker compose
FLINK_SQL_CLIENT = $(COMPOSE) exec -T flink-jobmanager /opt/flink/bin/sql-client.sh embedded

.PHONY: help up down generate create-topics process process-bronze process-silver \
        dbt-build benchmark logs status clean ps restart

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
	@echo "Schema Registry:  http://localhost:8085"
	@echo "Flink Dashboard:  http://localhost:8081"
	@echo "MinIO Console:    http://localhost:9001  (minioadmin/minioadmin)"
	@echo ""
	@echo "Next steps:"
	@echo "  make create-topics   # Create Kafka topics"
	@echo "  make generate        # Produce taxi events to Kafka"
	@echo "  make process         # Submit Flink SQL jobs"
	@echo "  make dbt-build       # Run dbt transformations"

down: ## Stop all services and remove volumes
	$(COMPOSE) --profile generator --profile dbt down -v
	@echo "Pipeline 01 stopped and volumes removed."

clean: ## Stop everything and prune all related resources
	$(COMPOSE) --profile generator --profile dbt down -v --remove-orphans
	docker network rm p01-pipeline-net 2>/dev/null || true
	@echo "Pipeline 01 fully cleaned."

restart: ## Restart all services
	$(MAKE) down
	$(MAKE) up

# =============================================================================
# Topic Management
# =============================================================================

create-topics: ## Create Kafka topics
	$(COMPOSE) exec kafka /opt/kafka/bin/kafka-topics.sh \
		--bootstrap-server localhost:9092 \
		--create \
		--topic taxi.raw_trips \
		--partitions 3 \
		--replication-factor 1 \
		--if-not-exists
	@echo "Topic taxi.raw_trips created (3 partitions)."

# =============================================================================
# Data Generation
# =============================================================================

generate: ## Produce taxi trip events to Kafka (burst mode)
	$(COMPOSE) run --rm data-generator
	@echo "Data generation complete."

generate-limited: ## Produce limited events for testing (10k)
	$(COMPOSE) run --rm -e MAX_EVENTS=10000 data-generator
	@echo "Limited data generation complete (10k events)."

# =============================================================================
# Flink SQL Processing
# =============================================================================

process: process-bronze process-silver ## Submit all Flink SQL jobs (Bronze + Silver)
	@echo "All Flink SQL jobs submitted."

process-bronze: ## Submit Bronze layer Flink SQL jobs
	@echo "=== Creating Kafka source table ==="
	$(FLINK_SQL_CLIENT) -f /opt/flink/sql/01-create-kafka-source.sql
	@echo ""
	@echo "=== Creating Iceberg catalog ==="
	$(FLINK_SQL_CLIENT) -f /opt/flink/sql/02-create-iceberg-catalog.sql
	@echo ""
	@echo "=== Creating Bronze table + INSERT job ==="
	$(FLINK_SQL_CLIENT) -f /opt/flink/sql/03-bronze-raw-trips.sql
	@echo "Bronze layer processing submitted."

process-silver: ## Submit Silver layer Flink SQL jobs
	@echo "=== Creating Silver table + INSERT job ==="
	$(FLINK_SQL_CLIENT) -f /opt/flink/sql/04-silver-cleaned-trips.sql
	@echo "Silver layer processing submitted."

# =============================================================================
# dbt Transformations
# =============================================================================

dbt-build: ## Run dbt build (full-refresh) on Iceberg Silver data
	$(COMPOSE) run --rm dbt build --full-refresh --profiles-dir .
	@echo "dbt build complete."

dbt-test: ## Run dbt tests only
	$(COMPOSE) run --rm dbt test --profiles-dir .

dbt-docs: ## Generate dbt documentation
	$(COMPOSE) run --rm dbt docs generate --profiles-dir .

# =============================================================================
# Benchmark (Full E2E)
# =============================================================================

benchmark: ## Full end-to-end benchmark: up → topics → generate → process → dbt → down
	@echo "============================================================"
	@echo "  Pipeline 01 Benchmark: Kafka + Flink + Iceberg"
	@echo "============================================================"
	@START_TIME=$$(date +%s) && \
	$(MAKE) up && \
	echo "Waiting for services to stabilize..." && \
	sleep 15 && \
	$(MAKE) create-topics && \
	$(MAKE) generate && \
	echo "Waiting for Flink processing to catch up..." && \
	sleep 10 && \
	$(MAKE) process && \
	echo "Waiting for streaming jobs to process data..." && \
	sleep 30 && \
	$(MAKE) dbt-build && \
	END_TIME=$$(date +%s) && \
	ELAPSED=$$((END_TIME - START_TIME)) && \
	echo "" && \
	echo "============================================================" && \
	echo "  BENCHMARK COMPLETE" && \
	echo "  Total elapsed: $${ELAPSED}s" && \
	echo "============================================================" && \
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
	@curl -s http://localhost:8081/jobs/overview 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "(Flink not running)"

ps: ## Show running containers
	$(COMPOSE) ps
