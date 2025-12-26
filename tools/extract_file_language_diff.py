#!/usr/bin/env python3
"""Extract file->language mappings from scan_report.json across runs and report differences."""
from pathlib import Path
import json

RUNS_DIR = Path('outputs_determinism')
OUT_DIR = Path('tmp_scan_output')
OUT_DIR.mkdir(exist_ok=True)

def load_lang_map(rpt_path):
    data = json.loads(rpt_path.read_text(encoding='utf-8'))
    # try common locations where per-file language is recorded
    maps = {}
    # search recursively for dicts with 'file' and 'language'
    def walk(obj):
        if isinstance(obj, dict):
            if 'file' in obj and 'language' in obj:
                maps[obj['file']] = obj.get('language')
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)
    walk(data)
    return maps

results = {}
for run in sorted(p for p in RUNS_DIR.glob('run_*') if p.is_dir()):
    rpt = run / 'scan_report.json'
    if not rpt.exists():
        continue
    results[run.name] = load_lang_map(rpt)

# compute differing files
all_files = set()
for m in results.values():
    all_files.update(m.keys())

diffs = {}
for f in sorted(all_files):
    vals = {r: results[r].get(f) for r in results}
    uniq = set(v for v in vals.values())
    if len(uniq) > 1:
        diffs[f] = vals

json_path = OUT_DIR / 'file_language_diffs.json'
json_path.write_text(json.dumps({'counts': {r: len(results[r]) for r in results}, 'diffs': diffs}, indent=2), encoding='utf-8')
print(f'Wrote {json_path} with {len(diffs)} differing files')
