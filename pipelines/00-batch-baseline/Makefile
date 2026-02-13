# Pipeline 00 - Batch Baseline (dbt + DuckDB on Parquet)
SHELL := bash
.DEFAULT_GOAL := help

# ── Lifecycle ────────────────────────────────────────────────

.PHONY: up down generate process dbt-build benchmark logs status help

up: ## Build and run the dbt container (full pipeline)
	docker compose up --build --abort-on-container-exit

down: ## Tear down containers and remove volumes
	docker compose down -v

generate: ## No-op: data is pre-existing parquet
	@echo "generate: no-op for batch-baseline (uses static parquet file)"

process: ## No-op: dbt handles all processing
	@echo "process: no-op for batch-baseline (run 'make dbt-build' instead)"

dbt-build: ## Run dbt build inside the container
	docker compose run --rm --entrypoint /bin/sh dbt -c "dbt deps --profiles-dir . && dbt build --full-refresh --profiles-dir ."

benchmark: ## Time a full dbt build
	@echo "=== Benchmark: Pipeline 00 - Batch Baseline ==="
	time docker compose run --rm --entrypoint /bin/sh dbt -c "dbt deps --profiles-dir . && dbt build --full-refresh --profiles-dir ."

logs: ## Show dbt container logs
	docker compose logs dbt

status: ## Show container status
	docker compose ps

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'
