# Release Checklist

Before cutting a release tag you must complete these steps and ensure CI passes:

1. Run unit and integration tests: `pytest -q` — all tests must pass.
2. Schema validation: generated machine output must validate against `docs/schemas/scan_report.schema.json`.
   - Ensure `governance.schema_version` in outputs matches `docs/schemas/VERSION`.
3. Determinism verification: run the determinism harness (`tools/determinism_harness.py`) in lightweight mode
   and confirm `tmp_scan_output/determinism_report.json` shows `consistent: true`.
4. Performance budgets: ensure `tests/test_performance.py` passes and monitoring thresholds are met.
5. Update `CHANGELOG.md` with user-facing notes.
6. Bump package version and `docs/schemas/VERSION` if schemas are changed.

Automated checks (CI):
- CI job `Schema & Determinism Validation` verifies schema validation and runs a quick determinism check.

If any step fails, do not cut a release; open a PR with the fixes and reference this checklist.
