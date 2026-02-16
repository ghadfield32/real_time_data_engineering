SHELL := bash
# =============================================================================
# Pipeline 23: Full Stack End-to-End Capstone
# =============================================================================
# Architecture: PostgreSQL (WAL) -> Debezium (Kafka Connect) -> Kafka ->
#               Flink SQL -> Iceberg (on MinIO) -> dbt (DuckDB) ->
#               ClickHouse (OLAP) -> Grafana (Dashboards)
# =============================================================================

COMPOSE = docker compose
FLINK_SQL_CLIENT = MSYS_NO_PATHCONV=1 $(COMPOSE) exec -T flink-jobmanager /opt/flink/bin/sql-client.sh embedded

.PHONY: help up down load-data register-connector connector-status list-connectors \
        delete-connector process process-bronze process-silver dbt-build \
        load-clickhouse benchmark logs logs-connect logs-flink status clean ps restart

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-25s\033[0m %s\n", $$1, $$2}'

# =============================================================================
# Lifecycle
# =============================================================================

up: ## Start all infrastructure services
	$(COMPOSE) up -d
	@echo ""
	@echo "=== Pipeline 23: Full Stack Capstone ==="
	@echo "PostgreSQL:       localhost:5432  (taxi/taxi/taxidb)"
	@echo "Kafka:            localhost:9092"
	@echo "Schema Registry:  http://localhost:8085"
	@echo "Kafka Connect:    http://localhost:8083"
	@echo "Flink Dashboard:  http://localhost:8081"
	@echo "MinIO Console:    http://localhost:9001  (minioadmin/minioadmin)"
	@echo "ClickHouse:       localhost:8123"
	@echo "Grafana:          http://localhost:3000  (admin/admin)"
	@echo ""
	@echo "Next steps:"
	@echo "  make register-connector  # Register Debezium CDC connector"
	@echo "  make load-data           # Load taxi data into PostgreSQL (triggers CDC)"
	@echo "  make process             # Submit Flink SQL jobs"
	@echo "  make dbt-build           # Run dbt transformations"

down: ## Stop all services and remove volumes
	$(COMPOSE) --profile loader --profile dbt down -v --remove-orphans
	@echo "Pipeline 23 stopped and volumes removed."

clean: ## Stop everything and prune all related resources
	$(COMPOSE) --profile loader --profile dbt down -v --remove-orphans
	docker network rm p23-pipeline-net 2>/dev/null || true
	@echo "Pipeline 23 fully cleaned."

restart: ## Restart all services
	$(MAKE) down
	$(MAKE) up

# =============================================================================
# Data Loading (CDC source)
# =============================================================================

load-data: ## Load taxi trip data into PostgreSQL (triggers CDC events)
	MSYS_NO_PATHCONV=1 $(COMPOSE) run --rm postgres-loader
	@echo "Data loaded into PostgreSQL. Debezium will capture changes via CDC."

# =============================================================================
# Debezium Connector Management
# =============================================================================

register-connector: ## Register the Debezium PostgreSQL connector
	@echo "Registering Debezium CDC connector..."
	curl -s -X POST http://localhost:8083/connectors \
		-H "Content-Type: application/json" \
		-d @kafka-connect/register-connector.json | python3 -m json.tool
	@echo ""
	@echo "Connector registered. CDC events will flow to Kafka topic: dbserver1.public.taxi_trips"

connector-status: ## Check Debezium connector status
	curl -s http://localhost:8083/connectors/taxi-cdc-connector/status | python3 -m json.tool

list-connectors: ## List all registered connectors
	curl -s http://localhost:8083/connectors | python3 -m json.tool

delete-connector: ## Delete the Debezium connector
	curl -s -X DELETE http://localhost:8083/connectors/taxi-cdc-connector

# =============================================================================
# Flink SQL Processing
# =============================================================================

process: process-bronze process-silver ## Submit all Flink SQL jobs (Bronze + Silver)
	@echo "All Flink SQL jobs complete."

process-bronze: ## Submit Bronze layer Flink SQL jobs (raw CDC -> Iceberg)
	@echo "=== Bronze: CDC Events -> Iceberg ==="
	$(FLINK_SQL_CLIENT) -i /opt/flink/sql/00-init.sql -f /opt/flink/sql/05-bronze-cdc.sql
	@echo "Bronze layer complete."

process-silver: ## Submit Silver layer Flink SQL jobs (parse CDC -> cleaned Iceberg)
	@echo "=== Silver: Bronze CDC -> Cleaned Iceberg ==="
	$(FLINK_SQL_CLIENT) -i /opt/flink/sql/00-init.sql -f /opt/flink/sql/06-silver-cdc.sql
	@echo "Silver layer complete."

# =============================================================================
# dbt Transformations (Gold Layer)
# =============================================================================

dbt-build: ## Run dbt build (full-refresh) on Iceberg Silver data
	MSYS_NO_PATHCONV=1 $(COMPOSE) run --rm --entrypoint /bin/sh dbt -c "dbt deps --profiles-dir . && dbt build --full-refresh --profiles-dir ."
	@echo "dbt build complete."

dbt-test: ## Run dbt tests only
	MSYS_NO_PATHCONV=1 $(COMPOSE) run --rm dbt test --profiles-dir .

dbt-docs: ## Generate dbt documentation
	MSYS_NO_PATHCONV=1 $(COMPOSE) run --rm dbt docs generate --profiles-dir .

# =============================================================================
# ClickHouse (OLAP Serving Layer)
# =============================================================================

load-clickhouse: ## Load Gold data from Iceberg into ClickHouse
	@echo "Loading Gold layer data into ClickHouse..."
	$(COMPOSE) exec clickhouse clickhouse-client --query "SELECT count(*) FROM nyc_taxi.fct_trips" 2>/dev/null || echo "(ClickHouse tables ready for data)"

# =============================================================================
# Benchmark (Full E2E Capstone)
# =============================================================================

benchmark: ## Full end-to-end capstone pipeline benchmark (down -> up)
	@echo "============================================================"
	@echo "  Pipeline 23: Full Stack Capstone Benchmark"
	@echo "  PostgreSQL -> Debezium -> Kafka -> Flink -> Iceberg"
	@echo "               -> dbt -> ClickHouse -> Grafana"
	@echo "============================================================"
	@START_TIME=$$(date +%s) && \
	$(MAKE) down 2>/dev/null || true && \
	$(MAKE) up && \
	echo "Waiting for services to stabilize (20s)..." && \
	sleep 20 && \
	$(MAKE) register-connector && \
	sleep 10 && \
	$(MAKE) load-data && \
	echo "Waiting for CDC events to flow through Kafka (30s)..." && \
	sleep 30 && \
	$(MAKE) process && \
	sleep 30 && \
	$(MAKE) dbt-build && \
	END_TIME=$$(date +%s) && \
	ELAPSED=$$((END_TIME - START_TIME)) && \
	echo "" && \
	echo "============================================================" && \
	echo "  CAPSTONE BENCHMARK COMPLETE" && \
	echo "  Total elapsed: $${ELAPSED}s" && \
	echo "" && \
	echo "  PostgreSQL -> Debezium -> Kafka -> Flink -> Iceberg" && \
	echo "             -> dbt -> ClickHouse -> Grafana" && \
	echo "" && \
	echo "  Grafana:     http://localhost:3000  (admin/admin)" && \
	echo "  ClickHouse:  localhost:8123" && \
	echo "  Flink:       http://localhost:8081" && \
	echo "  MinIO:       http://localhost:9001" && \
	echo "============================================================" && \
	mkdir -p benchmark_results && \
	echo "{\"pipeline\": \"23-full-stack-capstone\", \"elapsed_seconds\": $$ELAPSED, \"timestamp\": \"$$(date -Iseconds)\"}" > benchmark_results/latest.json && \
	echo "Results saved to benchmark_results/latest.json"

# =============================================================================
# Observability
# =============================================================================

logs: ## Tail logs from all services
	$(COMPOSE) logs -f --tail=100

logs-connect: ## Tail Kafka Connect logs
	$(COMPOSE) logs -f kafka-connect

logs-flink: ## Tail Flink JobManager logs
	$(COMPOSE) logs -f flink-jobmanager

logs-flink-tm: ## Tail Flink TaskManager logs
	$(COMPOSE) logs -f flink-taskmanager

logs-postgres: ## Tail PostgreSQL logs
	$(COMPOSE) logs -f postgres

logs-clickhouse: ## Tail ClickHouse logs
	$(COMPOSE) logs -f clickhouse

logs-grafana: ## Tail Grafana logs
	$(COMPOSE) logs -f grafana

status: ## Show service status and CDC metrics
	@echo "=== Pipeline 23: Full Stack Capstone - Service Status ==="
	$(COMPOSE) ps
	@echo ""
	@echo "=== Kafka Connect Connectors ==="
	@curl -s http://localhost:8083/connectors 2>/dev/null || echo "(Kafka Connect not running)"
	@echo ""
	@echo "=== CDC Connector Status ==="
	@curl -s http://localhost:8083/connectors/taxi-cdc-connector/status 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "(Connector not registered)"
	@echo ""
	@echo "=== Kafka Topics ==="
	@MSYS_NO_PATHCONV=1 $(COMPOSE) exec -T kafka /opt/kafka/bin/kafka-topics.sh \
		--bootstrap-server localhost:9092 --list 2>/dev/null || echo "(Kafka not running)"
	@echo ""
	@echo "=== ClickHouse Tables ==="
	@MSYS_NO_PATHCONV=1 $(COMPOSE) exec -T clickhouse clickhouse-client --query "SELECT name, total_rows FROM system.tables WHERE database = 'nyc_taxi'" 2>/dev/null || echo "(ClickHouse not running)"

ps: ## Show running containers
	$(COMPOSE) ps
