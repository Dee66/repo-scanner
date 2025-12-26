#!/usr/bin/env python3
"""Generate a lightweight AST-based call graph and symbol index for the repo.

Outputs:
 - analysis/call_graph.json
 - analysis/symbol_index.csv

This is a best-effort static analysis (heuristic resolution of call targets).
"""
import ast
import json
import os
from pathlib import Path
import csv

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "analysis"
OUT_DIR.mkdir(exist_ok=True)

EXCLUDE_DIRS = {
    'node_modules', '__pycache__', 'build', 'dist', 'venv', '.venv', '.env',
    '.pytest_cache', 'target', 'out', '.idea', '.vscode', '.egg-info',
    '.mypy_cache', 'site-packages', 'vendor', 'third_party', 'deps'
}


def should_skip(path: Path) -> bool:
    for part in path.parts:
        if part == '.git':
            return False
        if part.startswith('.') and part != '.git':
            return True
        if part in EXCLUDE_DIRS:
            return True
    return False


def get_call_name(node: ast.AST) -> str:
    # Heuristic to extract call name from ast.Call.func
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        # recursively build attribute chain
        parts = []
        cur = node
        while isinstance(cur, ast.Attribute):
            parts.append(cur.attr)
            cur = cur.value
        if isinstance(cur, ast.Name):
            parts.append(cur.id)
        return ".".join(reversed(parts))
    return ast.dump(node)


def analyze_file(py_path: Path):
    try:
        src = py_path.read_text()
    except Exception:
        return [], []

    try:
        tree = ast.parse(src)
    except SyntaxError:
        return [], []

    symbols = []
    edges = []

    # Track current function or class context while walking
    class FuncVisitor(ast.NodeVisitor):
        def __init__(self, filename):
            self.filename = filename
            self.context = []

        def visit_FunctionDef(self, node):
            fullname = "+".join(self.context + [node.name]) or node.name
            symbols.append({
                'symbol': fullname,
                'type': 'function',
                'file': str(self.filename),
                'lineno': node.lineno
            })
            self.context.append(node.name)
            self.generic_visit(node)
            self.context.pop()

        def visit_AsyncFunctionDef(self, node):
            return self.visit_FunctionDef(node)

        def visit_ClassDef(self, node):
            fullname = "+".join(self.context + [node.name]) or node.name
            symbols.append({
                'symbol': fullname,
                'type': 'class',
                'file': str(self.filename),
                'lineno': node.lineno
            })
            self.context.append(node.name)
            self.generic_visit(node)
            self.context.pop()

        def visit_Call(self, node):
            # resolve callee name heuristically
            callee = None
            try:
                callee = get_call_name(node.func)
            except Exception:
                callee = ast.dump(node.func)

            caller = "+".join(self.context) if self.context else '<module>'
            edges.append({
                'caller': caller,
                'callee': callee,
                'file': str(self.filename),
                'lineno': getattr(node, 'lineno', None)
            })
            self.generic_visit(node)

    visitor = FuncVisitor(py_path)
    visitor.visit(tree)

    # Also add module-level symbol
    symbols.append({
        'symbol': '<module>',
        'type': 'module',
        'file': str(py_path),
        'lineno': 1
    })

    return symbols, edges


def main():
    all_symbols = []
    all_edges = []

    for p in ROOT.rglob('*.py'):
        if should_skip(p.relative_to(ROOT)):
            continue
        # skip the virtual environment inside repo if any
        if '\n' in str(p):
            continue
        symbols, edges = analyze_file(p)
        all_symbols.extend(symbols)
        all_edges.extend(edges)

    # Write outputs
    call_graph = {
        'nodes': all_symbols,
        'edges': all_edges
    }

    with open(OUT_DIR / 'call_graph.json', 'w') as f:
        json.dump(call_graph, f, indent=2)

    # symbol index CSV
    with open(OUT_DIR / 'symbol_index.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['symbol', 'type', 'file', 'lineno'])
        writer.writeheader()
        for s in all_symbols:
            writer.writerow({k: s.get(k) for k in ['symbol', 'type', 'file', 'lineno']})

    print(f"Wrote {len(all_symbols)} symbols and {len(all_edges)} edges to {OUT_DIR}")


if __name__ == '__main__':
    main()
