#!/usr/bin/env python3
"""Find differing JSON leaf values across deterministic run outputs."""
from pathlib import Path
import json

RUNS_DIR = Path('outputs_determinism')

def load_json(run_dir: Path):
    rpt = run_dir / 'scan_report.json'
    return json.loads(rpt.read_text(encoding='utf-8'))

def gather_paths(obj, prefix=''):
    paths = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            sub = gather_paths(v, prefix + '/' + k if prefix else k)
            paths.update(sub)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            sub = gather_paths(item, f"{prefix}[{i}]")
            paths.update(sub)
    else:
        paths[prefix] = obj
    return paths

runs = sorted([p for p in RUNS_DIR.glob('run_*') if p.is_dir()])
data = {r.name: load_json(r) for r in runs}

all_paths = {}
for name, obj in data.items():
    pmap = gather_paths(obj)
    for p, v in pmap.items():
        all_paths.setdefault(p, {})[name] = v

diffs = {}
for p, m in all_paths.items():
    # if not all equal
    vals = list(m.values())
    if len(set(map(lambda x: json.dumps(x, sort_keys=True), vals))) > 1:
        diffs[p] = m

out_path = Path('tmp_scan_output/json_leaf_diffs.json')
out_path.write_text(json.dumps({'diff_count': len(diffs), 'diffs': diffs}, indent=2), encoding='utf-8')
print(f'Found {len(diffs)} differing leaf paths; wrote tmp_scan_output/json_leaf_diffs.json')
