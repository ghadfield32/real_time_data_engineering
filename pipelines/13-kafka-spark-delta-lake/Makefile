SHELL := bash
# =============================================================================
# Pipeline 13: Kafka -> Spark -> Delta Lake (+ dbt micro-batch)
# =============================================================================

COMPOSE = docker compose

.PHONY: help up down generate process process-bronze process-silver \
        dbt-build benchmark logs status clean topics

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

up: ## Start all infrastructure services
	$(COMPOSE) up -d kafka minio mc-init spark-master spark-worker
	@echo "Waiting for services..."
	@sleep 10
	$(MAKE) topics
	@echo ""
	@echo "=== Pipeline 13: Kafka + Spark + Delta Lake ==="
	@echo "Kafka:          localhost:9092"
	@echo "Spark UI:       http://localhost:8080"
	@echo "MinIO Console:  http://localhost:9001 (minioadmin/minioadmin)"

down: ## Stop all services and remove volumes
	$(COMPOSE) --profile generator --profile dbt down -v --remove-orphans
	@echo "Pipeline 13 stopped."

topics: ## Create Kafka topics
	$(COMPOSE) exec kafka /opt/kafka/bin/kafka-topics.sh \
		--bootstrap-server localhost:9092 \
		--create --if-not-exists \
		--topic taxi.raw_trips \
		--partitions 6 \
		--replication-factor 1
	@echo "Topic taxi.raw_trips created."

generate: ## Produce taxi events to Kafka
	MSYS_NO_PATHCONV=1 $(COMPOSE) run --rm \
		-e MODE=burst \
		-e MAX_EVENTS=10000 \
		data-generator
	@echo "Data generation complete."

process: process-bronze process-silver ## Run Bronze + Silver Spark jobs

process-bronze: ## Bronze: Kafka -> Delta Lake
	MSYS_NO_PATHCONV=1 $(COMPOSE) exec -T spark-master /opt/spark/bin/spark-submit \
		--master local[*] \
		/opt/spark-jobs/bronze_ingest.py
	@echo "Bronze ingest complete."

process-silver: ## Silver: Bronze Delta -> Silver Delta
	MSYS_NO_PATHCONV=1 $(COMPOSE) exec -T spark-master /opt/spark/bin/spark-submit \
		--master local[*] \
		/opt/spark-jobs/silver_transform.py
	@echo "Silver transform complete."

dbt-build: ## Run dbt build (micro-batch)
	MSYS_NO_PATHCONV=1 $(COMPOSE) run --rm --entrypoint /bin/sh dbt -c "dbt deps --profiles-dir . && dbt build --full-refresh --profiles-dir ."
	@echo "dbt build complete."

benchmark: ## Full end-to-end benchmark (down -> up)
	@echo "============================================================"
	@echo "  Pipeline 13 Benchmark: Kafka + Spark + Delta Lake"
	@echo "============================================================"
	@START_TIME=$$(date +%s) && \
	$(MAKE) down 2>/dev/null || true && \
	$(MAKE) up && \
	$(MAKE) generate && \
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
	echo "{\"pipeline\": \"13-kafka-spark-delta-lake\", \"elapsed_seconds\": $$ELAPSED, \"timestamp\": \"$$(date -Iseconds)\"}" > benchmark_results/latest.json && \
	echo "Results saved to benchmark_results/latest.json"

logs: ## View logs
	$(COMPOSE) logs -f

status: ## Show container status
	$(COMPOSE) ps

clean: down ## Full cleanup (stop + remove volumes)
	@echo "Pipeline 13 cleaned."
