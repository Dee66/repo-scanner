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


class TestDeserializationContextValidation:
    """Test that deserialization detection skips scanning/detection code."""

    def test_regex_pattern_definition_not_flagged(self):
        """A raw regex string containing 'eval' should not be flagged."""
        from src.core.pipeline.security_analysis import SecurityAnalyzer
        analyzer = SecurityAnalyzer.__new__(SecurityAnalyzer)
        # Simulate a line defining a regex pattern
        line = "PATTERN = r'eval\\s*\\('"
        content = "import re\nPATTERN = r'eval\\s*\\('\nre.compile(PATTERN)"
        result = analyzer._validate_deserialization_context(line, content, 2)
        assert result is False, "Regex pattern definitions should be skipped"

    def test_detection_code_context_not_flagged(self):
        """Lines in scanning/detection context should not be flagged."""
        from src.core.pipeline.security_analysis import SecurityAnalyzer
        analyzer = SecurityAnalyzer.__new__(SecurityAnalyzer)
        line = "if 'eval(' in content:"
        content = (
            "def detect_vulnerabilities(content):\n"
            "    # scan for unsafe patterns\n"
            "    if 'eval(' in content:\n"
            "        return True\n"
        )
        result = analyzer._validate_deserialization_context(line, content, 3)
        assert result is False, "Detection code context should be skipped"

    def test_real_eval_call_still_flagged(self):
        """Actual eval() usage in application code should still be flagged."""
        from src.core.pipeline.security_analysis import SecurityAnalyzer
        analyzer = SecurityAnalyzer.__new__(SecurityAnalyzer)
        line = "result = eval(user_input)"
        content = (
            "def process_data(user_input):\n"
            "    result = eval(user_input)\n"
            "    return result\n"
        )
        result = analyzer._validate_deserialization_context(line, content, 2)
        assert result is True, "Real eval() calls should still be flagged"
