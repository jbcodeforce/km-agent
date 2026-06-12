# Fit For Purpose

This document compares Apache Flink against three commonly co-used technologies: **Kafka Streams**, **Apache NiFi**, and **Rule Engines**. The central thesis is that these tools are complementary — each excels in a different domain, and modern data architectures combine them rather than choosing a single solution.

## Key Data Points
- **Flink vs Kafka Streams**: Flink is a full streaming platform with HA, fault tolerance via incremental snapshots, multi-language APIs (Java/Python/SQL), and support for both batch and stream processing. Kafka Streams is a Java-only library embedded in applications, simpler for Kafka-to-Kafka pipelines but replays all messages on failure.
- **Flink vs NiFi**: NiFi specializes in data logistics — secure ingestion, routing, and transformation with a visual drag-and-drop interface. Flink specializes in data computation — high-speed analytics on live streams with millisecond latency. A common pattern: NiFi cleans and feeds data into Kafka, which Flink reads for heavy processing.
- **Flink vs Rule Engines**: Rule engines (Rete Algorithm) automate if-then-else business logic with externalized, testable, auditable rules. Flink handles time-windowed stream processing and complex event patterns. They are complementary: Flink detects situations, rule engines decide next-best-action.

## Connection to Other Concepts
- The **Flink vs Kafka Streams** concept article covers the detailed technology comparison.
- The **Apache NiFi** concept article covers NiFi's data logistics role.
- The **Rule Engines** concept article covers CEP-rule engine integration patterns.

## Sources
- [Fit For Purpose](../summaries/fitforpurpose.md)