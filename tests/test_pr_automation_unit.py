import pytest
from src.core.bounty.pr_automation import SurgicalMinimalistFilter, CommitFragmenter


def test_surgical_minimalist_filter_handles_none_persona_and_returns_structure():
    filt = SurgicalMinimalistFilter()

    ai_solution = {
        "code_changes": [
            {"file": "src/main.py", "new_code": "def foo():\n    return 1\n", "changes": "Add foo"}
        ]
    }

    # maintainer_profile with None detected_persona should not raise
    maintainer_profile = {"detected_persona": None}
    existing_codebase = {}

    filtered = filt.filter_solution(ai_solution.copy(), existing_codebase, maintainer_profile)

    assert isinstance(filtered, dict)
    assert "code_changes" in filtered
    assert isinstance(filtered["code_changes"], list)


def test_commit_fragmenter_fragment_changes_structure():
    fragmenter = CommitFragmenter()

    # Basic filtered solution with multiple changes
    filtered_solution = {
        "code_changes": [
            {"file": "src/a.py", "changes": "Change A", "new_code": "print(1)"},
            {"file": "src/b.py", "changes": "Change B", "new_code": "print(2)"}
        ]
    }

    maintainer_profile = {}
    commit_plan = fragmenter.fragment_changes(filtered_solution, maintainer_profile)

    assert isinstance(commit_plan, list)
    assert len(commit_plan) >= 1
    for c in commit_plan:
        assert isinstance(c, dict)
        # Commit objects may use 'type' (grouping) or 'commit_number' for enumerated commits
        assert ("type" in c) or ("commit_number" in c)
        assert ("changes" in c) or ("files" in c)
        # message is required for commit humanization
        assert "message" in c
