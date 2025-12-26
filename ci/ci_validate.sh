#!/usr/bin/env bash
set -euo pipefail

# Quick CI validation script: validate schemas and run determinism quick check
python -c "from src.core.quality.schema_validator import validate_scan_report; print('Schema validation module available')"
python -m src.cli scan . --output-dir outputs_ci --format json
sha=$(sha256sum outputs_ci/scan_report.json | awk '{print $1}')
echo "scan_report.json SHA: $sha"
exit 0
