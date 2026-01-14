# Project Organization

## Directory Structure

```
Repo-Scanner/
├── 📄 README.md              # Project documentation
├── 📄 LICENSE                # MIT License
├── 📄 CHANGELOG.md           # Version history
├── 📄 RELEASE.md             # Release notes
├── ⚙️  pyproject.toml         # Python project configuration
├── ⚙️  pytest.ini             # Test configuration
├── 🐳 docker-compose.yml     # Docker orchestration
├── 🐳 Dockerfile             # Production container
├── 🐳 Dockerfile.test        # Test container
│
├── 📁 src/                   # Source code
├── 📁 tests/                 # Test suite
│
├── 📁 docs/                  # Documentation
│   ├── phase_reports/        # Phase completion reports
│   ├── old_reports/          # Historical scan reports
│   └── *.md                  # General documentation
│
├── 📁 scripts/               # Utility scripts
│   ├── batch_scan_repos.py
│   ├── validate_zero_fp_production.py
│   └── test_*.py             # Test scripts
│
├── 📁 reports/               # Generated reports
│   ├── scan_results/         # Scan output directories
│   ├── deployment/           # Deployment reports
│   ├── validation/           # Validation reports
│   └── *.json                # JSON reports
│
├── 📁 test_data/             # Test repositories and data
│   ├── test_governance/
│   ├── test_intent/
│   ├── test_repositories/
│   └── *.txt                 # Repository lists
│
├── 📁 archive/               # Historical/deprecated files
│   └── deployment/           # Old deployment reports
│
├── 📁 config/                # Configuration files
├── 📁 schemas/               # JSON schemas
├── 📁 templates/             # Report templates
├── 📁 ci/                    # CI/CD scripts
├── 📁 deployment/            # Deployment configs
├── 📁 helm/                  # Kubernetes Helm charts
├── 📁 k8s/                   # Kubernetes manifests
├── 📁 monitoring/            # Monitoring configs
├── 📁 tools/                 # Additional tools
├── 📁 validation/            # Validation scripts
├── 📁 validation_data/       # Validation test data
├── 📁 experiments/           # Experimental features
└── 📁 sme_reviews/           # SME review data
```

## File Organization Guidelines

### Keep in Root
- Essential project files (README, LICENSE, etc.)
- Build/package configuration (pyproject.toml, pytest.ini)
- Docker configuration (docker-compose.yml, Dockerfile)
- Core directories (src/, tests/)

### Documentation (docs/)
- All .md files except README, LICENSE, CHANGELOG, RELEASE
- Phase reports in docs/phase_reports/
- Old reports in docs/old_reports/

### Scripts (scripts/)
- All .py scripts except src/ code
- All .sh shell scripts
- Test utility scripts

### Reports (reports/)
- All scan results and outputs
- JSON reports and logs
- Deployment and validation reports

### Test Data (test_data/)
- Test repositories
- Test fixtures
- Repository lists (.txt files)

### Archive (archive/)
- Old deployment reports
- Deprecated documentation
- Historical validation reports

## Maintenance

### Regular Cleanup Tasks
1. Remove old scan results from reports/ (monthly)
2. Archive completed phase reports (after major releases)
3. Clean up test_data/ temporary files (weekly)
4. Review and remove unused experiments/ (quarterly)

### Never Delete
- src/ (source code)
- tests/ (test suite)
- docs/phase_reports/ (historical record)
- config/ (configuration)
- schemas/ (data schemas)

## Quick Reference

**Find a script:** Check `scripts/`
**Find documentation:** Check `docs/`
**Find scan results:** Check `reports/scan_results/`
**Find test data:** Check `test_data/`
**Find old reports:** Check `docs/old_reports/` or `archive/`
