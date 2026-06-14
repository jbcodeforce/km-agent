# Wiki Lint Report

Run: 2026-06-12T08:45:48Z
Articles checked: 5 concepts + 1 output

## Findings

### Critical

- **Missing concept: Apache Kafka** — Referenced in `related` fields by 2 articles (apache-flink.md, kafka-streams.md) and mentioned throughout the body of multiple articles. Given that the entire wiki revolves around Kafka-centric streaming architectures, a foundational concept article for Apache Kafka is essential. **Action**: Create `wiki/concepts/apache-kafka.md`.

- **Missing concept: Event-Driven Architecture** — Referenced in `related` fields by 3 articles (apache-nifi.md, complex-event-processing.md, rule-engines.md) and linked as a markdown link in the body of apache-nifi.md (`[Event-Driven Architecture](event-driven-architecture.md)`). This is a broken link in the NiFi article. **Action**: Create `wiki/concepts/event-driven-architecture.md`.

- **Missing concept: Streaming Architecture** — Referenced in `related` fields by 2 articles (apache-flink.md, kafka-streams.md). A high-level architectural concept that would provide useful context for the platform comparisons. **Action**: Create `wiki/concepts/streaming-architecture.md`.

### Warnings

- **Missing concept: State Management** — Referenced in `related` of apache-flink.md. Both Flink and NiFi articles discuss state management in their bodies but no dedicated concept exists. **Action**: Create `wiki/concepts/state-management.md` or fold into Streaming Architecture.

- **Missing concept: Time Windowing** — Referenced in `related` of complex-event-processing.md. Time windowing is a core CEP concept discussed in both the CEP and Rule Engines articles. **Action**: Create `wiki/concepts/time-windowing.md` or merge into the CEP article.

- **Missing concept: Data Ingestion** — Referenced in `related` of apache-nifi.md but covered primarily within the NiFi article itself. **Action**: Create standalone article if scope warrants, or remove from related.

- **Missing concept: Data Routing** — Referenced in `related` of apache-nifi.md but not a distinct concept outside of NiFi. **Action**: Remove from related or create if broader scope is desired.

- **Missing concept: Expert Systems** — Referenced in `related` of rule-engines.md. The Rule Engines article covers this as historical context. **Action**: Either create a brief Expert Systems article or remove from related.

- **`fitforpurpose.md` is its own source** — The Fit For Purpose summary lists itself as a source (`[Fit For Purpose](../summaries/fitforpurpose.md)`). This is a self-referential citation loop. **Action**: Remove self-reference from the Sources section.

- **Redundant event flow diagrams** — The event-driven architecture flow (`Event Sources → Kafka → Flink (CEP detection) → Rule Engine → Kafka → ...`) appears in both `complex-event-processing.md` and `rule-engines.md` with nearly identical content. **Action**: Consider consolidating or using cross-references instead of duplicating diagrams.

### Suggestions

- **Enrich `fitforpurpose.md`** — At ~230 words, the summary article is close to the thin-article threshold. It could benefit from a brief architectural decision framework (e.g., "when to use which combination") rather than just repeating comparisons.

- **Add a "Decision Guide" output** — The wiki has strong concept articles but no actionable output like a "How to Choose" guide. A decision matrix or architecture pattern guide would strengthen the output layer.

- **Cross-reference Kafka Streams → NiFi** — The Kafka Streams article links to NiFi in related but the relationship between these two tools is not discussed in the body of either article.

- **Tag inconsistency** — The NiFi article uses tag `data-routes` while the index lists `data-routing`. Consider normalizing.

- **Single source of truth** — All 5 concept articles and the summary derive from a single source (`raw/fitforpurpose.md`). This creates fragility — if the source changes, all articles need updating. Consider diversifying sources.

- **Add "Last Updated" to Fit For Purpose** — The summary output has no frontmatter or update date. Consider adding metadata for consistency.

## Summary
3 critical | 8 warnings | 6 suggestions