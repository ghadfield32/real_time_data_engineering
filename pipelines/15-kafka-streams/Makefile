SHELL := bash
# =============================================================================
# Pipeline 15: Kafka Streams Lightweight Processing
# =============================================================================

COMPOSE = docker compose

.PHONY: help up down generate topics process status logs benchmark count-messages

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

up: ## Start Kafka + Kafka Streams app
	$(COMPOSE) up -d --build
	@echo ""
	@echo "=== Pipeline 15: Kafka Streams ==="
	@echo "Kafka: localhost:9092"
	@echo "Streams app is running and auto-processing events."
	@echo ""
	@echo "Next: make generate  (produce events)"

down: ## Stop all services
	$(COMPOSE) --profile generator down -v --remove-orphans

topics: ## Create Kafka topics
	$(COMPOSE) exec kafka /opt/kafka/bin/kafka-topics.sh \
		--bootstrap-server localhost:9092 \
		--create --if-not-exists \
		--topic taxi.raw_trips --partitions 3 --replication-factor 1
	$(COMPOSE) exec kafka /opt/kafka/bin/kafka-topics.sh \
		--bootstrap-server localhost:9092 \
		--create --if-not-exists \
		--topic taxi.bronze --partitions 3 --replication-factor 1
	$(COMPOSE) exec kafka /opt/kafka/bin/kafka-topics.sh \
		--bootstrap-server localhost:9092 \
		--create --if-not-exists \
		--topic taxi.silver --partitions 3 --replication-factor 1
	@echo "All topics created."

generate: ## Produce 10k taxi events
	MSYS_NO_PATHCONV=1 $(COMPOSE) run --rm -e MAX_EVENTS=10000 data-generator
	@echo "Data generation complete. Kafka Streams will auto-process."

count-messages: ## Count messages in each topic
	@echo "=== Message Counts ==="
	@echo -n "raw_trips: " && MSYS_NO_PATHCONV=1 $(COMPOSE) exec -T kafka /opt/kafka/bin/kafka-run-class.sh \
		kafka.tools.GetOffsetShell --broker-list localhost:9092 --topic taxi.raw_trips --time -1 2>/dev/null | \
		awk -F: '{sum += $$3} END {print sum}'
	@echo -n "bronze:    " && MSYS_NO_PATHCONV=1 $(COMPOSE) exec -T kafka /opt/kafka/bin/kafka-run-class.sh \
		kafka.tools.GetOffsetShell --broker-list localhost:9092 --topic taxi.bronze --time -1 2>/dev/null | \
		awk -F: '{sum += $$3} END {print sum}'
	@echo -n "silver:    " && MSYS_NO_PATHCONV=1 $(COMPOSE) exec -T kafka /opt/kafka/bin/kafka-run-class.sh \
		kafka.tools.GetOffsetShell --broker-list localhost:9092 --topic taxi.silver --time -1 2>/dev/null | \
		awk -F: '{sum += $$3} END {print sum}'

benchmark: ## Full benchmark (down -> up -> topics)
	@echo "============================================================"
	@echo "  Pipeline 15 Benchmark: Kafka Streams (Lightweight)"
	@echo "============================================================"
	@START_TIME=$$(date +%s) && \
	$(MAKE) down 2>/dev/null || true && \
	$(MAKE) up && \
	$(MAKE) topics && \
	$(MAKE) generate && \
	echo "Waiting for Kafka Streams processing (10s)..." && \
	sleep 10 && \
	$(MAKE) count-messages && \
	END_TIME=$$(date +%s) && \
	ELAPSED=$$((END_TIME - START_TIME)) && \
	echo "" && \
	echo "============================================================" && \
	echo "  BENCHMARK COMPLETE" && \
	echo "  Total elapsed: $${ELAPSED}s" && \
	echo "============================================================" && \
	mkdir -p benchmark_results && \
	echo "{\"pipeline\": \"15-kafka-streams\", \"elapsed_seconds\": $$ELAPSED, \"timestamp\": \"$$(date -Iseconds)\"}" > benchmark_results/latest.json && \
	echo "Results saved to benchmark_results/latest.json"

logs: ## View logs
	$(COMPOSE) logs -f

status: ## Show status
	$(COMPOSE) ps
