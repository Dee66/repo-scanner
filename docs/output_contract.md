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