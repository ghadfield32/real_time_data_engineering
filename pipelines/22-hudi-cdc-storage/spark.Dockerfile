FROM apache/spark:3.3.3

USER root

# Pre-download Apache Hudi, Kafka, Hadoop AWS, and AWS SDK JARs
# Hudi provides CDC-optimized storage with upsert/delete support.
# This avoids runtime Maven/Ivy downloads which are slow and unreliable.
# Using Spark 3.3.3 for better stability (avoids Netty conflicts)
ARG HUDI_VERSION=0.15.0
ARG HADOOP_AWS_VERSION=3.3.4
ARG AWS_SDK_V1_VERSION=1.12.262
ARG SPARK_KAFKA_VERSION=3.3.3
ARG SCALA_VERSION=2.12

# Hudi Spark bundle (includes all Hudi components for Spark 3.3)
RUN wget -q -P /opt/spark/jars/ \
    "https://repo1.maven.org/maven2/org/apache/hudi/hudi-spark3.3-bundle_${SCALA_VERSION}/${HUDI_VERSION}/hudi-spark3.3-bundle_${SCALA_VERSION}-${HUDI_VERSION}.jar" \
    && echo "Hudi Spark bundle downloaded"

# Hadoop AWS (S3A filesystem)
RUN wget -q -P /opt/spark/jars/ \
    "https://repo1.maven.org/maven2/org/apache/hadoop/hadoop-aws/${HADOOP_AWS_VERSION}/hadoop-aws-${HADOOP_AWS_VERSION}.jar" \
    && echo "Hadoop AWS downloaded"

# AWS SDK v1 bundle (needed by hadoop-aws S3AFileSystem)
RUN wget -q -P /opt/spark/jars/ \
    "https://repo1.maven.org/maven2/com/amazonaws/aws-java-sdk-bundle/${AWS_SDK_V1_VERSION}/aws-java-sdk-bundle-${AWS_SDK_V1_VERSION}.jar" \
    && echo "AWS SDK v1 bundle downloaded"

# Spark SQL Kafka connector
RUN wget -q -P /opt/spark/jars/ \
    "https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_${SCALA_VERSION}/${SPARK_KAFKA_VERSION}/spark-sql-kafka-0-10_${SCALA_VERSION}-${SPARK_KAFKA_VERSION}.jar" \
    && echo "Spark SQL Kafka connector downloaded"

# Spark token provider (needed by spark-sql-kafka)
RUN wget -q -P /opt/spark/jars/ \
    "https://repo1.maven.org/maven2/org/apache/spark/spark-token-provider-kafka-0-10_${SCALA_VERSION}/${SPARK_KAFKA_VERSION}/spark-token-provider-kafka-0-10_${SCALA_VERSION}-${SPARK_KAFKA_VERSION}.jar" \
    && echo "Spark token provider downloaded"

# Kafka clients (needed by spark-sql-kafka)
RUN wget -q -P /opt/spark/jars/ \
    "https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.7.1/kafka-clients-3.7.1.jar" \
    && echo "Kafka clients downloaded"

# Commons pool2 (needed by Kafka connector)
RUN wget -q -P /opt/spark/jars/ \
    "https://repo1.maven.org/maven2/org/apache/commons/commons-pool2/2.12.0/commons-pool2-2.12.0.jar" \
    && echo "Commons pool2 downloaded"

# Create .ivy2 cache dir for any remaining package resolution
RUN mkdir -p /home/spark/.ivy2/cache && chown -R spark:spark /home/spark/.ivy2

# Verify key JARs exist
RUN ls -la /opt/spark/jars/hudi-spark*.jar \
           /opt/spark/jars/hadoop-aws-*.jar \
           /opt/spark/jars/spark-sql-kafka-*.jar

USER spark
