---
title: "Apache NiFi"
created: 2026-06-10
updated: 2026-06-11
sources: [raw/fitforpurpose.md]
related: [Apache Flink, Data Ingestion, Data Routing, Event-Driven Architecture]
tags: [nifi, data-ingestion, data-routes, logistics]
---

# Apache NiFi

Apache NiFi is a data logistics platform focused on ingestion, routing, transformation, and delivery of data from Point A to Point B. It is fundamentally different from Flink in scope: NiFi moves data, Flink computes on data.

## Primary Characteristics

- **Visual interface**: Drag-and-drop UI for building data flows — no-code/low-code approach.
- **Data movement**: Specializes in moving, routing, and securing data across diverse sources and destinations.
- **Latency**: Low latency (seconds) — suitable for batch-level data transfer, not real-time computation.
- **Historical lineage**: Excellent built-in data tracking and provenance.
- **Talent**: Designed for data administrators and IT generalists, not requiring deep streaming programming skills.

## Technical Architecture

NiFi operates on a bounded event-by-event queue model:

- **FlowFile model**: Data is encapsulated as a FlowFile with two parts — attributes (key-value metadata in JVM memory) and content (payload stored on disk in the Content Repository).
- **Thread-driven concurrency**: Configurable concurrent tasks on individual processors via the GUI.
- **Fault tolerance**: Write-ahead log repositories (FlowFile Repository and Provenance Repository) ensure data safety on local disk even after node crashes.
- **State management**: Primarily local to components, with external caches (Redis, HBase, DistributedMapCache). Stateless execution is supported for short-lived cloud-native jobs. NiFi is not designed for stateful processing beyond deduplication and basic caching.

## Flow Management

- Uses structured JSON for flow definitions, with Git-based flow management.
- Supports native Kubernetes deployment via ConfigMaps and native leases for leader election (no ZooKeeper dependency).
- Custom components written in Java bundled as .nar (NiFi Archive) files with strict classloader isolation.
- Native Python processor extensions via `uv` tooling, enabling pandas, scikit-learn, LLM/Vector DB integration without Java.

## Complementarity with Flink

In a modern data architecture, NiFi and Flink rarely compete:

1. NiFi gathers and cleans messy data from various corporate silos.
2. NiFi feeds clean topics within Apache Kafka.
3. Flink reads those topics to perform heavy calculations and real-time analytics.

## Typical Use Cases

- Feeding data lakes
- System migration
- Data ingestion from diverse sources (e.g., 100 retail stores to a cloud data lake)

## Sources
- [Fit for Purpose](../summaries/fitforpurpose.md)

## Related
- [Apache Flink](apache-flink.md)
- [Event-Driven Architecture](event-driven-architecture.md)