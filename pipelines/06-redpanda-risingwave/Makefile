# Pipeline 06 - Redpanda + RisingWave (Simplest Streaming Pipeline)
SHELL := bash
.DEFAULT_GOAL := help

COMPOSE := docker compose

# ── Lifecycle ────────────────────────────────────────────────

.PHONY: up down generate process dbt-build benchmark logs status help topics

up: ## Start Redpanda + RisingWave infrastructure
	$(COMPOSE) up -d redpanda risingwave
	@echo "Waiting for services to be healthy..."
	@$(COMPOSE) exec redpanda bash -c '\
		until rpk cluster health | grep -E "Healthy:.+true"; do \
			echo "  Waiting for Redpanda..."; sleep 3; \
		done'
	@echo "Redpanda is ready."
	@sleep 5
	@echo "Creating topics via rpk..."
	$(MAKE) topics

down: ## Tear down all containers and volumes
	$(COMPOSE) --profile generate --profile dbt down -v

topics: ## Create Redpanda topics
	$(COMPOSE) exec redpanda rpk topic create taxi.raw_trips \
		--brokers redpanda:9092 \
		--partitions 3 \
		--replicas 1 || true
	@echo "Topics created."

generate: ## Produce taxi events into Redpanda
	MSYS_NO_PATHCONV=1 $(COMPOSE) run --rm data-generator
	@echo "Event generation complete."

generate-limited: ## Produce limited events (10k) for benchmarking
	MSYS_NO_PATHCONV=1 $(COMPOSE) run --rm -e MAX_EVENTS=10000 data-generator
	@echo "Limited generation complete (10k events)."

process: ## Submit RisingWave SQL init scripts (source + materialized views)
	@echo "Submitting RisingWave SQL scripts..."
	MSYS_NO_PATHCONV=1 docker run --rm --network 06-redpanda-risingwave_pipeline-net \
		-v "$$(pwd)/risingwave/sql:/sql:ro" postgres:alpine \
		psql -h risingwave -p 4566 -U root -d dev -f /sql/01-create-source.sql || true
	@echo "[1/3] Redpanda source created."
	MSYS_NO_PATHCONV=1 docker run --rm --network 06-redpanda-risingwave_pipeline-net \
		-v "$$(pwd)/risingwave/sql:/sql:ro" postgres:alpine \
		psql -h risingwave -p 4566 -U root -d dev -f /sql/02-mv-bronze-trips.sql || true
	@echo "[2/3] Bronze materialized view created."
	MSYS_NO_PATHCONV=1 docker run --rm --network 06-redpanda-risingwave_pipeline-net \
		-v "$$(pwd)/risingwave/sql:/sql:ro" postgres:alpine \
		psql -h risingwave -p 4566 -U root -d dev -f /sql/03-mv-silver-metrics.sql || true
	@echo "[3/3] Silver materialized view created."
	@echo "All RisingWave objects created. MVs will update automatically as Redpanda events arrive."

dbt-build: ## Run dbt build against RisingWave
	MSYS_NO_PATHCONV=1 $(COMPOSE) run --rm --entrypoint /bin/sh dbt -c "dbt deps --profiles-dir . && dbt build --full-refresh --profiles-dir ."

benchmark: ## Run full pipeline benchmark (down -> up, generate + process + dbt)
	@echo "=== Benchmark: Pipeline 06 - Redpanda + RisingWave ==="
	@$(MAKE) down 2>/dev/null || true
	@echo "[1/4] Infrastructure up..."
	$(MAKE) up
	@echo "[2/4] Creating RisingWave streaming objects..."
	$(MAKE) process
	@echo "[3/4] Generating events (10k)..."
	$(MAKE) generate-limited
	@echo "[4/4] Running dbt build..."
	$(MAKE) dbt-build
	@echo "=== Benchmark complete ==="

logs: ## Tail logs for all services
	$(COMPOSE) --profile generate --profile dbt logs -f

status: ## Show container status and RisingWave MV row counts
	$(COMPOSE) ps
	@echo ""
	@echo "--- RisingWave Materialized View Counts ---"
	@MSYS_NO_PATHCONV=1 docker run --rm --network 06-redpanda-risingwave_pipeline-net postgres:alpine \
		psql -h risingwave -p 4566 -U root -d dev \
		-c "SELECT 'bronze_raw_trips' AS mv, count(*) FROM bronze_raw_trips UNION ALL SELECT 'silver_cleaned_trips', count(*) FROM silver_cleaned_trips;" 2>/dev/null || \
		echo "(RisingWave not running or MVs not created yet)"

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'
