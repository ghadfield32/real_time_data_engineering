SHELL := bash
# =============================================================================
# Pipeline 16: Redpanda -> Flink -> Apache Pinot (User-Facing OLAP)
# =============================================================================

COMPOSE = docker compose
FLINK_SQL_CLIENT = MSYS_NO_PATHCONV=1 $(COMPOSE) exec -T flink-jobmanager /opt/flink/bin/sql-client.sh embedded

.PHONY: help up down generate generate-limited create-topics process process-bronze process-silver \
        setup-pinot query-pinot benchmark logs status

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-25s\033[0m %s\n", $$1, $$2}'

up: ## Start all services
	$(COMPOSE) up -d
	@echo ""
	@echo "=== Pipeline 16: Redpanda + Flink + Pinot ==="
	@echo "Redpanda:         localhost:9092"
	@echo "Flink Dashboard:  http://localhost:8083"
	@echo "MinIO Console:    http://localhost:9003 (minioadmin/minioadmin)"
	@echo "Pinot Controller: http://localhost:9010"
	@echo "Pinot Broker:     http://localhost:8099"

down: ## Stop all services
	$(COMPOSE) --profile generator down -v --remove-orphans

create-topics: ## Create Redpanda topics
	$(COMPOSE) exec redpanda rpk topic create taxi.raw_trips \
		--brokers localhost:9092 --partitions 3 --replicas 1 || true

generate: ## Produce taxi events
	MSYS_NO_PATHCONV=1 $(COMPOSE) run --rm -e MAX_EVENTS=10000 data-generator

generate-limited: ## Produce limited events for testing (10k)
	MSYS_NO_PATHCONV=1 $(COMPOSE) run --rm -e MAX_EVENTS=10000 data-generator
	@echo "Limited data generation complete (10k events)."

process: process-bronze process-silver ## Flink Bronze + Silver

process-bronze: ## Bronze: Redpanda -> Iceberg
	$(FLINK_SQL_CLIENT) -i /opt/flink/sql/00-init.sql -f /opt/flink/sql/05-bronze.sql

process-silver: ## Silver: Bronze -> Cleaned Iceberg
	$(FLINK_SQL_CLIENT) -i /opt/flink/sql/00-init.sql -f /opt/flink/sql/06-silver.sql

setup-pinot: ## Create Pinot schema and real-time table
	@echo "Creating Pinot schema..."
	curl -s -X POST "http://localhost:9010/schemas" \
		-H "Content-Type: application/json" \
		-d @pinot/schemas/taxi_trips_schema.json | python3 -m json.tool
	@echo ""
	@echo "Creating Pinot real-time table..."
	curl -s -X POST "http://localhost:9010/tables" \
		-H "Content-Type: application/json" \
		-d @pinot/tables/taxi_trips_table.json | python3 -m json.tool
	@echo "Pinot table created. Events from Redpanda will be ingested automatically."

query-pinot: ## Run benchmark queries against Pinot
	@echo "=== Pinot Query Benchmark ==="
	@echo "Q1: Simple aggregate"
	@curl -s -X POST "http://localhost:8099/query/sql" \
		-H "Content-Type: application/json" \
		-d '{"sql":"SELECT COUNT(*) as total, AVG(fare_amount) as avg_fare FROM taxi_trips"}' | python3 -m json.tool
	@echo ""
	@echo "Q2: Top locations"
	@curl -s -X POST "http://localhost:8099/query/sql" \
		-H "Content-Type: application/json" \
		-d '{"sql":"SELECT PULocationID, COUNT(*) as trips, AVG(total_amount) as avg_total FROM taxi_trips GROUP BY PULocationID ORDER BY trips DESC LIMIT 10"}' | python3 -m json.tool
	@echo ""
	@echo "Q3: Payment type breakdown"
	@curl -s -X POST "http://localhost:8099/query/sql" \
		-H "Content-Type: application/json" \
		-d '{"sql":"SELECT payment_type, COUNT(*) as trips, SUM(total_amount) as revenue FROM taxi_trips GROUP BY payment_type ORDER BY revenue DESC"}' | python3 -m json.tool

benchmark: ## Full E2E benchmark (down -> up -> create-topics -> setup-pinot)
	@echo "============================================================"
	@echo "  Pipeline 16 Benchmark: Redpanda + Flink + Pinot"
	@echo "============================================================"
	@START_TIME=$$(date +%s) && \
	$(MAKE) down 2>/dev/null || true && \
	$(MAKE) up && \
	$(MAKE) create-topics && \
	$(MAKE) setup-pinot && \
	$(MAKE) generate-limited && \
	echo "Waiting for Pinot ingestion (15s)..." && \
	sleep 15 && \
	$(MAKE) query-pinot && \
	$(MAKE) process && \
	END_TIME=$$(date +%s) && \
	ELAPSED=$$((END_TIME - START_TIME)) && \
	echo "" && \
	echo "============================================================" && \
	echo "  BENCHMARK COMPLETE" && \
	echo "  Total elapsed: $${ELAPSED}s" && \
	echo "============================================================" && \
	mkdir -p benchmark_results && \
	echo "{\"pipeline\": \"16-pinot-serving\", \"elapsed_seconds\": $$ELAPSED, \"timestamp\": \"$$(date -Iseconds)\"}" > benchmark_results/latest.json && \
	echo "Results saved to benchmark_results/latest.json"

logs: ## View logs
	$(COMPOSE) logs -f

status: ## Show status
	$(COMPOSE) ps
	@echo ""
	@echo "=== Pinot Table Size ==="
	@curl -s "http://localhost:9010/tables/taxi_trips/size" 2>/dev/null | python3 -m json.tool || echo "(Pinot not ready)"
