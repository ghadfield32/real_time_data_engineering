# dbt Master - NYC Taxi Analytics
# Makefile wrapping common dbt commands with project-local profiles

SHELL := bash
DBT = uv run dbt
PROFILES = --profiles-dir .
PROJECT_DIR = nyc_taxi_dbt

.PHONY: help setup deps seed build run test docs clean fresh lint shell validate benchmark snapshot

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup: ## Initial project setup (install deps + copy profiles)
	uv sync
	cd $(PROJECT_DIR) && $(DBT) deps $(PROFILES)
	python scripts/setup_project.py

deps: ## Install dbt packages
	cd $(PROJECT_DIR) && $(DBT) deps $(PROFILES)

seed: ## Load seed files
	cd $(PROJECT_DIR) && $(DBT) seed $(PROFILES)

build: ## Full build: seed + run + test (incremental)
	cd $(PROJECT_DIR) && $(DBT) build $(PROFILES)

run: ## Run all models (incremental)
	cd $(PROJECT_DIR) && $(DBT) run $(PROFILES)

test: ## Run all tests (data + unit)
	cd $(PROJECT_DIR) && $(DBT) test $(PROFILES)

test-unit: ## Run only unit tests
	cd $(PROJECT_DIR) && $(DBT) test --select "test_type:unit" $(PROFILES)

test-data: ## Run only data tests
	cd $(PROJECT_DIR) && $(DBT) test --select "test_type:data" $(PROFILES)

docs: ## Generate and serve documentation
	cd $(PROJECT_DIR) && $(DBT) docs generate $(PROFILES) && $(DBT) docs serve $(PROFILES)

docs-gen: ## Generate documentation only (no serve)
	cd $(PROJECT_DIR) && $(DBT) docs generate $(PROFILES)

clean: ## Clean dbt artifacts
	cd $(PROJECT_DIR) && $(DBT) clean $(PROFILES)

fresh: ## Full refresh build (rebuild all tables from scratch)
	cd $(PROJECT_DIR) && $(DBT) build --full-refresh $(PROFILES)

debug: ## Check dbt connection and configuration
	cd $(PROJECT_DIR) && $(DBT) debug $(PROFILES)

lint: ## Lint SQL with SQLFluff
	cd $(PROJECT_DIR) && uv run sqlfluff lint models/ --config ../.sqlfluff

lint-fix: ## Auto-fix SQL lint issues
	cd $(PROJECT_DIR) && uv run sqlfluff fix models/ --config ../.sqlfluff

snapshot: ## Run SCD Type 2 snapshots
	cd $(PROJECT_DIR) && $(DBT) snapshot $(PROFILES)

shell: ## Interactive DuckDB shell connected to dev database
	uv run python scripts/shell.py

validate: ## Run project validation suite
	uv run python scripts/validate.py

benchmark: ## Run performance benchmarks
	uv run python scripts/benchmark.py

# =============================================================================
# Pipeline Comparison Framework
# =============================================================================

# Find pipeline directory by numeric ID (e.g., P=01 → pipelines/01-kafka-flink-iceberg)
PIPELINE_DIR = $(shell ls -d pipelines/$(P)-* 2>/dev/null | head -1)

pipeline-up: ## Start a pipeline (usage: make pipeline-up P=01)
	@if [ -z "$(PIPELINE_DIR)" ]; then echo "Pipeline $(P) not found"; exit 1; fi
	@echo "Starting $(PIPELINE_DIR)..."
	cd $(PIPELINE_DIR) && make up

pipeline-down: ## Stop a pipeline (usage: make pipeline-down P=01)
	@if [ -z "$(PIPELINE_DIR)" ]; then echo "Pipeline $(P) not found"; exit 1; fi
	@echo "Stopping $(PIPELINE_DIR)..."
	cd $(PIPELINE_DIR) && make down

pipeline-logs: ## Tail pipeline logs (usage: make pipeline-logs P=01)
	@if [ -z "$(PIPELINE_DIR)" ]; then echo "Pipeline $(P) not found"; exit 1; fi
	cd $(PIPELINE_DIR) && make logs

pipeline-benchmark: ## Benchmark a pipeline (usage: make pipeline-benchmark P=01)
	@if [ -z "$(PIPELINE_DIR)" ]; then echo "Pipeline $(P) not found"; exit 1; fi
	@echo "Benchmarking $(PIPELINE_DIR)..."
	cd $(PIPELINE_DIR) && make benchmark

benchmark-all: ## Benchmark all pipelines sequentially
	@for p in 00 01 02 03 04 05 06 07 08 09 10 11; do \
		dir=$$(ls -d pipelines/$$p-* 2>/dev/null | head -1); \
		if [ -n "$$dir" ]; then \
			echo "\n=== Benchmarking $$dir ==="; \
			cd $$dir && make benchmark && cd ../..; \
		fi; \
	done

benchmark-core: ## Benchmark Tier 1 pipelines only (00-06)
	@for p in 00 01 02 03 04 05 06; do \
		dir=$$(ls -d pipelines/$$p-* 2>/dev/null | head -1); \
		if [ -n "$$dir" ]; then \
			echo "\n=== Benchmarking $$dir ==="; \
			cd $$dir && make benchmark && cd ../..; \
		fi; \
	done

compare: ## Generate comparison report from all benchmark results
	uv run python shared/benchmarks/report.py

clean-all: ## Stop all pipelines and remove volumes
	@for p in 00 01 02 03 04 05 06 07 08 09 10 11; do \
		dir=$$(ls -d pipelines/$$p-* 2>/dev/null | head -1); \
		if [ -n "$$dir" ]; then \
			echo "Stopping $$dir..."; \
			cd $$dir && make down 2>/dev/null; cd ../..; \
		fi; \
	done
