FROM python:3.12-slim
RUN pip install --no-cache-dir setuptools soda-core-duckdb
WORKDIR /soda
ENTRYPOINT ["soda"]
CMD ["--help"]
