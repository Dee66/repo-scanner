import json
import pytest
from pathlib import Path
from src.core.quality.output_contract import generate_machine_output


def test_scan_report_includes_schema_version_if_defined(tmp_path):
    """If the scan_report schema defines a `governance.schema_version` property,
    the generated machine output must include `governance.schema_version`.
    Otherwise the test is a no-op.
    """
    schema_path = Path(__file__).parent.parent / "schemas" / "output" / "scan_report.json"
    if not schema_path.exists():
        pytest.skip("No scan_report schema present")

    try:
        schema = json.loads(schema_path.read_text())
    except Exception:
        pytest.skip("Unable to read scan_report schema")

    governance_props = schema.get("properties", {}).get("metadata", {}).get("properties", {})
    if "schema_version" not in governance_props:
        pytest.skip("Schema does not declare metadata.schema_version; skipping compatibility assertion")

    # Generate a minimal machine output and assert presence and correctness of schema_version
    analysis = {
        "repository_root": str(tmp_path),
        "files": [],
        "decision_artifacts": {
            "executive_verdict": "PASS",
            "safe_to_change_surface": [],
            "no_touch_zones": [],
            "misleading_signals": [],
            "what_not_to_fix": [],
            "confidence_and_limits": {
                "overall_confidence": 0.8,
                "confidence_breakdown": {
                    "structural_analysis": 0.8,
                    "governance_signals": 0.8,
                    "testing_coverage": 0.8,
                    "integration_patterns": 0.8
                },
                "analysis_limits": ["Test limit"],
                "assumptions_made": ["Test assumption"]
            },
            "validity_window": {
                "valid_from": "2024-01-01T00:00:00Z",
                "valid_until": "2024-01-31T00:00:00Z",
                "invalidation_triggers": ["Test trigger"]
            },
            "artifacts": []
        }
    }
    out = generate_machine_output(analysis, str(tmp_path))
    metadata = out.get("metadata", {})
    assert "schema_version" in metadata and metadata.get("schema_version"), (
        "Schema declares metadata.schema_version but generated output is missing metadata.schema_version"
    )

    # Ensure the produced schema_version matches docs/schemas/VERSION
    verpath = Path('docs') / 'schemas' / 'VERSION'
    if verpath.exists():
        expected = verpath.read_text(encoding='utf-8').strip()
        assert metadata.get('schema_version') == expected, (
            f"Generated metadata.schema_version ({metadata.get('schema_version')}) does not match docs/schemas/VERSION ({expected})"
        )

    # Validate the generated output against the scan_report schema
    # This will raise an exception (fail test) if validation fails.
    from src.core.quality import schema_validator
    tmp_json = tmp_path / 'scan_report.json'
    tmp_json.write_text(json.dumps(out), encoding='utf-8')
    schema_validator.validate_scan_report(str(tmp_json))
