# Cloud Storage Configuration

How to replace MinIO with AWS S3, Google Cloud Storage, or Azure ADLS Gen2.

---

## Overview

The template uses two storage clients with different endpoint formats:

| Client | Used by | Endpoint format |
|--------|---------|----------------|
| S3A (Hadoop) | Flink | `http://minio:9000` (with `http://`) |
| DuckDB httpfs | dbt | `minio:9000` (NO `http://` prefix) |

This asymmetry is intentional and critical — DuckDB httpfs does not accept a scheme prefix.

---

## Local MinIO (default)

`.env.example` defaults:

```ini
STORAGE=minio
WAREHOUSE=s3a://warehouse/
S3_ENDPOINT=http://minio:9000
S3_USE_SSL=false
S3_PATH_STYLE=true
DUCKDB_S3_ENDPOINT=minio:9000
DUCKDB_S3_USE_SSL=false
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
```

MinIO is started via `infra/storage.minio.yml`. The `mc-init` service creates the `warehouse` bucket.

---

## AWS S3

See `.env.aws.example` for the full template.

### Key changes

```ini
STORAGE=aws_s3
WAREHOUSE=s3a://your-bucket-name/warehouse/
S3_ENDPOINT=               # empty — S3A uses AWS default endpoint
S3_USE_SSL=true
S3_PATH_STYLE=false        # AWS uses virtual-hosted style
DUCKDB_S3_ENDPOINT=        # empty — DuckDB uses native AWS endpoint
DUCKDB_S3_USE_SSL=true
AWS_REGION=us-east-1
# IAM-preferred: no keys needed if running on EC2/EKS with a role
# AWS_ACCESS_KEY_ID=        # leave empty for IAM role
# AWS_SECRET_ACCESS_KEY=    # leave empty for IAM role
```

### Makefile compose for AWS (no storage overlay)

Since `STORAGE=aws_s3`, the `ifeq ($(STORAGE),minio)` block is skipped — no `storage.minio.yml` is included. No MinIO container starts.

### Flink `core-site.xml` for S3

```xml
<configuration>
  <property>
    <name>fs.s3a.aws.credentials.provider</name>
    <!-- Use IAM role (instance profile or IRSA): -->
    <value>com.amazonaws.auth.InstanceProfileCredentialsProvider</value>
    <!-- Or for explicit keys: -->
    <!-- <value>com.amazonaws.auth.EnvironmentVariableCredentialsProvider</value> -->
  </property>
  <property>
    <name>fs.s3a.connection.ssl.enabled</name>
    <value>true</value>
  </property>
  <property>
    <name>fs.s3a.path.style.access</name>
    <value>false</value>  <!-- false for AWS -->
  </property>
  <!-- Remove or leave empty: -->
  <!-- <name>fs.s3a.endpoint</name> -->
</configuration>
```

### DuckDB `profiles.yml` for S3

```yaml
settings:
  s3_endpoint: ""          # empty = real AWS S3
  s3_use_ssl: true
  s3_url_style: "vhost"    # or remove — DuckDB defaults to vhost for real S3
  s3_region: "us-east-1"
  # For IAM role — duckdb uses boto3/credential chain automatically
  # No s3_access_key_id / s3_secret_access_key needed
```

---

## Google Cloud Storage (GCS)

See `.env.gcs.example`.

### GCS requires a different Flink JAR

The `docker/flink.Dockerfile` must include the GCS connector instead of the S3A plugin:

```dockerfile
# Add to flink.Dockerfile:
RUN wget -q "https://storage.googleapis.com/hadoop-lib/gcs/gcs-connector-hadoop3-latest.jar" \
    -O /opt/flink/lib/gcs-connector-hadoop3-latest.jar
```

### Key changes

```ini
STORAGE=gcs
WAREHOUSE=gs://your-bucket/warehouse/
# GCS uses gs:// scheme, not s3a://
```

### Flink `core-site.xml` for GCS

```xml
<configuration>
  <property>
    <name>fs.gs.impl</name>
    <value>com.google.cloud.hadoop.fs.gcs.GoogleHadoopFileSystem</value>
  </property>
  <property>
    <name>fs.AbstractFileSystem.gs.impl</name>
    <value>com.google.cloud.hadoop.fs.gcs.GoogleHadoopFS</value>
  </property>
  <!-- Workload Identity (Kubernetes): -->
  <property>
    <name>google.cloud.auth.type</name>
    <value>APPLICATION_DEFAULT</value>
  </property>
  <!-- Or service account key (not recommended for prod): -->
  <!--
  <property>
    <name>google.cloud.auth.service.account.json.keyfile</name>
    <value>/gcloud/sa-key.json</value>
  </property>
  -->
</configuration>
```

### DuckDB for GCS

DuckDB's httpfs doesn't natively support GCS authentication via ADC. Options:
- Use HMAC keys (GCS interoperability mode): `s3_endpoint=storage.googleapis.com`, `s3_url_style=path`
- Use the BigQuery Storage API via a different connector

---

## Azure ADLS Gen2

See `.env.azure.example`.

### Key changes

```ini
STORAGE=azure
WAREHOUSE=abfs://your-container@your-account.dfs.core.windows.net/warehouse/
# Azure uses abfs:// scheme
```

### Flink `core-site.xml` for Azure

```xml
<configuration>
  <property>
    <name>fs.azure.account.auth.type</name>
    <value>OAuth</value>
  </property>
  <property>
    <name>fs.azure.account.oauth.provider.type</name>
    <value>org.apache.hadoop.fs.azurebfs.oauth2.WorkloadIdentityTokenProvider</value>
  </property>
  <!-- Or managed identity: -->
  <!--
  <property>
    <name>fs.azure.account.oauth.provider.type</name>
    <value>org.apache.hadoop.fs.azurebfs.oauth2.MsiTokenProvider</value>
  </property>
  -->
</configuration>
```

### Flink Dockerfile for Azure

```dockerfile
# Add Azure HDFS connector:
RUN wget -q "https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-azure/3.3.6/hadoop-azure-3.3.6.jar" \
    -O /opt/flink/lib/hadoop-azure-3.3.6.jar
```

---

## Troubleshooting Cloud Storage

| Error | Cause | Fix |
|-------|-------|-----|
| `Access Denied (403)` | Wrong credentials or missing IAM permission | Verify role has `s3:GetObject`, `s3:PutObject`, `s3:ListBucket` on your bucket |
| `The specified bucket does not exist` | Bucket name typo or wrong region | Check `WAREHOUSE` var and region |
| `DuckDB IO Error: ... 403` | `DUCKDB_S3_ENDPOINT` has wrong format | Must be `minio:9000` (local) or empty string (AWS) — no `http://` prefix |
| Flink job fails immediately with S3 error | `core-site.xml` not updated for cloud | Remove MinIO-specific `fs.s3a.endpoint` when using real AWS |
| `NoSuchKey` on Iceberg metadata | Wrong `WAREHOUSE` path | Verify path: must end with `/` and bucket must be writable |
| `ClassNotFoundException: GoogleHadoopFileSystem` | GCS JAR not in Flink image | Add GCS connector to `docker/flink.Dockerfile` |
