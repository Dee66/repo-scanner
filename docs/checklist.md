# ShieldCraft Engine Implementation Checklist

**Version:** 1.0.0  
**Source Spec:** spec/test_spec.yml v1.0.0  
**Last Updated:** 2025-12-23  
**Implementation Target:** AI-driven iterative development  
**Risk Level:** MEDIUM (spec complexity, no external dependencies)

<div role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0" style="width:94%; background:#e6eef0; border-radius:8px; padding:6px; box-shadow: inset 0 1px 2px rgba(0,0,0,0.04);">
  <div style="width:0%; background:linear-gradient(90deg,#84cc16,#22c55e,#10b981); color:#fff; padding:10px 12px; text-align:right; border-radius:6px; font-weight:700; transition:width 0.5s ease;">
    <span style="display:inline-block; background:rgba(0,0,0,0.12); padding:4px 8px; border-radius:999px; font-size:0.95em;">0% · 0/52</span>
  </div>
</div>

**Milestone Status:**  
**Foundation:** 0/5 (0%) 📋 | **Principles:** 0/7 (0%) 📋 | **Constraints:** 0/8 (0%) 📋  
**Pipeline:** 0/2 (0%) 📋 | **Safety:** 0/9 (0%) 📋 | **Framework:** 0/6 (0%) 📋 | **Quality:** 0/5 (0%) 📋

---

## Executive Summary

**Objective:** Implement ShieldCraft Engine as a deterministic repository analysis tool with explicit refusal-first discipline.

**Key Priorities:**
- **CRITICAL:** Authority ceiling and safety mechanisms (prevents unsafe analysis)
- **HIGH:** Behavioral principles and trust guarantees (core discipline)
- **MEDIUM:** Operating constraints and determinism (execution boundaries)

**Risk Assessment:** MEDIUM - Complex spec with interdependent components. Requires careful sequencing of safety mechanisms before analysis logic.

**Success Criteria:**
- All 52 tasks completed
- Deterministic verification passes
- Refusal mechanisms functional
- Authority bounds respected

---

## 1. System Foundation

**Section Goal:** Establish core system identity and boundaries  
**Priority:** HIGH  
**Dependencies:** None  
**Tasks:** 5/5  
**Status:** 0% (0/5)

### Core Identity
- [x] SYS-001: Implement system configuration with name, version, classification, authority level, and status
- [x] SYS-002: Define public description explaining deterministic assessment capabilities
- [ ] SYS-003: Document explicit non-claims (no execution, no business correctness, no defect finding, no human replacement, no forced action)

### Core Purpose
- [ ] SYS-004: Implement core promise of auditable repository snapshots
- [ ] SYS-005: Define non-promise limitations (no completeness guarantees, no intent coverage, no security coverage, no fitness guarantees)

---

## 2. Behavioral Principles & Trust

**Section Goal:** Implement refusal-first discipline and trust guarantees  
**Priority:** CRITICAL  
**Dependencies:** System Foundation  
**Tasks:** 7/7  
**Status:** 0% (0/7)

### Epistemic Principles
- [x] PRN-001: Implement only observable claims principle
- [x] PRN-002: Implement evidence separation from judgment
- [x] PRN-003: Implement uncertainty visibility requirement
- [x] PRN-004: Implement confidence justification requirement
- [ ] PRN-005: Implement silence preference over false precision

### Behavioral Rules
- [x] PRN-006: Implement refusal check for never_guess_intent
- [x] PRN-007: Implement refusal check for never_optimize_for_output_volume
- [x] PRN-008: Implement refusal check for never_mask_unknowns
- [x] PRN-009: Implement refusal check for never_force_action
- [ ] PRN-010: Implement refusal check for never_require_manual_intervention

### Trust Guarantees
- [x] PRN-011: Implement determinism_is_mandatory guarantee
- [x] PRN-012: Implement reproducibility_is_required guarantee
- [x] PRN-013: Implement conservative_bias_on_ambiguity guarantee
- [x] PRN-014: Implement explicit_limits_of_authority guarantee

---

## 3. Operating Constraints

**Section Goal:** Define execution boundaries and determinism requirements  
**Priority:** HIGH  
**Dependencies:** Behavioral Principles & Trust  
**Tasks:** 8/8  
**Status:** 0% (0/8)

### Execution Environment
- [x] CON-001: Implement offline_only execution mode
- [x] CON-002: Implement network_access forbidden constraint
- [x] CON-003: Implement external_services forbidden constraint
- [x] CON-004: Implement repository_modification forbidden constraint
- [ ] CON-005: Implement execute_application_code forbidden constraint

### Determinism Requirements
- [x] CON-006: Implement required determinism guarantee
- [x] CON-007: Implement identical_input_identical_output guarantee
- [x] CON-008: Implement canonical_file_traversal guarantee
- [x] CON-009: Implement canonical_sorting_of_all_outputs guarantee
- [x] CON-010: Implement no_timestamps guarantee
- [x] CON-011: Implement no_random_values guarantee
- [ ] CON-012: Implement stable_hashes_required guarantee

### Failure Handling
- [x] CON-013: Implement repeated_runs verification (2 runs)
- [x] CON-014: Implement hash_algorithm sha256 verification
- [x] CON-015: Implement mismatch_action invalidate_run policy
- [x] CON-016: Implement fail_soft_never_fail_stop philosophy
- [x] CON-017: Implement unexpected_conditions actions (isolate, continue, downgrade, emit warning)

---

## 4. Analysis Pipeline

**Section Goal:** Implement core repository analysis workflow  
**Priority:** MEDIUM  
**Dependencies:** Operating Constraints  
**Tasks:** 2/2  
**Status:** 0% (0/2)

### Pipeline Stages
- [x] APL-001: Implement analysis pipeline with 12 stages (repository_discovery through determinism_verification)
- [x] APL-002: Implement bounded_parallelism strategy with pure tasks and shared state forbidden

---

## 5. Authority Ceiling & Safety

**Section Goal:** Implement safety mechanisms and refusal boundaries  
**Priority:** CRITICAL  
**Dependencies:** Analysis Pipeline  
**Tasks:** 9/9  
**Status:** 0% (0/9)

### Authority Definition
- [x] AUT-001: Implement authority ceiling definition (maximum complexity beyond which system refuses guidance)
- [x] AUT-002: Implement triggers (unbounded_blast_radius, contradictory_governance_signals, missing_ownership_artifacts, excessive_polyglot_sprawl, critical_paths_unverifiable)
- [ ] AUT-003: Implement behavior_on_trigger actions (emit_refusal_artifact, suppress_recommendations, downgrade_all_confidence_levels)

### Intent Classification
- [x] AUT-004: Implement intent_posture_classification purpose (classify observable posture, not human intent)
- [x] AUT-005: Implement constraints (inference_must_be_evidence_anchored, classification_must_be_downgradable)
- [x] AUT-006: Implement postures (prototype, productized_service, internal_tool, legacy_system, platform_core)
- [x] AUT-007: Implement confidence_required guarantee

### Safe Change Surface
- [x] AUT-008: Implement safe_change_surface definition (bounded model for acceptable risk changes)
- [x] AUT-009: Implement properties (explicit_safe_zones, explicit_no_touch_zones, blast_radius_characterization, evidence_references, expiry_conditions)
- [ ] AUT-010: Implement rules (absence_is_valid_outcome, safe_surface_may_be_empty, first_action_may_be_explicit_non_action)

### Refusal Artifact
- [x] AUT-011: Implement refusal_artifact definition (first-class output for responsible guidance refusal)
- [x] AUT-012: Implement required_fields (reason_for_refusal, missing_or_unknowable_information, blast_radius_unbounded_statement, responsible_human_role_required)
- [x] AUT-013: Implement guarantees (refusal_is_success, refusal_is_auditable)

---

## 6. Risk & Decision Framework

**Section Goal:** Implement assessment and decision generation mechanisms  
**Priority:** MEDIUM  
**Dependencies:** Authority Ceiling & Safety  
**Tasks:** 6/6  
**Status:** 0% (0/6)

### Risk Synthesis
- [x] RDF-001: Implement risk_and_gap_synthesis with gap_types (structural, testing, governance, integration, knowledge_risk)
- [x] RDF-002: Implement prioritization method (impact_over_effort)
- [ ] RDF-003: Implement outputs (prioritized_gap_list, negative_roi_optimizations)

### Decision Artifacts
- [ ] RDF-004: Implement decision_artifacts with required artifacts (executive_verdict, safe_to_change_surface, no_touch_zones, misleading_signals, what_not_to_fix, refusal_artifact_if_applicable, confidence_and_limits, validity_window)

### Confidence Model
- [x] RDF-005: Implement confidence_model with levels (HIGH, MEDIUM, LOW)
- [x] RDF-006: Implement rules (confidence_must_be_justified, confidence_must_be_downgraded_on_ambiguity, refusal_forces_LOW)

---

## 7. Output Contract & Quality

**Section Goal:** Implement quality assurance and compliance mechanisms  
**Priority:** HIGH  
**Dependencies:** Risk & Decision Framework  
**Tasks:** 5/5  
**Status:** 0% (0/5)

### Output Contract
- [x] QUA-001: Implement primary_report format (markdown, senior_human_reviewer tone, silence/brevity/severity rules, required sections)
- [x] QUA-002: Implement machine_readable_output format (json, deterministic, canonical_sorting, governance_hash_embedded)

### Quality Assurance
- [x] QUA-003: Implement silence_policy with allowed_conditions (no_material_findings, no_safe_action_identified) and explicit_silence_verdict
- [x] QUA-004: Implement quality_bar with minimum_standard (decision_grade) and rejection_conditions (generic_advice, vanity_metrics, unjustified_opinions, action_bias, hidden_uncertainty)
- [x] QUA-005: Implement success_criteria (deterministic_verification_passed, refusal_possible_and_clean, blast_radius_explicit, authority_bounds_respected, trust_maintained_over_output_volume)

---

## Summary (v1.0.0 Spec)

**Total Tasks:** 52  
**Completed:** 0  
**Remaining:** 52  
**Progress:** 0%

**Priority Breakdown:**
- **CRITICAL:** 16 tasks (Authority Ceiling & Safety, Behavioral Principles)
- **HIGH:** 13 tasks (System Foundation, Operating Constraints, Output Contract & Quality)
- **MEDIUM:** 23 tasks (Analysis Pipeline, Risk & Decision Framework)

**Next Steps:**
1. Start with System Foundation (SYS-001 through SYS-005)
2. Implement Behavioral Principles & Trust (PRN-001 through PRN-014)
3. Establish Operating Constraints (CON-001 through CON-017)
4. Build Analysis Pipeline (APL-001 through APL-002)
5. Implement Authority Ceiling & Safety (AUT-001 through AUT-013)
6. Add Risk & Decision Framework (RDF-001 through RDF-006)
7. Finalize Output Contract & Quality (QUA-001 through QUA-005)

---

## Change Log

**v1.0.0 (2025-12-23):**
- Initial implementation checklist created
- 52 tasks across 7 sections
- Priority levels assigned
- Dependencies mapped
- Progress tracking enabled

---

*This checklist enables systematic, iterative implementation of ShieldCraft Engine. Each task is designed to be implementable independently while building toward the complete system. Update progress as tasks are completed.*

---

## Supplemental fixes

These supplemental checklist items capture the concrete remediation and hardening work we've planned and started implementing. Each item is written as a single, unambiguous task suitable for direct implementation and CI verification.

 - [x] SFX-001: Add and formalize strict JSON schemas for all machine-readable outputs under `docs/schemas/`, including field names, types, `required` arrays, and explicit enum/value constraints where applicable.
 - [x] SFX-002: Implement a schema loader and validator (`src/core/quality/schema_validator.py`) that is invoked by the pipeline and CI; validator must fail the run on missing required keys and return clear diagnostics for each missing field.
 - [x] SFX-003: Integrate schema validation into the pipeline `analysis` stage so that `tmp_scan_output/scan_report.json` and other artifacts are validated automatically after generation.
 - [x] SFX-004: Expand `src/core/pipeline/repository_discovery.py` canonical exclude list to cover generated, cached, and output directories (`.scanner_cache`, `tmp_scan_output`, `scan_output`, `reports`, `outputs`, `analysis`) and common compiled artifacts (`.pyc`, `.pyo`, `.class`, coverage files); add unit test to assert excluded paths.
 - [x] SFX-005: Re-run the scanner end-to-end after exclude updates and record outputs to `tmp_scan_output/`; produce a machine-readable `scan_report.json` for validation and comparison with previous runs.
 - [x] SFX-006: Validate `tmp_scan_output/scan_report.json` against `docs/schemas/scan_report.schema.json`; create a triage report listing every schema failure with file/path and JSON pointer to the failing value.
 - [x] SFX-007: For each high-severity finding in reports, attach explicit evidence: minimal proof snippet (file path, line range, quoted lines) and deterministic provenance (git commit SHA and file byte offsets). Add unit tests verifying presence of evidence fields for severity >= HIGH.
 - [x] SFX-008: Implement deterministic provenance fields in machine outputs: `repo_commit` (SHA), `source_path`, `byte_range` or `line_range`, and `evidence_snippet`. Ensure no use of non-deterministic timestamps in primary artifacts (respect `no_timestamps`).
 - [x] SFX-009: Harden detectors to be evidence-first: update detector code so every claim is only emitted if linked to one or more evidence objects; add tests that simulate detector inputs and assert claims without evidence are not emitted.
- [ ] SFX-010: Add stricter schema versions and compatibility tests: create a `docs/schemas/compatibility.md` and a test that fails if generated output does not conform to the current schema version.
- [ ] SFX-011: Create a golden-repos dataset and calibration harness (`tests/golden/`) with 3-5 representative repositories; write calibration tests that compute detector precision/recall metrics and produce a failing CI check if precision for `HIGH` findings drops below a configured threshold.
- [ ] SFX-012: Implement adversarial/unit/property tests for detectors that exercise edge cases (obfuscated comments, generated files, polyglot files); add these to `tests/` and ensure they run in CI within a bounded time budget.
- [ ] SFX-013: Add CI gating: include a `ci/schema_validation.yml` job that runs schema validation and deterministic verification on PRs; the job must fail PR merges on schema violations or determinism mismatch.
- [ ] SFX-014: Implement determinism verification harness: run the pipeline twice in isolation on the same input snapshot and assert bitwise-equal outputs (or canonicalized equality) for all machine-readable artifacts; add this harness to CI as a fast check (sampled or lightweight mode).
- [ ] SFX-015: Add performance profiling and budgets: add a pipeline stage that measures runtime and memory per stage; add thresholds in `docs/quality/` and have the CI job warn or fail when budgets are exceeded.
- [ ] SFX-016: Update documentation (`docs/README_ARCHITECTURE.md`, `docs/phase_C_diffs.md`) to include the supplemental fixes, expected artifacts, and the verification steps required for each fix.
- [ ] SFX-017: Add an automated remediation-triage script (`tools/triage_schema_failures.py`) that parses validator output and emits actionable TODOs (file, detector, fix recommendation) so engineers can quickly patch detectors or schemas.
- [ ] SFX-018: Add release checklist entries and version bumping: add a `RELEASE.md` step that requires schema validation and determinism verification to pass before cutting a release tag.

---

Add these items to the project TODO tracker and mark progress as you complete each task.

**Progress Note (2025-12-26):** SFX-001 through SFX-009 implemented and unit-tested. SFX-009 (evidence-first enforcement) has targeted tests and the pipeline-level filter in `src/core/quality/output_contract.py`; full test suite passes locally (78 passed, 1 warning).

