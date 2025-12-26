import os
from pathlib import Path
import pytest

from src.core.quality import schema_validator


def test_scan_report_schema(tmp_path):
    report = Path('tmp_scan_output/scan_report.json')
    assert report.exists(), 'Scan report not generated; run scanner first'
    # Should not raise
    schema_validator.validate_scan_report(str(report))


def test_bounty_assessment_schema_noop():
    # Smoke test placeholder: ensure validator loads schema
    s = schema_validator.load_schema('bounty_assessment.schema.json')
    assert 'required' in s
