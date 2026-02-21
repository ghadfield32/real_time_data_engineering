FROM python:3.12-slim

# Build argument to select the dbt adapter
ARG DBT_ADAPTER=dbt-duckdb
ARG DBT_ADAPTER_VERSION=">=1.8"

WORKDIR /dbt

# Install dbt with the specified adapter
RUN pip install --no-cache-dir \
    "dbt-core>=1.8" \
    "${DBT_ADAPTER}${DBT_ADAPTER_VERSION}" \
    pyarrow \
    pandas

# For dbt-duckdb with Iceberg support
RUN if [ "$DBT_ADAPTER" = "dbt-duckdb" ]; then \
    pip install --no-cache-dir duckdb; \
    fi

# dbt project files are mounted at runtime via volume (../dbt:/dbt in base.yml).
# No COPY needed — the build context is docker/ which does not contain dbt/.

ENTRYPOINT ["dbt"]
CMD ["build", "--profiles-dir", "."]
