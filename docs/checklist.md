# Implementation Checklist — Repo Scanner V5

## Required (P0)
- [x] docs/product.yml present and valid
- [x] docs/checklist.md present and readable
- [x] src/ exists with initial adapter (src/adapters/python_adapter.py)
- [x] tests/ contains at least one test exercising scanner CLI
- [x] pyproject.toml present and installable

## Recommended (P1)
- [x] tests/fixtures/minimal_repo produces deterministic scan
- [x] ci/verify_determinism.yml included and passing
- [x] outputs/scan_report.json generated and signed in sample run

## Nice-to-have (P2)
- [x] additional language presets (rust/java)
- [x] example API server (src/api_server.py)
