SHELL := bash
# =============================================================================
# Pipeline 20: Kafka + Bytewax Python Streaming
# =============================================================================

COMPOSE = docker compose

.PHONY: help up down generate generate-limited topics benchmark logs status count-messages

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

up: ## Start Kafka + Bytewax processor
	$(COMPOSE) up -d --build
	@echo ""
	@echo "=== Pipeline 20: Kafka + Bytewax ==="
	@echo "Kafka: localhost:9092"
	@echo "Bytewax processor is running and auto-processing events."
	@echo ""
	@echo "Next: make generate"

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
	MSYS_NO_PATHCONV=1 $(COMPOSE) run --rm data-generator
	@echo "Data generation complete. Bytewax will auto-process."

generate-limited: ## Produce limited events for testing (10k)
	MSYS_NO_PATHCONV=1 $(COMPOSE) run --rm -e MAX_EVENTS=10000 data-generator
	@echo "Limited data generation complete (10k events)."

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
	@echo "  Pipeline 20 Benchmark: Kafka + Bytewax (Python Streaming)"
	@echo "============================================================"
	@START_TIME=$$(date +%s) && \
	$(MAKE) down 2>/dev/null || true && \
	$(MAKE) up && \
	$(MAKE) topics && \
	$(MAKE) generate-limited && \
	echo "Waiting for Bytewax processing (15s)..." && \
	sleep 15 && \
	$(MAKE) count-messages && \
	END_TIME=$$(date +%s) && \
	ELAPSED=$$((END_TIME - START_TIME)) && \
	echo "" && \
	echo "============================================================" && \
	echo "  BENCHMARK COMPLETE" && \
	echo "  Total elapsed: $${ELAPSED}s" && \
	echo "============================================================" && \
	mkdir -p benchmark_results && \
	echo "{\"pipeline\": \"20-kafka-bytewax\", \"elapsed_seconds\": $$ELAPSED, \"timestamp\": \"$$(date -Iseconds)\"}" > benchmark_results/latest.json && \
	echo "Results saved to benchmark_results/latest.json"

logs: ## View logs
	$(COMPOSE) logs -f

status: ## Show status
	$(COMPOSE) ps
