FROM python:3.12-slim
RUN pip install dagster dagster-webserver dagster-postgres dagster-docker
WORKDIR /opt/dagster/app
COPY . .
