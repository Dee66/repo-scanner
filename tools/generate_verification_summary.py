#!/usr/bin/env python3
"""Run selected verification tests and aggregate results into tmp_scan_output.

Produces `tmp_scan_output/verification_summary.json` and `.md` including
calibration report + adversarial test outputs.
"""
from pathlib import Path
import json
import subprocess

OUT = Path('tmp_scan_output')
OUT.mkdir(exist_ok=True)

def run_pytest(path):
    cmd = ['pytest', '-q', str(path)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return {
        'path': str(path),
        'returncode': r.returncode,
        'stdout': r.stdout,
        'stderr': r.stderr
    }

summary = {}

# run calibration and adversarial tests
tests = [
    'tests/test_calibration_golden_repos.py',
    'tests/test_adversarial_property.py'
]

for t in tests:
    if Path(t).exists():
        summary[t] = run_pytest(t)
    else:
        summary[t] = {'error': 'test file missing'}

# include calibration report if present
calib = Path('tmp_scan_output/calibration_report.json')
calib_data = None
if calib.exists():
    try:
        calib_data = json.loads(calib.read_text(encoding='utf-8'))
    except Exception:
        calib_data = None

out = {
    'tests': summary,
    'calibration_report': calib_data
}

json_path = OUT / 'verification_summary.json'
json_path.write_text(json.dumps(out, indent=2), encoding='utf-8')

md_lines = ['# Verification Summary', '']
for t, r in summary.items():
    md_lines.append(f'## {t}')
    if 'error' in r:
        md_lines.append(f"- Error: {r['error']}")
        md_lines.append('')
        continue
    md_lines.append(f"- Return code: {r['returncode']}")
    stdout_snip = (r.get('stdout') or '').strip().splitlines()[:10]
    if stdout_snip:
        md_lines.append('---')
        md_lines.extend(stdout_snip)
        md_lines.append('---')
    md_lines.append('')

md_lines.append('## Calibration Summary')
if calib_data:
    s = calib_data.get('summary', {})
    md_lines.append(f"- Repos evaluated: {len(calib_data.get('repos', {}))}")
    md_lines.append(f"- Precision: {s.get('precision')}")
    md_lines.append(f"- Recall: {s.get('recall')}")
    md_lines.append(f"- F1: {s.get('f1')}")
else:
    md_lines.append('- No calibration report found')

md_path = OUT / 'verification_summary.md'
md_path.write_text('\n'.join(md_lines), encoding='utf-8')

print(f'Wrote verification summary to {json_path} and {md_path}')
