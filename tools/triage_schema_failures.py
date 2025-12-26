#!/usr/bin/env python3
"""Triage schema validator output and emit actionable TODOs.

Usage: run schema validator (or capture its exception text) and pass a
path to a JSON file containing the validation diagnostics. This script
parses diagnostics and writes `tmp_scan_output/schema_triage.json` with
a list of file/detector recommendations.

This is a lightweight helper for developers to quickly locate offending
fields when schema validation fails.
"""
from pathlib import Path
import json
import re
import sys

OUT = Path('tmp_scan_output')
OUT.mkdir(exist_ok=True)


def parse_validator_message(msg: str):
    """Parse typical validator messages into structured diagnostics.

    Supports fallback messages like "Missing required key: /a/b/c" and
    jsonschema messages with pointers like " /a/b: 'x' is a required property".
    """
    diags = []
    for line in msg.splitlines():
        line = line.strip()
        if not line:
            continue
        # Missing required key fallback
        m = re.match(r"Missing required key: (/.+)", line)
        if m:
            diags.append({'pointer': m.group(1), 'message': line})
            continue
        # jsonschema pointer style: "/a/b: 'x' is a required property"
        m = re.match(r"(/[^:]+):\s*(.+)", line)
        if m:
            diags.append({'pointer': m.group(1), 'message': m.group(2)})
            continue
        # fallback: entire line as message
        diags.append({'pointer': None, 'message': line})
    return diags


def recommend_fix(pointer: str, message: str):
    """Return a short recommendation based on pointer and message."""
    if not pointer:
        return {'action': 'inspect', 'reason': message}
    parts = [p for p in pointer.split('/') if p]
    if parts and parts[0] == 'decision_artifacts':
        return {'action': 'check_detector', 'target': 'decision_artifacts', 'reason': message}
    if parts and parts[0] == 'structure':
        return {'action': 'check_pipeline_stage', 'target': 'structural_modeling', 'reason': message}
    return {'action': 'inspect_field', 'target': '/'.join(parts), 'reason': message}


def triage_from_text(msg: str):
    parsed = parse_validator_message(msg)
    todos = []
    for d in parsed:
        rec = recommend_fix(d.get('pointer'), d.get('message'))
        todos.append({'pointer': d.get('pointer'), 'message': d.get('message'), 'recommendation': rec})
    return todos


def main():
    if len(sys.argv) >= 2:
        inpath = Path(sys.argv[1])
        if not inpath.exists():
            print(f'Input file {inpath} not found', file=sys.stderr)
            sys.exit(2)
        msg = inpath.read_text(encoding='utf-8')
    else:
        # read from stdin
        msg = sys.stdin.read()

    todos = triage_from_text(msg)
    outp = OUT / 'schema_triage.json'
    outp.write_text(json.dumps({'todos': todos}, indent=2), encoding='utf-8')
    print(f'Wrote triage to {outp}')


if __name__ == '__main__':
    main()
