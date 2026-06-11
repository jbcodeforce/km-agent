# Fit for Purpose

## Main Thesis
This document provides a practical comparison guide to help architects choose the right tool for different parts of a streaming data and real-time processing architecture. It covers three key comparison areas: Kafka Streams vs. Flink, Apache NiFi vs. Flink, and Rule Engines vs. Flink's CEP capabilities.

## Key Findings

### Kafka Streams vs. Flink
Flink is a complete streaming computation system with built-in high availability, fault tolerance, and self-monitoring. Kafka Streams is a library that embeds directly into Java applications, leaving deployment to the developer. Key differences:

- **Deployment model**: Flink runs jobs in a cluster; Kafka Streams runs inside Java applications.
- **Data sources/sinks**: Flink supports multiple sources and sinks beyond Kafka; Kafka Streams is Kafka-centric.
- **State restoration**: Flink restores from incremental snapshots; Kafka Streams restores by replaying messages.
- **Programming flexibility**: Flink supports Java, Python, and SQL; Kafka Streams is Java-only.
- **Stream type**: Flink handles both bounded (batch) and unbounded streams; Kafka Streams handles streams only.
- **Late data**: Kafka Streams handles late arrival more easily; Flink requires watermark implementation.
- **Complex Event Processing**: Flink has built-in CEP capabilities for pattern detection; Kafka Streams does not.

### NiFi vs. Flink
These tools address different layers of the data architecture:
- **NiFi** is for data logistics — ingestion, routing, transformation, and delivery with a visual drag-and-drop interface.
- **Flink** is for heavy computation — complex analytics on live data streams with millisecond latency.
- In practice, they complement each other: NiFi gathers and cleans messy data, feeds clean Kafka topics, and Flink reads those topics for heavy calculations.

### Rule Engines vs. Flink
Rule engines (implementing the Rete Algorithm) and Flink's CEP serve complementary purposes:
- **Rule engines** handle prescriptive business logic (`if...then` constructs), providing transparent decision logic that can be tested and maintained separately from code.
- **Flink** handles complex event detection and time-windowing logic.
- Two integration patterns are described:
  1. Flink calls a remote rule engine via REST (separation of concerns, higher latency).
  2. Rule engine embedded inside the Flink application (lower latency, reduced complexity from retries and circuit breakers).

## Key Data Points
- NiFi processes data at second-level latency; Flink at millisecond-level latency.
- NiFi uses a bounded event-by-event queue model with FlowFiles (attributes in memory, content on disk).
- Flink uses JobManager orchestrating TaskManagers, coordinated via Kubernetes scheduler.
- Expert systems based on rule engines help automate human decisions while maintaining logic transparency.