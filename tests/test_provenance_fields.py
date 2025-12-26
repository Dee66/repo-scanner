from pathlib import Path
from src.core.quality.output_contract import generate_machine_output


def test_provenance_population(tmp_path):
    # Create repo structure
    repo = tmp_path / 'repo'
    repo.mkdir()
    src = repo / 'file.py'
    content = 'line1\nmatch line\nline3\n'
    src.write_text(content)

    analysis = {
        'repository_root': str(repo),
        'files': [str(src)],
        'decision_artifacts': {
            'artifacts': [
                {
                    'id': 'f2',
                    'type': 'finding',
                    'severity': 'HIGH',
                    'title': 'Issue with file',
                    'description': 'Problem found',
                    'evidence': [
                        {
                            'source_path': 'file.py',
                            'snippet': 'match line'
                        }
                    ]
                }
            ]
        }
    }

    output = generate_machine_output(analysis, str(repo))
    artifacts = output.get('decision_artifacts', {}).get('artifacts', [])
    assert len(artifacts) == 1
    ev = artifacts[0].get('evidence')[0]
    assert 'line_range' in ev and isinstance(ev['line_range'], list)
    assert ev['line_range'][0] == 2
    assert 'byte_range' in ev and isinstance(ev['byte_range'], list)
    assert ev['repo_commit']  # exists (may be 'unknown-commit')
