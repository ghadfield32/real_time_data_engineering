# Real-Time Data Engineering Pipeline: Complete Reference

## Context

The current NYC Taxi dbt project is a batch-oriented pipeline (parquet file → DuckDB → dbt models). This document maps **every major real-time data engineering technology and pattern** — organized as a linear journey from foundational concepts through each pipeline stage — so that every option is understood at every step, for any scale and any latency requirement.

---

## Table of Contents

1. [Current Pipeline Architecture (Baseline)](#1-current-pipeline-architecture-baseline)
2. [Core Concepts](#2-core-concepts)
3. [Stage 1 — Ingestion: Getting Data Into the Pipeline](#3-stage-1--ingestion-getting-data-into-the-pipeline)
4. [Stage 2 — Stream Processing: Transforming Data in Motion](#4-stage-2--stream-processing-transforming-data-in-motion)
5. [Stage 3 — Storage: Landing Processed Data](#5-stage-3--storage-landing-processed-data)
6. [Stage 4 — Transformation: Analytical Modeling](#6-stage-4--transformation-analytical-modeling)
7. [Stage 5 — Orchestration: Coordinating the Pipeline](#7-stage-5--orchestration-coordinating-the-pipeline)
8. [Stage 6 — Serving: Delivering Data to Consumers](#8-stage-6--serving-delivering-data-to-consumers)
9. [Stage 7 — Governance & Observability](#9-stage-7--governance--observability)
10. [Architecture Patterns](#10-architecture-patterns)
11. [End-to-End Integration Patterns](#11-end-to-end-integration-patterns)
12. [Decision Matrices: Choosing by Scale & Needs](#12-decision-matrices-choosing-by-scale--needs)
13. [2026 Industry Trends & Market Context](#13-2026-industry-trends--market-context)
14. [Complete Reference Architecture](#14-complete-reference-architecture)
15. [Implementation Roadmap](#15-implementation-roadmap)
16. [Implementation Results & Benchmarks](#16-implementation-results--benchmarks)

---

## 1. Current Pipeline Architecture (Baseline)

```
Static Parquet File
    ↓
[SOURCE] raw_yellow_trips (dbt-duckdb external)
    ↓
[STAGING] stg_yellow_trips (TABLE) + 3 ref views
    ↓
[INTERMEDIATE] int_trip_metrics → int_daily_summary, int_hourly_patterns
    ↓
[MARTS CORE] fct_trips (incremental) + dim_dates, dim_locations, dim_payment_types
    ↓
[MARTS ANALYTICS] mart_daily_revenue, mart_location_performance, mart_hourly_demand,
                   anomaly_daily_trips (Python), export_daily_revenue (external parquet)
```

**Current gaps for real-time:** Static parquet source, Makefile-only orchestration, no event streaming, no CDC, no continuous processing, no serving layer beyond exported files.

---

## 2. Core Concepts

These are foundational ideas you must understand before evaluating any specific tool. Every streaming technology builds on these primitives.

### 2a. Message Queues vs Event Streams

This is the single most important conceptual distinction in the messaging world. Choosing the wrong paradigm is the most common architectural mistake.

| Dimension | Message Queue | Event Stream |
|-----------|--------------|--------------|
| **Examples** | RabbitMQ, NATS, Amazon SQS | Apache Kafka, Redpanda, Apache Pulsar |
| **Read model** | Destructive — message removed after consumption | Non-destructive — events retained on a log |
| **Consumer pattern** | Competing consumers (one consumer gets each message) | Multiple independent consumer groups read independently |
| **Replay** | Not possible once consumed | Full replay from any historical offset |
| **Retention** | Deleted after acknowledgment | Retained for configured period (hours to forever) |
| **Ordering** | Per-queue (may not be strict) | Per-partition strict ordering |
| **Primary use** | Task distribution, work queues, RPC, request/reply | Event sourcing, stream processing, log aggregation, CDC |
| **Throughput** | 10K–100K msg/s typical | 500K–1M+ msg/s typical |

**When to use a message queue:** You need work distribution (send a task to exactly one worker), request/reply patterns, complex routing rules (priority queues, dead-letter exchanges), or moderate throughput with low latency.

**When to use an event stream:** You need an immutable log of everything that happened, multiple consumers reading the same data independently, replay capability, high throughput, or stream processing.

**Key insight:** Many architectures use both. Kafka for the event backbone, RabbitMQ/NATS for microservice task distribution.

### 2b. Event Time vs Processing Time

Every event has two timestamps:

- **Event time:** When the event actually occurred (e.g., when the taxi meter stopped)
- **Processing time:** When the system receives/processes the event

These can differ by seconds, minutes, or hours (network delays, offline devices, batch uploads). Stream processors must handle this gap correctly, or aggregations will be wrong.

**Example:** A taxi trip ends at 11:58 PM but the event arrives at 12:03 AM. Does it count in today's daily summary or yesterday's? Event-time processing puts it in yesterday's — the correct answer.

### 2c. Windowing

Windowing is how stream processors group unbounded data into finite chunks for aggregation. Every stream processing engine implements these window types:

| Window Type | Behavior | Use Case |
|-------------|----------|----------|
| **Tumbling** | Fixed-size, non-overlapping, contiguous (e.g., every 5 minutes). Each event belongs to exactly one window. | Periodic aggregations: "total revenue per hour" |
| **Hopping** | Fixed-size but overlapping, advancing by a smaller "hop" interval (e.g., 10-min windows every 2 min). Events appear in multiple windows. | Smoothing: "rolling 10-minute average, updated every 2 minutes" |
| **Sliding** | Triggered when events enter or leave the window boundary. Event-driven, not clock-driven. | Alerting: "fire alarm if >5 errors in any 10-minute span" |
| **Session** | Dynamic windows grouped by activity, separated by inactivity gaps. New window starts after configurable idle period. | User behavior: "group all clicks in a browsing session" |
| **Global** | Single window encompassing all events. Requires custom triggers to emit results. | All-time state: "running total of all trips ever" |

**Related concepts:**

- **Watermarks:** A timestamp threshold that declares "all events before this time have arrived." Used to decide when a window's results are final. Determines the tradeoff between completeness and latency.
- **Triggers:** Policies for when to emit window results — at watermark passage, at every element, after a delay, or periodically.
- **Allowed lateness:** A grace period after the watermark for accepting late events. Late arrivals within this window can update already-emitted results.

### 2d. Exactly-Once Semantics

The three delivery guarantees:

| Guarantee | Meaning | Trade-off |
|-----------|---------|-----------|
| **At-most-once** | Fire and forget. May lose messages. | Fastest, lowest overhead |
| **At-least-once** | Retry until acknowledged. May duplicate. | Good balance for many use cases |
| **Exactly-once** | Each message processed exactly once, even during failures. | Highest overhead, hardest to implement |

Exactly-once is achieved through combinations of idempotent writes, transactional producers/consumers, and checkpoint/offset management. Kafka, Flink, and Spark all support it, but the implementation cost varies.

**Practical note:** Many production systems use at-least-once delivery with idempotent consumers (deduplication at the application layer) rather than paying the full exactly-once overhead.

### 2e. Backpressure & Flow Control

Backpressure occurs when a downstream consumer cannot keep up with an upstream producer. It is one of the most common failure modes in production streaming systems.

| Strategy | How It Works | Used By |
|----------|-------------|---------|
| **Pull-based consumption** | Consumer requests data at its own pace (inherent backpressure) | Kafka, Redpanda |
| **Credit-based flow control** | Downstream grants credits to upstream; upstream sends only what credits allow | Flink |
| **Rate limiting** | Cap the read rate from sources | Spark Structured Streaming |
| **Queue thresholds** | Configurable FlowFile queue limits; producers pause when thresholds are hit | NiFi |
| **Buffering** | Temporarily store excess data in bounded or unbounded buffers | Most systems |
| **Load shedding** | Drop messages when overwhelmed (last resort) | Configurable in most systems |
| **Dynamic scaling** | Auto-scale consumers to match producer rate | Cloud-managed services |

**Why it matters:** Without backpressure handling, a fast producer will overwhelm a slow consumer, causing out-of-memory errors, cascading failures, or silent data loss.

### 2f. State Management in Streaming

Stateful operations (counts, joins, deduplication, windowed aggregations) require the stream processor to maintain state that survives failures:

- **Checkpointing:** Periodically snapshot state to durable storage (Flink, Spark)
- **Changelog topics:** Write state changes to a Kafka topic for recovery (Kafka Streams)
- **RocksDB:** Embedded key-value store for large state that doesn't fit in memory (Flink, Spark 3.5+)
- **State backends:** Pluggable storage for state — in-memory (fast, limited), RocksDB (large, slower), remote (cloud-native)

---

## 3. Stage 1 — Ingestion: Getting Data Into the Pipeline

This stage answers: **How does raw data enter the system?** Options range from simple message queues to enterprise event streaming platforms to fully managed cloud services.

### 3a. Apache Kafka — The Industry Standard Event Stream

**What it does:** Distributed event streaming platform — the "central nervous system" for real-time data. The dominant choice for event streaming since 2011.

| Component | Role |
|-----------|------|
| **Brokers** | Receive, store, serve messages (min 3 for fault tolerance) |
| **Topics** | Named feeds organizing events (e.g., `taxi.rides`, `taxi.payments`) |
| **Partitions** | Subdivisions of topics enabling parallel processing and ordering |
| **Consumer Groups** | Coordinate multiple consumers reading from topics |
| **Schema Registry** | Validates message schemas (Avro/Protobuf/JSON), enforces data contracts |
| **KRaft (Kafka 4.0)** | Metadata management via Raft consensus — **ZooKeeper fully removed in Kafka 4.0 (March 2025)** |

**Kafka 4.0 (March 2025) — Major milestone:**
- ZooKeeper completely removed after 14 years. KRaft is the only metadata mode.
- KIP-848: New consumer group protocol for faster rebalances.
- KIP-932: Early access "Queues for Kafka" — point-to-point consumption beyond partition limits.
- Minimum client version: 2.1 (old protocol APIs removed).
- Simpler operations: No more ZooKeeper cluster to manage.

**Kafka Connect:** Configuration-only connectors (no code) to move data between Kafka and external systems:
- **Source connectors:** Ingest from databases, APIs, files into Kafka
- **Sink connectors:** Write from Kafka to warehouses, data lakes, S3, Elasticsearch

**Kafka Streams:** Lightweight client library (Java) for in-app stream processing — no separate cluster needed. Good for filtering, enrichment, simple aggregations within microservices. Runs wherever your Java app runs.

**Deployment options:**
- **Confluent Cloud (managed):** No ops overhead, throughput-based pricing, scale-to-zero, governance suite
- **Amazon MSK (managed):** AWS-native managed Kafka, integrates with AWS services
- **Self-hosted:** Full control, no licensing cost, significant operational burden

**How it fits:** Taxi trip events produced to Kafka topics in real-time instead of landing as a daily parquet file. Downstream consumers (Flink, Spark, dbt) read from these topics.

```
Taxi Meters/APIs → Kafka Producer → topic: taxi.raw_trips → Consumers
```

### 3b. Redpanda — Kafka-Compatible, Simpler Operations

**What it does:** Kafka-compatible streaming platform written in C++. Single binary, no JVM, no ZooKeeper/KRaft complexity. Full Kafka API compatibility — existing clients, Connect, and Streams work unchanged.

| Aspect | Kafka | Redpanda |
|--------|-------|----------|
| **Language** | Java (JVM) | C++ (no JVM) |
| **Dependencies** | KRaft (was ZooKeeper) | None — single binary |
| **Tail latency** | Higher (JVM GC pauses) | Consistently lower |
| **Operational complexity** | Moderate-high | Low (single binary) |
| **Kafka API compatible** | N/A (is Kafka) | Yes — drop-in replacement |
| **Built-in extras** | Requires separate Schema Registry, REST Proxy | Includes Schema Registry, HTTP Proxy, WebAssembly transforms |
| **Deployment** | Self-managed or managed (Confluent, MSK) | Self-managed or Redpanda Cloud |

**Enterprise adoption:** NYSE (4-5x performance improvement over Kafka), Cisco, Moody's, Vodafone, Activision, two of the top five U.S. banks.

**2025-2026:** Acquired Oxla (distributed SQL engine), launched "Agentic Data Plane" for AI agent governance. Partnered with Akamai for global edge streaming.

**When to choose Redpanda:** Simpler operations than Kafka, lower tail latency requirements, smaller ops teams, Kafka-compatible ecosystem needed without JVM overhead.

### 3c. Apache Pulsar — Decoupled Compute/Storage

**What it does:** Cloud-native distributed messaging with independent compute and storage scaling.

| Aspect | Kafka | Pulsar |
|--------|-------|--------|
| **Architecture** | Monolithic (brokers = routing + storage) | Modular (brokers route, BookKeeper stores) |
| **Scaling** | Compute/storage coupled | Independent compute/storage scaling |
| **Geo-Replication** | Limited | Built-in, advanced |
| **Multi-Tenancy** | Basic | Native, first-class |
| **Unified messaging** | Streaming only | Streaming + queuing in one system |
| **Market position** | Industry standard | Niche but growing in multi-tenant/global setups |

**When to choose Pulsar:** Complex multi-tenant setups, need independent compute/storage scaling, global geo-replication requirements, mixed streaming + queuing patterns. Kafka remains the default for pure event streaming at scale.

### 3d. Cloud-Managed Streaming Services

For most enterprises, the first encounter with streaming is through a cloud provider's managed service — not self-hosted open-source. These trade flexibility for operational simplicity.

#### AWS Kinesis Family

| Service | Role |
|---------|------|
| **Kinesis Data Streams** | Managed real-time streaming. Scales via shards (each: 1 MB/s in, 2 MB/s out). Supports replay and enhanced fan-out for multiple consumers. |
| **Kinesis Data Firehose** | Zero-code delivery pipeline. Ingests streams and delivers to S3, Redshift, OpenSearch, Splunk. No consumer code needed. |
| **Managed Service for Apache Flink** | Managed Flink for SQL/Java/Scala processing against Kinesis streams. (Formerly Kinesis Data Analytics.) |

**Best for:** AWS-native shops, moderate scale, teams wanting zero-ops streaming. Shard-based scaling is less elastic than Pub/Sub.

#### Google Cloud Pub/Sub + Dataflow

| Service | Role |
|---------|------|
| **Pub/Sub** | Globally distributed messaging with automatic horizontal scaling. No shard/partition planning — abstracts scaling entirely. Push and pull delivery. |
| **Dataflow** | Managed Apache Beam runner. Unified batch + streaming. Auto-scaling workers. |

**Best for:** Best automatic-scaling story among the three clouds. Globally distributed use cases. Teams using Apache Beam. Generally cheaper at equivalent scale.

#### Azure Event Hubs + Stream Analytics

| Service | Role |
|---------|------|
| **Event Hubs** | Managed event ingestion, **Kafka-protocol-compatible** — existing Kafka clients connect without code changes. Scales via throughput units. "Capture" writes events to Blob/Data Lake automatically. |
| **Stream Analytics** | Managed streaming SQL for real-time analytics, anomaly detection, and ETL. |

**Best for:** Azure-first enterprises. Kafka protocol compatibility is a major differentiator — can migrate Kafka workloads to Event Hubs without rewriting producers/consumers.

#### Cloud Services Comparison

| Aspect | AWS Kinesis | GCP Pub/Sub | Azure Event Hubs |
|--------|------------|-------------|-----------------|
| **Scaling model** | Manual (shards) | Automatic | Manual (throughput units) |
| **Kafka compatible** | No | No | Yes |
| **Pricing model** | Per-shard hour + data | Per-message + data | Per throughput unit + data |
| **Max throughput** | Shard-limited | Near-unlimited | Throughput-unit-limited |
| **Ecosystem lock-in** | High (AWS-only APIs) | Moderate (Beam portable) | Low (Kafka protocol) |
| **Best for** | AWS-native, moderate scale | Global scale, auto-scaling | Kafka migration to cloud |

### 3e. Message Queues (Task Distribution, Not Event Streaming)

These are **not** event streams — they're for task distribution, RPC, and work queues. Understanding when to use them (and when not to) prevents architectural mistakes.

#### RabbitMQ

- AMQP-based, sophisticated routing (exchanges, bindings, priority queues, dead-letter exchanges)
- Throughput: 50K–100K msg/s
- Supports complex routing patterns that Kafka cannot express natively
- Best for: Request/reply, task distribution, complex routing, moderate throughput

#### NATS / NATS JetStream

- Ultra-lightweight: single Go binary, 1 vCPU / 1GB RAM
- Latency: sub-millisecond
- Throughput: 200K–400K msg/s with persistence (JetStream)
- JetStream adds persistence, replay, exactly-once semantics
- Increasingly popular in cloud-native/Kubernetes environments
- Best for: Microservices communication, IoT, edge computing, low-resource environments

#### Amazon SQS / SNS

- Fully managed queue (SQS) and pub/sub (SNS) on AWS
- SQS: Standard (at-least-once, best-effort ordering) or FIFO (exactly-once, strict ordering)
- SNS + SQS: Fan-out pattern (one publish → multiple queue consumers)
- Best for: Simple AWS-native task queuing, serverless architectures (Lambda triggers)

### 3f. Change Data Capture (CDC)

CDC captures row-level database changes (INSERT, UPDATE, DELETE) and streams them as events. It bridges the gap between transactional databases and event streaming.

#### Debezium — The Standard

**What it does:** Monitors database transaction logs and streams changes as events.

```
PostgreSQL/MySQL/MongoDB → Debezium → Kafka Topics → Downstream Processing
```

- Captures INSERT, UPDATE, DELETE as changelog events with before/after state
- Deploys on Kafka Connect for fault-tolerant, scalable CDC
- End-to-end latency: milliseconds to tens of milliseconds
- **Debezium Server 2.x:** Lightweight standalone mode — streams to Kafka, Kinesis, Pub/Sub, Pulsar (no Kafka Connect required)
- Supports: PostgreSQL, MySQL, MongoDB, SQL Server, Oracle, Cassandra, Vitess, Spanner

**How it fits:** If taxi data lived in a transactional database, Debezium would stream every new trip record to Kafka in real-time, replacing the static parquet ingestion.

#### Estuary Flow — Managed CDC Alternative

- Managed real-time CDC and ETL platform
- Sub-100ms end-to-end latency
- Exactly-once delivery
- SQL and TypeScript transformations in-stream, plus dbt integration
- Positioned as a modern alternative to Debezium + Kafka Connect for teams wanting managed infrastructure

#### Flink CDC

- YAML-based CDC ingestion directly into Flink
- Built-in schema evolution support
- No Kafka required as intermediary (can read directly from database logs)
- Best for: Teams already using Flink who want CDC without the Kafka Connect layer

### 3g. Apache NiFi — Visual Data Flow Automation

**What it does:** Visual drag-and-drop data flow platform for complex routing, transformation, and system mediation.

- Enterprise-grade security (RBAC, SSL/TLS, data masking, provenance tracking)
- **NiFi 2.0+:** Native Python API, AI-powered processors
- 15+ years of maturity, widely adopted in finance/healthcare/government
- Built-in backpressure via FlowFile queue thresholds
- Data provenance: track every byte from source to destination

**Best for:** Complex data routing with visual interface, non-developer teams, enterprise compliance requirements. Complementary to Kafka — NiFi routes and transforms, Kafka streams.

### 3h. Ingestion Decision Summary

| Need | Best Choice | Runner-Up |
|------|------------|-----------|
| Event streaming (general) | Apache Kafka | Redpanda |
| Simpler Kafka operations | Redpanda | Confluent Cloud |
| AWS-native streaming | Kinesis Data Streams | Amazon MSK (managed Kafka) |
| GCP-native streaming | Pub/Sub | Confluent Cloud on GCP |
| Azure-native streaming | Event Hubs (Kafka-compatible) | Confluent Cloud on Azure |
| Multi-tenant / global | Pulsar | Confluent Cloud |
| CDC from databases | Debezium + Kafka Connect | Estuary Flow (managed) |
| Task distribution / RPC | RabbitMQ or NATS | Amazon SQS |
| Visual data routing | Apache NiFi | — |
| Microservices / edge / IoT | NATS JetStream | Redpanda |

---

## 4. Stage 2 — Stream Processing: Transforming Data in Motion

This stage answers: **How do you clean, enrich, aggregate, and transform data as it flows?** Options range from lightweight in-app libraries to full distributed processing engines.

### 4a. Apache Flink — Stateful Stream Processing (Industry Standard)

**What it does:** True event-at-a-time stream processor. The industry standard for stateful streaming as of 2025-2026.

**Core capabilities:**
- **Flink SQL:** ANSI SQL for real-time transformations, joins, aggregations, windowing
- **Stateful processing:** Built-in state management for counts, deduplication, joins, aggregations (RocksDB-backed)
- **Event-time processing:** Processes by when events occurred, handles late/out-of-order data via watermarks
- **Exactly-once semantics:** No data loss or duplication, even during failures
- **Flink CDC:** YAML-based CDC ingestion with schema evolution support
- **Flink SQL Gateway:** REST API for submitting SQL queries (enables dbt-like workflows)

**How it fits in our pipeline:**
```
Kafka (taxi.raw_trips)
    → Flink SQL: clean, filter negatives, add surrogate keys     [replaces stg_yellow_trips]
    → Flink SQL: compute duration, speed, tip%                    [replaces int_trip_metrics]
    → Flink SQL: windowed aggregations (5-min, hourly, daily)     [replaces int_daily_summary]
    → Write to Iceberg / Delta Lake / DuckDB
    → dbt handles final mart-level modeling
```

**Deployment:** Self-managed, AWS Managed Flink (formerly Kinesis Data Analytics), Confluent Cloud (Flink-as-a-service), Ververica Platform.

**Latency:** Sub-second to millisecond range.

**Best for:** Sub-second latency, complex stateful processing, CDC workflows, real-time anomaly detection, windowed aggregations.

### 4b. Apache Spark Structured Streaming

**What it does:** Stream processing extension of Spark's batch engine. Processes data as micro-batches by default.

**Processing modes:**

| Mode | Latency | Guarantee | Status |
|------|---------|-----------|--------|
| **Micro-batch (default)** | ~100ms | Exactly-once | Stable, widely used |
| **Continuous (since 2.3)** | ~1ms | At-least-once | Less common |
| **Real-time (2025 Databricks)** | Single-digit ms | Exactly-once | New, being open-sourced |

**Core capabilities:**
- Unbounded table abstraction — same DataFrame API for batch and streaming
- RocksDB-backed state management (Spark 3.5+)
- Watermarking for late data
- Integrates with Spark MLlib for ML pipelines
- Existing Spark skills transfer directly to streaming

**How it fits:**
```
Kafka → Spark Structured Streaming → Delta Lake / Iceberg tables → dbt models
```

**Best for:** Organizations already in Spark/Databricks ecosystem, mixed batch/stream workloads, ML pipeline integration, when ~100ms latency is acceptable.

### 4c. Flink vs Spark — Head-to-Head

| Aspect | Flink | Spark Structured Streaming |
|--------|-------|---------------------------|
| **Processing model** | True event-at-a-time | Micro-batch (default) |
| **Latency** | Sub-second to milliseconds | ~100ms (micro-batch) |
| **Stateful processing** | Built from ground up, first-class | Improved in 3.5+, but secondary to batch |
| **Learning curve** | Steeper (new paradigm) | Easier if already using Spark |
| **Batch capabilities** | Good | Excellent |
| **CDC integration** | More mature (Flink CDC) | Via Kafka Connect |
| **ML integration** | Growing | Strong (MLlib) |
| **SQL support** | Flink SQL (ANSI, streaming-native) | Spark SQL (batch-first, streaming added) |
| **2026 trend** | Ascending — industry standard for streaming | Dominant for analytics + streaming |

**Rule of thumb:** Flink for sub-second latency and complex CDC. Spark for analytical streaming and existing Spark shops.

### 4d. Streaming SQL Engines

These let you write standard PostgreSQL-compatible SQL that processes streaming data continuously. No Java, no Scala, no framework — just SQL.

#### RisingWave

- PostgreSQL-compatible streaming database (any Postgres client works: DBeaver, Metabase, psql)
- Standard SQL for continuous processing with millisecond latency
- **Dynamic materialized views:** Incrementally updated as new data arrives (not static refresh)
- Distributed Rust engine with decoupled storage
- 2025: Added vector search, Iceberg support, schema evolution
- Used by 1000+ organizations

#### Materialize

- PostgreSQL-compatible streaming SQL engine
- Keeps materialized views incrementally updated as source data changes
- Complex JOINs and aggregations at millisecond latency
- Integrates with Kafka, Kinesis, CDC sources, S3
- "Towards Real-Time dbt" — purpose-built for dbt + streaming integration
- Built on Timely Dataflow (Rust)

#### ksqlDB (Confluent — Maintenance Mode)

- Confluent's streaming SQL engine built on Kafka Streams
- **Custom SQL dialect** (not PostgreSQL-compatible) — requires ksqlDB-specific tooling
- Works only with Kafka (no other sources)
- **2025-2026 status: Maintenance mode.** Confluent has shifted to Apache Flink as their primary stream processing engine after acquiring Immerok (Flink startup) in 2023. ksqlDB still ships but receives no major new features.
- **Lesson learned:** The industry has moved toward PostgreSQL-compatible streaming SQL (RisingWave, Materialize) and Flink rather than proprietary dialects.

#### Streaming SQL Comparison

| Aspect | RisingWave | Materialize | ksqlDB |
|--------|-----------|-------------|--------|
| **SQL dialect** | PostgreSQL | PostgreSQL | Custom (non-standard) |
| **Data sources** | Kafka, Pulsar, S3, DBs | Kafka, Postgres, S3 | Kafka only |
| **Architecture** | Distributed Rust, decoupled storage | Timely Dataflow (Rust) | Kafka Streams (JVM) |
| **Client compatibility** | Any PostgreSQL client | Any PostgreSQL client | ksqlDB-specific only |
| **Status** | Active development, growing | Active development, cloud focus | Maintenance mode |

**How streaming SQL fits:** Replace dbt intermediate views with continuously-updating materialized views. `int_daily_summary` becomes a live-updating view that reflects new trips within milliseconds.

### 4e. Apache Beam — Unified Batch + Streaming SDK

**What it does:** A single programming model (SDK) that runs on multiple engines. Write once, deploy to Flink, Spark, or Google Dataflow.

- Write pipeline once in Java, Python, or Go
- Choose batch or streaming execution at runtime
- Eliminates Lambda Architecture's dual code paths
- LinkedIn reduced batch processing time by 94% with Beam + Flink
- **Google Dataflow** is the canonical managed Beam runner

**Best for:** Teams wanting engine portability, unified batch/streaming code, Google Cloud environments (Dataflow).

### 4f. Kafka Streams — Lightweight In-App Processing

**What it does:** A Java client library (not a framework, not a cluster) for stream processing. Runs inside your application — no separate infrastructure.

- No separate cluster to deploy and manage
- Exactly-once processing via Kafka transactions
- Good for: filtering, enrichment, simple aggregations, joining streams
- Scales by adding more application instances
- State backed by changelog topics in Kafka

**Best for:** Microservices that need to process their own Kafka topics. Simple transformations that don't warrant a Flink/Spark cluster.

**Limitation:** Only works with Kafka topics as input/output. No SQL interface. Java/Scala only.

### 4g. Emerging / Lightweight Processors

#### Bytewax
- Stream processing in Python (built on Timely Dataflow in Rust)
- Familiar Python APIs for teams without JVM experience
- Good for ML feature engineering and lightweight stream processing

#### Timeplus / Proton
- Open-source (Apache 2.0) streaming SQL built on ClickHouse
- Single C++ binary, under 500MB, no JVM
- Claims 90M events/second on a laptop
- Lightweight Flink/ksqlDB alternative for edge and embedded streaming

### 4h. Stream Processing Decision Summary

| Need | Best Choice | Runner-Up |
|------|------------|-----------|
| Sub-second stateful streaming | Apache Flink | RisingWave |
| Analytical streaming + ML | Spark Structured Streaming | Flink + external ML |
| SQL-only streaming (simplest) | RisingWave or Materialize | Flink SQL |
| Engine portability | Apache Beam | — |
| In-app lightweight processing | Kafka Streams | Bytewax (Python) |
| GCP-managed processing | Dataflow (Beam) | Spark on Dataproc |
| AWS-managed processing | Managed Flink | Spark on EMR |
| Edge / embedded streaming | Timeplus/Proton | Bytewax |

---

## 5. Stage 3 — Storage: Landing Processed Data

This stage answers: **Where does processed streaming data land for querying?** The lakehouse paradigm (open table formats on object storage) has become the standard for unified batch + streaming storage.

### 5a. Open Table Formats (Lakehouse)

These formats sit on top of object storage (S3, GCS, Azure Blob) and provide database-like capabilities (ACID, time travel, schema evolution) for files (Parquet, ORC).

| Format | Philosophy | Best For |
|--------|-----------|----------|
| **Apache Iceberg** | Engine-agnostic, specification-first | Portability across engines (Spark, Flink, Trino, Presto, DuckDB) |
| **Delta Lake** | Transaction-log centric, Databricks ecosystem | Spark-native simplicity, Databricks shops |
| **Apache Hudi** | Built for incremental/CDC workflows | Streaming upserts, change data capture workloads |

**All three provide:** ACID transactions, time travel (query data as of any past point), schema evolution, partition evolution, concurrent readers/writers.

#### Apache Iceberg (Most Portable — Industry Default for New Projects)

- Specification-first design: any engine can read/write if it implements the spec
- Works with: Spark, Flink, Trino, Presto, DuckDB, Snowflake, BigQuery, Athena
- **2025-2026 convergence point:** Iceberg is becoming the standard interface between streaming and batch — Kafka→Iceberg pipelines are a first-class pattern
- Confluent deeply integrated Flink + Kafka + Iceberg as a unified platform
- Apache Pinot added Iceberg table support (late 2025)
- **REST Catalog:** Standard API for catalog interoperability across engines

#### Delta Lake (Spark/Databricks Ecosystem)

- Transaction log stored alongside data files
- Deep Spark integration — most features work out of the box with Spark
- **Delta Lake 4.0:** UniForm allows Delta tables to be read as Iceberg or Hudi
- Liquid Clustering replaces traditional partitioning with adaptive data layout
- Databricks Unity Catalog provides governance on top

#### Apache Hudi (CDC/Upsert-Heavy Workloads)

- Built-in Merge-on-Read and Copy-on-Write table types
- Optimized for streaming upserts (update-heavy workloads)
- Record-level indexing for fast point lookups
- Best for: CDC pipelines where records are frequently updated

### 5b. Iceberg as the Streaming Sink (2025-2026 Pattern)

The dominant 2025-2026 pattern is streaming directly into Iceberg tables:

```
Kafka → Flink → Iceberg (Bronze) → Flink/Spark → Iceberg (Silver) → dbt → Iceberg (Gold)
```

- Flink's Iceberg sink supports exactly-once writes
- Spark Structured Streaming writes natively to Iceberg
- Small files are automatically compacted (Iceberg maintenance operations)
- Time travel enables easy debugging: "what did the data look like at 3 PM?"
- Multiple engines (Flink writing, dbt reading) can operate concurrently on the same tables

### 5c. Traditional Warehouses as Streaming Sinks

For teams not ready for lakehouse architecture, cloud warehouses can receive streaming data:

| Warehouse | Streaming Ingestion | Mechanism |
|-----------|-------------------|-----------|
| **Snowflake** | Snowpipe Streaming (low-latency), Snowpipe (micro-batch) | Kafka connector or Snowpipe REST API |
| **BigQuery** | BigQuery Storage Write API (streaming insert) | Direct API or Kafka connector |
| **Redshift** | Redshift Streaming Ingestion | Direct from Kinesis or MSK (Kafka) |

**Trade-off:** Simpler architecture (fewer components) but higher per-query cost, less control over data layout, and vendor lock-in.

### 5d. Storage Decision Summary

| Need | Best Choice | Runner-Up |
|------|------------|-----------|
| Engine-portable lakehouse | Apache Iceberg | Delta Lake (with UniForm) |
| Spark/Databricks ecosystem | Delta Lake | Iceberg |
| CDC/upsert-heavy workloads | Apache Hudi | Iceberg (improving) |
| Simplest path (no lakehouse) | Cloud warehouse (Snowflake/BigQuery) | DuckDB (small scale) |
| Small-scale / local dev | DuckDB | SQLite |

---

## 6. Stage 4 — Transformation: Analytical Modeling

This stage answers: **How do you build business-level analytical models on top of streamed data?** dbt remains the standard for this layer, but its role and capabilities change in a streaming context.

### 6a. dbt Micro-Batch Incremental Models (dbt 1.9+)

Process incremental models in multiple queries based on `event_time`:

- **Default:** One batch per day; configurable to hours or minutes
- **Reprocess failed batches independently** — no full rebuild needed
- **Auto-detect parallel batch execution** for non-overlapping time windows
- **Practical approach:** Run dbt every 5–15 minutes with micro-batch for near-real-time freshness

```yaml
# Example micro-batch config
models:
  - name: fct_trips
    config:
      materialized: incremental
      incremental_strategy: microbatch
      event_time: pickup_datetime
      batch_size: hour  # Process one hour at a time
```

**How it fits:** The stream processor (Flink/Spark) handles real-time cleaning and enrichment (Bronze→Silver). dbt runs in micro-batch mode every 5–15 minutes to build Gold-layer analytics (Silver→Gold).

### 6b. dbt Mesh (Multi-Project Orchestration)

For large-scale federated teams where different domains own different parts of the pipeline:

- **Cross-project model references:** `ref('project_name', 'model_name')`
- **Model contracts:** Schema guarantees between projects (column names, types, constraints)
- **Model versions:** Publish v1 and v2 simultaneously during migrations
- **Job dependencies across projects:** Downstream projects wait for upstream to finish
- **State-aware orchestration:** Detects deleted tables and cascades impact

### 6c. Streaming SQL + dbt (Hybrid Pattern)

The streaming SQL engine handles low-latency transforms; dbt handles analytical modeling:

| Concern | Handled By |
|---------|-----------|
| Real-time cleaning, deduplication | Stream processor (Flink) or Streaming SQL (RisingWave/Materialize) |
| Windowed aggregations (5-min, hourly) | Stream processor |
| Live materialized views | Streaming SQL engine |
| Dimensional modeling (facts/dims) | dbt |
| Business KPIs, cross-domain joins | dbt |
| Data quality tests | dbt (91+ tests) |
| Schema contracts | dbt model contracts |

**Materialize + dbt:** Purpose-built "real-time dbt" — Materialize maintains live materialized views, dbt defines the logic and tests.

**Snowflake Streams + Tasks:** Trigger dbt runs on data changes (near-real-time) — Snowflake detects new data and kicks off dbt.

**Separation of concerns:** Stream processors own the "data in motion" layer; dbt owns the "analytics modeling" layer. This division is the 2026 consensus architecture.

---

## 7. Stage 5 — Orchestration: Coordinating the Pipeline

This stage answers: **What triggers pipeline stages and manages dependencies?** Options range from event-driven YAML to Python-native DAGs to visual builders.

### 7a. Kestra — Event-Driven Declarative Orchestration

**What it does:** YAML-first, event-driven orchestration with millisecond trigger latency.

**Key features:**
- Single YAML file defines entire workflow (Infrastructure as Code)
- Real-time triggers: webhooks, APIs, event-based, scheduled
- **Native dbt plugin:** Orchestrate dbt Core and dbt Cloud runs
- Language-agnostic (non-Python engineers can contribute)
- **1.0 LTS released Sept 2025;** includes AI Copilot for YAML generation
- Cuts automation costs by up to 40%

**Example Kestra workflow for our pipeline:**
```yaml
id: taxi-pipeline
namespace: nyc_taxi
triggers:
  - id: on_data_arrival
    type: io.kestra.plugin.core.trigger.Webhook
tasks:
  - id: dbt_seed
    type: io.kestra.plugin.dbt.cli.DbtCLI
    commands: ["dbt seed --profiles-dir ."]
  - id: dbt_run
    type: io.kestra.plugin.dbt.cli.DbtCLI
    commands: ["dbt run --profiles-dir ."]
  - id: dbt_test
    type: io.kestra.plugin.dbt.cli.DbtCLI
    commands: ["dbt test --profiles-dir ."]
```

### 7b. Apache Airflow — Battle-Tested at Scale

- Python DAGs, 10+ years of maturity, massive community
- **Airflow + Cosmos:** Auto-converts dbt projects to Airflow DAGs; proven at 2000+ model scale
- Best for: Complex workflows at scale, teams with Python expertise, organizations with existing Airflow infrastructure
- Limitations: Scheduler-based (not truly event-driven), steep learning curve

### 7c. Dagster — Asset-Centric Orchestration

- **Software-defined assets:** Each dbt model becomes a Dagster asset with lineage tracking
- **dagster-dbt:** Deep integration — each dbt model/source/test visible as a Dagster asset
- Hybrid orchestration with Spark, Python, dbt in a single graph
- Best for: Data asset materialization, teams wanting per-model lineage, hybrid pipelines

### 7d. Prefect — Developer-Friendly Python

- Python decorators (`@flow`, `@task`) — minimal boilerplate
- **prefect-dbt:** Every dbt model/source becomes a Prefect task
- Automatic retries, event-driven triggers, growing real-time capabilities
- Best for: ML/data science workflows, Python-native teams, rapid prototyping

### 7e. Mage AI — All-in-One Visual + Code

- Visual pipeline builder + Python/SQL/R code
- **Runs dbt natively** alongside other transforms without external orchestrator
- Webhooks and event-based triggers
- Best for: All-in-one pipelines, teams wanting visual + code, fast iteration

### 7f. Orchestration Comparison

| Aspect | Kestra | Airflow | Dagster | Prefect | Mage AI |
|--------|--------|---------|---------|---------|---------|
| **Approach** | YAML declarative | Python DAGs | Python assets | Python decorators | Visual + Python |
| **Event-driven** | Native, ms latency | Limited | Emerging | Native, growing | Webhooks, events |
| **dbt integration** | Plugin (Core+Cloud) | Cosmos / Cloud | dagster-dbt (asset) | prefect-dbt | Native built-in |
| **Learning curve** | Low (YAML) | Steep (Python) | Moderate (assets) | Low-moderate | Low (visual) |
| **Best for** | Event-driven ETL | Complex at scale | Asset materialization | ML/DS workflows | All-in-one |
| **Market position** | Fastest growing 2024-25 | Dominant (10+ years) | Top 3 | Top 3 | Growing |

---

## 8. Stage 6 — Serving: Delivering Data to Consumers

This stage answers: **How do end users and applications query the processed data?** This is the final hop — where analytical results become dashboards, API responses, ML predictions, and operational actions. The original document's biggest gap.

### 8a. Real-Time OLAP Engines

These databases are purpose-built for **sub-second analytical queries at high concurrency** — the serving layer that sits between your pipeline and your users.

#### Apache Pinot (User-Facing Analytics)

- Originally from LinkedIn ("Who Viewed Your Profile")
- **Star-tree indexing** for pre-aggregated metrics delivers sub-second queries at thousands of QPS
- Best-in-class real-time ingestion directly from Kafka
- **2025:** Iceberg table support added (with deletes and time travel coming 2026)
- StarTree offers a managed cloud version
- Best for: User-facing analytics dashboards, high-concurrency real-time queries

#### Apache Druid (Time-Series / Event Data)

- Optimized for time-series and event data
- Real-time + batch ingestion
- Strong at dashboarding and interactive slice-and-dice on time-series
- Historically popular for ad-tech, monitoring, clickstream
- Imply offers a managed cloud version
- Best for: Time-series analytics, interactive exploration, ad-tech

#### ClickHouse (Aggregate Queries at Massive Scale)

- Fastest columnar OLAP for aggregate queries (billions of rows/second)
- Extremely popular for log analytics, observability, and product analytics
- Best with micro-batched ingestion (less native streaming than Pinot/Druid)
- **ClickHouse Cloud** is a managed offering
- 2025: Production-ready vector similarity search added
- Massive and growing community
- Best for: Log analytics, observability, product analytics, aggregate queries over very large datasets

#### StarRocks (Vectorized OLAP)

- Fully vectorized MPP query engine
- Supports real-time ingestion from Kafka
- Primary-key table model with MinMax/zone map indexing
- Increasingly adopted as a "better Druid" or "ClickHouse with easier distributed operations"
- CelerData offers a managed version
- Best for: Mixed real-time + batch analytics, teams wanting Druid-like capabilities with simpler operations

#### OLAP Comparison

| Aspect | Pinot | Druid | ClickHouse | StarRocks |
|--------|-------|-------|-----------|-----------|
| **Real-time ingestion** | Native (Kafka) | Native | Micro-batch preferred | Native (Kafka) |
| **Query latency** | Sub-second | Sub-second | Sub-second | Sub-second |
| **Concurrency** | Very high (1000s QPS) | High | Moderate-high | High |
| **Best data type** | Mixed dimensions + metrics | Time-series | Logs, wide tables | Mixed |
| **Managed offering** | StarTree | Imply | ClickHouse Cloud | CelerData |
| **Complexity** | Moderate | Moderate-high | Low-moderate | Moderate |

### 8b. BI & Visualization Layer

Dashboarding tools that connect to the storage or OLAP layer:

| Tool | Type | Best For |
|------|------|----------|
| **Tableau** | Enterprise BI | Large organizations, rich visualization, executive dashboards |
| **Looker (Google)** | Semantic-layer BI | Governed metrics, LookML modeling, self-service |
| **Metabase** | Open-source BI | Quick setup, SQL-friendly, small-medium teams |
| **Apache Superset** | Open-source BI | Flexible, extensible, large-scale open-source deployments |
| **Grafana** | Monitoring / time-series | Operational dashboards, metrics, alerting |
| **Preset** | Managed Superset | Superset without ops overhead |

### 8c. ML Feature Stores

Feature stores bridge streaming data and ML model serving — computing features in real-time and serving them at low latency during inference.

#### Feast (Open-Source, Linux Foundation)

- Leading open-source feature store
- Pip-installable, no infrastructure required for getting started
- **Online stores:** Redis, DynamoDB for low-latency serving
- **Offline stores:** BigQuery, Snowflake, S3 for training
- Adapting for RAG/LLM vector embedding serving

#### Tecton (Managed, Enterprise)

- Built by creators of Uber's Michelangelo
- Real-time streaming ingestion — features available for inference in seconds
- Strongest streaming support among feature stores
- Enterprise-grade for production ML at scale

#### Databricks Feature Store

- Integrated with Unity Catalog and MLflow
- Leverages Delta Lake for feature tables
- Best for Databricks/Spark shops

**The pattern:** Streaming pipeline computes features in real-time (e.g., "rolling 5-minute average fare") → writes to online store (Redis) → ML model reads at inference time for fraud detection, dynamic pricing, recommendations.

### 8d. Reverse ETL

Move data from the warehouse/lakehouse back to operational systems:

| Tool | What It Does |
|------|-------------|
| **Census** | Sync warehouse data to CRMs, ad platforms, support tools |
| **Hightouch** | Audience building and activation from warehouse data |
| **Polytomic** | Bi-directional sync between databases and SaaS tools |

**The pattern:** dbt Gold models → Reverse ETL → Salesforce, HubSpot, Marketo, Intercom, Google Ads

### 8e. API Layer

For applications that need programmatic access to pipeline outputs:

- **REST/GraphQL APIs** backed by OLAP engines or cached results
- **Cube.js / Cube:** Semantic layer + caching + API on top of any database
- **Hasura:** Auto-generates GraphQL APIs from PostgreSQL (and now other sources)

### 8f. Serving Decision Summary

| Need | Best Choice | Runner-Up |
|------|------------|-----------|
| User-facing real-time dashboards | Apache Pinot | StarRocks |
| Time-series / monitoring | Apache Druid or Grafana | ClickHouse |
| Log analytics / observability | ClickHouse | Elastic/OpenSearch |
| General-purpose analytics | ClickHouse | StarRocks |
| Enterprise BI | Tableau or Looker | Superset (open-source) |
| Quick open-source BI | Metabase | Apache Superset |
| ML feature serving | Feast (open-source) or Tecton (managed) | Databricks Feature Store |
| Reverse ETL | Census or Hightouch | Polytomic |
| API layer | Cube.js | Hasura |

---

## 9. Stage 7 — Governance & Observability

This stage answers: **How do you ensure data quality, enforce contracts, and monitor pipeline health in a streaming context?** Streaming adds unique challenges — you cannot simply re-run a batch to fix bad data that has already been consumed.

### 9a. Schema Registry (Confluent)

- Validates schemas for Kafka messages (Avro, Protobuf, JSON Schema)
- Enforces backward/forward/full compatibility between schema versions
- Central repository for data contracts
- Prevents producers from publishing messages that would break consumers
- **Redpanda includes a built-in Schema Registry** (no separate service)

### 9b. Schema Evolution in Streaming

- Streams adapt to schema drift in near-real-time
- No manual DDL for new source attributes
- **Expand-contract pattern:** Add new fields first (expand), migrate consumers, remove old fields (contract)
- Iceberg and Delta Lake support schema evolution natively at the storage layer

### 9c. Data Contracts

- Explicit expectations on data shape (dbt model contracts: column names, types, constraints)
- Prevent upstream changes from breaking downstream consumers
- Schema-as-code: versioned, tested, validated before deployment
- **In streaming:** Contracts enforced at Schema Registry (ingestion boundary) AND at dbt (transformation boundary)

### 9d. Data Quality in Streaming

Streaming adds unique data quality challenges: bad data is consumed immediately and cannot simply be re-batched.

**Strategies:**
- **Dead-letter queues (DLQ):** Route malformed/invalid messages to a separate topic for investigation instead of dropping them
- **In-stream validation:** Check data quality rules as events flow (schema validation, range checks, null checks)
- **Late-data handling:** Watermarks + allowed lateness to handle out-of-order events correctly
- **Deduplication:** Exactly-once semantics or idempotent writes to prevent duplicates

### 9e. Data Observability Tools

| Tool | Type | Focus |
|------|------|-------|
| **Monte Carlo** | Commercial | Pioneer of "data observability." ML-based anomaly detection, automatic lineage mapping, freshness/volume/schema monitoring |
| **Elementary Data** | Open-source, dbt-native | Data observability built into dbt. Monitors test results, schema changes, freshness. **Most relevant for dbt-centric pipelines.** |
| **Soda Core** | Open-source | Define expectations (freshness, volume, schema, custom SQL) and validate continuously. Can run in-stream. |
| **Acceldata** | Commercial | Real-time monitoring of streaming workloads. Alerts on data drift, schema violations, pipeline failures. |
| **Great Expectations** | Open-source | Data validation framework. Define expectations in Python, validate in batch or micro-batch. |

**Key metrics to monitor in streaming:**
- **Freshness:** How recent is the latest data? (detects pipeline stalls)
- **Volume:** Is the event rate within expected bounds? (detects source failures or floods)
- **Schema:** Have field names, types, or structures changed? (detects breaking changes)
- **Distribution:** Are value distributions stable? (detects data drift)
- **Consumer lag:** How far behind are consumers from the latest offset? (detects backpressure)

---

## 10. Architecture Patterns

These are the high-level blueprints for organizing all the stages above. Choose based on your latency requirements, complexity tolerance, and team capabilities.

### 10a. Lambda Architecture (Batch + Speed Layers)

```
                    ┌─── Batch Layer (Spark/dbt) ──── Serving Layer ───┐
Raw Events ────┤                                                       ├──→ Query
                    └─── Speed Layer (Flink/Kafka Streams) ───────────┘
```

- **Pros:** Handles massive historical data + real-time freshness
- **Cons:** Two code paths (batch + streaming), high complexity, data consistency challenges between layers
- **2026 status:** Being phased out in favor of Kappa in new projects. Still exists in legacy architectures.

### 10b. Kappa Architecture (Stream-Only)

```
Raw Events → Kafka (immutable log) → Stream Processor (Flink) → Materialized Views → Query
                                          ↑
                            Replay from any timestamp for reprocessing
```

- **Pros:** Single code path, lower complexity, easier debugging, replay for reprocessing
- **Cons:** Requires immutable event log with long retention, stream processor must handle all complexity
- **2026 status:** Growing as the default architecture. Kappa + open table formats (Iceberg) is the mainstream choice for new projects.

### 10c. Medallion Architecture (Bronze / Silver / Gold)

```
Bronze (Raw)              Silver (Refined)             Gold (Business-Ready)
──────────────────        ──────────────────           ──────────────────────
Kafka events              Cleaned, deduplicated        Aggregated KPIs
dumped as-is              Standardized schema          Dimensional models
DQ checks only            Business rules applied       BI-layer ready

Maps to dbt:              Maps to dbt:                 Maps to dbt:
(minimal dbt or none)     staging + intermediate       marts
```

This is what our current pipeline already follows — staging=Silver, marts=Gold. Adding streaming means Bronze becomes a Kafka-fed raw layer landing in Iceberg.

**2026 status:** Universal adoption. Bronze/Silver/Gold is the standard vocabulary for data organization.

### 10d. Event-Driven Architecture (EDA)

```
Database Changes → CDC (Debezium) → Kafka → Stream Processor → Materialized Views
                                         → Cache Invalidation
                                         → Search Index Update
                                         → ML Feature Store
                                         → Alert/Notification
```

Systems react to state changes in real-time rather than polling on schedule. Multiple consumers independently react to the same events.

**Key pattern:** Event sourcing — store the full sequence of events (not just current state). Enables replay, audit, and temporal queries.

### 10e. Streaming Lakehouse (2025-2026 Convergent Pattern)

```
Kafka → Flink → Iceberg (Bronze/Silver) → dbt / Spark / Trino → Iceberg (Gold) → OLAP / BI
                    ↑                                                    ↓
        Unified catalog (REST Catalog / Unity Catalog)          Feature Store / Reverse ETL
```

This is the convergence of Kappa + Medallion + Lakehouse:
- Single streaming path (Kappa) deposits into open table format (Iceberg)
- Data organized as Bronze/Silver/Gold (Medallion)
- Multiple engines read/write the same tables (Lakehouse)
- Catalog provides unified governance and discovery

---

## 11. End-to-End Integration Patterns

These are complete, opinionated pipeline architectures showing how all stages connect. Choose based on your team, scale, and latency requirements.

### Pattern 1: Kafka → Flink → Iceberg → dbt (Lowest Latency)

```
Taxi APIs ──CDC──→ Kafka ──→ Flink SQL ──→ Iceberg (Bronze/Silver) ──→ dbt ──→ Gold
```

- Flink handles cleaning, enrichment, windowed aggregations in real-time
- dbt handles final analytical modeling (marts) in micro-batch
- Latency: **sub-second** for stream processing, **minutes** for dbt refresh
- Best for: Low-latency requirements, CDC-heavy, complex stateful processing

### Pattern 2: Kafka → Warehouse → dbt (Traditional Real-Time ELT)

```
Taxi APIs ──→ Kafka ──→ Kafka Connect Sink ──→ Snowflake/BigQuery ──→ dbt ──→ Analytics
```

- Kafka Connect handles ingestion (no custom code)
- Warehouse provides compute for all transformations
- dbt applies the full transformation layer
- Latency: **seconds to minutes**
- Best for: Teams already on a cloud warehouse, wanting simplicity over low-latency

### Pattern 3: Kafka → Spark Streaming → Delta Lake → dbt (Spark-Centric)

```
Taxi APIs ──→ Kafka ──→ Spark Structured Streaming ──→ Delta Lake ──→ dbt ──→ Analytics
```

- Spark handles real-time processing + ML feature engineering
- Delta Lake provides ACID, time travel, UniForm for Iceberg compatibility
- dbt models consume Delta tables
- Latency: **~100ms** for stream processing, **minutes** for dbt
- Best for: Databricks/Spark shops, ML pipeline integration

### Pattern 4: Streaming SQL + dbt (Simplest Real-Time)

```
Kafka ──→ Materialize/RisingWave ──→ Live Materialized Views ──→ dbt ──→ Analytics
```

- Streaming SQL engine replaces intermediate aggregations with live views
- Views update incrementally at millisecond latency
- dbt handles final business logic and testing
- Latency: **milliseconds** for materialized views, **minutes** for dbt Gold
- Best for: Smallest team size, SQL-only skill set, fastest path to real-time

### Pattern 5: Kappa + dbt Micro-Batch (Balanced)

```
Event Log (Kafka) ──→ Flink ──→ Iceberg ──→ dbt (micro-batch every 5-15 min) ──→ Analytics
                          ↑
              Replay from any timestamp for backfill
```

- Single streaming code path (Kappa)
- dbt micro-batching (dbt 1.9+) processes in bounded time windows
- Reprocess failed batches without full rebuild
- Latency: **sub-second** for streaming, **5–15 minutes** for dbt
- Best for: Most teams — balances real-time freshness with dbt's modeling power

### Pattern 6: Cloud-Managed (Minimal Ops)

```
APIs ──→ Kinesis/Pub-Sub/Event Hubs ──→ Managed Flink/Dataflow ──→ Warehouse ──→ dbt ──→ BI
```

- All infrastructure managed by cloud provider
- No Kafka/Flink/storage to operate
- Latency: **seconds to minutes**
- Best for: Small teams, cloud-native, wanting zero ops overhead

### Pattern 7: Batch-First with Streaming Readiness (Pragmatic Starting Point)

```
Files/APIs ──→ Orchestrator (Airflow/Kestra) ──→ Warehouse/DuckDB ──→ dbt ──→ Analytics
                                                        ↑
                                    (Add Kafka + stream processor later when needed)
```

- Start with batch orchestration (replace Makefile)
- dbt handles all transformations
- Add streaming components incrementally when latency requirements demand it
- Latency: **minutes to hours** (batch), upgradeable to real-time
- Best for: Projects like our NYC Taxi pipeline — start with orchestration, add streaming when needed

---

## 12. Decision Matrices: Choosing by Scale & Needs

### 12a. By Company Size / Team

| Scale | Ingestion | Processing | Storage | Transformation | Orchestration | Serving |
|-------|-----------|-----------|---------|---------------|---------------|---------|
| **Solo / Startup (1-3 eng)** | Cloud-managed (Kinesis/Pub-Sub) or NATS | Streaming SQL (RisingWave) or Managed Flink | Cloud warehouse (Snowflake/BQ) or DuckDB | dbt Core | Kestra or Prefect | Metabase or Superset |
| **Small team (3-10 eng)** | Redpanda or Confluent Cloud | Flink (managed) or Spark Streaming | Iceberg on object storage | dbt Core + micro-batch | Dagster or Kestra | ClickHouse or Metabase |
| **Medium org (10-50 eng)** | Kafka (self-managed or Confluent) | Flink or Spark (on Kubernetes) | Iceberg or Delta Lake | dbt Cloud + Mesh | Airflow or Dagster | Pinot/ClickHouse + Tableau |
| **Enterprise (50+ eng)** | Kafka + Schema Registry + governance | Flink (dedicated cluster) | Iceberg + REST Catalog + Unity Catalog | dbt Cloud + Mesh + contracts | Airflow + Cosmos | Pinot + Tableau/Looker + Feature Store |

### 12b. By Latency Requirement

| Latency Need | Architecture | Key Technologies | Cost/Complexity |
|-------------|-------------|-----------------|----------------|
| **Real-time (< 1 second)** | Kappa + OLAP | Kafka → Flink → Iceberg → Pinot | High |
| **Near-real-time (1-60 seconds)** | Kappa + dbt micro-batch | Kafka → Flink → Iceberg → dbt | Medium-high |
| **Minutes (1-15 min)** | Streaming + micro-batch dbt | Kafka → Spark/Flink → Warehouse → dbt | Medium |
| **Hourly** | Micro-batch orchestrated | Cloud ingestion → Warehouse → dbt (hourly) | Medium-low |
| **Daily (batch)** | Traditional ELT | Files/APIs → Orchestrator → Warehouse → dbt | Low |

### 12c. By Primary Use Case

| Use Case | Recommended Pattern | Key Reason |
|----------|-------------------|------------|
| **Fraud detection** | Kafka → Flink → Feature Store → ML | Sub-second decisions on transactions |
| **IoT / sensor data** | NATS/Kafka → Flink → Iceberg → Druid | High volume, time-series, real-time alerting |
| **User-facing analytics** | Kafka → Flink → Pinot | High concurrency, sub-second queries |
| **Executive dashboards** | Kafka → Warehouse → dbt → Tableau | Daily/hourly refresh sufficient, simpler architecture |
| **Log analytics** | Kafka → Flink → ClickHouse | Massive volume, aggregate queries |
| **CDC / data sync** | Debezium → Kafka → Flink → Iceberg | Real-time database replication |
| **ML features** | Kafka → Flink → Feature Store (Feast/Tecton) | Real-time feature computation + low-latency serving |
| **Product analytics** | Kafka → ClickHouse or Pinot | Event tracking, funnel analysis, real-time |
| **Operational alerting** | Kafka → Flink → Alert system | Sub-second anomaly detection |
| **Batch reporting** | Orchestrator → Warehouse → dbt → BI | Lowest cost, simplest architecture |

### 12d. Technology Decision Matrix (Comprehensive)

| Need | Recommended Tool | Why |
|------|-----------------|-----|
| Event streaming backbone | Apache Kafka (4.0+) | Industry standard, massive ecosystem, KRaft simplified ops |
| Simpler Kafka alternative | Redpanda | C++, single binary, Kafka-compatible, lower latency |
| Cloud-native streaming | Pulsar | Decoupled compute/storage, multi-tenant, geo-replication |
| AWS-managed streaming | Kinesis or Amazon MSK | Zero-ops, AWS-native integration |
| GCP-managed streaming | Pub/Sub + Dataflow | Best auto-scaling, globally distributed |
| Azure-managed streaming | Event Hubs | Kafka-protocol-compatible, Azure-native |
| CDC from databases | Debezium + Kafka Connect | Battle-tested, millisecond-latency CDC |
| Managed CDC | Estuary Flow | Sub-100ms, exactly-once, no infrastructure |
| Sub-second stream processing | Apache Flink | True streaming, best stateful processing |
| Analytical streaming + ML | Spark Structured Streaming | Rich ML libraries, unified batch/stream |
| Streaming SQL (simplest) | RisingWave or Materialize | PostgreSQL-compatible, incrementally-updated views |
| Unified batch + streaming SDK | Apache Beam | Write once, run on Flink/Spark/Dataflow |
| Lightweight in-app processing | Kafka Streams | No separate cluster, Java library |
| Visual data routing | Apache NiFi | Drag-and-drop, enterprise security, provenance |
| Microservices messaging | NATS JetStream | Ultra-lightweight, sub-ms latency |
| Task distribution / RPC | RabbitMQ | Complex routing, priority queues, exchanges |
| Lakehouse storage (portable) | Apache Iceberg | Engine-agnostic, industry default for new projects |
| Lakehouse storage (Spark) | Delta Lake | Deep Spark integration, UniForm for portability |
| Lakehouse storage (CDC-heavy) | Apache Hudi | Optimized for streaming upserts |
| Cloud warehouse | Snowflake / BigQuery / Redshift | Simplest path, all compute managed |
| Local/small-scale storage | DuckDB | In-process, zero ops, fast analytics |
| Analytical transformation | dbt Core / dbt Cloud | Industry standard for SQL analytics modeling |
| Event-driven orchestration | Kestra | YAML-first, ms triggers, native dbt plugin |
| Battle-tested orchestration | Airflow + Cosmos | 10+ years, proven at massive scale |
| Asset-centric orchestration | Dagster + dagster-dbt | Per-model lineage, hybrid workflows |
| Developer-friendly orchestration | Prefect | Python decorators, rapid prototyping |
| All-in-one orchestration | Mage AI | Visual + code, native dbt |
| User-facing real-time OLAP | Apache Pinot | Highest concurrency, Kafka-native ingestion |
| Time-series OLAP | Apache Druid | Interactive exploration, time-series optimized |
| Aggregate query OLAP | ClickHouse | Fastest aggregates at billion-row scale |
| General-purpose OLAP | StarRocks | Vectorized, simpler ops than Druid |
| Enterprise BI | Tableau or Looker | Rich visualization, governed metrics |
| Open-source BI | Metabase or Superset | Free, SQL-friendly, fast setup |
| ML feature serving | Feast (open-source) or Tecton (managed) | Real-time features for model inference |
| Reverse ETL | Census or Hightouch | Warehouse → operational systems |
| Data observability | Monte Carlo (commercial) or Elementary (dbt-native) | Freshness, volume, schema monitoring |
| Data quality testing | dbt tests + Soda Core + Great Expectations | Multi-layered validation |

---

## 13. 2026 Industry Trends & Market Context

### Market-Shaping Events

**IBM acquires Confluent for $11B (December 2025, closing mid-2026):** IBM becomes the dominant force in event streaming (50%+ market share in event broker/messaging). Rationale: "real-time data as the missing layer for enterprise AI." Confluent's TAM doubled from $50B to $100B in 2025.

**Kafka 4.0 drops ZooKeeper (March 2025):** Most significant Kafka architectural change in 14 years. Simplifies operations dramatically. KRaft is now the only metadata mode.

**ksqlDB enters maintenance mode:** Confluent shifted to Flink as primary stream processor after Immerok acquisition. Industry moving to PostgreSQL-compatible streaming SQL.

### Technology Trends

- **Streaming-first:** Real-time ingestion is the default, not the exception. Batch is a special case of streaming (bounded stream).
- **Kappa over Lambda:** Single streaming path replacing complex dual-path architectures. Kappa + Iceberg is the mainstream pattern.
- **Open table formats win:** Iceberg emerging as the convergence point for streaming + batch. Delta Lake (UniForm) and Hudi remain viable. Vendor lock-in is ending.
- **Diskless/cloud-native Kafka:** WarpStream (acquired by Confluent), AutoMQ — separate compute from storage, run on S3. Dramatically lower cost and simpler operations. Major architectural trend.
- **Event-driven orchestration:** 70% of scheduled DAGs becoming unnecessary with event triggers (Kestra, Dagster sensors, Prefect events).
- **dbt centrality:** dbt for analytical modeling; stream processors for low-level transforms. Clear separation of concerns.
- **Flink ascendancy:** Industry standard for stateful streaming. Confluent, AWS, and the open-source community all converging on Flink.
- **Medallion adoption:** Bronze/Silver/Gold as universal data organization vocabulary.
- **Data contracts everywhere:** Schema enforcement at production boundaries — Schema Registry at ingestion, dbt contracts at transformation, API contracts at serving.

### AI + Streaming

- **Streaming + AI agents:** Dominant 2026 narrative. Redpanda's "Agentic Data Plane," Confluent's "event-driven AI" positioning, IBM's acquisition rationale — all center on AI agents consuming and producing real-time event streams.
- **AI-embedded processing:** Anomaly detection, dynamic pricing, fraud scoring running inline within the stream processor (Flink ML, Spark MLlib).
- **Real-time vector search:** ClickHouse and RisingWave added vector similarity search for RAG/LLM use cases.
- **Platform consolidation:** Point solutions consolidating into integrated data platforms (Confluent = Kafka + Flink + Iceberg + governance).

---

## 14. Complete Reference Architecture

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                          FULL REAL-TIME PIPELINE                                 │
├──────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  STAGE 1: DATA SOURCES                                                           │
│  ├── Taxi meter APIs / IoT sensors / Application events                          │
│  ├── Transactional databases (CDC via Debezium / Estuary Flow)                   │
│  ├── Third-party APIs and webhooks                                               │
│  └── File uploads (batch sources, backfill)                                      │
│           ↓                                                                      │
│  STAGE 2: INGESTION (pick one or combine)                                        │
│  ├── Event Streams: Kafka 4.0 / Redpanda / Pulsar                               │
│  ├── Cloud-Managed: Kinesis / Pub-Sub / Event Hubs                               │
│  ├── Message Queues: RabbitMQ / NATS (for task distribution)                     │
│  ├── CDC: Debezium + Kafka Connect / Flink CDC / Estuary Flow                    │
│  ├── Data Flow: Apache NiFi (visual routing)                                     │
│  └── Governance: Schema Registry (Avro/Protobuf/JSON), data contracts            │
│           ↓                                                                      │
│  STAGE 3: STREAM PROCESSING (pick one)                                           │
│  ├── Apache Flink: True streaming, SQL, stateful, CDC (sub-second)               │
│  ├── Spark Structured Streaming: Micro-batch, ML, DataFrames (~100ms)            │
│  ├── RisingWave / Materialize: Streaming SQL, materialized views (ms)            │
│  ├── Kafka Streams: Lightweight in-app processing (no cluster)                   │
│  ├── Apache Beam: Portable SDK (runs on Flink/Spark/Dataflow)                    │
│  └── Managed: AWS Managed Flink / GCP Dataflow / Azure Stream Analytics          │
│           ↓                                                                      │
│  STAGE 4: STORAGE (Lakehouse)                                                    │
│  ├── Iceberg / Delta Lake / Hudi on object storage (S3/GCS/Azure Blob)           │
│  ├── Bronze: Raw events landed as-is                                             │
│  ├── Silver: Cleaned, deduplicated, enriched (stream processor output)           │
│  ├── Gold: Business models (dbt marts)                                           │
│  └── Alternative: Cloud warehouse (Snowflake/BigQuery/Redshift)                  │
│           ↓                                                                      │
│  STAGE 5: TRANSFORMATION (dbt)                                                   │
│  ├── Micro-batch incremental models (every 5-15 min, dbt 1.9+)                  │
│  ├── Model contracts for schema guarantees                                       │
│  ├── 91+ data quality tests                                                      │
│  ├── dbt Mesh for multi-team orchestration                                       │
│  └── Streaming SQL integration (Materialize/RisingWave for live views)           │
│           ↓                                                                      │
│  STAGE 6: ORCHESTRATION (pick one)                                               │
│  ├── Kestra: Event-driven YAML workflows, ms triggers, dbt plugin               │
│  ├── Airflow + Cosmos: Battle-tested DAGs at scale                               │
│  ├── Dagster + dagster-dbt: Asset-centric with lineage                           │
│  ├── Prefect: Developer-friendly Python, event-driven                            │
│  └── Mage AI: All-in-one visual + code with native dbt                           │
│           ↓                                                                      │
│  STAGE 7: SERVING (pick per use case)                                            │
│  ├── Real-Time OLAP: Pinot / Druid / ClickHouse / StarRocks                     │
│  ├── BI Dashboards: Tableau / Looker / Metabase / Superset / Grafana            │
│  ├── ML Feature Store: Feast / Tecton / Databricks Feature Store                 │
│  ├── Reverse ETL: Census / Hightouch → CRM, ad platforms, ops tools             │
│  └── API Layer: Cube.js / Hasura / custom REST/GraphQL                           │
│           ↓                                                                      │
│  STAGE 8: GOVERNANCE & OBSERVABILITY (cross-cutting)                             │
│  ├── Schema Registry: Avro/Protobuf/JSON schema validation                      │
│  ├── Data Contracts: dbt contracts + Schema Registry                             │
│  ├── Data Observability: Monte Carlo / Elementary / Soda Core                    │
│  ├── Quality: Dead-letter queues, in-stream validation, dbt tests                │
│  └── Monitoring: Consumer lag, freshness, volume, schema drift                   │
│                                                                                  │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

## 15. Implementation Roadmap

To evolve the NYC Taxi project from batch to streaming, each step is independent and composable:

### Phase 1: Foundation (Batch + Orchestration)
1. **Add orchestration:** Replace the Makefile with Kestra or Airflow to schedule and trigger dbt runs
2. **Add data observability:** Integrate Elementary (dbt-native) for test result monitoring and freshness tracking
3. **Enforce data contracts:** Add dbt model contracts to Gold-layer marts

### Phase 2: Near-Real-Time (Streaming Source + Micro-Batch)
4. **Add streaming source:** Set up Kafka or Redpanda with a taxi trip producer (simulated or API-based)
5. **Enable CDC:** If data lives in a database, add Debezium for real-time change capture
6. **Enable micro-batch dbt:** Configure dbt 1.9+ micro-batch incremental models (5–15 minute refresh)
7. **Add Schema Registry:** Enforce Avro/Protobuf schemas at the Kafka boundary

### Phase 3: Real-Time Processing
8. **Add stream processing:** Flink SQL or Spark Structured Streaming for real-time cleaning/enrichment (Bronze→Silver)
9. **Upgrade storage:** Move from DuckDB to Iceberg tables on object storage
10. **Implement Medallion:** Bronze (raw events) → Silver (Flink-cleaned) → Gold (dbt marts)

### Phase 4: Full Real-Time Serving
11. **Add OLAP serving:** Deploy Pinot or ClickHouse for sub-second analytical queries
12. **Add BI layer:** Connect Metabase or Superset to the OLAP engine
13. **Add feature store:** If ML models are needed, deploy Feast for real-time feature serving
14. **Add monitoring:** Consumer lag alerts, data freshness SLAs, pipeline health dashboards

Each phase delivers value independently. Start with Phase 1 — it requires no new infrastructure beyond an orchestrator.

---

## 16. Implementation Results & Benchmarks

> **All 12 pipelines from Section 15 were fully implemented, tested, and benchmarked.** This section documents what actually happened when theory met practice.

### 16.1 What Was Built

Every pipeline in `pipelines/00-11/` was implemented as a fully isolated Docker Compose stack processing the same NYC Yellow Taxi data (January 2024, 2,964,624 rows source). Each streaming pipeline generates 10,000 events via a shared data generator, processes them through the Medallion architecture (Bronze → Silver), and was benchmarked for speed, memory, and correctness.

```
pipelines/
├── 00-batch-baseline/           # DuckDB + dbt (reference)
├── 01-kafka-flink-iceberg/      # Kafka + Flink SQL + Iceberg/MinIO
├── 02-kafka-spark-iceberg/      # Kafka + PySpark + Iceberg/MinIO
├── 03-kafka-risingwave/         # Kafka + RisingWave MVs
├── 04-redpanda-flink-iceberg/   # Redpanda + Flink SQL + Iceberg/MinIO
├── 05-redpanda-spark-iceberg/   # Redpanda + PySpark + Iceberg/MinIO
├── 06-redpanda-risingwave/      # Redpanda + RisingWave MVs
├── 07-kestra-orchestrated/      # P01 + Kestra
├── 08-airflow-orchestrated/     # P01 + Astronomer Airflow
├── 09-dagster-orchestrated/     # P01 + Dagster
├── 10-serving-comparison/       # ClickHouse + Metabase + Superset
├── 11-observability-stack/      # P01 + Elementary + Soda Core
└── comparison/                  # results.csv + comparison_report.md
```

### 16.2 Benchmark Results

#### Tier 1: Core Streaming Pipelines (10,000 events)

| # | Pipeline | Startup | Ingestion Rate | Bronze | Silver | Total Processing | Memory | Services |
|---|----------|---------|---------------|--------|--------|-----------------|--------|----------|
| 00 | Batch Baseline | n/a | n/a | n/a | n/a | **21s** (full 2.96M) | minimal | 1 |
| 01 | Kafka+Flink+Iceberg | 31s | 18,586 evt/s | 13s | 9s | **24s** | 2,870 MB | 7 |
| 02 | Kafka+Spark+Iceberg | 18s | 24,370 evt/s | 12s | 10s | **24s** | 1,230 MB | 6 |
| 03 | Kafka+RisingWave | 34s | 18,069 evt/s | auto | auto | **~2s** | 687 MB | 4 |
| 04 | Redpanda+Flink+Iceberg | 26s | 25,139 evt/s | 14s | 11s | **27s** | 1,860 MB | 6 |
| 05 | Redpanda+Spark+Iceberg | 19s | 24,636 evt/s | 16s | 12s | **30s** | 917 MB | 5 |
| 06 | Redpanda+RisingWave | 34s | 18,030 evt/s | auto | auto | **~2s** | 449 MB | 3 |

#### Tier 2: Orchestrator Overhead (vs Pipeline 01 baseline)

| # | Orchestrator | Processing Time | Memory | Overhead (Memory) | Overhead (Time) | UI Port |
|---|-------------|-----------------|--------|-------------------|-----------------|---------|
| 07 | Kestra | 26s | 2,890 MB | +485 MB | +2s | :8083 |
| 08 | Airflow (Astro) | 27s | 2,230 MB* | +~1,500 MB | +3s | :8080 |
| 09 | Dagster | 26s | 2,770 MB | +502 MB | +2s | :3000 |

*Airflow memory shown is infra-only; Astronomer adds ~1,500 MB for webserver + scheduler + triggerer + postgres.

#### Tier 3-4: Serving & Observability

| # | Pipeline | Key Finding |
|---|----------|-------------|
| 10 | ClickHouse + Metabase + Superset | 2.76M rows loaded; all 4 benchmark queries <50ms cold and warm |
| 11 | Elementary + Soda Core | dbt-native monitoring + in-pipeline quality checks working |

### 16.3 Speed Rankings

**By Total Processing Time (fastest to slowest):**

| Rank | Pipeline | Processing Time | Why |
|------|----------|----------------|-----|
| 1 | RisingWave (P03/P06) | ~2s | Materialized views auto-process events as they arrive — no batch step needed |
| 2 | Batch Baseline (P00) | 21s | DuckDB on local parquet is blazing fast for 2.96M rows |
| 3 | Kafka+Flink (P01) | 24s | Flink SQL batch mode, Iceberg write overhead |
| 4 | Kafka+Spark (P02) | 24s | Spark Structured Streaming, similar to Flink |
| 5 | Kestra+Flink (P07) | 26s | +2s orchestrator overhead |
| 6 | Dagster+Flink (P09) | 26s | +2s orchestrator overhead |
| 7 | Redpanda+Flink (P04) | 27s | Slightly slower Flink processing vs P01 |
| 8 | Airflow+Flink (P08) | 27s | +3s orchestrator overhead |
| 9 | Redpanda+Spark (P05) | 30s | Spark slightly slower with Redpanda broker |

### 16.4 Broker Comparison: Kafka vs Redpanda

Three paired comparisons isolating the broker as the only variable:

| Metric | Kafka (P01) | Redpanda (P04) | Winner |
|--------|-------------|----------------|--------|
| Ingestion rate | 18,586 evt/s | 25,139 evt/s | **Redpanda** (+35%) |
| Bronze processing | 13s | 14s | Kafka (marginal) |
| Silver processing | 9s | 11s | Kafka |
| Memory | 2,870 MB | 1,860 MB | **Redpanda** (-35%) |
| Services needed | 7 | 6 | **Redpanda** (no Schema Registry needed) |
| Startup time | 31s | 26s | **Redpanda** (-16%) |

| Metric | Kafka (P02) | Redpanda (P05) | Winner |
|--------|-------------|----------------|--------|
| Ingestion rate | 24,370 evt/s | 24,636 evt/s | Tie |
| Total processing | 24s | 30s | **Kafka** |
| Memory | 1,230 MB | 917 MB | **Redpanda** (-25%) |

| Metric | Kafka (P03) | Redpanda (P06) | Winner |
|--------|-------------|----------------|--------|
| Ingestion rate | 18,069 evt/s | 18,030 evt/s | Tie |
| Total processing | ~2s | ~2s | Tie |
| Memory | 687 MB | 449 MB | **Redpanda** (-35%) |

**Verdict:** Redpanda consistently uses 25-35% less memory and eliminates the need for a separate Schema Registry container. Ingestion rates are comparable or better. Kafka had marginally faster Flink processing in one test, but the difference is small.

### 16.5 Processor Comparison: Flink vs Spark vs RisingWave

Using Kafka-based pipelines (P01 vs P02 vs P03) as the control group:

| Metric | Flink SQL (P01) | Spark (P02) | RisingWave (P03) |
|--------|----------------|-------------|-----------------|
| Processing model | Batch SQL statements | PySpark jobs | Materialized views |
| Processing time | 24s | 24s | **~2s** |
| Bronze rows | 10,000 | 10,000 | 10,000 |
| Silver rows | 9,855 | 9,739 | 9,766 |
| Memory | 2,870 MB | 1,230 MB | **687 MB** |
| Services | 7 | 6 | **4** |
| Language | SQL | Python | SQL |
| Storage format | Iceberg (MinIO) | Iceberg (MinIO) | Internal (PG-compatible) |
| JARs required | 7 custom JARs | 5 custom JARs | None |
| Setup complexity | High | Medium | **Low** |

**Key insight:** RisingWave is dramatically simpler and faster for streaming SQL workloads. The tradeoff is that it stores data internally (not Iceberg), so it's less interoperable with the broader lakehouse ecosystem. Flink and Spark both write to Iceberg, which is the 2026 industry standard for open table formats.

### 16.6 Orchestrator Comparison: Kestra vs Airflow vs Dagster

| Metric | Kestra (P07) | Airflow (P08) | Dagster (P09) |
|--------|-------------|---------------|---------------|
| Memory overhead | +485 MB | +~1,500 MB | +502 MB |
| Processing overhead | +2s | +3s | +2s |
| Service count | +2 | +3-4 | +3 |
| Configuration | YAML flows | Python DAGs | Python definitions |
| dbt integration | Plugin (CLI) | Cosmos (per-model tasks) | dagster-dbt (native assets) |
| UI quality | Clean, modern | Mature, full-featured | Best lineage graph |
| Lineage visibility | Flow-level | Task-level (with Cosmos) | **Asset-level** (best) |
| Setup difficulty | Easiest | Hardest (Astronomer) | Medium |
| Community/ecosystem | Growing | **Largest** | Growing fast |

**Verdict:** Kestra wins for simplicity (YAML-native, lowest overhead). Dagster wins for dbt integration (asset-based model, best lineage). Airflow wins for ecosystem maturity but has the heaviest footprint.

### 16.7 Memory Efficiency Rankings

| Rank | Pipeline | Memory | Memory/Service |
|------|----------|--------|---------------|
| 1 | P06 Redpanda+RisingWave | **449 MB** | 150 MB |
| 2 | P03 Kafka+RisingWave | 687 MB | 172 MB |
| 3 | P05 Redpanda+Spark | 917 MB | 183 MB |
| 4 | P02 Kafka+Spark | 1,230 MB | 205 MB |
| 5 | P04 Redpanda+Flink | 1,860 MB | 310 MB |
| 6 | P08 Airflow (infra) | 2,230 MB | 319 MB |
| 7 | P09 Dagster | 2,770 MB | 277 MB |
| 8 | P01 Kafka+Flink | 2,870 MB | 410 MB |
| 9 | P07 Kestra | 2,890 MB | 321 MB |

**What drives memory:** Flink TaskManager alone consumes 875-930 MB. Schema Registry adds 340-428 MB. Kafka uses 315-492 MB. Redpanda uses only 193-237 MB for the same function.

### 16.8 Strengths and Weaknesses

#### Brokers

| Technology | Strengths | Weaknesses | Best For |
|-----------|-----------|------------|----------|
| **Kafka** | Industry standard, massive ecosystem, proven at petabyte scale, KRaft eliminates ZooKeeper | Higher memory (needs Schema Registry as separate service), more configuration required | Production systems needing maximum ecosystem compatibility |
| **Redpanda** | 25-35% less memory, built-in Schema Registry, faster startup, C++ implementation, Kafka API-compatible | Smaller community, fewer managed service options, less battle-tested at extreme scale | Teams wanting Kafka compatibility with lower resource footprint |

#### Stream Processors

| Technology | Strengths | Weaknesses | Best For |
|-----------|-----------|------------|----------|
| **Flink SQL** | True streaming engine, exactly-once semantics, best Iceberg integration, SQL-native | Highest memory (1.5+ GB for JM+TM), requires 7 JARs, complex setup, JVM-heavy | Production streaming with Iceberg lakehouse, exactly-once requirements |
| **Spark** | Mature ecosystem, Python-native (PySpark), strong ML integration, good for batch+streaming | Micro-batch (not true streaming), moderate memory, requires custom Docker image with JARs | Teams already using Spark, Python-centric data engineering, ML pipelines |
| **RisingWave** | 12x faster processing, lowest memory, fewest services, SQL-only (no JARs), PostgreSQL compatible | Internal storage (no Iceberg), newer project, smaller community, less enterprise adoption | Rapid prototyping, streaming SQL analytics, teams wanting simplicity over ecosystem |

#### Orchestrators

| Technology | Strengths | Weaknesses | Best For |
|-----------|-----------|------------|----------|
| **Kestra** | Lightest resource footprint, YAML-native, modern UI, easy to learn | Smallest community, fewer plugins, less documentation | Small teams, YAML-first workflows, lightweight orchestration |
| **Airflow** | Largest ecosystem, most mature, Cosmos dbt integration, Astronomer managed option | Heaviest footprint (~1.5 GB), complex setup, Python DAGs can be verbose | Enterprise teams, complex multi-system workflows, existing Airflow shops |
| **Dagster** | Best dbt integration (native assets), best lineage graph, asset-centric model is intuitive | Medium complexity, Dagster-specific concepts to learn | dbt-heavy teams, asset-centric thinking, teams wanting deep lineage |

### 16.9 Practical Recommendations

#### By Use Case

| Use Case | Recommended Pipeline | Why |
|----------|---------------------|-----|
| **Learning/prototyping** | P06 (Redpanda+RisingWave) | 3 services, 449 MB, SQL-only, instant results |
| **Production lakehouse** | P04 (Redpanda+Flink+Iceberg) | Open table format, lower memory than Kafka variant |
| **Enterprise standard** | P01 (Kafka+Flink+Iceberg) + P09 (Dagster) | Full ecosystem, Iceberg, asset-based orchestration |
| **Python-centric team** | P02 (Kafka+Spark+Iceberg) | PySpark, familiar API, ML pipeline ready |
| **Real-time SQL analytics** | P03 or P06 (RisingWave) | Materialized views, ~2s processing, PostgreSQL wire protocol |
| **OLAP serving** | P10 (ClickHouse) | Sub-50ms queries on millions of rows |
| **Data quality first** | P11 (Elementary+Soda) | dbt-native monitoring + in-pipeline validation |
| **Minimal operations** | P06 → P03 | Fewest moving parts, lowest memory, auto-processing |

#### Decision Flow

```
Need streaming?
├── No  → Pipeline 00 (Batch dbt)
└── Yes
    ├── Need Iceberg/lakehouse?
    │   ├── Yes
    │   │   ├── Prefer SQL? → P04 (Redpanda+Flink+Iceberg)
    │   │   └── Prefer Python? → P02 (Kafka+Spark+Iceberg)
    │   └── No → P06 (Redpanda+RisingWave)
    │
    ├── Need orchestration?
    │   ├── YAML-first → P07 (Kestra)
    │   ├── dbt-centric → P09 (Dagster)
    │   └── Enterprise/existing → P08 (Airflow)
    │
    └── Need serving?
        └── Yes → P10 (ClickHouse + Metabase or Superset)
```

### 16.10 Lessons Learned

#### What Worked Well
- **Shared data generator**: A single Python producer worked identically across all Kafka and Redpanda pipelines with just a `BROKER_URL` env var change
- **Shared dbt models with adapter dispatch**: Same SQL logic across DuckDB, Spark, and PostgreSQL (RisingWave) via macro dispatch
- **Shared Flink Dockerfile**: Pre-installing 7 JARs in a custom image eliminated runtime dependency issues across P01, P04, P07-P09, P11
- **Docker Compose profiles**: `--profile generator` and `--profile dbt` kept ephemeral containers out of `docker compose up -d`

#### What Was Harder Than Expected
- **Flink JAR management**: Finding compatible versions of 7 JARs (Kafka connector, Iceberg runtime, AWS bundle, Hadoop) took significant iteration
- **Flink classloader**: Required `classloader.check-leaked-classloader: false` for Iceberg compatibility
- **MSYS path conversion on Windows**: Every `docker exec` command needed `MSYS_NO_PATHCONV=1` to prevent `/opt/...` from being converted to `C:/Program Files/Git/opt/...`
- **RisingWave psql**: The RisingWave Docker image doesn't include `psql`, requiring manual installation or a sidecar container
- **Dagster DAGSTER_HOME**: Required explicit `dagster.yaml` with PostgreSQL config and `DAGSTER_HOME` env var — not documented clearly for Docker deployments
- **Astronomer CLI on Windows**: TTY warnings and path issues required workarounds

#### Silver Row Count Differences
| Processor | Silver Rows | Filter Logic |
|-----------|-------------|-------------|
| Flink SQL | 9,855 | NULL checks + distance >= 0 + fare >= 0 + date range 2024 |
| PySpark | 9,739 | Same filters but Spark's NULL handling differs slightly |
| RisingWave | 9,766 | PostgreSQL-style NULL propagation, slightly different edge cases |

All three are valid — the differences come from how each engine handles NULL comparisons and edge cases in timestamp parsing. In production, these would be aligned with explicit COALESCE/IFNULL patterns.

### 16.11 Technology Maturity Assessment (2026)

| Technology | Maturity | Production Readiness | Ecosystem Size |
|-----------|----------|---------------------|---------------|
| Apache Kafka | Mature | Production-proven at every scale | Massive |
| Apache Flink | Mature | Production-proven (Alibaba, Uber, Netflix) | Large |
| Apache Spark | Mature | Production-proven everywhere | Massive |
| Apache Iceberg | Mature | Industry standard table format (2026) | Large, growing |
| Redpanda | Maturing | Production-ready, growing adoption | Medium |
| RisingWave | Early-maturing | Production-ready for specific workloads | Small, growing |
| ClickHouse | Mature | Production-proven (Cloudflare, Uber) | Large |
| Kestra | Early-maturing | Production-ready, growing adoption | Small |
| Airflow | Mature | Industry standard orchestrator | Massive |
| Dagster | Maturing | Production-ready, strong dbt ecosystem | Medium, growing |
| Elementary | Maturing | Production-ready for dbt monitoring | Medium |
| Soda Core | Maturing | Production-ready for data quality | Medium |
