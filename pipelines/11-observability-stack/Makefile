SHELL := bash
# Pipeline 11: Observability Stack
COMPOSE := docker compose
FLINK_SQL_CLIENT = MSYS_NO_PATHCONV=1 $(COMPOSE) exec -T flink-jobmanager /opt/flink/bin/sql-client.sh embedded

.PHONY: up down generate create-topics process process-bronze process-silver dbt-build soda-check elementary-report benchmark logs status help

up: ## Start all infrastructure services
	$(COMPOSE) up -d
	@echo ""
	@echo "=== Pipeline 11: Observability Stack ==="
	@echo "Kafka:            localhost:9092"
	@echo "Flink Dashboard:  http://localhost:8081"
	@echo "MinIO Console:    http://localhost:9001"

down: ## Stop all services and remove volumes
	$(COMPOSE) --profile generator --profile dbt --profile quality down -v

create-topics: ## Create Kafka topics
	$(COMPOSE) exec kafka /opt/kafka/bin/kafka-topics.sh \
		--bootstrap-server localhost:9092 \
		--create --if-not-exists \
		--topic taxi.raw_trips --partitions 3 --replication-factor 1

generate: ## Produce taxi events to Kafka
	MSYS_NO_PATHCONV=1 $(COMPOSE) run --rm data-generator

process-bronze: ## Submit Bronze layer Flink SQL jobs (batch mode)
	@echo "=== Bronze: Kafka → Iceberg ==="
	$(FLINK_SQL_CLIENT) -i /opt/flink/sql/00-init.sql -f /opt/flink/sql/05-bronze.sql
	@echo "Bronze layer complete."

process-silver: ## Submit Silver layer Flink SQL jobs (batch mode)
	@echo "=== Silver: Bronze → Cleaned Iceberg ==="
	$(FLINK_SQL_CLIENT) -i /opt/flink/sql/00-init.sql -f /opt/flink/sql/06-silver.sql
	@echo "Silver layer complete."

process: process-bronze process-silver ## Submit all Flink SQL jobs (Bronze + Silver)
	@echo "All Flink SQL jobs submitted."

dbt-build: ## Run dbt build with Elementary
	MSYS_NO_PATHCONV=1 $(COMPOSE) run --rm --entrypoint /bin/sh dbt -c "dbt deps --profiles-dir . && dbt build --full-refresh --profiles-dir ."

soda-check: ## Run Soda Core quality checks
	@echo "=== Running Soda Core Checks ==="
	MSYS_NO_PATHCONV=1 $(COMPOSE) run --rm soda scan -d nyc_taxi -c /soda/configuration.yml /soda/checks/bronze_checks.yml
	MSYS_NO_PATHCONV=1 $(COMPOSE) run --rm soda scan -d nyc_taxi -c /soda/configuration.yml /soda/checks/silver_checks.yml
	MSYS_NO_PATHCONV=1 $(COMPOSE) run --rm soda scan -d nyc_taxi -c /soda/configuration.yml /soda/checks/gold_checks.yml
	@echo "=== Soda checks complete ==="

elementary-report: ## Generate Elementary observability report
	MSYS_NO_PATHCONV=1 $(COMPOSE) run --rm --entrypoint /bin/sh dbt -c "dbt deps --profiles-dir . && dbt run --select elementary --profiles-dir ."
	@echo "Elementary report generated. Check dbt_project/target/elementary_output.html"

benchmark: ## Full E2E: generate -> process -> dbt -> quality checks
	@echo "============================================================"
	@echo "  Pipeline 11 Benchmark: Observability Stack"
	@echo "============================================================"
	@START_TIME=$$(date +%s) && \
	$(MAKE) up && \
	echo "Waiting for services to stabilize..." && \
	sleep 15 && \
	$(MAKE) create-topics && \
	$(MAKE) generate && \
	echo "Waiting for Flink processing to catch up..." && \
	sleep 10 && \
	$(MAKE) process-bronze && \
	echo "Waiting for Bronze data to settle..." && \
	sleep 10 && \
	$(MAKE) process-silver && \
	echo "Waiting for Silver data to settle..." && \
	sleep 30 && \
	$(MAKE) dbt-build && \
	$(MAKE) soda-check && \
	END_TIME=$$(date +%s) && \
	ELAPSED=$$((END_TIME - START_TIME)) && \
	echo "" && \
	echo "============================================================" && \
	echo "  BENCHMARK COMPLETE" && \
	echo "  Total elapsed: $${ELAPSED}s" && \
	echo "============================================================"

logs: ## Tail all logs
	$(COMPOSE) logs -f --tail=100

status: ## Show service status
	$(COMPOSE) ps

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
