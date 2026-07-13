# Wiki Index

Last compiled: 2026-06-20T13:22:00Z
Articles: 62 | Sources: 34 | Outputs: 34

## Concepts
- [Agentic AI Architecture](wiki/concepts/agentic-ai-architecture.md) — Architecture patterns for AI agents: tool calling, memory, and workflow orchestration. Tags: ai, agents, architecture, tools, memory, orchestration.
- [Apache Flink Core Concepts](wiki/concepts/flink-core-concepts.md) — Comprehensive overview of Flink's core concepts: architecture, state, windowing, watermarks, and data skew. Tags: flink, concepts, stream-processing, state, windowing, watermarks, architecture, data-skew.
- [Apache Flink](wiki/concepts/apache-flink.md) — Overview of Apache Flink as a distributed stream processing framework. Tags: flink, streaming, distributed, framework.
- [Apache Hive](wiki/concepts/apache-hive.md) — Distributed data warehouse on Hadoop with SQL interface, pluggable engines, LLAP, and ACID support. Tags: hive, data-warehouse, OLAP, Hadoop, Metastore, schema-on-read, LLAP.
- [Apache NiFi](wiki/concepts/apache-nifi.md) — Data flow automation tool for routing, transforming, and delivering data. Tags: nifi, data-flow, etl.
- [Center of Excellence for Stream Processing](wiki/concepts/stream-processing-coe.md) — Organizational structure for governing stream processing: architecture, security, multi-tenancy, deployment best practices, sizing, and community development. Tags: coe, methodology, governance, stream-processing.
- [Complex Event Processing (CEP)](wiki/concepts/cep.md) — Flink's complex event processing library for detecting patterns in event streams. Tags: flink, cep, pattern-matching, event-processing.
- [Confluent Cloud Flink](wiki/concepts/confluent-cloud-flink.md) — Confluent Cloud's serverless, managed Flink service with auto-inference, Autopilot, and tight Kafka integration. Tags: flink, confluent-cloud, managed-service, serverless, sql, streaming, operations, kafka.
- [Confluent Manager for Flink](wiki/concepts/confluent-manager-for-flink.md) — Kubernetes operator providing job lifecycle management, RBAC, REST APIs, and metadata storage for Flink on Confluent Platform. Tags: flink, confluent-platform, cmf, kubernetes, operations, rbac.
- [Confluent Platform Flink](wiki/concepts/confluent-platform-flink.md) — Confluent's self-managed, Kubernetes-only Flink distribution with SQL, DataStream, and ProcessFunction support plus CMF. Tags: flink, confluent-platform, kubernetes, managed-distribution, operations.
- [Confluent Tableflow](wiki/concepts/confluent-tableflow.md) — Confluent Cloud service materializing Kafka topics as Iceberg/Delta Lake tables on S3 for lakehouse analytics. Tags: flink, operations, tableflow, iceberg, lakehouse, kafka.
- [DataStream API](wiki/concepts/datastream-api.md) — Flink's core API for stream and batch processing: transformations, windows, state, and time semantics. Tags: flink, datastream, streaming, batch.
- [Data as a Product](wiki/concepts/data-as-a-product.md) — Architectural paradigm treating datasets as self-contained products with clear ownership, quality metrics, and consumer-focused interfaces. Tags: data-product, data-mesh, streaming, methodology, flink, governance.
- [Data Contracts](wiki/concepts/data-contracts.md) — Formal agreements between Flink producers and consumers covering schema, watermark strategies, lateness tolerance, and quality guarantees. Tags: data-contracts, streaming, schema, slo, quality, flink.
- [Data Mesh](wiki/concepts/data-mesh.md) — Organizational paradigm restructuring data platforms from centralized lakes to domain-oriented decentralized networks of data products. Tags: data-mesh, methodology, domain-driven-design, decentralized, governance.
- [DBT Confluent Adapter](wiki/concepts/dbt-confluent-adapter.md) — DBT adapter for Confluent enabling dbt transformations on Flink SQL. Tags: dbt, confluent, flink, sql.
- [DBT Materializations](wiki/concepts/dbt-materializations.md) — DBT materialization types and configurations for Flink. Tags: dbt, materializations, flink.
- [DBT Snapshots SCD2](wiki/concepts/dbt-snapshots-scd2.md) — DBT snapshot strategy for Slowly Changing Dimensions Type 2. Tags: dbt, snapshots, scd2, dimensions.
- [DBT](wiki/concepts/dbt.md) — Data Build Tool for transforming data in warehouses. Tags: dbt, transformation, sql, analytics.
- [Dual-Nature Storage](wiki/concepts/dual-nature-storage.md) — Serving a single Flink data product simultaneously as live Kafka stream and historical Iceberg table for unified streaming/batch access. Tags: dual-nature, streaming, batch, iceberg, kafka, tableflow, flink.
- [Event-Driven AI Agents](wiki/concepts/event-driven-ai-agents.md) — AI agents triggered by events in streaming data rather than user requests. Tags: ai, agents, event-driven, streaming.
- [Event-Driven Architecture](wiki/concepts/event-driven-architecture.md) — Architecture style built around asynchronous event production and consumption. Tags: architecture, events, decoupling, streaming.
- [Exactly-Once Delivery](wiki/concepts/exactly-once-delivery.md) — Semantic guarantee that each event is processed exactly once in distributed stream processing. Tags: exactly-once, flink, kafka, transactions, idempotency.
- [Flink AI and ML Functions](wiki/concepts/flink-ai-ml.md) — Flink 2.2.0 AI/ML capabilities: ML_PREDICT for LLM inference and VECTOR_SEARCH for real-time vector similarity search. Tags: flink, ai, ml, llm, vector-search, sql.
- [Flink Architecture](wiki/concepts/flink-architecture.md) — Flink's runtime architecture: JobManager/TaskManager model, dashboard, and credit-based network flow control. Tags: flink, architecture, dashboard, network-stack.
- [Flink Architecture Overview](wiki/concepts/flink-architecture-overview.md) — High-level overview of Flink's distributed architecture and components. Tags: flink, architecture, overview, distributed.
- [Flink Classical Deployment Pattern](wiki/concepts/flink-classical-deployment-pattern.md) — Traditional YARN/standalone deployment model for Flink clusters. Tags: flink, deployment, yarn, standalone, classical.
- [Flink Cluster Scaling](wiki/concepts/flink-cluster-scaling.md) — Horizontal and vertical scaling of Flink clusters: adding TaskManagers, adjusting slots, monitoring, and rollback. Tags: flink, scaling, taskmanager, slots, performance, operations.
- [Flink Cluster Sizing](wiki/concepts/flink-cluster-sizing.md) — Guidelines for sizing Flink clusters based on workload characteristics, resource requirements, and scaling considerations. Tags: flink, sizing, resources, planning.
- [Flink Data Skew](wiki/concepts/flink-data-skew.md) — Handling data skew in Flink jobs: detection, prevention, and remediation strategies. Tags: flink, skew, performance, optimization.
- [Flink DataStream API](wiki/concepts/flink-datastream-api.md) — Detailed guide to Flink's DataStream API for stream and batch processing. Tags: flink, datastream, api, streaming, batch.
- [Flink Deduplication](wiki/concepts/flink-deduplication.md) — Strategies for deduplicating events in Flink streaming pipelines. Tags: flink, deduplication, exactly-once, idempotency.
- [Flink Deployment Approaches](wiki/concepts/flink-deployment-approaches.md) — Different approaches to deploying Flink applications in production. Tags: flink, deployment, production, strategies.
- [Flink Deployment Models](wiki/concepts/flink-deployment-models.md) — Overview of Flink deployment models: session, application, and per-job clusters. Tags: flink, deployment, models, session, application.
- [Flink Disaster Recovery](wiki/concepts/flink-disaster-recovery.md) — Disaster recovery strategies for Flink clusters and jobs. Tags: flink, disaster-recovery, backup, restore, high-availability.
- [Flink Event Time](wiki/concepts/flink-event-time.md) — Event time processing in Flink: handling late events, watermarks, and time attributes. Tags: flink, event-time, watermarks, late-events.
- [Flink Exactly-Once Sinks](wiki/concepts/flink-exactly-once-sinks.md) — Implementing exactly-once semantics with Flink sinks and external systems. Tags: flink, exactly-once, sinks, transactions, two-phase-commit.
- [Flink Fault Tolerance](wiki/concepts/flink-fault-tolerance.md) — Flink's fault tolerance mechanism: checkpoints, savepoints, and recovery. Tags: flink, fault-tolerance, checkpoints, savepoints, recovery.
- [Flink First Java Applications](wiki/concepts/flink-first-java-applications.md) — Getting started with Flink using Java: word count and basic examples. Tags: flink, java, getting-started, word-count.
- [Flink Governance](wiki/concepts/flink-governance.md) — Governance, change management, and best practices for Flink operations. Tags: flink, governance, change-management, best-practices.
- [Flink Job Lifecycle](wiki/concepts/flink-job-lifecycle.md) — Complete lifecycle management for Flink jobs: deployment, scaling, monitoring, and upgrades. Tags: flink, job-lifecycle, deployment, monitoring, upgrades.
- [Flink K8s Deployment](wiki/concepts/flink-k8s-deployment.md) — Deploying Flink on Kubernetes: native integration, operator, and best practices. Tags: flink, kubernetes, deployment, operator, native.
- [Flink K8s Tuning](wiki/concepts/flink-k8s-tuning.md) — Tuning Flink on Kubernetes: resource sizing, memory layout, parallelism, and performance optimization. Tags: flink, kubernetes, tuning, resources, memory, performance.
- [Flink Kafka Connector](wiki/concepts/flink-kafka-connector.md) — Integrating Flink with Kafka: reliable ingestion, partitioning, and Exactly-Once semantics. Tags: flink, kafka, connector, streaming.
- [Flink Query Profiler](wiki/concepts/flink-query-profiler.md) — Flink SQL Query Profiler for real-time visual performance dashboards and bottleneck identification. Tags: flink, sql, profiler, performance, observability.
- [Flink Release Timeline](wiki/concepts/flink-release-timeline.md) — Timeline of major Apache Flink and Confluent Flink releases from 2025–2026. Tags: flink, releases, timeline, versions.
- [Flink SQL Materialized Tables](wiki/concepts/flink-sql-materialized-tables.md) — Materialized Tables in Flink SQL automate offset bookkeeping and job orchestration through a single SQL statement. Tags: flink, sql, materialized-tables, confluent, automation.
- [Hive Metastore](wiki/concepts/hive-metastore.md) — Centralized metadata repository for big data cataloging shared by Hive, Spark, Presto, and Impala. Tags: hive, metastore, catalog, schema, HMS.
- [Open Table Format](wiki/concepts/open-table-format.md) — Open-source tabular data formats (Iceberg, Delta Lake) adding metadata layers for ACID guarantees and query performance on object storage. Tags: iceberg, delta-lake, lakehouse, open-table-format.
- [Snapshot Queries](wiki/concepts/snapshot-queries.md) — Fast batch-style queries across Kafka topics and Tableflow data, 50–100x faster for interactive analysis. Tags: flink, sql, snapshot, queries, confluent, performance.
- [Streaming Agents](wiki/concepts/streaming-agents.md) — Framework for building event-driven AI agents that observe, decide, and act in real-time within event streams. Tags: ai, agents, streaming, event-driven, flink.
- [Tableflow Integration](wiki/concepts/tableflow-integration.md) — Integration of Flink with Tableflow for upsert and DLQ support with Iceberg/Delta Lake. Tags: flink, tableflow, iceberg, delta-lake, upsert.

## Recent Outputs
- [Last Flink News](wiki/summaries/news-index.md) — Summary of major Flink news, releases, and feature updates through mid-2026.
- [Confluent Tableflow](wiki/summaries/cc-tableflow.md) — Cloud service materializing Kafka topics as Iceberg/Delta Lake tables for lakehouse analytics.
- [Confluent Cloud for Apache Flink](wiki/summaries/ccloud-flink.md) — Summary of Confluent Cloud's managed, serverless Flink service with Kafka integration, Autopilot, and SQL-only processing.
- [Confluent Platform for Flink](wiki/summaries/cp-flink.md) — Summary of Confluent's self-managed, Kubernetes-only Flink distribution with CMF, RBAC, and hybrid Kafka support.

## Summaries
- [Apache Flink Core Concepts](wiki/summaries/index.md) — Foundational concepts: architecture, state, windowing, event time, watermarks, and data skew.
- [Contributing to flink-studies Repository](wiki/summaries/contributing.md) — Contribution guidelines for the flink-studies project.
- [Flink Tuning on Kubernetes](wiki/summaries/k8s_tuning.md) — Day-2 tuning guide for Flink on K8s.
- [Moving to a Data as a Product Architecture](wiki/summaries/data_as_a_product.md) — Methodology critiquing medallion architecture and advocating Data as a Product principles.
- [Governance, Change Management & Best Practices](wiki/summaries/governance.md) — Governance overview for Flink operations.
- [Confluent Cloud for Apache Flink](wiki/summaries/ccloud-flink.md) — Summary of Confluent Cloud's managed, serverless Flink service with Kafka integration, Autopilot, and SQL-only processing.
- [Apache Hive](wiki/summaries/hive.md) — Distributed Hadoop data warehouse with SQL interface, pluggable engines, LLAP, and ACID support.