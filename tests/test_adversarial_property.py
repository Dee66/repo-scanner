import os
from pathlib import Path
import json
from src.core.quality.output_contract import generate_machine_output


def test_generated_artifact_high_without_evidence_is_dropped(tmp_path):
    # Simulate a generated artifact path
    repo = tmp_path
    gen_dir = repo / 'dist'
    gen_dir.mkdir()
    (gen_dir / 'bundle.min.js').write_text('// generated bundle', encoding='utf-8')

    analysis = {
        'repository_root': str(repo),
        'files': [str(gen_dir / 'bundle.min.js')],
        'decision_artifacts': {
            'artifacts': [
                {
                    'id': 'g1',
                    'type': 'finding',
                    'severity': 'HIGH',
                    'title': 'Generated artifact issue',
                    'evidence': [],
                    'description': 'Should be dropped because generated'
                }
            ]
        }
    }

    out = generate_machine_output(analysis, str(repo))
    arts = out.get('decision_artifacts', {}).get('artifacts', [])
    ids = [a.get('id') for a in arts]
    assert 'g1' not in ids


def test_obfuscated_comment_evidence_populates_provenance(tmp_path):
    repo = tmp_path
    f = repo / 'src' / 'module.py'
    f.parent.mkdir()
    content = """
# normal code
# o b f u s c a t e d: secret_key = 'XYZ123'  # hidden
def foo():
    pass
"""
    f.write_text(content, encoding='utf-8')

    # detector emitted a HIGH finding but attached snippet evidence matching obfuscated comment
    snippet = "o b f u s c a t e d: secret_key = 'XYZ123'"
    analysis = {
        'repository_root': str(repo),
        'files': [str(f)],
        'decision_artifacts': {
            'artifacts': [
                {
                    'id': 'o1',
                    'type': 'finding',
                    'severity': 'HIGH',
                    'title': 'Obfuscated secret',
                    'description': 'Detected obfuscated secret in comments',
                    'evidence': [
                        {
                            'repo_commit': 'unknown-commit',
                            'source_path': str(f.relative_to(repo)),
                            'snippet': snippet
                        }
                    ]
                }
            ]
        }
    }

    out = generate_machine_output(analysis, str(repo))
    arts = out.get('decision_artifacts', {}).get('artifacts', [])
    # artifact should remain
    found = next((a for a in arts if a.get('id') == 'o1'), None)
    assert found is not None
    ev = found.get('evidence', [])[0]
    # provenance fields should be populated
    assert ev.get('line_range') is not None or ev.get('byte_range') is not None


def test_polyglot_file_without_evidence_is_dropped(tmp_path):
    repo = tmp_path
    poly = repo / 'poly.txt'
    # create a polyglot-like file mixing html and js
    poly.write_text('<html><script>/* payload */ var a = 1;</script></html>', encoding='utf-8')

    analysis = {
        'repository_root': str(repo),
        'files': [str(poly)],
        'decision_artifacts': {
            'artifacts': [
                {
                    'id': 'p1',
                    'type': 'finding',
                    'severity': 'HIGH',
                    'title': 'Polyglot suspicious',
                    'description': 'No evidence attached',
                    'evidence': []
                }
            ]
        }
    }

    out = generate_machine_output(analysis, str(repo))
    arts = out.get('decision_artifacts', {}).get('artifacts', [])
    ids = [a.get('id') for a in arts]
    assert 'p1' not in ids
