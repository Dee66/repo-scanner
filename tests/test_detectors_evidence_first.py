from src.core.quality.output_contract import generate_machine_output


def test_high_findings_without_evidence_are_dropped(tmp_path):
    analysis = {
        'repository_root': str(tmp_path),
        'files': [],
        'decision_artifacts': {
            'artifacts': [
                {
                    'id': 'a1',
                    'type': 'finding',
                    'severity': 'HIGH',
                    'title': 'No evidence',
                    'description': 'Should be dropped',
                    'evidence': []
                },
                {
                    'id': 'a2',
                    'type': 'finding',
                    'severity': 'LOW',
                    'title': 'Low severity without evidence',
                    'description': 'Should be kept',
                    'evidence': []
                }
            ]
        }
    }

    out = generate_machine_output(analysis, str(tmp_path))
    artifacts = out.get('decision_artifacts', {}).get('artifacts', [])
    ids = [a.get('id') for a in artifacts]
    assert 'a1' not in ids
    assert 'a2' in ids
