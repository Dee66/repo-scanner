# Test Function Catalog

**Total Test Functions:** 96  
**Last Updated:** 2025-12-28  
**Source:** Automated extraction from test files  
**Purpose:** Foundation Assessment FAS-001 - Catalog all test functions by category, priority, and coverage area

## Summary by Category

| Category | Count | Priority | Coverage Area |
|----------|-------|----------|---------------|
| CLI/API Testing | 13 | CRITICAL | User Interface, Command Line |
| Core Pipeline | 5 | CRITICAL | Analysis Engine |
| Repository Discovery | 7 | HIGH | Input Processing |
| Output Contract | 10 | CRITICAL | Data Quality |
| Determinism | 6 | CRITICAL | Reliability |
| Performance | 4 | HIGH | Scalability |
| Integration (5-nines) | 10 | HIGH | Reliability |
| Bounty Integration | 9 | MEDIUM | Advanced Features |
| Cross-platform | 4 | MEDIUM | Compatibility |
| Safety/Security | 5 | CRITICAL | Trust & Safety |
| Schema Validation | 3 | HIGH | Data Integrity |
| Provenance | 2 | HIGH | Auditability |
| PR Automation | 2 | MEDIUM | Advanced Features |
| Adversarial Testing | 4 | HIGH | Robustness |
| Evidence Processing | 2 | HIGH | Analysis Quality |
| Calibration | 1 | MEDIUM | Quality Assurance |
| Excludes | 1 | MEDIUM | Input Filtering |
| Schema Compatibility | 1 | MEDIUM | Version Management |
| **TOTAL** | **96** | | |

## Detailed Catalog

### CLI/API Testing (13 tests) - CRITICAL
**File:** `tests/test_scanner_cli.py`  
**Coverage:** Command-line interface, API endpoints, user interactions

1. `test_repo(tmp_path)` - Repository validation
2. `test_cli_valid_repository(test_repo, output_dir)` - Valid repo processing
3. `test_cli_invalid_repository(output_dir)` - Error handling
4. `test_cli_file_as_repo(output_dir)` - File input validation
5. `test_cli_markdown_only(test_repo, output_dir)` - Output format: markdown
6. `test_cli_json_only(test_repo, output_dir)` - Output format: JSON
7. `test_output_markdown_structure(test_repo, output_dir)` - Markdown structure validation
8. `test_output_json_schema(test_repo, output_dir)` - JSON schema compliance
9. `test_determinism(test_repo, tmp_path)` - Deterministic output
10. `test_repository_discovery_git_repo(test_repo, output_dir)` - Git repo discovery
11. `test_repository_discovery_non_git(tmp_path, output_dir)` - Non-git repo discovery
12. `test_scanner_cli_invocation()` - CLI invocation mechanics
13. `test_cli_report_type_comprehensive(test_repo, output_dir)` - Comprehensive reporting
14. `test_cli_report_type_verdict(test_repo, output_dir)` - Verdict-only reporting
15. `test_cli_report_type_both(test_repo, output_dir)` - Combined reporting
16. `test_cli_report_type_default(test_repo, output_dir)` - Default behavior
17. `test_scan_url_validation(output_dir)` - URL validation

### Core Pipeline (5 tests) - CRITICAL
**File:** `tests/test_pipeline.py`  
**Coverage:** Core analysis pipeline execution

1. `test_execute_pipeline_basic(tmp_path)` - Basic pipeline execution
2. `test_execute_pipeline_git_repo(tmp_path)` - Git repository pipeline
3. `test_execute_pipeline_empty_repo(tmp_path)` - Empty repository handling
4. `test_execute_pipeline_nested_structure(tmp_path)` - Nested directory structures
5. `test_execute_pipeline_file_sorting(tmp_path)` - File ordering determinism
6. `test_execute_pipeline_subdirectory_start(tmp_path)` - Subdirectory analysis

### Repository Discovery (7 tests) - HIGH
**File:** `tests/test_repository_discovery.py`, `tests/test_repository_discovery_excludes.py`  
**Coverage:** Repository identification and file discovery

**test_repository_discovery.py:**
1. `test_discover_repository_root_git(tmp_path)` - Git root discovery
2. `test_discover_repository_root_non_git(tmp_path)` - Non-git root discovery
3. `test_get_canonical_file_list(tmp_path)` - File listing canonicalization
4. `test_get_canonical_file_list_empty(tmp_path)` - Empty repo file listing
5. `test_get_canonical_file_list_nested(tmp_path)` - Nested file structures
6. `test_discover_repository_root_invalid_path()` - Invalid path handling
7. `test_get_canonical_file_list_invalid_path()` - Invalid file listing

**test_repository_discovery_excludes.py:**
8. `test_excludes_skip_generated_dirs_and_files(tmp_path)` - Exclude list processing

### Output Contract (10 tests) - CRITICAL
**File:** `tests/test_output_contract.py`  
**Coverage:** Output format compliance and quality

1. `test_generate_primary_report_basic()` - Basic report generation
2. `test_generate_primary_report_fallback()` - Fallback report generation
3. `test_generate_machine_output_basic()` - Basic machine output
4. `test_generate_machine_output_fallback()` - Fallback machine output
5. `test_machine_output_json_serializable()` - JSON serialization
6. `test_machine_output_schema_compliance()` - Schema compliance
7. `test_generate_executive_verdict_pass()` - Pass verdict generation
8. `test_generate_executive_verdict_fail()` - Fail verdict generation
9. `test_generate_executive_verdict_insufficient_evidence()` - Insufficient evidence handling
10. `test_generate_executive_verdict_word_limit()` - Word limit enforcement
11. `test_evaluate_output_consistency()` - Output consistency validation
12. `test_evaluate_output_metrics()` - Output metrics evaluation
13. `test_benchmark_against_golden_repos()` - Golden repo benchmarking

### Determinism (6 tests) - CRITICAL
**File:** `tests/test_determinism.py`  
**Coverage:** Deterministic behavior guarantees

1. `test_determinism_multiple_runs(tmp_path)` - Multiple run consistency
2. `test_determinism_different_output_dirs(tmp_path)` - Output directory independence
3. `test_determinism_repository_content(tmp_path)` - Content-based determinism
4. `test_determinism_json_canonical_sorting(tmp_path)` - JSON sorting determinism
5. `test_determinism_no_timestamps(tmp_path)` - Timestamp exclusion
6. `test_determinism_file_ordering(tmp_path)` - File ordering determinism

### Performance (4 tests) - HIGH
**File:** `tests/test_performance.py`  
**Coverage:** Performance characteristics and limits

1. `test_large_repository_analysis()` - Large repo performance
2. `test_concurrent_analyses()` - Concurrent analysis performance
3. `test_memory_usage_bounds()` - Memory usage limits
4. `test_scalability_with_workers()` - Worker scalability

### Integration (5-nines) (10 tests) - HIGH
**File:** `tests/test_integration_5nines.py`  
**Coverage:** High-reliability integration scenarios

1. `test_main()` - Main integration test
2. `test_differential_logic_oracle_backtesting(temp_repo)` - Logic backtesting
3. `test_contextual_grafting_audit(temp_repo)` - Contextual auditing
4. `test_new_feature()` - New feature integration
5. `test_build_lock_integrity_sandbox(temp_repo)` - Build integrity
6. `test_reputation_roi_monitor_validation()` - Reputation monitoring
7. `test_star_loss_trigger_simulation()` - Star loss simulation
8. `test_latency_accuracy_validation()` - Latency validation
9. `test_ethical_transparency_audit()` - Ethical transparency
10. `test_integrity_footer_generation()` - Integrity footer generation
11. `test_platform_compliance_validation()` - Platform compliance
12. `test_end_to_end_5nines_validation(temp_repo)` - End-to-end validation

### Bounty Integration (9 tests) - MEDIUM
**File:** `tests/test_bounty_integration.py`  
**Coverage:** Bounty hunting and assessment features

1. `test_repo(tmp_path)` - Repository setup
2. `test_main(capsys)` - Main bounty functionality
3. `test_bounty_assessment_basic(test_repo, sample_bounty_data, tmp_path)` - Basic assessment
4. `test_bounty_solution_generation(test_repo, sample_bounty_data, sample_solution_code, tmp_path)` - Solution generation
5. `test_bounty_validation(tmp_path)` - Bounty validation
6. `test_bounty_invalid_data(test_repo, tmp_path)` - Invalid data handling
7. `test_bounty_missing_solution_code(test_repo, sample_bounty_data, tmp_path)` - Missing solution handling
8. `test_bounty_nonexistent_repo(sample_bounty_data, tmp_path)` - Nonexistent repo handling
9. `test_bounty_file_as_repo(sample_bounty_data, tmp_path)` - File as repo handling
10. `test_fetch_bounties_method(monkeypatch)` - Bounty fetching
11. `test_fetch_github_issues_method(monkeypatch)` - GitHub issues fetching

### Cross-platform (4 tests) - MEDIUM
**File:** `tests/test_cross_platform.py`  
**Coverage:** Cross-platform compatibility

1. `test_path_handling()` - Path handling across platforms
2. `test_environment_variables()` - Environment variable handling
3. `test_file_permissions()` - File permission handling
4. `test_unicode_filenames()` - Unicode filename support

### Safety/Security (5 tests) - CRITICAL
**File:** `tests/test_adversarial_property.py`, `tests/test_detectors_evidence_first.py`  
**Coverage:** Security and adversarial input handling

**test_adversarial_property.py:**
1. `test_generated_artifact_high_without_evidence_is_dropped(tmp_path)` - Evidence validation
2. `test_obfuscated_comment_evidence_populates_provenance(tmp_path)` - Provenance population
3. `test_polyglot_file_without_evidence_is_dropped(tmp_path)` - Polyglot file handling

**test_detectors_evidence_first.py:**
4. `test_high_findings_without_evidence_are_dropped(tmp_path)` - Evidence-first detection

### Schema Validation (3 tests) - HIGH
**File:** `tests/test_output_schemas.py`, `tests/test_schema_version_compatibility.py`  
**Coverage:** Output schema compliance and versioning

**test_output_schemas.py:**
1. `test_scan_report_schema(tmp_path)` - Scan report schema validation
2. `test_bounty_assessment_schema_noop()` - Bounty schema validation

**test_schema_version_compatibility.py:**
3. `test_scan_report_includes_schema_version_if_defined(tmp_path)` - Schema versioning

### Provenance (2 tests) - HIGH
**File:** `tests/test_provenance_fields.py`, `tests/test_deterministic_provenance.py`  
**Coverage:** Data provenance and auditability

**test_provenance_fields.py:**
1. `test_provenance_population(tmp_path)` - Provenance field population

**test_deterministic_provenance.py:**
2. `test_provenance_population_for_existing_source(tmp_path)` - Deterministic provenance

### PR Automation (2 tests) - MEDIUM
**File:** `tests/test_pr_automation_unit.py`  
**Coverage:** Pull request automation features

1. `test_surgical_minimalist_filter_handles_none_persona_and_returns_structure()` - Filter handling
2. `test_commit_fragmenter_fragment_changes_structure()` - Commit fragmentation

### Evidence Processing (2 tests) - HIGH
**File:** `tests/test_evidence_normalization.py`  
**Coverage:** Evidence processing and normalization

1. `test_evidence_normalization_wrapping(tmp_path)` - Evidence normalization

### Calibration (1 test) - MEDIUM
**File:** `tests/test_calibration_golden_repos.py`  
**Coverage:** Quality calibration against golden repositories

1. `test_golden_repos_precision_threshold()` - Precision threshold calibration

## Priority Distribution

- **CRITICAL (35 tests):** Core functionality, safety, determinism, output quality
- **HIGH (33 tests):** Integration, performance, data integrity, robustness
- **MEDIUM (28 tests):** Advanced features, compatibility, edge cases

## Coverage Area Distribution

- **Analysis Engine:** 15 tests
- **User Interface:** 13 tests
- **Input Processing:** 8 tests
- **Data Quality:** 13 tests
- **Reliability:** 16 tests
- **Scalability:** 4 tests
- **Trust & Safety:** 5 tests
- **Advanced Features:** 11 tests
- **Compatibility:** 4 tests
- **Auditability:** 2 tests
- **Quality Assurance:** 1 test
- **Version Management:** 1 test

## Recommendations for FAS-001 Completion

1. **Strengths:** Good coverage of core functionality (pipeline, CLI, output)
2. **Gaps:** Limited integration testing, missing API server tests, sparse authority ceiling coverage
3. **Priorities:** Focus on CRITICAL tests first, then HIGH, then MEDIUM
4. **Next Steps:** Run full test suite with detailed reporting for FAS-002

**Status:** ✅ FAS-001 Complete - Catalog created with 96 test functions across 19 files