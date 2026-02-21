# Secrets and Authentication

How to handle credentials safely from local development to production.

---

## Principle: Identity-First, Keys as Last Resort

| Environment | Preferred method | Fallback |
|-------------|-----------------|---------|
| Local dev | `.env` with MinIO creds (no real secrets) | N/A |
| AWS EC2/EKS | IAM Instance Profile / IRSA (no keys) | AWS Secrets Manager |
| GCP GKE | Workload Identity (no keys) | Secret Manager |
| Azure AKS | Managed Identity (no keys) | Azure Key Vault |
| CI/CD | OIDC federation (no long-lived keys) | Short-lived tokens |

**Never** commit real cloud credentials to `.env` or any git-tracked file.

---

## Local Development

For local development with MinIO, the "credentials" are not real secrets:

```ini
# .env (local MinIO — not real credentials)
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
```

These are MinIO's default admin credentials and only work within your local Docker network. They are safe to include in `.env.example` as defaults.

---

## AWS (IAM)

### EC2 Instance Profiles

If Flink runs on EC2, attach an IAM role to the instance. No credentials needed in config:

```xml
<!-- core-site.xml: use instance profile -->
<property>
  <name>fs.s3a.aws.credentials.provider</name>
  <value>com.amazonaws.auth.InstanceProfileCredentialsProvider</value>
</property>
```

The `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` env vars are absent — S3A falls back to the credential chain.

### EKS + IRSA (IAM Roles for Service Accounts)

```bash
# Create OIDC provider for your EKS cluster:
eksctl utils associate-iam-oidc-provider --cluster de-pipeline --approve

# Create IAM role with S3 policy:
eksctl create iamserviceaccount \
  --name de-pipeline-flink \
  --namespace default \
  --cluster de-pipeline \
  --attach-policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess \
  --approve

# In Flink pod spec:
# serviceAccountName: de-pipeline-flink
```

No credentials needed anywhere in code or config.

### AWS Secrets Manager

For Kafka API keys, database passwords, etc.:

```bash
aws secretsmanager create-secret \
  --name de-pipeline/kafka-creds \
  --secret-string '{"api_key":"...","api_secret":"..."}'
```

Inject at runtime via:
- AWS Secrets Manager CSI Driver (Kubernetes)
- `aws secretsmanager get-secret-value` in entrypoint scripts
- Airflow's AWS Secrets Manager backend

---

## GCP (Workload Identity)

### GKE Workload Identity

```bash
# Bind GCP service account to Kubernetes service account:
gcloud iam service-accounts add-iam-policy-binding \
  de-pipeline@PROJECT.iam.gserviceaccount.com \
  --role roles/iam.workloadIdentityUser \
  --member "serviceAccount:PROJECT.svc.id.goog[default/de-pipeline-flink]"

kubectl annotate serviceaccount de-pipeline-flink \
  iam.gke.io/gcp-service-account=de-pipeline@PROJECT.iam.gserviceaccount.com
```

No service account key files needed — Workload Identity provides a token automatically.

### GCP Secret Manager

```bash
gcloud secrets create kafka-api-key --replication-policy=automatic
echo -n "your-api-key" | gcloud secrets versions add kafka-api-key --data-file=-
```

---

## Azure (Managed Identity)

### AKS Workload Identity

```bash
# Create managed identity:
az identity create -n de-pipeline-flink -g my-resource-group

# Assign Storage Blob Data Contributor:
az role assignment create \
  --assignee "$(az identity show -n de-pipeline-flink -g my-resource-group --query principalId -o tsv)" \
  --role "Storage Blob Data Contributor" \
  --scope "/subscriptions/SUB/resourceGroups/RG/providers/Microsoft.Storage/storageAccounts/ACCOUNT"

# In AKS pod spec:
# azure.workload.identity/use: "true"
# serviceAccountName: de-pipeline-flink
```

### Azure Key Vault

```bash
az keyvault secret set \
  --vault-name de-pipeline-kv \
  --name kafka-api-key \
  --value "your-api-key"
```

---

## CI/CD (GitHub Actions, GitLab, etc.)

### GitHub Actions + OIDC (no long-lived keys)

```yaml
# .github/workflows/deploy.yml
permissions:
  id-token: write
  contents: read

jobs:
  deploy:
    steps:
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::ACCOUNT:role/GitHubActionsRole
          aws-region: us-east-1
      # Now AWS CLI + boto3 work without stored keys
```

### GitLab + OIDC

```yaml
# .gitlab-ci.yml
variables:
  AWS_ROLE_ARN: "arn:aws:iam::ACCOUNT:role/GitLabRole"
id_tokens:
  GITLAB_OIDC_TOKEN:
    aud: https://gitlab.com
```

---

## What to Put in `.env` (and what NOT to)

### Safe to commit in `.env.example` (no real secrets)

```ini
BROKER=redpanda
STORAGE=minio
TOPIC=taxi.raw_trips
MAX_EVENTS=10000
MINIO_ROOT_USER=minioadmin       # local MinIO only
MINIO_ROOT_PASSWORD=minioadmin   # local MinIO only
AWS_ACCESS_KEY_ID=minioadmin     # local MinIO only
AWS_SECRET_ACCESS_KEY=minioadmin # local MinIO only
```

### Never commit in any file

```ini
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE         # real AWS key
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG   # real AWS secret
KAFKA_API_KEY=abc123...                         # broker API key
KAFKA_API_SECRET=def456...                      # broker API secret
DATABASE_PASSWORD=prod-password                 # any real password
```

### `.gitignore` for this template

```gitignore
.env
.env.local
*.key
*.pem
*.jks
build/
de_pipeline.duckdb
dbt/target/
```
