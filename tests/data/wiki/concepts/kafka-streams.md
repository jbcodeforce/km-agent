---
title: "Kafka Streams"
created: 2026-06-11
updated: 2026-06-11
sources: [raw/fitforpurpose.md]
related: [Apache Flink, Apache Kafka, Streaming Architecture]
tags: [kafka-streams, streaming, java, library]
---

# Kafka Streams

Kafka Streams is a Java library that can be embedded within any standard Java application for stream processing. Unlike Apache Flink, it does not dictate a deployment method — it runs as part of the application code rather than as a cluster-managed job.

## Core Characteristics

- **Library, not platform**: Kafka Streams is embedded within Java applications rather than running as a separate cluster service.
- **Kafka-centric**: Designed specifically for Kafka-to-Kafka processing pipelines. It is not designed for multiple sources and sinks.
- **Java only**: No official support for Python or SQL — all processing logic must be written in Java.
- **Stream only**: Handles unbounded data streams. Does not support batch processing.
- **Simpler setup**: Easier to define a pipeline for Kafka records and do the consume-process-produce loop.

## Comparison with Flink

| Dimension | Kafka Streams | Apache Flink |
|-----------|---------------|--------------|
| **Type** | Library embedded in app | Full streaming platform |
| **Deployment** | Within Java application | Job in Flink cluster |
| **Fault tolerance** | Replays all messages from Kafka | Restores from incremental snapshots |
| **Coordination** | Leverages Kafka cluster | JobManager orchestrates TaskManagers |
| **Language** | Java only | Java, Python, SQL |
| **Sources/Sinks** | Kafka only | Multiple connectors |
| **Processing mode** | Stream only | Stream and batch |
| **CEP** | Not built-in | Built-in Complex Event Processing |
| **Late data** | Easier native support | Watermark-based, developer-defined |
| **Scaling** | Horizontal via k8s, bounded by partitions | Horizontal via cluster managers |

## When to Use Kafka Streams

- Simple Kafka-to-Kafka pipelines where Flink's full platform is overkill.
- Teams already comfortable with Java and the Kafka ecosystem.
- When simplicity of deployment and setup is valued over advanced capabilities.

## Sources
- [Fit for Purpose](../summaries/fitforpurpose.md)

## Related
- [Apache Flink](apache-flink.md)
- [Apache NiFi](apache-nifi.md)
- [Complex Event Processing](complex-event-processing.md)