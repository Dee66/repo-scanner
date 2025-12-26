# Schema Compatibility Guidance

This document describes the compatibility policy for the scanner's machine-readable
JSON outputs and how schema versions are managed.

Policy summary:

- The authoritative schema files live under `docs/schemas/` and the active
  schema version is recorded in `docs/schemas/VERSION`.
- Generated outputs MUST include `governance.schema_version` set to the value
  in `docs/schemas/VERSION` when the schema declares that property.
- CI and local tests will validate outputs against `docs/schemas/scan_report.schema.json`.
- When changing a schema in a non-backwards-compatible way, update `docs/schemas/VERSION`
  and follow the release checklist in `RELEASE.md`.

Developer checklist:

1. Update `docs/schemas/scan_report.schema.json` (or other schema files).
2. Bump `docs/schemas/VERSION` (semantic versioning recommended).
3. Run `pytest tests/test_schema_version_compatibility.py` to ensure generated
   outputs include the new `governance.schema_version` and validate against the schema.
4. If schema validation fails, use `tools/triage_schema_failures.py` to extract
   actionable TODOs for detector fixes or schema adjustments.

Compatibility note:

The schema validator uses `jsonschema` when available and falls back to a
lightweight required-key checker. Always prefer running CI with `jsonschema`
installed to get full diagnostics.
