FROM python:3.12-slim
RUN pip install --no-cache-dir soda-core-duckdb soda-core-scientific
WORKDIR /soda
ENTRYPOINT ["soda"]
CMD ["--help"]
