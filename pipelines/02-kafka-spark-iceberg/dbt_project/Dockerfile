FROM python:3.12-slim

WORKDIR /usr/src/dbt

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

# Install dbt-duckdb and iceberg support
RUN pip install --no-cache-dir \
    dbt-duckdb>=1.8.0 \
    dbt-core>=1.8.0 \
    duckdb>=1.0.0 \
    pyiceberg>=0.6.0 \
    pyarrow>=14.0.0 \
    boto3>=1.34.0

# Default entrypoint (overridden in docker-compose)
ENTRYPOINT ["dbt"]
CMD ["--version"]
