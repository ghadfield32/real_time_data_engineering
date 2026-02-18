SHELL := bash
# =============================================================================
# Pipeline 18: Prefect Orchestrated (Kafka + Flink + Iceberg + Prefect)
# =============================================================================
# Makefile for orchestrating the Prefect-managed streaming pipeline lifecycle.
# =============================================================================

COMPOSE = docker compose
FLINK_SQL_CLIENT = MSYS_NO_PATHCONV=1 $(COMPOSE) exec -T flink-jobmanager /opt/flink/bin/sql-client.sh embedded

.PHONY: help up down generate generate-limited create-topics process process-bronze process-silver \
        dbt-build benchmark logs status clean ps restart prefect-ui run-flow

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# =============================================================================
# Lifecycle
# =============================================================================

up: ## Start all infrastructure services (including Prefect server)
	$(COMPOSE) up -d
	@echo ""
	@echo "=== Pipeline 18: Prefect Orchestrated ==="
	@echo "Kafka:            localhost:9092"
	@echo "Schema Registry:  http://localhost:8085"
	@echo "Flink Dashboard:  http://localhost:8081"
	@echo "MinIO Console:    http://localhost:9001  (minioadmin/minioadmin)"
	@echo "Prefect UI:       http://localhost:4200"
	@echo ""
	@echo "Next steps:"
	@echo "  make create-topics   # Create Kafka topics"
	@echo "  make generate        # Produce taxi events to Kafka"
	@echo "  make process         # Submit Flink SQL jobs"
	@echo "  make dbt-build       # Run dbt transformations"
	@echo "  make run-flow        # Execute the Prefect flow"
	@echo "  make prefect-ui      # Open Prefect UI"

down: ## Stop all services and remove volumes
	$(COMPOSE) --profile generator --profile dbt down -v
	@echo "Pipeline 18 stopped and volumes removed."

clean: ## Stop everything and prune all related resources
	$(COMPOSE) --profile generator --profile dbt down -v --remove-orphans
	docker network rm p18-pipeline-net 2>/dev/null || true
	@echo "Pipeline 18 fully cleaned."

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

generate-limited: ## Produce limited events for testing (10k)
	MSYS_NO_PATHCONV=1 $(COMPOSE) run --rm -e MAX_EVENTS=10000 data-generator
	@echo "Limited data generation complete (10k events)."

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
# Prefect
# =============================================================================

prefect-ui: ## Show Prefect UI URL
	@echo "Prefect UI: http://localhost:4200"

run-flow: ## Execute the Prefect taxi pipeline flow
	@echo "Running Prefect taxi pipeline flow..."
	$(COMPOSE) exec prefect-worker python /flows/taxi_pipeline.py
	@echo "Prefect flow execution complete."

# =============================================================================
# Benchmark (Full E2E)
# =============================================================================

benchmark: ## Full end-to-end benchmark: down -> up -> topics -> generate -> process -> dbt -> down
	@echo "============================================================"
	@echo "  Pipeline 18 Benchmark: Prefect Orchestrated"
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
	$(MAKE) dbt-build && \
	END_TIME=$$(date +%s) && \
	ELAPSED=$$((END_TIME - START_TIME)) && \
	echo "" && \
	echo "============================================================" && \
	echo "  BENCHMARK COMPLETE" && \
	echo "  Total elapsed: $${ELAPSED}s" && \
	echo "============================================================" && \
	mkdir -p benchmark_results && \
	echo "{\"pipeline\": \"18-prefect-orchestrated\", \"elapsed_seconds\": $$ELAPSED, \"timestamp\": \"$$(date -Iseconds)\"}" > benchmark_results/latest.json && \
	echo "Results saved to benchmark_results/latest.json" && \
	$(MAKE) down

# =============================================================================
# Observability
# =============================================================================

logs: ## Tail logs from all services
	$(COMPOSE) logs -f --tail=100

logs-prefect: ## Tail Prefect logs
	$(COMPOSE) logs -f prefect-server prefect-worker

status: ## Show service status
	@echo "=== Pipeline 18: Service Status ==="
	$(COMPOSE) ps
	@echo ""
	@echo "=== Kafka Topics ==="
	$(COMPOSE) exec kafka /opt/kafka/bin/kafka-topics.sh \
		--bootstrap-server localhost:9092 --list 2>/dev/null || echo "(Kafka not running)"
	@echo ""
	@echo "=== Flink Jobs ==="
	@curl -s http://localhost:8081/jobs/overview 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "(Flink not running)"
	@echo ""
	@echo "=== Prefect ==="
	@curl -s http://localhost:4200/api/health 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "(Prefect not running)"

ps: ## Show running containers
	$(COMPOSE) ps
