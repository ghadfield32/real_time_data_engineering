SHELL := bash
# =============================================================================
# Pipeline 07: Kestra Orchestrated (Kafka + Flink + Iceberg + Kestra)
# =============================================================================
# Makefile for orchestrating the Kestra-managed streaming pipeline lifecycle.
# =============================================================================

COMPOSE = docker compose
FLINK_SQL_CLIENT = MSYS_NO_PATHCONV=1 $(COMPOSE) exec -T flink-jobmanager /opt/flink/bin/sql-client.sh embedded

.PHONY: help up down generate create-topics process process-bronze process-silver \
        dbt-build benchmark logs status clean ps restart kestra-ui

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# =============================================================================
# Lifecycle
# =============================================================================

up: ## Start all infrastructure services (including Kestra)
	$(COMPOSE) up -d
	@echo ""
	@echo "=== Pipeline 07: Kestra Orchestrated ==="
	@echo "Kafka:            localhost:9092"
	@echo "Schema Registry:  http://localhost:8085"
	@echo "Flink Dashboard:  http://localhost:8081"
	@echo "MinIO Console:    http://localhost:9001  (minioadmin/minioadmin)"
	@echo "Kestra UI:        http://localhost:8083"
	@echo ""
	@echo "Next steps:"
	@echo "  make create-topics   # Create Kafka topics"
	@echo "  make generate        # Produce taxi events to Kafka"
	@echo "  make process         # Submit Flink SQL jobs"
	@echo "  make dbt-build       # Run dbt transformations"
	@echo "  make kestra-ui       # Open Kestra UI"

down: ## Stop all services and remove volumes
	$(COMPOSE) --profile generator --profile dbt down -v
	@echo "Pipeline 07 stopped and volumes removed."

clean: ## Stop everything and prune all related resources
	$(COMPOSE) --profile generator --profile dbt down -v --remove-orphans
	docker network rm p07-pipeline-net 2>/dev/null || true
	@echo "Pipeline 07 fully cleaned."

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
	MSYS_NO_PATHCONV=1 $(COMPOSE) run --rm data-generator
	@echo "Data generation complete."

# =============================================================================
# Flink SQL Processing
# =============================================================================

process: process-bronze process-silver ## Submit all Flink SQL jobs (Bronze + Silver)
	@echo "All Flink SQL jobs submitted."

process-bronze: ## Submit Bronze layer Flink SQL jobs (batch mode)
	@echo "=== Bronze: Kafka → Iceberg ==="
	$(FLINK_SQL_CLIENT) -i /opt/flink/sql/00-init.sql -f /opt/flink/sql/05-bronze.sql
	@echo "Bronze layer complete."

process-silver: ## Submit Silver layer Flink SQL jobs (batch mode)
	@echo "=== Silver: Bronze → Cleaned Iceberg ==="
	$(FLINK_SQL_CLIENT) -i /opt/flink/sql/00-init.sql -f /opt/flink/sql/06-silver.sql
	@echo "Silver layer complete."

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
# Kestra
# =============================================================================

kestra-ui: ## Show Kestra UI URL
	@echo "Kestra UI: http://localhost:8083"

# =============================================================================
# Benchmark (Full E2E)
# =============================================================================

benchmark: ## Full end-to-end benchmark: up -> topics -> generate -> process -> dbt -> down
	@echo "============================================================"
	@echo "  Pipeline 07 Benchmark: Kestra Orchestrated"
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
	echo "{\"pipeline\": \"07-kestra-orchestrated\", \"elapsed_seconds\": $$ELAPSED, \"timestamp\": \"$$(date -Iseconds)\"}" > benchmark_results/latest.json && \
	echo "Results saved to benchmark_results/latest.json" && \
	$(MAKE) down

# =============================================================================
# Observability
# =============================================================================

logs: ## Tail logs from all services
	$(COMPOSE) logs -f --tail=100

logs-kestra: ## Tail Kestra logs
	$(COMPOSE) logs -f kestra

status: ## Show service status
	@echo "=== Pipeline 07: Service Status ==="
	$(COMPOSE) ps
	@echo ""
	@echo "=== Kafka Topics ==="
	$(COMPOSE) exec kafka /opt/kafka/bin/kafka-topics.sh \
		--bootstrap-server localhost:9092 --list 2>/dev/null || echo "(Kafka not running)"
	@echo ""
	@echo "=== Flink Jobs ==="
	@curl -s http://localhost:8081/jobs/overview 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "(Flink not running)"
	@echo ""
	@echo "=== Kestra ==="
	@curl -s http://localhost:8083/api/v1/flows 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "(Kestra not running)"

ps: ## Show running containers
	$(COMPOSE) ps
