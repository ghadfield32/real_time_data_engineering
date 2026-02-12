SHELL := bash
# Pipeline 10: Serving Layer Comparison
COMPOSE := docker compose

.PHONY: up down benchmark benchmark-queries logs status help

up: ## Start ClickHouse + Metabase + Superset
	$(COMPOSE) up -d
	@echo ""
	@echo "=== Pipeline 10: Serving Comparison ==="
	@echo "ClickHouse HTTP:  http://localhost:8123"
	@echo "ClickHouse TCP:   localhost:9100"
	@echo "Metabase:         http://localhost:3030"
	@echo "Superset:         http://localhost:8088  (admin/admin)"
	@echo ""

down: ## Stop all services and remove volumes
	$(COMPOSE) down -v

load-data: ## Load Gold-layer data into ClickHouse (from pipeline output)
	@echo "Loading data into ClickHouse..."
	@echo "Note: Run a Tier 1 pipeline first to generate Gold-layer data."
	@echo "Then export to parquet and load with:"
	@echo "  clickhouse-client --query 'INSERT INTO nyc_taxi.fct_trips FORMAT Parquet' < fct_trips.parquet"

benchmark-queries: ## Run benchmark queries against ClickHouse
	@echo "=== ClickHouse Query Benchmarks ==="
	@for q in 01-daily-revenue 02-top-zones 03-hourly-heatmap 04-complex-revenue; do \
		echo ""; \
		echo "--- Query: $$q ---"; \
		for run in 1 2 3 4 5; do \
			START=$$(date +%s%N); \
			docker exec p10-clickhouse clickhouse-client --queries-file /queries/$$q.sql > /dev/null 2>&1; \
			END=$$(date +%s%N); \
			ELAPSED=$$((($${END} - $${START}) / 1000000)); \
			echo "  Run $$run: $${ELAPSED}ms"; \
		done; \
	done
	@echo ""
	@echo "=== Benchmark complete ==="

benchmark: up benchmark-queries ## Full benchmark: start services + run queries

logs: ## Tail logs
	$(COMPOSE) logs -f

status: ## Show service status
	$(COMPOSE) ps

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
