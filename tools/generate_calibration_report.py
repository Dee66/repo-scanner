#!/usr/bin/env python3
"""Generate a calibration report from tests/golden expected/predicted files.

Writes `tmp_scan_output/calibration_report.json` and `tmp_scan_output/calibration_report.md`.
"""
from pathlib import Path
import json

BASE = Path('tests/golden')
OUT_DIR = Path('tmp_scan_output')
OUT_DIR.mkdir(exist_ok=True)

expected_files = sorted(BASE.glob('expected_*.json'))

report = {
    'repos': {},
    'summary': {}
}

total_tp = 0
total_fp = 0
total_fn = 0

for ef in expected_files:
    name = ef.name.replace('expected_', '').replace('.json', '')
    pf = BASE / f'predicted_{name}.json'
    if not pf.exists():
        continue
    exp = json.loads(ef.read_text(encoding='utf-8'))
    pred = json.loads(pf.read_text(encoding='utf-8'))

    def high_ids(rep):
        arts = rep.get('decision_artifacts', {}).get('artifacts', [])
        return {a.get('id') for a in arts if (a.get('severity') or '').upper() == 'HIGH'}

    exp_h = high_ids(exp)
    pred_h = high_ids(pred)

    tp = len(exp_h & pred_h)
    fp = len(pred_h - exp_h)
    fn = len(exp_h - pred_h)

    total_tp += tp
    total_fp += fp
    total_fn += fn

    report['repos'][name] = {
        'expected_high': sorted(list(exp_h)),
        'predicted_high': sorted(list(pred_h)),
        'tp': tp,
        'fp': fp,
        'fn': fn
    }

# compute metrics
precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else None
recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else None
f1 = (2 * precision * recall / (precision + recall)) if precision and recall and (precision + recall) > 0 else None

report['summary'] = {
    'total_tp': total_tp,
    'total_fp': total_fp,
    'total_fn': total_fn,
    'precision': precision,
    'recall': recall,
    'f1': f1,
}

# write JSON
json_path = OUT_DIR / 'calibration_report.json'
json_path.write_text(json.dumps(report, indent=2), encoding='utf-8')

# write simple markdown
md_lines = [
    '# Calibration Report',
    '',
    f"**Repos evaluated:** {len(report['repos'])}",
    '',
    '## Summary',
    '',
]
md_lines.append(f"- True positives: {total_tp}")
md_lines.append(f"- False positives: {total_fp}")
md_lines.append(f"- False negatives: {total_fn}")
md_lines.append(f"- Precision: {precision if precision is not None else 'N/A'}")
md_lines.append(f"- Recall: {recall if recall is not None else 'N/A'}")
md_lines.append(f"- F1: {f1 if f1 is not None else 'N/A'}")
md_lines.append('')
md_lines.append('## Per-repo details')
md_lines.append('')
for name, data in report['repos'].items():
    md_lines.append(f"### {name}")
    md_lines.append(f"- TP: {data['tp']}  FP: {data['fp']}  FN: {data['fn']}")
    md_lines.append(f"- Expected HIGH: {', '.join(data['expected_high'])}")
    md_lines.append(f"- Predicted HIGH: {', '.join(data['predicted_high'])}")
    md_lines.append('')

md_path = OUT_DIR / 'calibration_report.md'
md_path.write_text('\n'.join(md_lines), encoding='utf-8')

print(f'Wrote calibration report to {json_path} and {md_path}')
