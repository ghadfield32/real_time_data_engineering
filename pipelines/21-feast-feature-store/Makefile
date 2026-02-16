SHELL := bash
# =============================================================================
# Pipeline 21: Kafka + Flink + Iceberg + Feast Feature Store
# =============================================================================
# Makefile for orchestrating the Feast feature store streaming pipeline.
# =============================================================================

COMPOSE = docker compose
FLINK_SQL_CLIENT = MSYS_NO_PATHCONV=1 $(COMPOSE) exec -T flink-jobmanager /opt/flink/bin/sql-client.sh embedded

.PHONY: help up down generate create-topics process process-bronze process-silver \
        feast-apply feast-materialize feast-serve benchmark logs status

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-25s\033[0m %s\n", $$1, $$2}'

# =============================================================================
# Lifecycle
# =============================================================================

up: ## Start all infrastructure
	$(COMPOSE) up -d
	@echo ""
	@echo "=== Pipeline 21: Feast Feature Store ==="
	@echo "Kafka:           localhost:9092"
	@echo "Schema Registry: http://localhost:8085"
	@echo "Flink Dashboard: http://localhost:8081"
	@echo "MinIO Console:   http://localhost:9001  (minioadmin/minioadmin)"
	@echo "Feast Server:    http://localhost:6566"

down: ## Stop all services
	$(COMPOSE) --profile generator --profile feast down -v --remove-orphans

# =============================================================================
# Topic Management
# =============================================================================

create-topics: ## Create Kafka topics
	$(COMPOSE) exec kafka /opt/kafka/bin/kafka-topics.sh \
		--bootstrap-server localhost:9092 --create --if-not-exists \
		--topic taxi.raw_trips --partitions 3 --replication-factor 1

# =============================================================================
# Data Generation
# =============================================================================

generate: ## Produce taxi events
	MSYS_NO_PATHCONV=1 $(COMPOSE) run --rm data-generator

# =============================================================================
# Flink SQL Processing
# =============================================================================

process: process-bronze process-silver ## Flink Bronze + Silver

process-bronze: ## Bronze layer
	$(FLINK_SQL_CLIENT) -i /opt/flink/sql/00-init.sql -f /opt/flink/sql/05-bronze.sql

process-silver: ## Silver layer
	$(FLINK_SQL_CLIENT) -i /opt/flink/sql/00-init.sql -f /opt/flink/sql/06-silver.sql

# =============================================================================
# Feast Feature Store
# =============================================================================

feast-materialize: ## Export Iceberg data to Feast and materialize features
	MSYS_NO_PATHCONV=1 $(COMPOSE) run --rm feast-server python /app/feast_repo/materialize_features.py

feast-serve: ## Show Feast server URL
	@echo "Feast Feature Server: http://localhost:6566"

# =============================================================================
# Benchmark (Full E2E)
# =============================================================================

benchmark: ## Full E2E benchmark (down -> up)
	@echo "============================================================"
	@echo "  Pipeline 21 Benchmark: Feast Feature Store"
	@echo "============================================================"
	@START_TIME=$$(date +%s) && \
	$(MAKE) down 2>/dev/null || true && \
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
	$(MAKE) feast-materialize && \
	END_TIME=$$(date +%s) && \
	ELAPSED=$$((END_TIME - START_TIME)) && \
	echo "" && \
	echo "============================================================" && \
	echo "  BENCHMARK COMPLETE" && \
	echo "  Total elapsed: $${ELAPSED}s" && \
	echo "============================================================" && \
	mkdir -p benchmark_results && \
	echo "{\"pipeline\": \"21-feast-feature-store\", \"elapsed_seconds\": $$ELAPSED, \"timestamp\": \"$$(date -Iseconds)\"}" > benchmark_results/latest.json && \
	echo "Results saved to benchmark_results/latest.json" && \
	$(MAKE) down

# =============================================================================
# Observability
# =============================================================================

logs: ## View logs
	$(COMPOSE) logs -f

status: ## Show status
	$(COMPOSE) ps
