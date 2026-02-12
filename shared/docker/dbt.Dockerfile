FROM python:3.12-slim

# Build argument to select the dbt adapter
ARG DBT_ADAPTER=dbt-duckdb
ARG DBT_ADAPTER_VERSION=">=1.8"

WORKDIR /dbt

# Install dbt with the specified adapter
RUN pip install --no-cache-dir \
    "dbt-core>=1.8" \
    "${DBT_ADAPTER}${DBT_ADAPTER_VERSION}" \
    "dbt-utils>=1.1.0" \
    pyarrow \
    pandas

# For dbt-duckdb with Iceberg support
RUN if [ "$DBT_ADAPTER" = "dbt-duckdb" ]; then \
    pip install --no-cache-dir duckdb; \
    fi

# Copy dbt project (mounted or copied at build time)
COPY dbt_project/ /dbt/

# Install dbt packages
RUN dbt deps --profiles-dir . 2>/dev/null || true

ENTRYPOINT ["dbt"]
CMD ["build", "--profiles-dir", "."]
