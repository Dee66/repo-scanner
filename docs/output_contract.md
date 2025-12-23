OUTPUT CONTRACT — v1 (AUTHORITATIVE)

This section defines all permissible outputs of the scanner.
Anything not explicitly allowed here must not be produced.

The scanner may generate multiple artifacts, but every artifact must conform to a defined purpose, schema, and evidentiary standard.

1. EXECUTIVE VERDICT
Purpose

Answer one question only:

“Can a competent engineer safely act on this repository right now, and if so, how?”

Constraints

Max 300 words

No generic phrasing

No claims without evidence references

Must degrade to “INSUFFICIENT EVIDENCE” if confidence < threshold

Required Fields

verdict: SAFE | CAUTION | UNSAFE | INSUFFICIENT_EVIDENCE

confidence: HIGH | MEDIUM | LOW

scope_of_assessment: explicit boundaries

blocking_risks: list or empty

safe_action_summary: what is safe to do now

unsafe_action_summary: what is unsafe now

evidence_index_refs: list of IDs

Prohibited

Opinions

Comparisons to “typical repos”

Statements not anchored to evidence

2. SAFE-TO-CHANGE MAP
Purpose

Tell the customer where they can safely touch the code.

Output Form

Structured map, not prose.

Required Fields (per unit)

artifact_id (file / module / package)

change_safety: SAFE | RISKY | UNSAFE | UNKNOWN

reason_codes (enumerated, not free text)

evidence_refs

confidence

Constraints

UNKNOWN is acceptable and preferred over guessing

SAFE requires positive evidence, not absence of problems

3. RISK & GAP LEDGER (PRIMARY VALUE)
Purpose

Provide an actionable, prioritized list of real problems.

Required Fields (per gap)

gap_id

gap_type: STRUCTURAL | TEST | SECURITY | INTEGRATION | SPEC_MISMATCH | UNKNOWN

priority: P0_SECURITY | P0_INTEGRATION | P0 | P1 | P2

description: precise, bounded

affected_artifacts

evidence_refs

why_this_matters

recommended_next_action

estimated_effort_range

confidence

Constraints

No “best practices” language

No speculative remediation

Every gap must explain impact, not just existence

4. EVIDENCE INDEX (NON-NEGOTIABLE)
Purpose

Make every claim auditable.

Required Fields

evidence_id

evidence_type: FILE_HASH | AST_SIGNAL | TEST_RESULT | STRUCTURE | CONFIG | DIFF

source_artifact

extracted_fact

derivation_method

confidence_weight

Constraints

All higher-level outputs must reference this index

Evidence must be reproducible deterministically

5. CONFIDENCE & COVERAGE REPORT
Purpose

Expose how much of the repo was actually understood.

Required Fields

coverage_by_dimension:

structure

code

tests

specs

security

unknown_areas

degraded_modes_triggered

confidence_downgrades_applied

reasons_for_uncertainty

Constraints

High confidence requires high coverage

Low coverage must cap conclusions

6. DETERMINISM & INTEGRITY REPORT
Purpose

Prove the scanner is trustworthy.

Required Fields

runs_executed

canonical_hash

hash_consistency: PASS | FAIL

nondeterminism_sources_detected

execution_environment_fingerprint

Constraints

Any FAIL invalidates verdicts

Must be machine-verifiable

7. MACHINE-READABLE CORE OUTPUT (JSON)
Purpose

Enable automation, re-scans, comparisons, CI use.

Requirements

Fully normalized

Sorted keys

No timestamps inside hashed sections

Forward-compatible versioning

8. EXPLICITLY FORBIDDEN OUTPUTS

The scanner must never emit:

Generic summaries (“overall solid”, “generally well structured”)

File counts, LOC, or vanity metrics without interpretation

Recommendations without evidence

Claims about business logic correctness

Security guarantees

Statements based on intuition or heuristics without signals

9. FAILURE MODE OUTPUT

If the scanner cannot meet evidentiary thresholds:

It must output:

verdict: INSUFFICIENT_EVIDENCE

Clear explanation of why

What inputs are missing

What would increase confidence

Silence is preferred over misleading output.

10. OUTPUT CONTRACT INVARIANTS (HARD RULES)

Every claim → evidence

Every verdict → confidence

Every confidence → coverage

Every recommendation → bounded action

Unknown > incorrect

Deterministic > fast

Useful > verbose

---

OUTPUT CONTRACT — v2 (AUTHORITATIVE)

This section defines the dual report system introduced in v2, supporting both comprehensive analysis and concise verdict reports.

## Report Types

### 1. COMPREHENSIVE ANALYSIS REPORT
**Purpose**: Provide complete technical assessment with full evidence chain for detailed review and audit.

**Format**: Markdown document with all required sections from v1 PRIMARY_REPORT schema.

**Constraints**:
- Evidence-dense but not verbose
- All claims anchored to verifiable evidence
- Includes complete risk synthesis and decision artifacts
- No length limit (severity drives length)

**Required Sections** (same as v1 PRIMARY_REPORT):
- executive_summary
- system_characterization  
- evidence_highlights
- misleading_signals
- safe_to_change_surface
- risk_synthesis
- decision_artifacts
- authority_ceiling_evaluation
- what_not_to_fix
- refusal_or_first_action
- confidence_and_limits
- validity_and_expiry

### 2. EXECUTIVE VERDICT REPORT
**Purpose**: Provide concise, decision-focused assessment answering: "Can a competent engineer safely act on this repository right now, and if so, how?"

**Format**: Markdown document with structured verdict sections.

**Constraints**:
- Max 300 words total
- Evidence-based with explicit references
- Degrades to INSUFFICIENT_EVIDENCE if confidence < 0.5
- No speculation or generic statements

**Required Sections**:
- Executive Verdict (verdict + confidence + assessment)
- Scope of Assessment (repository + risk level + confidence)
- Blocking Risks (if verdict = FAIL, list critical issues)
- Safe Action Summary (permitted actions based on verdict)
- Unsafe Action Summary (prohibited actions and conditions)

**Verdict Values**: PASS | FAIL | INSUFFICIENT_EVIDENCE

### 3. MACHINE-READABLE OUTPUT
**Purpose**: Structured data for automated processing and integration.

**Format**: Canonical JSON with embedded governance hash.

**Constraints**:
- Deterministic sorting
- All timestamps in ISO format
- Confidence scores as floats 0.0-1.0
- Evidence references as structured objects

### 4. BOUNTY ARTIFACTS (ALGORA INTEGRATION)
**Purpose**: Provide bounty-specific decision support for Algora bounty hunting platform.

**Required Fields**

profitability_score: float (0.0-1.0)

merge_confidence: float (0.0-1.0)

maintainer_compatibility: object
- compatibility_score: float (0.0-1.0)
- compatibility_factors: array of strings
- recommended_approach: string

bounty_recommendations: array of objects
- priority: "high" | "medium" | "low"
- action: string
- rationale: string
- confidence: float

**Constraints**
- Profitability score must use Bayesian probability framework
- Merge confidence must achieve 99.999% accuracy target
- All recommendations must be evidence-based
- Compatibility factors must reference specific maintainer preferences

**Evidence Standards**
- Profitability calculations must reference risk_synthesis, test_signals, and maintainer_profile
- Compatibility assessment must reference intent_posture and governance analysis
- Recommendations must include confidence scores and rationale

## CLI Interface (v2)

New `--report-type` argument controls output generation:

- `comprehensive`: Generate comprehensive report + machine output
- `verdict`: Generate executive verdict + machine output  
- `both`: Generate comprehensive report + executive verdict + machine output

## Evidence Standards (v2)

**Enhanced Rigor**:
- All claims must reference specific evidence sources
- Confidence scores must reflect actual assessment coverage
- Unknown states preferred over incorrect assumptions
- Evidence format: [EVIDENCE:source.field] or [EVIDENCE:stage_name]

**Degradation Rules**:
- Confidence < 0.5 → INSUFFICIENT_EVIDENCE
- Missing evidence → qualification or omission
- Contradictory evidence → explicit uncertainty statement

## Migration from v1

v2 maintains backward compatibility while adding dual report capability:
- Existing `--format` argument still supported for basic output control
- `--report-type` takes precedence when both specified
- All v1 schemas remain valid
- Executive verdict now computed from analysis data instead of placeholder