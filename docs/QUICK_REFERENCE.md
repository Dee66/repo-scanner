# Quick Reference - Where to Find Things

## 📍 Need to Find Something?

### Documentation
- **Phase reports:** `docs/phase_reports/`
- **Old scan reports:** `docs/old_reports/`
- **General docs:** `docs/`
- **Project structure:** `docs/PROJECT_ORGANIZATION.md`
- **This guide:** `docs/QUICK_REFERENCE.md`

### Scripts
- **All Python scripts:** `scripts/`
- **Batch scanning:** `scripts/batch_scan_repos.py`
- **Validation:** `scripts/validate_zero_fp_production.py`
- **Test scripts:** `scripts/test_*.py`

### Reports & Results
- **Scan results:** `reports/scan_results/`
- **JSON reports:** `reports/*.json`
- **Deployment logs:** `reports/deployment/`
- **Validation reports:** `reports/validation/`

### Test Data
- **Test repositories:** `test_data/test_*/`
- **Repository lists:** `test_data/*.txt`
- **Test fixtures:** `test_data/`

### Configuration
- **Project config:** `pyproject.toml`
- **Test config:** `pytest.ini`
- **App configs:** `config/`
- **Schemas:** `schemas/`
- **Templates:** `templates/`

### Deployment
- **Docker:** `docker-compose.yml`, `Dockerfile`
- **Kubernetes:** `k8s/`, `helm/`
- **CI/CD:** `ci/`
- **Deployment configs:** `deployment/`

### Source Code
- **Main code:** `src/`
- **Tests:** `tests/`
- **Tools:** `tools/`
- **Experiments:** `experiments/`

## 🗂️ Directory Quick Access

```bash
# Navigate to common locations
cd src/                    # Source code
cd tests/                  # Test suite
cd docs/                   # Documentation
cd scripts/                # Utility scripts
cd reports/scan_results/   # Scan outputs
cd test_data/              # Test repositories
```

## 🧹 Cleanup Commands

```bash
# Clean build artifacts (safe)
rm -rf __pycache__ .pytest_cache .coverage htmlcov/

# Clean old scan results (review first!)
rm -rf reports/scan_results/old_*/

# Clean test outputs
rm -rf test_data/tmp_*
```

## 📦 Common Tasks

### Run scanner
```bash
python src/cli.py scan /path/to/repo --output-dir reports/scan_results/
```

### Run tests
```bash
pytest tests/
```

### Generate docs
```bash
# Check docs/ directory for latest reports
ls -lh docs/phase_reports/
```

### Batch scan
```bash
python scripts/batch_scan_repos.py --input test_data/demo_repos.txt
```

## 🔍 Search Tips

```bash
# Find a specific file
find . -name "filename.py"

# Search in documentation
grep -r "keyword" docs/

# List recent scan results
ls -lt reports/scan_results/ | head -10

# Find Python scripts
find scripts/ -name "*.py"
```

## ⚠️ Never Delete
- `src/` - Source code
- `tests/` - Test suite  
- `config/` - Configuration
- `schemas/` - Data schemas
- `docs/phase_reports/` - Historical records

## 📞 Need Help?
Check `README.md` in the project root for full documentation.
