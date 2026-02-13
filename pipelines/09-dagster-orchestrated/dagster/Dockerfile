FROM python:3.12-slim
RUN pip install dagster dagster-webserver dagster-postgres dagster-docker
RUN mkdir -p /opt/dagster/home
COPY dagster.yaml /opt/dagster/home/dagster.yaml
WORKDIR /opt/dagster/app
COPY . .
ENV DAGSTER_HOME=/opt/dagster/home
