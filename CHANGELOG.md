# Changelog

## Unreleased

- chore: Stabilize determinism and evidence provenance
  - Canonicalize and deduplicate repository file lists before counting to ensure deterministic `structure.file_counts`.
  - Normalize evidence objects and populate deterministic provenance (`line_range`, `byte_range`, `repo_commit`).
  - Recompute determinism verification after final output normalization so `determinism_verification.determinism_hash` reflects the written output.
  - Add schema version wiring and schema validation integration for machine-readable outputs.
  - Tools: determinism harness and JSON-diff utilities added under `tools/` for verification and triage.

Full test suite: 83 passed, 1 warning.
