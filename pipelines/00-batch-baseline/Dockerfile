FROM python:3.12-slim

RUN pip install --no-cache-dir dbt-duckdb==1.9.1

WORKDIR /dbt

# Install dbt packages on build (if packages.yml exists)
COPY dbt_project/packages.yml /dbt/packages.yml
COPY dbt_project/dbt_project.yml /dbt/dbt_project.yml
COPY dbt_project/profiles.yml /dbt/profiles.yml
RUN dbt deps --profiles-dir .

# Copy remaining project files
COPY dbt_project/ /dbt/

ENTRYPOINT ["dbt"]
CMD ["build", "--full-refresh", "--profiles-dir", "."]
