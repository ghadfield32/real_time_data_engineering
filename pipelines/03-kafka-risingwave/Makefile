# Pipeline 03 - Kafka + RisingWave (Simplest Streaming Pipeline)
SHELL := bash
.DEFAULT_GOAL := help

COMPOSE := docker compose
PSQL    := PGPASSWORD= psql -h localhost -p 4566 -U root -d dev

# ── Lifecycle ────────────────────────────────────────────────

.PHONY: up down generate process dbt-build benchmark logs status help topics

up: ## Start Kafka + RisingWave infrastructure
	$(COMPOSE) up -d kafka risingwave
	@echo "Waiting for services to be healthy..."
	@$(COMPOSE) exec kafka bash -c '\
		until /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list 2>/dev/null; do \
			echo "  Waiting for Kafka..."; sleep 3; \
		done'
	@echo "Kafka is ready."
	@sleep 5
	@echo "Creating Kafka topics..."
	$(MAKE) topics

down: ## Tear down all containers and volumes
	$(COMPOSE) --profile generate --profile dbt down -v

topics: ## Create Kafka topics
	$(COMPOSE) exec kafka /opt/kafka/bin/kafka-topics.sh \
		--bootstrap-server localhost:9092 \
		--create --if-not-exists \
		--topic taxi.raw_trips \
		--partitions 3 \
		--replication-factor 1
	@echo "Topics created."

generate: ## Produce taxi events into Kafka
	$(COMPOSE) run --rm data-generator
	@echo "Event generation complete."

process: ## Submit RisingWave SQL init scripts (source + materialized views)
	@echo "Submitting RisingWave SQL scripts..."
	$(COMPOSE) exec -T risingwave \
		psql -h localhost -p 4566 -U root -d dev -f /risingwave/sql/01-create-source.sql || true
	@echo "[1/3] Kafka source created."
	$(COMPOSE) exec -T risingwave \
		psql -h localhost -p 4566 -U root -d dev -f /risingwave/sql/02-mv-bronze-trips.sql || true
	@echo "[2/3] Bronze materialized view created."
	$(COMPOSE) exec -T risingwave \
		psql -h localhost -p 4566 -U root -d dev -f /risingwave/sql/03-mv-silver-metrics.sql || true
	@echo "[3/3] Silver materialized view created."
	@echo "All RisingWave objects created. MVs will update automatically as Kafka events arrive."

dbt-build: ## Run dbt build against RisingWave
	$(COMPOSE) run --rm dbt build --profiles-dir .

benchmark: ## Run full pipeline benchmark (generate + process + dbt)
	@echo "=== Benchmark: Pipeline 03 - Kafka + RisingWave ==="
	@echo "[1/4] Infrastructure up..."
	$(MAKE) up
	@echo "[2/4] Creating RisingWave streaming objects..."
	$(MAKE) process
	@echo "[3/4] Generating events..."
	time $(MAKE) generate
	@echo "[4/4] Running dbt build..."
	time $(MAKE) dbt-build
	@echo "=== Benchmark complete ==="

logs: ## Tail logs for all services
	$(COMPOSE) --profile generate --profile dbt logs -f

status: ## Show container status and RisingWave MV row counts
	$(COMPOSE) ps
	@echo ""
	@echo "--- RisingWave Materialized View Counts ---"
	@$(COMPOSE) exec -T risingwave \
		psql -h localhost -p 4566 -U root -d dev \
		-c "SELECT 'bronze_raw_trips' AS mv, count(*) FROM bronze_raw_trips UNION ALL SELECT 'silver_cleaned_trips', count(*) FROM silver_cleaned_trips;" 2>/dev/null || \
		echo "(RisingWave not running or MVs not created yet)"

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'
