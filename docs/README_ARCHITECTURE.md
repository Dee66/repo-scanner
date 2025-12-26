# Repo-Scanner Architecture & Developer Guide

This document is the developer-grade single source of truth for the project. It complements `docs/phase_ABC_report.md` by providing per-file responsibilities, public APIs, data schemas, a dataflow diagram, reproducibility steps, and links to diffs and tracebacks produced during Phase C.

**Location:** `docs/README_ARCHITECTURE.md`

---

## 1) File index (key modules)
- `src/cli.py` — CLI entrypoint. Subcommands: `scan`, `bounty`, `validate`. Parses JSON inputs and orchestrates pipeline + `BountyService` calls.
- `src/services/bounty_service.py` — Bounty orchestration: `analyze_bounty_opportunity(repository_url, bounty_data, analysis_results)` and `generate_bounty_solution(bounty_data, maintainer_profile, governance, solution_code, ...)`.
- `src/core/bounty/pr_automation.py` — `PRAutomationEngine` builds PR content: title, description, labels, checklist, CI integration, commit fragmentation and filtered AI solution. Also contains `SurgicalMinimalistFilter` and `CommitFragmenter`.
- `src/core/bounty/maintainer_profile_engine.py` — Builds maintainer profile used to adapt PR language and commit messages.
- `src/core/bounty/profitability_triage.py` — Triage engine to assess bounty profitability and triage decision.
- `src/core/bounty/adr_engine.py` — ADR analysis engine; extracts ADR files and relevant decisions.
- `src/core/bounty/historical_forensics.py` — Forensics engine for contextual anchors.
- `src/core/quality/output_contract.py` — Functions to generate `scan_report.json` / markdown outputs used by CLI `scan`.

Other supporting modules are in `src/core/pipeline/*` and `src/core/bounty/*` — see repository tree for a full list.

---

## 2) Public interfaces & usage

CLI usage (examples):

1. Scan a repository (produce reports):
```
python -m src.cli scan /path/to/repo --output-dir ./out --format both
```

2. Run bounty analysis (single bounty):
```
python -m src.cli bounty /path/to/repo --bounty-data '{"id":"x","title":"T","description":"D"}' --output-dir ./out
```

3. Run bounty and generate solution (requires `--solution-code`):
```
python -m src.cli bounty /path/to/repo --bounty-data '{...}' --output-dir ./out --generate-solution --solution-code '{...}'
```

Programmatic API (important functions):
- `BountyService.analyze_bounty_opportunity(repository_url: str, bounty_data: Dict, analysis_results: Dict) -> Dict` — returns assessment dict.
- `BountyService.generate_bounty_solution(bounty_data: Dict, maintainer_profile: Dict, governance: Dict, solution_code: Dict, adr_analysis: Dict=None, forensics_data: Dict=None, repo_path: str=None) -> Dict` — returns `solution_package` containing `pr_content` and `integration_plan`.
- `PRAutomationEngine.generate_pr_content(bounty_data, maintainer_profile, governance, solution_code, adr_analysis=None, forensics_data=None, repo_path=None) -> Dict` — builds PR dict with keys: `title, description, branch_name, labels, checklist, ci_cd_integration, review_requirements, testing_requirements, commit_fragmentation, filtered_solution, generated_at, confidence_score`.

---

## 3) Output JSON schemas (informal)
Below are concise schemas for the artifacts the tests assert. These are intentionally permissive but list required top-level fields and expected types.

`bounty_assessment.json` (requirements):
- `bounty_id` (string)
- `repository_url` (string)
- `assessment_timestamp` (string, isoformat)
- `overall_recommendation` (string)
- `components` (object) — includes `maintainer_profile`, `profitability_triage`, `integration_analysis`
- `risk_factors` (array[string])
- `success_probability` (number)
- `estimated_effort` (object)
- `next_steps` (array[object])

`bounty_solution.json` (requirements):
- `bounty_id` (string)
- `pr_content` (object) — must include `title` (string), `description` (string), `branch_name` (string)
- `integration_plan` (object)
- `generated_at` (string)
- `confidence_score` (number)

`pr_content.md` (markdown) — should contain PR title and sections: `## Description`, `## Checklist` at minimum.

---

## 4) Dataflow (bounty path)

ASCII flow (bounty solution generation):

CLI (`src/cli.py`) -> execute_pipeline(repo) -> analysis_result
    -> BountyService.analyze_bounty_opportunity(repository_url, bounty_data, analysis_result)
        -> profile_engine.generate_maintainer_profile(...)
        -> triage_engine.triage_bounty_profitability(...)
        -> api_engine.analyze_api_integration_points(...)
        -> _generate_bounty_assessment(...) -> assessment
    -> if --generate-solution:
        -> BountyService.generate_bounty_solution(...)
            -> _generate_pr_content(...) -> generate_pr_for_bounty(...) -> PRAutomationEngine.generate_pr_content(...)
                 -> SurgicalMinimalistFilter.filter_solution(...) -> CommitFragmenter.fragment_changes(...)
                 -> templates + _generate_pr_description(...) + _generate_pr_checklist(...) + _generate_ci_cd_integration(...)
            -> _generate_integration_plan(...) -> package solution

---

## 5) Per-file change summaries (Phase C)
- See `docs/phase_C_diffs.md` for annotated diffs and the representative tracebacks that led to each edit.

---

## 6) Full reproducibility appendix

Environment (what I used locally):
- OS: Linux
- Python: 3.11 (pyenv used in developer environment)
- Test runner: `pytest` >= 6

Commands used to reproduce traces and test runs:
```
pytest -q tests/test_bounty_integration.py::TestBountyIntegration::test_bounty_solution_generation
pytest -q tests/test_pr_automation_unit.py
pytest -q
pytest --cov=src --cov-report=term --cov-report=xml -q
```

Representative tracebacks and where to find them:
- See `docs/phase_C_diffs.md` and the Phase C report for the exact stack traces used to identify each bug.

---

## 7) Next steps & recommended workplan
1. Add JSON Schema files (strict) for outputs and validate outputs in tests.
2. Harden all AI/engine outputs with defensive checks and add unit tests simulating None and malformed outputs.
3. Remove generated artifacts from the repository and add to `.gitignore` (prepare a clean PR branch).
4. Performance tuning of `execute_pipeline` or relax performance test thresholds depending on CI environment.

---

If you want, I will now:
- add strict JSON Schema files under `docs/schemas/` and add validation tests; and
- clean noisy generated artifacts from the repo and create a focused PR branch.
