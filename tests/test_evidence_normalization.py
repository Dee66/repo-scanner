from src.core.quality.output_contract import generate_machine_output


def test_evidence_normalization_wrapping(tmp_path):
    # Create a fake analysis with a HIGH severity artifact with string evidence
    analysis = {
        'repository_root': str(tmp_path),
        'files': [],
        'decision_artifacts': {
            'artifacts': [
                {
                    'id': 'f1',
                    'type': 'finding',
                    'severity': 'HIGH',
                    'title': 'Critical issue',
                    'description': 'An important problem',
                    'evidence': 'Found in module X'
                }
            ]
        }
    }

    output = generate_machine_output(analysis, str(tmp_path))
    artifacts = output.get('decision_artifacts', {}).get('artifacts', [])
    assert len(artifacts) == 1
    ev = artifacts[0].get('evidence')
    assert isinstance(ev, list)
    assert len(ev) == 1
    assert isinstance(ev[0], dict)
    assert 'repo_commit' in ev[0]
    assert 'source_path' in ev[0]
