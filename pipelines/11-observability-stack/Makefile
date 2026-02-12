SHELL := bash
# Pipeline 11: Observability Stack
COMPOSE := docker compose
FLINK_SQL_CLIENT = $(COMPOSE) exec -T flink-jobmanager /opt/flink/bin/sql-client.sh embedded

.PHONY: up down generate create-topics process dbt-build soda-check elementary-report benchmark logs status help

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
	$(COMPOSE) run --rm data-generator

process: ## Submit Flink SQL jobs (Bronze + Silver)
	$(FLINK_SQL_CLIENT) -f /opt/flink/sql/01-create-kafka-source.sql
	$(FLINK_SQL_CLIENT) -f /opt/flink/sql/02-create-iceberg-catalog.sql
	$(FLINK_SQL_CLIENT) -f /opt/flink/sql/03-bronze-raw-trips.sql
	$(FLINK_SQL_CLIENT) -f /opt/flink/sql/04-silver-cleaned-trips.sql

dbt-build: ## Run dbt build with Elementary
	$(COMPOSE) run --rm dbt deps --profiles-dir .
	$(COMPOSE) run --rm dbt build --profiles-dir .

soda-check: ## Run Soda Core quality checks
	@echo "=== Running Soda Core Checks ==="
	$(COMPOSE) run --rm soda scan -d nyc_taxi -c /soda/configuration.yml /soda/checks/bronze_checks.yml
	$(COMPOSE) run --rm soda scan -d nyc_taxi -c /soda/configuration.yml /soda/checks/silver_checks.yml
	$(COMPOSE) run --rm soda scan -d nyc_taxi -c /soda/configuration.yml /soda/checks/gold_checks.yml
	@echo "=== Soda checks complete ==="

elementary-report: ## Generate Elementary observability report
	$(COMPOSE) run --rm dbt run --select elementary --profiles-dir .
	@echo "Elementary report generated. Check dbt_project/target/elementary_output.html"

benchmark: ## Full E2E: generate -> process -> dbt -> quality checks
	@echo "=== Pipeline 11 Benchmark: Observability Stack ==="
	$(MAKE) up
	sleep 15
	$(MAKE) create-topics
	$(MAKE) generate
	sleep 10
	$(MAKE) process
	sleep 30
	$(MAKE) dbt-build
	$(MAKE) soda-check
	@echo "=== Benchmark complete ==="

logs: ## Tail all logs
	$(COMPOSE) logs -f --tail=100

status: ## Show service status
	$(COMPOSE) ps

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
