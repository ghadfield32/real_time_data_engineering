FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY generator.py .

# Default: parquet file mounted at /data
ENV BROKER_URL=kafka:9092
ENV TOPIC=taxi.raw_trips
ENV MODE=burst
ENV DATA_PATH=/data/yellow_tripdata_2024-01.parquet
ENV MAX_EVENTS=0

ENTRYPOINT ["python", "generator.py"]
