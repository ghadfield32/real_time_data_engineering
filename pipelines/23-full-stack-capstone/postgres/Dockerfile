FROM python:3.12-slim

RUN pip install --no-cache-dir pyarrow psycopg2-binary pandas

COPY load_data.py /app/load_data.py

WORKDIR /app

CMD ["python", "load_data.py"]
