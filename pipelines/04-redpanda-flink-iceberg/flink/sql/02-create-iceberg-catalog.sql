-- =============================================================================
-- Pipeline 04: Flink SQL - Iceberg Catalog
-- =============================================================================
-- Creates a Hadoop-based Iceberg catalog backed by MinIO (S3-compatible).
-- All Bronze and Silver tables will be created within this catalog.
-- =============================================================================

CREATE CATALOG iceberg_catalog WITH (
    'type' = 'iceberg',
    'catalog-type' = 'hadoop',
    'warehouse' = 's3a://warehouse/',
    'io-impl' = 'org.apache.iceberg.aws.s3.S3FileIO',
    's3.endpoint' = 'http://minio:9000',
    's3.access-key-id' = 'minioadmin',
    's3.secret-access-key' = 'minioadmin',
    's3.path-style-access' = 'true'
);
