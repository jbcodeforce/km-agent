# tests/data

Curated, small copies of real [flink-studies](https://github.com/jbcodeforce/flink-studies)
markdown used as the raw corpus for integration tests (`tests/it/`). Each file under
`raw/` has km-agent raw YAML frontmatter (added via `scripts/add_raw_frontmatter.py`) and
is tracked in `raw/.manifest.json`. Keep files small; they exist for deterministic,
fast compile/query tests, not as a faithful mirror of the source repo.
