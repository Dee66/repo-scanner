from pathlib import Path
from src.core.quality.output_contract import generate_machine_output


def test_provenance_population_for_existing_source(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    src_dir = repo / "src"
    src_dir.mkdir()
    file_path = src_dir / "file.py"
    content = "line1\nline2\nUNIQUE_SNIPPET\nline4\n"
    file_path.write_text(content)

    analysis = {
        'repository_root': str(repo),
        'files': [str(file_path)],
        'decision_artifacts': {
            'artifacts': [
                {
                    'id': 'f2',
                    'type': 'finding',
                    'severity': 'HIGH',
                    'title': 'Issue with evidence',
                    'description': 'An important problem',
                    'evidence': [
                        {
                            'source_path': str(file_path),
                            'snippet': 'UNIQUE_SNIPPET'
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
    assert 'line_range' in ev and isinstance(ev['line_range'], list) and len(ev['line_range']) == 2
    assert 'byte_range' in ev and isinstance(ev['byte_range'], list) and len(ev['byte_range']) == 2
