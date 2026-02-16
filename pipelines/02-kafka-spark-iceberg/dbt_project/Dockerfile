FROM python:3.12-slim

WORKDIR /usr/src/dbt

# Install system dependencies (Java required for dbt-spark)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        openjdk-21-jre-headless \
    && rm -rf /var/lib/apt/lists/*

# Install dbt-spark (reads Iceberg tables via Spark catalog)
# Using pure-sasl instead of sasl for Python 3.12 compatibility
RUN pip install --no-cache-dir \
    dbt-spark>=1.8.0 \
    dbt-core>=1.8.0 \
    pyhive>=0.7.0 \
    thrift>=0.16.0 \
    pure-sasl>=0.6.2 \
    thrift-sasl>=0.4.3

# Default entrypoint (overridden in docker-compose)
ENTRYPOINT ["dbt"]
CMD ["--version"]
