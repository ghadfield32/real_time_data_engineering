SHELL := bash
COMPOSE = docker compose

.PHONY: help up down generate generate-limited topics benchmark logs status

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

up: ## Start Kafka + Mage AI
	$(COMPOSE) up -d
	@echo ""
	@echo "=== Pipeline 19: Mage AI ==="
	@echo "Kafka:    localhost:9092"
	@echo "Mage UI:  http://localhost:6789"
	@echo ""
	@echo "Open Mage UI and run the taxi_pipeline."

down: ## Stop all services
	$(COMPOSE) --profile generator down -v --remove-orphans

topics: ## Create Kafka topics
	$(COMPOSE) exec kafka /opt/kafka/bin/kafka-topics.sh \
		--bootstrap-server localhost:9092 \
		--create --if-not-exists \
		--topic taxi.raw_trips --partitions 3 --replication-factor 1
	@echo "Topics created."

generate: ## Produce taxi events
	MSYS_NO_PATHCONV=1 $(COMPOSE) run --rm data-generator
	@echo "Data generation complete."

generate-limited: ## Produce limited events for testing (10k)
	MSYS_NO_PATHCONV=1 $(COMPOSE) run --rm -e MAX_EVENTS=10000 data-generator
	@echo "Limited data generation complete (10k events)."

mage-ui: ## Show Mage UI URL
	@echo "Mage UI: http://localhost:6789"

benchmark: ## Full benchmark (down -> up -> topics)
	@echo "============================================================"
	@echo "  Pipeline 19 Benchmark: Mage AI (Visual Pipeline)"
	@echo "============================================================"
	@START_TIME=$$(date +%s) && \
	$(MAKE) down 2>/dev/null || true && \
	$(MAKE) up && \
	$(MAKE) topics && \
	$(MAKE) generate-limited && \
	echo "Mage AI is a visual pipeline tool." && \
	echo "Open Mage UI at http://localhost:6789 and trigger taxi_pipeline." && \
	END_TIME=$$(date +%s) && \
	ELAPSED=$$((END_TIME - START_TIME)) && \
	echo "" && \
	echo "============================================================" && \
	echo "  BENCHMARK COMPLETE (data generation only)" && \
	echo "  Total elapsed: $${ELAPSED}s" && \
	echo "============================================================" && \
	mkdir -p benchmark_results && \
	echo "{\"pipeline\": \"19-mage-ai\", \"elapsed_seconds\": $$ELAPSED, \"timestamp\": \"$$(date -Iseconds)\"}" > benchmark_results/latest.json && \
	echo "Results saved to benchmark_results/latest.json"

logs: ## View logs
	$(COMPOSE) logs -f

status: ## Show status
	$(COMPOSE) ps
