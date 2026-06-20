# Wiki Index

Last compiled: 2026-06-19T21:36:20Z
Articles: 36 | Sources: 19 | Outputs: 19

## Concepts
- [Complex Event Processing (CEP)](wiki/concepts/cep.md) — Flink's complex event processing library for detecting patterns in event streams. Tags: flink, cep, pattern-matching, event-processing.
- [DataStream API](wiki/concepts/datastream-api.md) — Flink's core API for stream and batch processing: transformations, windows, state, and time semantics. Tags: flink, datastream, streaming, batch.
- [Event-Driven Architecture](wiki/concepts/event-driven-architecture.md) — Architecture style built around asynchronous event production and consumption. Tags: architecture, events, decoupling, streaming.
- [Flink Architecture](wiki/concepts/flink-architecture.md) — Flink's runtime architecture: JobManager/TaskManager model, dashboard, and credit-based network flow control. Tags: flink, architecture, dashboard, network-stack.
- [Flink Cluster Scaling](wiki/concepts/flink-cluster-scaling.md) — Horizontal and vertical scaling of Flink clusters: adding TaskManagers, adjusting slots, monitoring, and rollback. Tags: flink, scaling, taskmanager, slots, performance, operations.
- [Flink Cluster Sizing](wiki/concepts/flink-cluster-sizing.md) — Guidelines for sizing Flink clusters based on workload complexity, throughput, state size, and memory allocation. Tags: flink, sizing, resources, memory, performance, operations.
- [Flink Deployment Approaches](wiki/concepts/flink-deployment-approaches.md) — Four deployment methods: local binary, Docker, Kubernetes, and Confluent Cloud. Tags: flink, deployment, docker, kubernetes, confluent-cloud, getting-started.
- [Flink Disaster Recovery](wiki/concepts/flink-disaster-recovery.md) — Flink DR patterns (active-active and active-passive), checkpoint/savepoint management, and deployment-specific recovery strategies. Tags: flink, disaster-recovery, checkpoints, savepoints, high-availability, operations.
- [Flink K8s Deployment](wiki/concepts/flink-k8s-deployment.md) — Deploying Flink on Kubernetes via FKO/CMF: session vs application modes, environments, catalogs, compute pools. Tags: flink, kubernetes, k8s, deployment, cmf, fko, session-cluster, application-mode, checkpoint, savepoint, catalog.
- [Flink Keyed Aggregations](wiki/concepts/flink-keyed-aggregations.md) — KeyBy, sum/avg/min/max, rollup/cube, multi-stage aggregations, and GROUPING SETS in Flink SQL. Tags: flink, aggregation, keyby, grouping-sets, rollup, streaming-sql.
- [Flink Process Functions](wiki/concepts/flink-process-functions.md) — Low-level Flink APIs: ProcessFunction, KeyedProcessFunction, timers, and side outputs. Tags: flink, processfunction, timers, side-output, event-time.
- [Flink Process Table Function](wiki/concepts/flink-process-table-function.md) — PTFs: Flink's most powerful SQL/Table API function type for stateful N-to-M row transformations. Tags: flink, ptf, sql, udf, stateful-processing, table-api.
- [Flink SQL Changelog Modes](wiki/concepts/flink-sql-changelog-modes.md) — Three changelog modes (append, upsert, retract) for persisting dynamic table changes. Tags: flink, sql, changelog, upsert, retract, append, streaming.
- [Flink SQL Client](wiki/concepts/flink-sql-client.md) — CLI tool for writing and submitting SQL programs to Flink clusters. Tags: flink, sql, sql-client, cli, confluent.
- [Flink SQL DDL](wiki/concepts/flink-sql-ddl.md) — Flink SQL DDL patterns: CREATE TABLE, CTAS, primary keys, partitioning, watermarks. Tags: flink, sql, ddl, create-table, watermarks.
- [Flink SQL DML](wiki/concepts/flink-sql-dml.md) — Flink SQL DML patterns: streaming SELECT, filtering, joins, snapshot queries. Tags: flink, sql, dml, streaming, insert, select.
- [Flink SQL Dynamic Tables](wiki/concepts/flink-sql-dynamic-tables.md) — Flink SQL dynamic tables: continuously updated tables backed by streams. Tags: flink, sql, dynamic-table, streaming, materialized-view.
- [Flink SQL Materialized Tables](wiki/concepts/flink-sql-materialized-tables.md) — Flink SQL Materialized Tables: automated lifecycle management with CREATE OR ALTER. Tags: flink, sql, materialized-table, ci-cd, gitops, data-freshness.
- [Flink SQL Primary Key and Partitioning](wiki/concepts/flink-sql-primary-key-partitioning.md) — Using PRIMARY KEY and PARTITION BY in Flink SQL for upsert semantics and state deduplication. Tags: flink, sql, primary-key, partitioning, upsert, state.
- [Flink SQL Statement Sets](wiki/concepts/flink-sql-statement-sets.md) — Multi-sink SQL pipelines with EXPLAIN and SHOW statements for debugging. Tags: flink, sql, statement-set, multi-sink.
- [Flink SQL UDFs](wiki/concepts/flink-sql-udfs.md) — User-defined functions for Flink SQL: scalar, table, aggregate, table aggregate. Tags: flink, sql, udf, table-api, java, pyflink.
- [Flink SQL — Window Functions](wiki/concepts/flink-sql-window-functions.md) — TUMBLE/HOP/SESSION/Sliding windows with OVER clauses for real-time analytics. Tags: flink, sql, windowing, analytics.
- [Flink Stateful Functions](wiki/concepts/flink-stateful-functions.md) — Flink-based framework combining stream processing with stateful computation patterns. Tags: flink, stateful-functions.

## Recent Outputs
- [Cluster & Environment Management](wiki/summaries/cluster_mgt.md) — Cookbook chapter covering Flink cluster sizing, provisioning, scaling, and disaster recovery strategies.