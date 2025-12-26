# Phase C — Per-file annotated diffs and tracebacks

This file records the concrete edits made during Phase C, the tracebacks that led to each change, and rationale for developers.

## Summary of edits

- `src/services/bounty_service.py`
  - Added defensive handling when `_generate_pr_content` returns `None` to avoid callers doing `pr_content.get(...)` on None.
  - Rationale: AI/engine outputs sometimes return `None` on failure; callers must handle safely.

- `src/core/bounty/pr_automation.py`
  - Refactored `CommitFragmenter` usage: moved fragmentation logic into `fragment_changes(self, solution_code, maintainer_profile)` and ensured `__init__` does not reference external vars.
  - Moved helper functions into `PRAutomationEngine` scope and removed duplicated helper block that caused attribute errors.
  - Fixed `_generate_pr_checklist` signature to accept `adr_analysis` (optional) to match call-sites.
  - Hardened persona access: use `maintainer_profile.get('detected_persona') or {}` to avoid AttributeError when persona is None.

## Collected tracebacks (representative)

1) Initial failing test stderr excerpt:

```
Analysis error: Bounty analysis failed: 'NoneType' object has no attribute 'get'
Details: {'error': "'NoneType' object has no attribute 'get'"}
```

2) NameError in `CommitFragmenter.__init__` (repro):

```
NameError: name 'solution_code' is not defined
  File "src/core/bounty/pr_automation.py", line XXX, in __init__
    ... solution_code ...
```

3) AttributeError due to helper methods mis-scoped:

```
AttributeError: 'PRAutomationEngine' object has no attribute '_generate_adr_notes'
  File "src/core/bounty/pr_automation.py", line YYY, in generate_pr_content
    adr_notes = self._generate_adr_notes(adr_analysis, bounty_data)
```

4) TypeError for checklist signature mismatch:

```
TypeError: PRAutomationEngine._generate_pr_checklist() takes 3 positional arguments but 4 were given
```

5) AttributeError due to persona None in `SurgicalMinimalistFilter._find_minimal_implementation`:

```
AttributeError: 'NoneType' object has no attribute 'get'
  File "src/core/bounty/pr_automation.py", line 791, in _find_minimal_implementation
    if persona.get("persona") == "ziverge":
```

## Developer notes

- The changes are minimal and focused; avoid broad refactors in this patch to reduce risk. Adding unit tests prevents regressions for the fixed code paths.

## How to reproduce locally

Run the failing integration test (before the fixes):
```
pytest -q tests/test_bounty_integration.py::TestBountyIntegration::test_bounty_solution_generation
```

Run the new unit tests added in this patch:
```
pytest -q tests/test_pr_automation_unit.py
```
