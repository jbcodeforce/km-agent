---
title: "Apache Flink"
created: 2026-06-10
updated: 2026-06-11
sources: [raw/fitforpurpose.md]
related: [Apache Kafka, Apache NiFi, Complex Event Processing, State Management, Streaming Architecture, Kafka Streams]
tags: [flink, streaming, computation, architecture]
---

# Apache Flink

Apache Flink is a complete streaming computation system designed for high-speed, complex processing of data streams in real time. It supports both bounded (batch) and unbounded (streaming) data streams.

## Core Capabilities

- **Fault tolerance and HA**: Built-in high availability, fault tolerance, and self-monitoring across a variety of deployment models including Kubernetes.
- **Multiple sources and sinks**: Unlike Kafka Streams, Flink is not limited to Kafka — it supports diverse input and output connectors.
- **Layered API**: Supports multiple programming languages, with Java, Python, and SQL being the most popular.
- **Complex Event Processing (CEP)**: Built-in pattern detection capabilities for identifying sequences and correlations of events over time windows.
- **State management**: Restores state after failures from recent incremental snapshots, avoiding the need to replay all messages.
- **Job execution model**: User stream processing code is deployed and run as a **job** within the Flink cluster, orchestrated by the JobManager across TaskManagers.

## Watermarking for Late Data

Flink handles late-arriving data through a watermark mechanism. Developers must implement how to extract timestamps from Kafka records (e.g., via `KafkaDeserializationSchema<T>`) and define watermarks to track event time progress. This is less straightforward than Kafka Streams, which handles late arrival more natively.

## Integration with Rule Engines

Flink can integrate with rule engines in two ways:
1. **Remote decision service**: Flink calls a rule engine via REST endpoint within the processing flow. This separates business logic from streaming logic but adds network latency.
2. **Embedded rule engine**: The rule engine and ruleset run inside the Flink application, reducing latency and avoiding complexity from retries, circuit breakers, and failover.

## Complementarity with Other Tools

- **vs. Kafka Streams**: Flink is the more complete, cluster-managed system; Kafka Streams is a lightweight, embeddable Java library.
- **vs. Apache NiFi**: NiFi handles data logistics (ingestion, routing); Flink handles heavy computation and analytics. They are complementary — NiFi cleans and routes data, Flink processes it.
- **vs. Rule Engines**: Flink detects complex situations and patterns; rule engines provide prescriptive business logic for decision-making.

## Sources
- [Fit for Purpose](../summaries/fitforpurpose.md)

## Related
- [Kafka Streams](kafka-streams.md)
- [Apache NiFi](apache-nifi.md)
- [Complex Event Processing](complex-event-processing.md)
- [Rule Engines](rule-engines.md)