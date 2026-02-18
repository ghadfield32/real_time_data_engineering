# Pipeline 14 - Kafka + Materialize (Real-Time dbt)
SHELL := bash
.DEFAULT_GOAL := help

COMPOSE := docker compose

# ── Lifecycle ────────────────────────────────────────────────

.PHONY: up down generate generate-limited process dbt-build benchmark logs status help topics

up: ## Start Kafka + Materialize infrastructure
	$(COMPOSE) up -d kafka materialize
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
	MSYS_NO_PATHCONV=1 $(COMPOSE) run --rm data-generator
	@echo "Event generation complete."

generate-limited: ## Produce limited events for testing (10k)
	MSYS_NO_PATHCONV=1 $(COMPOSE) run --rm -e MAX_EVENTS=10000 data-generator
	@echo "Limited data generation complete (10k events)."

process: ## Submit Materialize SQL init scripts (connection + source + materialized views)
	@echo "Submitting Materialize SQL scripts..."
	MSYS_NO_PATHCONV=1 $(COMPOSE) exec -T materialize \
		psql -h localhost -p 6875 -U materialize -d materialize -f /materialize/sql/01-create-source.sql || true
	@echo "[1/3] Kafka connection and source created."
	MSYS_NO_PATHCONV=1 $(COMPOSE) exec -T materialize \
		psql -h localhost -p 6875 -U materialize -d materialize -f /materialize/sql/02-mv-bronze-trips.sql || true
	@echo "[2/3] Bronze materialized view created."
	MSYS_NO_PATHCONV=1 $(COMPOSE) exec -T materialize \
		psql -h localhost -p 6875 -U materialize -d materialize -f /materialize/sql/03-mv-silver-metrics.sql || true
	@echo "[3/3] Silver materialized view created."
	@echo "All Materialize objects created. MVs will update automatically as Kafka events arrive."

dbt-build: ## Run dbt build against Materialize
	MSYS_NO_PATHCONV=1 $(COMPOSE) run --rm --entrypoint /bin/sh dbt -c "dbt deps --profiles-dir . && dbt build --full-refresh --profiles-dir ."

benchmark: ## Run full pipeline benchmark (down -> up, generate + process + dbt)
	@echo "============================================================"
	@echo "  Pipeline 14 Benchmark: Kafka + Materialize"
	@echo "============================================================"
	@START_TIME=$$(date +%s) && \
	$(MAKE) down 2>/dev/null || true && \
	echo "[1/4] Infrastructure up..." && \
	$(MAKE) up && \
	echo "[2/4] Creating Materialize streaming objects..." && \
	$(MAKE) process && \
	echo "[3/4] Generating events..." && \
	$(MAKE) generate-limited && \
	echo "[4/4] Running dbt build..." && \
	$(MAKE) dbt-build && \
	END_TIME=$$(date +%s) && \
	ELAPSED=$$((END_TIME - START_TIME)) && \
	echo "" && \
	echo "============================================================" && \
	echo "  BENCHMARK COMPLETE" && \
	echo "  Total elapsed: $${ELAPSED}s" && \
	echo "============================================================" && \
	mkdir -p benchmark_results && \
	echo "{\"pipeline\": \"14-kafka-materialize\", \"elapsed_seconds\": $$ELAPSED, \"timestamp\": \"$$(date -Iseconds)\"}" > benchmark_results/latest.json && \
	echo "Results saved to benchmark_results/latest.json"

logs: ## Tail logs for all services
	$(COMPOSE) --profile generate --profile dbt logs -f

status: ## Show container status and Materialize MV row counts
	$(COMPOSE) ps
	@echo ""
	@echo "--- Materialize Materialized View Counts ---"
	@MSYS_NO_PATHCONV=1 $(COMPOSE) exec -T materialize \
		psql -h localhost -p 6875 -U materialize -d materialize \
		-c "SELECT 'bronze_raw_trips' AS mv, count(*) FROM bronze_raw_trips UNION ALL SELECT 'silver_cleaned_trips', count(*) FROM silver_cleaned_trips;" 2>/dev/null || \
		echo "(Materialize not running or MVs not created yet)"

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'
