SHELL := bash
###############################################################################
# Pipeline 05: Redpanda + Spark + Iceberg — Makefile
###############################################################################

COMPOSE := docker compose
PROJECT := 05-redpanda-spark-iceberg

.PHONY: up down generate process dbt-build benchmark logs status clean topics

# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

## Start all core services (Redpanda, Spark, MinIO, dbt)
up:
	$(COMPOSE) up -d redpanda minio mc-init spark-master spark-worker dbt
	@echo "Waiting for services to be healthy..."
	@sleep 10
	$(MAKE) topics

## Stop and remove all containers
down:
	$(COMPOSE) --profile generate down -v --remove-orphans

## Clean up all data (volumes, results)
clean:
	$(COMPOSE) --profile generate down -v --remove-orphans
	rm -rf benchmark_results/*.json

# ---------------------------------------------------------------------------
# Topic Management
# ---------------------------------------------------------------------------

## Create Redpanda topics
topics:
	$(COMPOSE) exec redpanda rpk topic create taxi.raw_trips \
		--brokers localhost:9092 \
		--partitions 6 \
		--replicas 1 || true
	@echo "Topic taxi.raw_trips created."

# ---------------------------------------------------------------------------
# Data Generation
# ---------------------------------------------------------------------------

## Produce taxi events to Redpanda
generate:
	MSYS_NO_PATHCONV=1 $(COMPOSE) run --rm \
		-e MODE=burst \
		-e MAX_EVENTS=0 \
		-e METRICS_PATH=/benchmarks/generator_metrics.json \
		data-generator
	@echo "Data generation complete."

## Produce a small sample (10k events) for testing
generate-sample:
	MSYS_NO_PATHCONV=1 $(COMPOSE) run --rm \
		-e MODE=burst \
		-e MAX_EVENTS=10000 \
		-e METRICS_PATH=/benchmarks/generator_metrics.json \
		data-generator
	@echo "Sample generation complete."

# ---------------------------------------------------------------------------
# Spark Processing
# ---------------------------------------------------------------------------

## Run Bronze + Silver Spark jobs sequentially
process: process-bronze process-silver

## Run Bronze ingest (Redpanda -> Iceberg)
process-bronze:
	MSYS_NO_PATHCONV=1 $(COMPOSE) exec -T spark-master /opt/spark/bin/spark-submit \
		--master local[*] \
		/opt/spark-jobs/bronze_ingest.py
	@echo "Bronze ingest complete."

## Run Silver transform (Bronze Iceberg -> Silver Iceberg)
process-silver:
	MSYS_NO_PATHCONV=1 $(COMPOSE) exec -T spark-master /opt/spark/bin/spark-submit \
		--master local[*] \
		/opt/spark-jobs/silver_transform.py
	@echo "Silver transform complete."

# ---------------------------------------------------------------------------
# dbt
# ---------------------------------------------------------------------------

## Install dbt dependencies and run full build (dbt-duckdb, reads Iceberg via iceberg_scan)
dbt-build:
	MSYS_NO_PATHCONV=1 $(COMPOSE) run --rm --entrypoint /bin/sh dbt -c "dbt deps --profiles-dir . && dbt build --profiles-dir ."

## Run dbt tests only
dbt-test:
	$(COMPOSE) exec dbt dbt test

## Generate dbt docs
dbt-docs:
	$(COMPOSE) exec dbt dbt docs generate

# ---------------------------------------------------------------------------
# Benchmark
# ---------------------------------------------------------------------------

## Run full end-to-end benchmark (down -> up)
benchmark:
	@echo "=== Pipeline 05: Redpanda + Spark + Iceberg Benchmark ==="
	@START_TIME=$$(date +%s) && \
	$(MAKE) down 2>/dev/null || true && \
	$(MAKE) up && \
	$(MAKE) generate-sample && \
	$(MAKE) process && \
	$(MAKE) dbt-build && \
	END_TIME=$$(date +%s) && \
	ELAPSED=$$((END_TIME - START_TIME)) && \
	echo "=== Benchmark complete (Total: $${ELAPSED}s) ==="

# ---------------------------------------------------------------------------
# Observability
# ---------------------------------------------------------------------------

## View logs for all services
logs:
	$(COMPOSE) logs -f

## View logs for a specific service (usage: make logs-svc SVC=redpanda)
logs-svc:
	$(COMPOSE) logs -f $(SVC)

## Show container status and health
status:
	$(COMPOSE) ps
	@echo ""
	@echo "--- Redpanda Topics ---"
	-$(COMPOSE) exec redpanda rpk topic list --brokers localhost:9092 2>/dev/null
	@echo ""
	@echo "--- Redpanda Consumer Groups ---"
	-$(COMPOSE) exec redpanda rpk group list --brokers localhost:9092 2>/dev/null
