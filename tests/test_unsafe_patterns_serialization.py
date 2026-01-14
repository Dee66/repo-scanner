from pathlib import Path

from src.core.pipeline.security_analysis.__init__ import SecurityAnalyzer


def test_unsafe_patterns_schema_alignment(tmp_path: Path):
    target = tmp_path / "sample.py"
    target.write_text(
        "import os\n"
        "os.system('ls')\n"  # command_injection (critical -> high)
        "# deterministic output for security\n"
    )

    analyzer = SecurityAnalyzer()
    result = analyzer.analyze_security_vulnerabilities([str(target)], semantic={})
    unsafe = result.get("unsafe_patterns", {})

    # Ensure patterns_by_language is populated
    assert "patterns_by_language" in unsafe
    py_entries = unsafe["patterns_by_language"].get("py") or unsafe["patterns_by_language"].get("python")
    assert py_entries, "Expected python findings"

    allowed = {"high", "medium", "low"}
    for file_entry in py_entries:
        for pattern in file_entry.get("patterns", []):
            assert "pattern" in pattern
            assert pattern.get("severity") in allowed

    # Summary counts should reflect normalized severities
    summary = unsafe.get("summary", {})
    assert summary.get("high_severity", 0) >= 1
    assert summary.get("low_severity", 0) >= 0
