#!/usr/bin/env python3
"""Determinism harness: run the scanner multiple times and compare machine outputs."""
from pathlib import Path
import subprocess
import hashlib
import json

ROOT = Path('.')
OUT_BASE = Path('outputs_determinism')
OUT_BASE.mkdir(exist_ok=True)
RUNS = 3

run_shas = []
details = {}

for i in range(1, RUNS + 1):
    outdir = OUT_BASE / f'run_{i}'
    if outdir.exists():
        # clear previous
        for p in outdir.glob('*'):
            if p.is_file():
                p.unlink()
    else:
        outdir.mkdir(parents=True)

    # run scan
    print(f'Run {i}: generating output in {outdir}')
    subprocess.run(['python', '-m', 'src.cli', 'scan', '.', '--output-dir', str(outdir), '--format', 'json'], check=True)

    rpt = outdir / 'scan_report.json'
    if not rpt.exists():
        raise SystemExit(f'Missing output {rpt}')

    b = rpt.read_bytes()
    sha = hashlib.sha256(b).hexdigest()
    run_shas.append(sha)
    details[f'run_{i}'] = {'sha': sha, 'size': len(b)}

unique = sorted(set(run_shas))
consistent = len(unique) == 1

report = {
    'runs': details,
    'unique_shas': unique,
    'unique_count': len(unique),
    'consistent': consistent
}

out_dir = Path('tmp_scan_output')
out_dir.mkdir(exist_ok=True)
json_path = out_dir / 'determinism_report.json'
json_path.write_text(json.dumps(report, indent=2), encoding='utf-8')

md_lines = [
    '# Determinism Report',
    '',
    f"Runs: {RUNS}",
    f"Unique SHAs: {len(unique)}",
    f"Consistent: {consistent}",
    '',
]
for run, info in details.items():
    md_lines.append(f"- {run}: sha={info['sha']} size={info['size']}")

md_path = out_dir / 'determinism_report.md'
md_path.write_text('\n'.join(md_lines), encoding='utf-8')

print(f'Wrote determinism report to {json_path} and {md_path}')
