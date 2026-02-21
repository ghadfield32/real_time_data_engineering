# Production Deployment Notes

What changes when you move from local Docker to a production environment.

---

## Summary of Changes

| Component | Local (this template) | Production |
|-----------|----------------------|------------|
| Broker | Redpanda/Kafka in Docker | Confluent Cloud, MSK, Aiven, self-managed cluster |
| Object storage | MinIO | AWS S3, GCS, Azure ADLS Gen2 |
| Iceberg catalog | Hadoop (file-based) | REST catalog (Lakekeeper, Nessie, Polaris) |
| Flink | Docker Compose | Kubernetes (Flink Operator) or Managed Flink (EMR, Kinesis) |
| dbt | `docker compose run` | Orchestrated run (Airflow, Prefect, Dagster, dbt Cloud) |
| Secrets | `.env` file | AWS Secrets Manager, GCP Secret Manager, Vault |
| TLS/Auth | None (internal network) | mTLS, SASL/SCRAM, IAM roles |

---

## 1. Broker

### Replace with external broker

Remove the broker overlay from compose (no `infra/broker.*.yml`). Update `.env`:

```ini
# External managed broker — no in-Docker broker needed
BOOTSTRAP_SERVERS=your-broker.us-east-1.aws.confluent.cloud:9092
```

Update `flink/sql/01_source.sql.tmpl`:

```sql
'properties.bootstrap.servers' = '${BOOTSTRAP_SERVERS}',
'properties.security.protocol' = 'SASL_SSL',
'properties.sasl.mechanism' = 'PLAIN',
'properties.sasl.jaas.config' = 'org.apache.kafka.common.security.plain.PlainLoginModule required username="${KAFKA_API_KEY}" password="${KAFKA_API_SECRET}";',
```

### Topic creation in prod

Don't use `make create-topics` (it uses `rpk` or `kafka-topics.sh` inside Docker). Use your broker's admin API or IaC (Terraform, Confluent Terraform provider, etc.).

---

## 2. Object Storage

See [06_cloud_storage.md](06_cloud_storage.md) for full S3/GCS/Azure configuration.

**Key principle**: Don't use MinIO in prod. Remove `infra/storage.minio.yml` overlay and point `WAREHOUSE`, `S3_ENDPOINT`, credentials at your cloud bucket.

### Flink S3 (AWS)

In `infra/base.yml`, replace MinIO env vars with IAM role via IRSA (Kubernetes) or instance profile:

```yaml
# Remove these (they override IAM role):
# AWS_ACCESS_KEY_ID: ...
# AWS_SECRET_ACCESS_KEY: ...

# Add if needed:
AWS_REGION: us-east-1
```

The Flink S3A plugin (`S3_HADOOP_AWS_JAR`) reads from the EC2 instance metadata automatically when no keys are set.

### DuckDB / dbt (cloud S3)

```yaml
# dbt/profiles.yml — cloud S3
dev:
  settings:
    # For AWS: use IAM role (no keys in env)
    # For GCS: use GOOGLE_APPLICATION_CREDENTIALS=/gcloud/creds.json
    s3_endpoint: ""          # empty = real AWS S3
    s3_use_ssl: true
    s3_region: us-east-1
```

---

## 3. Iceberg Catalog (REST)

Switch to REST catalog for production multi-writer safety.

Start Lakekeeper (already in template as optional profile):

```bash
# Edit .env: CATALOG=rest
make up EXTRA_PROFILES="--profile catalog-rest"
```

Or point at an external Lakekeeper / Nessie / Polaris:

```ini
LAKEKEEPER_URL=https://your-catalog.company.com/catalog
```

Update `00_catalog_rest.sql.tmpl` with your catalog URI.

REST catalog gives you:
- Atomic multi-table commits (critical for streaming)
- Version history and rollback
- Centralized access control
- Cross-engine compatibility (Flink + Spark + Trino reading the same tables)

---

## 4. Flink (Kubernetes)

### Flink Operator

Use the Apache Flink Kubernetes Operator for managed lifecycle:

```yaml
# flink-deployment.yaml (abbreviated)
apiVersion: flink.apache.org/v1beta1
kind: FlinkDeployment
metadata:
  name: de-pipeline
spec:
  image: your-registry/flink:2.0.1-java17-custom  # your flink.Dockerfile
  flinkVersion: v2_0
  flinkConfiguration:
    taskmanager.numberOfTaskSlots: "4"
    state.backend: rocksdb
    state.checkpoints.dir: s3://your-bucket/checkpoints
    classloader.check-leaked-classloader: "false"
  jobManager:
    resource:
      memory: "2048m"
      cpu: 1
  taskManager:
    resource:
      memory: "4096m"
      cpu: 2
  job:
    jarURI: local:///opt/flink/lib/your-job.jar
    entryClass: org.apache.flink.sql.SqlRunner
    args: ["/opt/sql/05_bronze.sql"]
```

### SQL Jobs on Kubernetes

For SQL-only pipelines (no custom JAR), use the Flink SQL Gateway or a custom entrypoint that runs `sql-client.sh`.

```dockerfile
# In your prod flink.Dockerfile, pre-embed your SQL files:
COPY build/sql/ /opt/flink/sql/
```

### Checkpoints and Savepoints

```bash
# Take savepoint before upgrade/maintenance:
flink savepoint <JOB_ID> s3://your-bucket/savepoints/

# Resume from savepoint:
flink run --fromSavepoint s3://your-bucket/savepoints/<SP_ID> ...
```

---

## 5. dbt (Orchestrated)

In production, `dbt build` is not run via `docker compose run`. Use an orchestrator.

### Airflow DAG (example)

```python
from airflow.providers.docker.operators.docker import DockerOperator

dbt_build = DockerOperator(
    task_id='dbt_build',
    image='your-registry/dbt:latest',
    command='sh -c "dbt deps && dbt build --full-refresh"',
    environment={
        'DUCKDB_S3_ENDPOINT': '',        # real S3 → empty endpoint
        'AWS_REGION': 'us-east-1',
        # Credentials from Airflow connections / environment
    },
)
```

### Prefect / Dagster / dbt Cloud

Replace `make dbt-build` with the relevant platform's dbt task. The `dbt/` directory is standalone.

---

## 6. Secrets Management

**Never commit real credentials to `.env`.**

### AWS

```bash
# Use IAM roles (IRSA for EKS, instance profiles for EC2)
# No AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY needed for AWS services

# For cross-account access:
AWS_ROLE_ARN=arn:aws:iam::ACCOUNT:role/DE-Pipeline-Role
```

### Kubernetes Secrets

```bash
kubectl create secret generic de-pipeline-secrets \
  --from-literal=kafka-api-key=... \
  --from-literal=kafka-api-secret=...
```

Reference in Flink Operator deployment as `envFrom: secretRef`.

### Vault (HashiCorp)

```bash
vault kv put secret/de-pipeline \
  kafka_api_key=... \
  s3_access_key=...
```

Use Vault Agent Injector for automatic secret injection into pods.

---

## 7. TLS and Authentication

### Kafka SASL/SSL

Add to `01_source.sql.tmpl`:

```sql
'properties.security.protocol' = 'SASL_SSL',
'properties.sasl.mechanism' = 'PLAIN',
'properties.ssl.truststore.location' = '/etc/ssl/truststore.jks',
```

### MinIO to S3 TLS

In `core-site.xml` for cloud:

```xml
<property>
  <name>fs.s3a.connection.ssl.enabled</name>
  <value>true</value>
</property>
<!-- Remove path-style — AWS doesn't require it -->
<property>
  <name>fs.s3a.path.style.access</name>
  <value>false</value>
</property>
```

---

## 8. Monitoring in Production

See [07_observability.md](07_observability.md) for metrics.

Key production additions:
- **Alerting**: Flink checkpoint failure rate > 0 → PagerDuty
- **Consumer lag SLA**: DLQ messages > 0 → immediate alert
- **Storage**: Set S3 lifecycle policy to expire Bronze after 30 days, Silver after 1 year
- **Cost**: Flink spot instances for TM; on-demand for JM; S3 Intelligent-Tiering for Silver
