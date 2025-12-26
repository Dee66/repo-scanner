import json
from pathlib import Path
import pytest


def _load(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def _high_ids(report: dict):
    arts = report.get('decision_artifacts', {}).get('artifacts', [])
    return {a.get('id') for a in arts if (a.get('severity') or '').upper() == 'HIGH'}


def test_golden_repos_precision_threshold():
    """Compute precision on HIGH findings across golden repos.

    The test will fail if overall precision for HIGH findings falls below 0.60.
    """
    base = Path('tests/golden')
    expected_files = sorted(base.glob('expected_*.json'))
    assert expected_files, "No golden expected files found"

    total_tp = 0
    total_fp = 0

    for ef in expected_files:
        name = ef.name.replace('expected_', '').replace('.json', '')
        pf = base / f'predicted_{name}.json'
        if not pf.exists():
            pytest.skip(f'Missing predicted file for {name}')
        exp = _load(ef)
        pred = _load(pf)

        exp_high = _high_ids(exp)
        pred_high = _high_ids(pred)

        tp = len(exp_high & pred_high)
        fp = len(pred_high - exp_high)

        total_tp += tp
        total_fp += fp

    if total_tp + total_fp == 0:
        pytest.skip('No HIGH findings in predictions; nothing to evaluate')

    precision = total_tp / (total_tp + total_fp)
    assert precision >= 0.60, f'Precision for HIGH findings too low: {precision:.2f} < 0.60'
