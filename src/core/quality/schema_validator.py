"""Schema validator for repository artifacts.

Behavior:
- Prefer the `jsonschema` package (Draft-07) when available and emit
  detailed validation diagnostics.
- If `jsonschema` is not installed, fall back to a lightweight recursive
  required-key checker that reports JSON Pointer locations for missing keys.

Validator loads schemas from `docs/schemas/` at the repository root.
"""
import json
from pathlib import Path
from typing import Dict, Any, List

try:
    import jsonschema
    from jsonschema import Draft7Validator
    HAS_JSONSCHEMA = True
except Exception:
    HAS_JSONSCHEMA = False


def _schema_dir() -> Path:
    # project root is parents[3] from src/core/quality
    return Path(__file__).resolve().parents[3] / "docs" / "schemas"


def load_schema(name: str) -> Dict[str, Any]:
    path = _schema_dir() / name
    with open(path, 'r') as f:
        return json.load(f)


def _format_json_pointer(path_parts: List) -> str:
    if not path_parts:
        return '/'
    return '/' + '/'.join(str(p) for p in path_parts)


def _fallback_required_check(doc: Any, schema: Dict[str, Any], path: List = None) -> List[str]:
    """Recursive required-key check when `jsonschema` is unavailable.

    Returns a list of diagnostic strings describing missing required fields
    with JSON Pointer locations.
    """
    path = path or []
    errors: List[str] = []
    required = schema.get('required', [])
    for key in required:
        if not isinstance(doc, dict) or key not in doc:
            ptr = _format_json_pointer(path + [key])
            errors.append(f"Missing required key: {ptr}")
    # recurse into properties if both doc and schema specify them
    properties = schema.get('properties', {})
    if isinstance(doc, dict):
        for key, subschema in properties.items():
            if key in doc:
                errors.extend(_fallback_required_check(doc[key], subschema, path + [key]))
    return errors


def validate_against_schema(doc: Dict[str, Any], schema_name: str) -> List[str]:
    """Validate a loaded document against a named schema file.

    Returns a list of diagnostic messages. Empty list == valid.
    """
    schema = load_schema(schema_name)
    if HAS_JSONSCHEMA:
        validator = Draft7Validator(schema)
        errors = []
        for err in sorted(validator.iter_errors(doc), key=lambda e: e.path):
            ptr = _format_json_pointer(list(err.path))
            errors.append(f"{ptr}: {err.message}")
        return errors
    else:
        return _fallback_required_check(doc, schema, [])


def _validate_file(path_to_json: str, schema_name: str) -> None:
    doc = json.loads(Path(path_to_json).read_text())
    errors = validate_against_schema(doc, schema_name)
    if errors:
        msg = "Schema validation failed:\n" + "\n".join(errors)
        raise ValueError(msg)


def validate_scan_report(path_to_json: str) -> None:
    _validate_file(path_to_json, 'scan_report.schema.json')


def validate_bounty_assessment(path_to_json: str) -> None:
    _validate_file(path_to_json, 'bounty_assessment.schema.json')


def validate_bounty_solution(path_to_json: str) -> None:
    _validate_file(path_to_json, 'bounty_solution.schema.json')


__all__ = [
    'validate_scan_report',
    'validate_bounty_assessment',
    'validate_bounty_solution',
    'validate_against_schema',
    'load_schema'
]
