# =============================================================================
# Flink Image with Kafka + Iceberg Connectors
# =============================================================================
# Base: Flink 2.0.1 (Java 17)
# Adds: Kafka SQL connector, Iceberg Flink runtime, AWS S3 bundle
# =============================================================================

FROM flink:2.0.1-java17

# Connector versions (Flink 2.0 requires new connector builds)
ARG FLINK_KAFKA_CONNECTOR_VERSION=4.0.1-2.0
ARG ICEBERG_VERSION=1.10.1
ARG FLINK_MAJOR_MINOR=2.0

# Download Kafka SQL connector (fat jar)
RUN wget -q -P /opt/flink/lib/ \
    "https://repo1.maven.org/maven2/org/apache/flink/flink-sql-connector-kafka/${FLINK_KAFKA_CONNECTOR_VERSION}/flink-sql-connector-kafka-${FLINK_KAFKA_CONNECTOR_VERSION}.jar" \
    && echo "Kafka SQL connector downloaded"

# Download Iceberg Flink runtime
RUN wget -q -P /opt/flink/lib/ \
    "https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-flink-runtime-${FLINK_MAJOR_MINOR}/${ICEBERG_VERSION}/iceberg-flink-runtime-${FLINK_MAJOR_MINOR}-${ICEBERG_VERSION}.jar" \
    && echo "Iceberg Flink runtime downloaded"

# Download Iceberg AWS bundle (for S3FileIO with MinIO)
RUN wget -q -P /opt/flink/lib/ \
    "https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-aws-bundle/${ICEBERG_VERSION}/iceberg-aws-bundle-${ICEBERG_VERSION}.jar" \
    && echo "Iceberg AWS bundle downloaded"

# Download Hadoop client (required for Iceberg Hadoop catalog)
ARG HADOOP_VERSION=3.3.6
RUN wget -q -P /opt/flink/lib/ \
    "https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-client-api/${HADOOP_VERSION}/hadoop-client-api-${HADOOP_VERSION}.jar" \
    && wget -q -P /opt/flink/lib/ \
    "https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-client-runtime/${HADOOP_VERSION}/hadoop-client-runtime-${HADOOP_VERSION}.jar" \
    && echo "Hadoop client jars downloaded"

# Download Hadoop AWS module (for S3A filesystem in Iceberg Hadoop catalog)
RUN wget -q -P /opt/flink/lib/ \
    "https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/${HADOOP_VERSION}/hadoop-aws-${HADOOP_VERSION}.jar" \
    && echo "Hadoop AWS jar downloaded"

# Download AWS SDK v1 bundle (required by hadoop-aws)
ARG AWS_SDK_VERSION=1.12.367
RUN wget -q -P /opt/flink/lib/ \
    "https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/${AWS_SDK_VERSION}/aws-java-sdk-bundle-${AWS_SDK_VERSION}.jar" \
    && echo "AWS SDK bundle downloaded"

# Enable S3 filesystem plugin (for Flink checkpoints on S3)
RUN mkdir -p /opt/flink/plugins/s3-fs-hadoop \
    && cp /opt/flink/opt/flink-s3-fs-hadoop-*.jar /opt/flink/plugins/s3-fs-hadoop/ 2>/dev/null || true

# Verify all JARs are present
RUN ls -la /opt/flink/lib/flink-sql-connector-kafka*.jar \
           /opt/flink/lib/iceberg-flink-runtime*.jar \
           /opt/flink/lib/iceberg-aws-bundle*.jar \
           /opt/flink/lib/hadoop-client-*.jar \
           /opt/flink/lib/hadoop-aws-*.jar \
           /opt/flink/lib/aws-java-sdk-bundle-*.jar
