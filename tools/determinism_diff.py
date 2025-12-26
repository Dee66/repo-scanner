#!/usr/bin/env python3
"""Compare deterministic run outputs by canonicalizing JSON and diffing."""
from pathlib import Path
import json
import difflib

RUNS_DIR = Path('outputs_determinism')
OUT_DIR = Path('tmp_scan_output')
OUT_DIR.mkdir(exist_ok=True)


def canonicalize(obj):
    # Recursively canonicalize JSON: sort dict keys; sort lists if possible
    if isinstance(obj, dict):
        return {k: canonicalize(obj[k]) for k in sorted(obj.keys())}
    if isinstance(obj, list):
        # if list of dicts with 'id', sort by id
        if all(isinstance(x, dict) and 'id' in x for x in obj):
            return sorted((canonicalize(x) for x in obj), key=lambda d: d.get('id'))
        # if list of primitives, sort
        if all(not isinstance(x, (dict, list)) for x in obj):
            try:
                return sorted(obj)
            except Exception:
                return [canonicalize(x) for x in obj]
        return [canonicalize(x) for x in obj]
    return obj


def load_and_canon(path: Path):
    data = json.loads(path.read_text(encoding='utf-8'))
    return canonicalize(data)


def main():
    runs = sorted([p for p in RUNS_DIR.glob('run_*') if p.is_dir()])
    if not runs:
        print('No run directories found under outputs_determinism/')
        return

    canon_texts = {}
    raw_texts = {}
    for r in runs:
        rpt = r / 'scan_report.json'
        if not rpt.exists():
            print('Missing', rpt)
            continue
        canon = load_and_canon(rpt)
        txt = json.dumps(canon, indent=2, ensure_ascii=False, sort_keys=True)
        canon_texts[r.name] = txt.splitlines()
        raw_texts[r.name] = rpt.read_text(encoding='utf-8').splitlines()

    # Choose first run as baseline
    baseline = runs[0].name
    diffs = {}
    for name, lines in canon_texts.items():
        if name == baseline:
            continue
        d = list(difflib.unified_diff(canon_texts[baseline], lines, fromfile=baseline, tofile=name, lineterm=''))
        diffs[name] = d

    # Write report
    report = {
        'baseline': baseline,
        'runs': list(canon_texts.keys()),
        'diffs': {k: len(v) for k, v in diffs.items()}
    }
    (OUT_DIR / 'determinism_canonical_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')

    md = ['# Determinism Canonical Diff Report', '', f'- Baseline: {baseline}', '']
    for name, d in diffs.items():
        md.append(f'## Diff: {baseline} -> {name} (lines changed: {len(d)})')
        if d:
            md.append('```diff')
            md.extend(d[:400])
            if len(d) > 400:
                md.append('... (truncated)')
            md.append('```')
        md.append('')

    (OUT_DIR / 'determinism_canonical_report.md').write_text('\n'.join(md), encoding='utf-8')
    print('Wrote determinism_canonical_report.json and .md in tmp_scan_output')


if __name__ == '__main__':
    main()
