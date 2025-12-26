import json
import pytest
from pathlib import Path
from src.core.quality.output_contract import generate_machine_output


def test_scan_report_includes_schema_version_if_defined(tmp_path):
    """If the scan_report schema defines a `governance.schema_version` property,
    the generated machine output must include `governance.schema_version`.
    Otherwise the test is a no-op.
    """
    schema_path = Path("docs/schemas/scan_report.schema.json")
    if not schema_path.exists():
        pytest.skip("No scan_report schema present")

    try:
        schema = json.loads(schema_path.read_text())
    except Exception:
        pytest.skip("Unable to read scan_report schema")

    governance_props = schema.get("properties", {}).get("governance", {}).get("properties", {})
    if "schema_version" not in governance_props:
        pytest.skip("Schema does not declare governance.schema_version; skipping compatibility assertion")

    # Generate a minimal machine output and assert presence and correctness of schema_version
    analysis = {
        "repository_root": str(tmp_path),
        "files": [],
        "decision_artifacts": {}
    }
    out = generate_machine_output(analysis, str(tmp_path))
    gov = out.get("governance", {})
    assert "schema_version" in gov and gov.get("schema_version"), (
        "Schema declares governance.schema_version but generated output is missing governance.schema_version"
    )

    # Ensure the produced schema_version matches docs/schemas/VERSION
    verpath = Path('docs') / 'schemas' / 'VERSION'
    if verpath.exists():
        expected = verpath.read_text(encoding='utf-8').strip()
        assert gov.get('schema_version') == expected, (
            f"Generated governance.schema_version ({gov.get('schema_version')}) does not match docs/schemas/VERSION ({expected})"
        )

    # Validate the generated output against the scan_report schema
    # This will raise an exception (fail test) if validation fails.
    from src.core.quality import schema_validator
    tmp_json = tmp_path / 'scan_report.json'
    tmp_json.write_text(json.dumps(out), encoding='utf-8')
    schema_validator.validate_scan_report(str(tmp_json))
