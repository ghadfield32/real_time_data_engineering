SHELL := bash
# =============================================================================
# Pipeline 17: Kafka -> Flink -> Druid + Grafana
# =============================================================================

COMPOSE = docker compose
FLINK_SQL_CLIENT = MSYS_NO_PATHCONV=1 $(COMPOSE) exec -T flink-jobmanager /opt/flink/bin/sql-client.sh embedded

.PHONY: help up down generate generate-limited create-topics process setup-druid query-druid benchmark logs status

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-25s\033[0m %s\n", $$1, $$2}'

up: ## Start all services
	$(COMPOSE) up -d
	@echo ""
	@echo "=== Pipeline 17: Kafka + Flink + Druid + Grafana ==="
	@echo "Kafka:           localhost:9092"
	@echo "Flink Dashboard: http://localhost:8081"
	@echo "Druid Console:   http://localhost:8889"
	@echo "Grafana:         http://localhost:3000  (admin/admin)"
	@echo "MinIO Console:   http://localhost:9001  (minioadmin/minioadmin)"

down: ## Stop all services
	$(COMPOSE) --profile generator down -v --remove-orphans

create-topics: ## Create Kafka topics
	$(COMPOSE) exec kafka /opt/kafka/bin/kafka-topics.sh \
		--bootstrap-server localhost:9092 --create --if-not-exists \
		--topic taxi.raw_trips --partitions 3 --replication-factor 1

generate: ## Produce taxi events
	MSYS_NO_PATHCONV=1 $(COMPOSE) run --rm -e MAX_EVENTS=10000 data-generator

generate-limited: ## Produce limited events for testing (10k)
	MSYS_NO_PATHCONV=1 $(COMPOSE) run --rm -e MAX_EVENTS=10000 data-generator
	@echo "Limited data generation complete (10k events)."

process: ## Flink Bronze + Silver
	@echo "=== Flink Bronze ==="
	$(FLINK_SQL_CLIENT) -i /opt/flink/sql/00-init.sql -f /opt/flink/sql/05-bronze.sql
	@echo "=== Flink Silver ==="
	$(FLINK_SQL_CLIENT) -i /opt/flink/sql/00-init.sql -f /opt/flink/sql/06-silver.sql

setup-druid: ## Create Druid Kafka ingestion supervisor
	@echo "Creating Druid Kafka supervisor..."
	curl -s -X POST "http://localhost:8082/druid/indexer/v1/supervisor" \
		-H "Content-Type: application/json" \
		-d @druid/conf/supervisor-spec.json | python3 -m json.tool
	@echo "Druid supervisor created. Will auto-ingest from Kafka."

query-druid: ## Run benchmark queries
	@echo "=== Druid Query Benchmark ==="
	@echo "Q1: Total count"
	@curl -s -X POST "http://localhost:8888/druid/v2/sql" \
		-H "Content-Type: application/json" \
		-d '{"query":"SELECT COUNT(*) as total_rows, SUM(\"sum_fare_amount\") as total_fare FROM taxi_trips"}' 2>/dev/null || echo "(Druid not ready)"
	@echo ""
	@echo "Q2: By location"
	@curl -s -X POST "http://localhost:8888/druid/v2/sql" \
		-H "Content-Type: application/json" \
		-d '{"query":"SELECT \"PULocationID\", SUM(\"count\") as trips FROM taxi_trips GROUP BY \"PULocationID\" ORDER BY trips DESC LIMIT 10"}' 2>/dev/null || echo "(Druid not ready)"

benchmark: ## Full E2E benchmark (down -> up -> create-topics -> setup-druid)
	@echo "============================================================"
	@echo "  Pipeline 17 Benchmark: Kafka + Flink + Druid + Grafana"
	@echo "============================================================"
	@START_TIME=$$(date +%s) && \
	$(MAKE) down 2>/dev/null || true && \
	$(MAKE) up && \
	$(MAKE) create-topics && \
	$(MAKE) setup-druid && \
	$(MAKE) generate-limited && \
	echo "Waiting for Druid ingestion (20s)..." && \
	sleep 20 && \
	$(MAKE) query-druid && \
	$(MAKE) process && \
	END_TIME=$$(date +%s) && \
	ELAPSED=$$((END_TIME - START_TIME)) && \
	echo "" && \
	echo "============================================================" && \
	echo "  BENCHMARK COMPLETE" && \
	echo "  Total elapsed: $${ELAPSED}s" && \
	echo "============================================================" && \
	mkdir -p benchmark_results && \
	echo "{\"pipeline\": \"17-druid-timeseries\", \"elapsed_seconds\": $$ELAPSED, \"timestamp\": \"$$(date -Iseconds)\"}" > benchmark_results/latest.json && \
	echo "Results saved to benchmark_results/latest.json"

logs: ## View logs
	$(COMPOSE) logs -f

status: ## Show status
	$(COMPOSE) ps
