# Forensic Code-to-Spec Reconciliation — Forensic Report

Generated: 2025-12-26
Confidence: 0.85

## Executive summary
- Completed a leaf-level mapping from all public entry points (CLI subcommands and FastAPI routes) to implementation code and terminal sinks.
- Identified explicit product claims referencing "99.999% SME accuracy" and missing validation artifacts under `validation_data/`.
- Located unimplemented flows (git clone) and adapter stubs raising NotImplementedError.

## Contents
- Entry points (CLI)
- Entry points (API)
- Per-entry-point call chains (leaf-level)
- Terminal sinks (files, temp dirs, stdout, in-memory)
- Claims and validation artifacts
- TODOs / NotImplementedError locations
- Recommendations / next steps

---

## CLI entry points

### `scan`
- Handler: `handle_scan_command` — [src/cli.py](src/cli.py#L145-L219)
- Call chain (selected leaf-level entries):
  - `handle_scan_command` — [src/cli.py](src/cli.py#L145-L219)
  - `execute_pipeline` — [src/core/pipeline/analysis.py](src/core/pipeline/analysis.py#L91-L156)
  - `discover_repository_root` / `get_canonical_file_list` — [src/core/pipeline/repository_discovery.py](src/core/pipeline/repository_discovery.py#L13-L56) and [src/core/pipeline/repository_discovery.py](src/core/pipeline/repository_discovery.py#L87-L132)
  - pipeline stage examples (leaf analyzers): `analyze_repository_structure` — [src/core/pipeline/structural_modeling.py](src/core/pipeline/structural_modeling.py#L8-L40), `analyze_semantic_structure` — [src/core/pipeline/static_semantic_analysis.py](src/core/pipeline/static_semantic_analysis.py#L10-L40), `generate_decision_artifacts` — [src/core/pipeline/decision_artifact_generation.py](src/core/pipeline/decision_artifact_generation.py#L6-L70)
  - Output generation: `generate_primary_report`, `generate_machine_output`, `generate_executive_verdict` — [src/core/quality/output_contract.py](src/core/quality/output_contract.py#L190-L605)
- Terminal sinks:
  - File write: `scan_report.md` — [src/cli.py](src/cli.py#L196-L199)
  - File write: `verdict_report.md` — [src/cli.py](src/cli.py#L200-L205)
  - File write: `scan_report.json` — [src/cli.py](src/cli.py#L208-L212)
  - Stdout prints (progress/messages) — [src/cli.py](src/cli.py#L109-L141)
  - Output directory creation (`mkdir`) — [src/cli.py](src/cli.py#L165-L171)

---

### `bounty`
- Handler: `handle_bounty_command` — [src/cli.py](src/cli.py#L220-L373)
- Call chain (selected leaf-level entries):
  - `handle_bounty_command` — [src/cli.py](src/cli.py#L220-L373)
  - `execute_pipeline` — [src/core/pipeline/analysis.py](src/core/pipeline/analysis.py#L91-L156)
  - `BountyService.analyze_bounty_opportunity` — [src/services/bounty_service.py](src/services/bounty_service.py#L34-L96)
    - `_generate_maintainer_profile` → `generate_maintainer_profile` — [src/core/bounty/maintainer_profile_engine.py](src/core/bounty/maintainer_profile_engine.py#L578-L582)
    - `triage_bounty_profitability` — [src/core/bounty/profitability_triage.py](src/core/bounty/profitability_triage.py#L489-L496)
    - `generate_pr_for_bounty` — [src/core/bounty/pr_automation.py](src/core/bounty/pr_automation.py#L573-L579)
- Terminal sinks:
  - Batch results JSON: `bounty_batch_results.json` — [src/cli.py](src/cli.py#L336-L344)
  - Single assessment JSON: `bounty_assessment.json` — [src/cli.py](src/cli.py#L349-L352)
  - Bounty solution JSON: `bounty_solution.json` — [src/cli.py](src/cli.py#L355-L359)
  - PR content markdown: `pr_content.md` — [src/cli.py](src/cli.py#L362-L366)
  - Validator persistence (writes): `validation_data/bounty_validation_cases.json` — [src/core/bounty/accuracy_validator.py](src/core/bounty/accuracy_validator.py#L42-L78)

---

### `validate`
- Handler: `handle_validate_command` — [src/cli.py](src/cli.py#L374-L428)
- Call chain (selected leaf-level entries):
  - `handle_validate_command` — [src/cli.py](src/cli.py#L374-L428)
  - `BountyService.validate_bounty_accuracy` — [src/services/bounty_service.py](src/services/bounty_service.py#L100-L107)
  - `validate_bounty_accuracy` → `BountyAccuracyValidator` — [src/core/bounty/accuracy_validator.py](src/core/bounty/accuracy_validator.py#L356-L380)
  - `BountyAccuracyValidator.calculate_accuracy_metrics` — [src/core/bounty/accuracy_validator.py](src/core/bounty/accuracy_validator.py#L88-L180)
- Terminal sinks:
  - Validation report: `bounty_accuracy_report.md` — [src/cli.py](src/cli.py#L392-L398)
  - Metrics JSON: `bounty_accuracy_metrics.json` — [src/cli.py](src/cli.py#L411-L416)
  - Reads/writes `validation_data/*` directory — [src/core/bounty/accuracy_validator.py](src/core/bounty/accuracy_validator.py#L40-L78)

---

## API entry points (FastAPI)

### `POST /scan`
- Handler: `start_scan` — [src/api_server.py](src/api_server.py#L117-L142)
- Call chain:
  - `start_scan` enqueues background task `process_scan_job` — [src/api_server.py](src/api_server.py#L191-L301)
  - `process_scan_job` invokes `execute_pipeline` via `asyncio.get_event_loop().run_in_executor` — [src/core/pipeline/analysis.py](src/core/pipeline/analysis.py#L91-L156)
- Terminal sinks:
  - Temporary clone dir: `tempfile.TemporaryDirectory()` (placeholder) and `raise NotImplementedError("Git URL scanning not yet implemented")` — [src/api_server.py](src/api_server.py#L212-L215)
  - Output directory `/tmp/scanner-{job_id}` created and report writes:
    - `scan_report.md` — [src/api_server.py](src/api_server.py#L246-L249)
    - `verdict_report.md` — [src/api_server.py](src/api_server.py#L250-L253)
    - `scan_report.json` — [src/api_server.py](src/api_server.py#L256-L259)
  - In-memory `jobs` dict (status/progress/result) — [src/api_server.py](src/api_server.py#L120-L140)

---

### `GET /status/{job_id}`
- Handler: `get_job_status` — [src/api_server.py](src/api_server.py#L144-L151)
- Sink: reads in-memory `jobs` dict — [src/api_server.py](src/api_server.py#L120-L140)

### `GET /results/{job_id}/{filename}`
- Handler: `get_job_result` — [src/api_server.py](src/api_server.py#L153-L175)
- Sink: reads `/tmp/scanner-{job_id}/{filename}` and returns via `FileResponse` — [src/api_server.py](src/api_server.py#L159-L168)

### Health & Monitoring endpoints
- `GET /health` — [src/api_server.py](src/api_server.py#L77-L86)
- `GET /health/detailed` — [src/api_server.py](src/api_server.py#L87-L92) (calls `get_health_checker` from monitoring)
- `GET /metrics` — [src/api_server.py](src/api_server.py#L93-L98) (calls metrics collector)
- `GET /performance` — [src/api_server.py](src/api_server.py#L99-L104)
- Alerts: `GET /alerts`, `GET /alerts/history` — [src/api_server.py](src/api_server.py#L105-L116)

Monitoring components are imported from `src/core/monitoring.py` and may perform additional IO (logs, DBs, external collectors).

---

## Claims (explicit product statements)
- "Orchestrates bounty core modules to provide comprehensive bounty hunting capabilities with 99.999% SME accuracy." — docstring, [src/services/bounty_service.py](src/services/bounty_service.py#L1-L6)
- Additional claims appear in project docs and packaging metadata (check `docs/` and PKG-INFO if present).

## Validation/backtesting data (status)
- Referenced paths:
  - `validation_data/bounty_validation_cases.json` — used by `BountyAccuracyValidator` — [src/core/bounty/accuracy_validator.py](src/core/bounty/accuracy_validator.py#L42-L78)
  - `validation_data/sme_validations.json` — referenced by `claims_validator` — [src/core/validation/claims_validator.py](src/core/validation/claims_validator.py#L235-L240)
- Workspace status: the directory `validation_data/` exists but contains no validation files; both expected JSON files are MISSING.

## TODOs / NotImplementedError / FIXMEs
- `raise NotImplementedError("Git URL scanning not yet implemented")` — [src/api_server.py](src/api_server.py#L212-L215)
- Adapter stubs raising or marked TODO (examples): [src/adapters/python_adapter.py](src/adapters/python_adapter.py#L6-L22), [src/adapters/java_adapter.py](src/adapters/java_adapter.py#L6-L22), [src/adapters/rust_adapter.py](src/adapters/rust_adapter.py#L6-L22)
- Claims validator placeholder referencing missing file: [src/core/validation/claims_validator.py](src/core/validation/claims_validator.py#L235-L240)
- PR automation TODO: [src/core/bounty/pr_automation.py](src/core/bounty/pr_automation.py#L73-L76)

## Recommendations / next steps
1. Create minimal `validation_data/bounty_validation_cases.json` and `validation_data/sme_validations.json` to allow `validate` and claims checks to run and produce meaningful reports. I can generate example files matching the expected schemas.
2. Implement `git clone` in `process_scan_job` to support `repository_url` scanning (requires network access and design decisions about credentials and timeouts).
3. Implement or expand adapters in `src/adapters/` to remove NotImplementedError stubs if you want deeper code-modeling coverage.
4. Consider adding runtime licensing enforcement (currently missing) if launching commercially.

---

## Appendix: Important evidence links
- CLI: [src/cli.py](src/cli.py#L1-L520)
- API Server: [src/api_server.py](src/api_server.py#L1-L323)
- Pipeline controller: [src/core/pipeline/analysis.py](src/core/pipeline/analysis.py#L1-L400)
- Bounty service: [src/services/bounty_service.py](src/services/bounty_service.py#L1-L420)
- Accuracy validator: [src/core/bounty/accuracy_validator.py](src/core/bounty/accuracy_validator.py#L1-L520)
- Claims validator: [src/core/validation/claims_validator.py](src/core/validation/claims_validator.py#L1-L320)
- Output contract: [src/core/quality/output_contract.py](src/core/quality/output_contract.py#L190-L605)

---
