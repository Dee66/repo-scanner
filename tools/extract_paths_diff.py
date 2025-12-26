#!/usr/bin/env python3
"""Extract filesystem paths from scan_report.json across runs and diff them."""
from pathlib import Path
import json
import re

RUNS_DIR = Path('outputs_determinism')
OUT_DIR = Path('tmp_scan_output')
OUT_DIR.mkdir(exist_ok=True)

def collect_paths(obj, prefix='/home'):
    paths = set()
    if isinstance(obj, dict):
        for v in obj.values():
            paths.update(collect_paths(v, prefix))
    elif isinstance(obj, list):
        for item in obj:
            paths.update(collect_paths(item, prefix))
    elif isinstance(obj, str):
        if obj.startswith(prefix) or re.search(r'\b' + re.escape(str(Path.cwd())) , obj):
            # split possible lists inside strings
            for part in re.split(r"[,;]\s*", obj):
                if part.startswith(prefix):
                    paths.add(part)
    return paths

results = {}
for run in sorted(p for p in RUNS_DIR.glob('run_*') if p.is_dir()):
    rpt = run / 'scan_report.json'
    if not rpt.exists():
        continue
    data = json.loads(rpt.read_text(encoding='utf-8'))
    paths = collect_paths(data)
    results[run.name] = sorted(paths)

# write per-run lists
for k, v in results.items():
    (OUT_DIR / f'files_{k}.txt').write_text('\n'.join(v), encoding='utf-8')

# compute diffs between runs
runs = sorted(results.keys())
diffs = {}
for i in range(1, len(runs)):
    a = set(results[runs[0]])
    b = set(results[runs[i]])
    diffs[runs[i]] = {
        'only_in_baseline': sorted(list(a - b)),
        'only_in_run': sorted(list(b - a))
    }

out = {'per_run_counts': {k: len(v) for k, v in results.items()}, 'diffs': diffs}
json_path = OUT_DIR / 'files_list_diff.json'
json_path.write_text(json.dumps(out, indent=2), encoding='utf-8')
md_lines = ['# Files List Diff', '']
for k, v in out['per_run_counts'].items():
    md_lines.append(f'- {k}: {v} paths')
md_lines.append('')
for run, d in diffs.items():
    md_lines.append(f'## Diff baseline -> {run}')
    md_lines.append(f'- Only in baseline: {len(d["only_in_baseline"])}')
    md_lines.append(f'- Only in run: {len(d["only_in_run"])}')
    md_lines.append('')

(OUT_DIR / 'files_list_diff.md').write_text('\n'.join(md_lines), encoding='utf-8')
print('Wrote files_list_diff.json and .md in tmp_scan_output')
