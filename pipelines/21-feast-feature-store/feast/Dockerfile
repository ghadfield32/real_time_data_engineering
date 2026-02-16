FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir "feast[redis,duckdb]" pyarrow

COPY feature_store.yaml /app/feast_repo/feature_store.yaml
COPY features.py /app/feast_repo/features.py

CMD ["feast", "-c", "/app/feast_repo", "serve", "--host", "0.0.0.0", "--port", "6566"]
