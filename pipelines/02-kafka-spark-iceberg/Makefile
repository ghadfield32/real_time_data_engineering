SHELL := bash
###############################################################################
# Pipeline 02: Kafka + Spark + Iceberg — Makefile
###############################################################################

COMPOSE := docker compose
PROJECT := 02-kafka-spark-iceberg

# Iceberg JARs needed by Spark (fetched at spark-submit time via --packages)
ICEBERG_VERSION := 1.5.2
SPARK_PACKAGES := org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:$(ICEBERG_VERSION),org.apache.hadoop:hadoop-aws:3.3.4,software.amazon.awssdk:bundle:2.25.11

.PHONY: up down generate process dbt-build benchmark logs status clean topics

# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

## Start all core services (Kafka, Spark, MinIO, dbt)
up:
	$(COMPOSE) up -d kafka minio mc-init spark-master spark-worker dbt
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

## Create Kafka topics
topics:
	$(COMPOSE) exec kafka /opt/kafka/bin/kafka-topics.sh \
		--bootstrap-server localhost:9092 \
		--create --if-not-exists \
		--topic taxi.raw_trips \
		--partitions 6 \
		--replication-factor 1
	@echo "Topic taxi.raw_trips created."

# ---------------------------------------------------------------------------
# Data Generation
# ---------------------------------------------------------------------------

## Produce taxi events to Kafka
generate:
	$(COMPOSE) run --rm \
		-e MODE=burst \
		-e MAX_EVENTS=0 \
		-e METRICS_PATH=/benchmarks/generator_metrics.json \
		data-generator
	@echo "Data generation complete."

## Produce a small sample (10k events) for testing
generate-sample:
	$(COMPOSE) run --rm \
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

## Run Bronze ingest (Kafka -> Iceberg)
process-bronze:
	$(COMPOSE) exec spark-master /opt/bitnami/spark/bin/spark-submit \
		--master spark://spark-master:7077 \
		--deploy-mode client \
		--packages $(SPARK_PACKAGES) \
		--conf spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions \
		--conf spark.sql.catalog.warehouse=org.apache.iceberg.spark.SparkCatalog \
		--conf spark.sql.catalog.warehouse.type=hadoop \
		--conf "spark.sql.catalog.warehouse.warehouse=s3a://warehouse/" \
		--conf spark.sql.catalog.warehouse.io-impl=org.apache.iceberg.aws.s3.S3FileIO \
		--conf spark.hadoop.fs.s3a.endpoint=http://minio:9000 \
		--conf spark.hadoop.fs.s3a.access.key=minioadmin \
		--conf spark.hadoop.fs.s3a.secret.key=minioadmin \
		--conf spark.hadoop.fs.s3a.path.style.access=true \
		--conf spark.hadoop.fs.s3a.impl=org.apache.hadoop.fs.s3a.S3AFileSystem \
		/opt/spark-jobs/bronze_ingest.py
	@echo "Bronze ingest complete."

## Run Silver transform (Bronze Iceberg -> Silver Iceberg)
process-silver:
	$(COMPOSE) exec spark-master /opt/bitnami/spark/bin/spark-submit \
		--master spark://spark-master:7077 \
		--deploy-mode client \
		--packages $(SPARK_PACKAGES) \
		--conf spark.sql.extensions=org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions \
		--conf spark.sql.catalog.warehouse=org.apache.iceberg.spark.SparkCatalog \
		--conf spark.sql.catalog.warehouse.type=hadoop \
		--conf "spark.sql.catalog.warehouse.warehouse=s3a://warehouse/" \
		--conf spark.sql.catalog.warehouse.io-impl=org.apache.iceberg.aws.s3.S3FileIO \
		--conf spark.hadoop.fs.s3a.endpoint=http://minio:9000 \
		--conf spark.hadoop.fs.s3a.access.key=minioadmin \
		--conf spark.hadoop.fs.s3a.secret.key=minioadmin \
		--conf spark.hadoop.fs.s3a.path.style.access=true \
		--conf spark.hadoop.fs.s3a.impl=org.apache.hadoop.fs.s3a.S3AFileSystem \
		/opt/spark-jobs/silver_transform.py
	@echo "Silver transform complete."

# ---------------------------------------------------------------------------
# dbt
# ---------------------------------------------------------------------------

## Install dbt dependencies and run full build
dbt-build:
	$(COMPOSE) exec dbt dbt deps
	$(COMPOSE) exec dbt dbt seed
	$(COMPOSE) exec dbt dbt build

## Run dbt tests only
dbt-test:
	$(COMPOSE) exec dbt dbt test

## Generate dbt docs
dbt-docs:
	$(COMPOSE) exec dbt dbt docs generate

# ---------------------------------------------------------------------------
# Benchmark
# ---------------------------------------------------------------------------

## Run full end-to-end benchmark
benchmark: up
	@echo "=== Pipeline 02 Benchmark ==="
	$(MAKE) generate
	$(MAKE) process
	$(MAKE) dbt-build
	@echo "=== Benchmark complete ==="

# ---------------------------------------------------------------------------
# Observability
# ---------------------------------------------------------------------------

## View logs for all services
logs:
	$(COMPOSE) logs -f

## View logs for a specific service (usage: make logs-svc SVC=kafka)
logs-svc:
	$(COMPOSE) logs -f $(SVC)

## Show container status and health
status:
	$(COMPOSE) ps
	@echo ""
	@echo "--- Kafka Topics ---"
	-$(COMPOSE) exec kafka /opt/kafka/bin/kafka-topics.sh \
		--bootstrap-server localhost:9092 --list 2>/dev/null
	@echo ""
	@echo "--- Kafka Consumer Group Offsets ---"
	-$(COMPOSE) exec kafka /opt/kafka/bin/kafka-consumer-groups.sh \
		--bootstrap-server localhost:9092 --list 2>/dev/null
