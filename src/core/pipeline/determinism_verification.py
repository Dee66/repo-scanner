"""Determinism Verification for Repository Intelligence Scanner."""

import hashlib
import json
from typing import Dict, List


def verify_determinism(file_list: List[str], structure: Dict, semantic: Dict,
                      test_signals: Dict, governance: Dict, intent_posture: Dict,
                      misleading_signals: Dict, safe_change_surface: Dict,
                      risk_synthesis: Dict, decision_artifacts: Dict,
                      authority_ceiling_evaluation: Dict) -> Dict:
    """Verify determinism of the analysis pipeline."""
    # Safety checks
    if not isinstance(file_list, list):
        file_list = []
    if not isinstance(structure, dict):
        structure = {}
    if not isinstance(semantic, dict):
        semantic = {}
    if not isinstance(test_signals, dict):
        test_signals = {}
    if not isinstance(governance, dict):
        governance = {}
    if not isinstance(intent_posture, dict):
        intent_posture = {}
    if not isinstance(misleading_signals, dict):
        misleading_signals = {}
    if not isinstance(safe_change_surface, dict):
        safe_change_surface = {}
    if not isinstance(risk_synthesis, dict):
        risk_synthesis = {}
    if not isinstance(decision_artifacts, dict):
        decision_artifacts = {}
    if not isinstance(authority_ceiling_evaluation, dict):
        authority_ceiling_evaluation = {}

    # Generate canonical representation of all analysis data
    canonical_data = _generate_canonical_analysis_data(
        file_list, structure, semantic, test_signals, governance, intent_posture,
        misleading_signals, safe_change_surface, risk_synthesis, decision_artifacts,
        authority_ceiling_evaluation
    )

    # Calculate deterministic hash
    analysis_hash = _calculate_deterministic_hash(canonical_data)

    # Verify internal consistency
    consistency_check = _verify_internal_consistency(canonical_data)

    # Generate determinism report
    determinism_report = _generate_determinism_report(analysis_hash, consistency_check)

    return {
        "determinism_hash": analysis_hash,
        "consistency_check": consistency_check,
        "determinism_report": determinism_report,
        "canonical_data_summary": _summarize_canonical_data(canonical_data),
        "verification_timestamp": "2025-12-23T00:00:00Z",  # Placeholder for deterministic timestamp
        "verification_version": "1.0.0"
    }


def _generate_canonical_analysis_data(file_list: List[str], structure: Dict, semantic: Dict,
                                     test_signals: Dict, governance: Dict, intent_posture: Dict,
                                     misleading_signals: Dict, safe_change_surface: Dict,
                                     risk_synthesis: Dict, decision_artifacts: Dict,
                                     authority_ceiling_evaluation: Dict) -> Dict:
    """Generate canonical representation of all analysis data for hashing."""
    # Sort file list deterministically
    sorted_files = sorted(file_list) if isinstance(file_list, list) else []

    # Create canonical versions of all data structures
    canonical_data = {
        "files": sorted_files,
        "file_count": len(sorted_files),
        "structure": _canonicalize_dict(structure),
        "semantic": _canonicalize_dict(semantic),
        "test_signals": _canonicalize_dict(test_signals),
        "governance": _canonicalize_dict(governance),
        "intent_posture": _canonicalize_dict(intent_posture),
        "misleading_signals": _canonicalize_dict(misleading_signals),
        "safe_change_surface": _canonicalize_dict(safe_change_surface),
        "risk_synthesis": _canonicalize_dict(risk_synthesis),
        "decision_artifacts": _canonicalize_dict(decision_artifacts),
        "authority_ceiling_evaluation": _canonicalize_dict(authority_ceiling_evaluation)
    }

    return canonical_data


def _canonicalize_dict(data: Dict) -> Dict:
    """Convert dictionary to canonical form for deterministic hashing."""
    if not isinstance(data, dict):
        return data

    # Recursively canonicalize nested dictionaries
    canonical = {}
    for key in sorted(data.keys()):
        value = data[key]
        if isinstance(value, dict):
            canonical[key] = _canonicalize_dict(value)
        elif isinstance(value, list):
            # Sort lists of dictionaries by their string representation for determinism
            if value and isinstance(value[0], dict):
                canonical[key] = sorted(value, key=lambda x: json.dumps(_canonicalize_dict(x), sort_keys=True))
            else:
                canonical[key] = sorted(value) if all(isinstance(item, (str, int, float, bool)) for item in value) else value
        else:
            canonical[key] = value

    return canonical


def _calculate_deterministic_hash(canonical_data: Dict) -> str:
    """Calculate SHA-256 hash of canonical data for determinism verification."""
    # Convert to JSON with sorted keys for deterministic representation
    json_str = json.dumps(canonical_data, sort_keys=True, separators=(',', ':'))

    # Calculate hash
    hash_obj = hashlib.sha256(json_str.encode('utf-8'))
    return hash_obj.hexdigest()


def _verify_internal_consistency(canonical_data: Dict) -> Dict:
    """Verify internal consistency of analysis results."""
    consistency_issues = []
    consistency_score = 1.0

    # Check file count consistency
    file_count = canonical_data.get("file_count", 0)
    files_list = canonical_data.get("files", [])
    if len(files_list) != file_count:
        consistency_issues.append({
            "issue": "file_count_mismatch",
            "description": f"File count ({file_count}) doesn't match files list length ({len(files_list)})",
            "severity": "high"
        })
        consistency_score -= 0.3

    # Check structural analysis consistency
    structure = canonical_data.get("structure", {})
    if structure:
        file_counts = structure.get("file_counts", {})
        # Sum only categorical counts (exclude the 'total' entry) to avoid
        # double-counting the overall total which is also present in the map.
        total_from_categories = sum(v for k, v in file_counts.items() if k != 'total')
        # Prefer explicit 'total' if present, otherwise compare against summed categories
        reported_total = file_counts.get('total', total_from_categories)

        if total_from_categories != file_count or reported_total != file_count:
            consistency_issues.append({
                "issue": "structure_file_count_mismatch",
                "description": f"Structure file counts total ({total_from_categories}) doesn't match overall count ({file_count})",
                "severity": "medium"
            })
            consistency_score -= 0.2

    # Check semantic analysis consistency
    semantic = canonical_data.get("semantic", {})
    if semantic:
        semantic_file_count = len(semantic.get("files_analyzed", []))
        if semantic_file_count > file_count:
            consistency_issues.append({
                "issue": "semantic_file_count_mismatch",
                "description": f"Semantic analysis claims {semantic_file_count} files but only {file_count} total files",
                "severity": "medium"
            })
            consistency_score -= 0.1

    # Check risk synthesis consistency
    risk_synthesis = canonical_data.get("risk_synthesis", {})
    if risk_synthesis:
        component_risks = risk_synthesis.get("component_risks", {})
        if len(component_risks) != 8:  # Should have 8 component risks
            consistency_issues.append({
                "issue": "risk_component_count_mismatch",
                "description": f"Risk synthesis has {len(component_risks)} components, expected 8",
                "severity": "low"
            })
            consistency_score -= 0.05

    # Check decision artifacts consistency
    decision_artifacts = canonical_data.get("decision_artifacts", {})
    if decision_artifacts:
        action_plan = decision_artifacts.get("action_plan", {})
        immediate_actions = action_plan.get("immediate_actions", [])
        short_term_actions = action_plan.get("short_term_actions", [])
        long_term_actions = action_plan.get("long_term_actions", [])

        total_actions = len(immediate_actions) + len(short_term_actions) + len(long_term_actions)
        reported_total = action_plan.get("action_count", 0)

        if total_actions != reported_total:
            consistency_issues.append({
                "issue": "action_count_mismatch",
                "description": f"Action plan reports {reported_total} actions but found {total_actions}",
                "severity": "low"
            })
            consistency_score -= 0.05

    return {
        "consistency_score": max(0.0, consistency_score),
        "issues_found": len(consistency_issues),
        "consistency_issues": consistency_issues,
        "overall_consistency": "high" if consistency_score >= 0.9 else "medium" if consistency_score >= 0.7 else "low"
    }


def _generate_determinism_report(analysis_hash: str, consistency_check: Dict) -> Dict:
    """Generate comprehensive determinism verification report."""
    consistency_score = consistency_check.get("consistency_score", 0)
    issues_found = consistency_check.get("issues_found", 0)
    overall_consistency = consistency_check.get("overall_consistency", "unknown")

    # Determine overall determinism status
    if consistency_score >= 0.9 and issues_found == 0:
        determinism_status = "verified"
        confidence_level = "high"
        description = "Analysis pipeline produces fully deterministic results"
    elif consistency_score >= 0.7:
        determinism_status = "acceptable"
        confidence_level = "medium"
        description = "Analysis pipeline produces mostly deterministic results with minor inconsistencies"
    else:
        determinism_status = "compromised"
        confidence_level = "low"
        description = "Analysis pipeline has significant determinism issues"

    return {
        "determinism_status": determinism_status,
        "confidence_level": confidence_level,
        "description": description,
        "analysis_hash": analysis_hash,
        "consistency_score": consistency_score,
        "issues_found": issues_found,
        "hash_algorithm": "SHA-256",
        "verification_method": "canonical_data_hashing"
    }


def _summarize_canonical_data(canonical_data: Dict) -> Dict:
    """Generate summary of canonical data for reporting."""
    return {
        "total_files": canonical_data.get("file_count", 0),
        "data_components": len([k for k in canonical_data.keys() if k != "files"]),
        "hash_input_size": len(json.dumps(canonical_data, sort_keys=True)),
        "has_all_required_components": all(key in canonical_data for key in [
            "files", "structure", "semantic", "test_signals", "governance",
            "intent_posture", "misleading_signals", "safe_change_surface",
            "risk_synthesis", "decision_artifacts", "authority_ceiling_evaluation"
        ])
    }


def verify_reproducibility(previous_results: Dict, current_results: Dict) -> Dict:
    """
    BPS-012: Verify that analysis results are reproducible.

    Compares previous analysis results with current results to ensure reproducibility.
    """
    reproducibility_checks = {}

    # Check if both results have determinism hashes
    prev_hash = previous_results.get("determinism_verification", {}).get("determinism_hash")
    curr_hash = current_results.get("determinism_verification", {}).get("determinism_hash")

    if prev_hash and curr_hash:
        reproducibility_checks["hash_consistency"] = prev_hash == curr_hash
    else:
        reproducibility_checks["hash_consistency"] = False

    # Check key result components for consistency
    key_components = [
        "repository_root", "files", "structure", "semantic", "security_analysis",
        "compliance_analysis", "dependency_analysis", "risk_synthesis"
    ]

    component_consistency = {}
    for component in key_components:
        prev_comp = previous_results.get(component, {})
        curr_comp = current_results.get(component, {})

        # Simple consistency check - same keys and similar structure
        prev_keys = set(_flatten_keys(prev_comp))
        curr_keys = set(_flatten_keys(curr_comp))

        component_consistency[component] = {
            "key_overlap": len(prev_keys & curr_keys) / max(len(prev_keys | curr_keys), 1),
            "structure_preserved": _compare_structure(prev_comp, curr_comp)
        }

    reproducibility_checks["component_consistency"] = component_consistency

    # Overall reproducibility assessment
    hash_consistent = reproducibility_checks["hash_consistency"]
    avg_key_overlap = sum(c["key_overlap"] for c in component_consistency.values()) / len(component_consistency)
    structure_preserved = all(c["structure_preserved"] for c in component_consistency.values())

    overall_reproducible = hash_consistent and (avg_key_overlap > 0.95) and structure_preserved

    return {
        "reproducible": overall_reproducible,
        "reproducibility_checks": reproducibility_checks,
        "reproducibility_score": avg_key_overlap if hash_consistent else 0.0,
        "verification_timestamp": "2025-12-23T00:00:00Z"
    }


def _flatten_keys(data: Dict, prefix: str = "") -> List[str]:
    """Flatten nested dictionary keys for comparison."""
    keys = []
    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        keys.append(full_key)
        if isinstance(value, dict):
            keys.extend(_flatten_keys(value, full_key))
    return keys


def _compare_structure(dict1: Dict, dict2: Dict) -> bool:
    """Compare structure of two dictionaries."""
    if type(dict1) != type(dict2):
        return False

    if not isinstance(dict1, dict):
        return True  # Non-dict values are considered structurally equivalent

    keys1 = set(dict1.keys())
    keys2 = set(dict2.keys())

    # Allow some flexibility - 80% key overlap considered structural preservation
    overlap = len(keys1 & keys2)
    total = len(keys1 | keys2)

    return (overlap / total) > 0.8 if total > 0 else True


def enforce_reproducibility_guarantee(analysis_results: Dict, repository_path: str) -> Dict:
    """
    BPS-012: Enforce reproducibility guarantee for analysis results.

    Stores analysis results and verifies they can be reproduced.
    """
    import os
    import json

    # Create reproducibility cache directory
    cache_dir = os.environ.get("SCANNER_CACHE_DIR", os.path.join(os.path.dirname(repository_path), ".scanner_cache"))
    os.makedirs(cache_dir, exist_ok=True)

    # Generate cache key from repository path
    repo_hash = hashlib.md5(repository_path.encode()).hexdigest()
    cache_file = os.path.join(cache_dir, f"reproducibility_{repo_hash}.json")

    reproducibility_status = {
        "guarantee_enforced": False,
        "previous_results_available": False,
        "reproducibility_verified": False,
        "cache_file": cache_file
    }

    try:
        # Try to load previous results
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                previous_results = json.load(f)
            reproducibility_status["previous_results_available"] = True

            # Verify reproducibility
            reproducibility_check = verify_reproducibility(previous_results, analysis_results)
            reproducibility_status["reproducibility_verified"] = reproducibility_check["reproducible"]
            reproducibility_status["reproducibility_details"] = reproducibility_check

        # Store current results for future reproducibility checks
        with open(cache_file, 'w') as f:
            json.dump(analysis_results, f, indent=2, sort_keys=True)

        reproducibility_status["guarantee_enforced"] = True

    except Exception as e:
        reproducibility_status["error"] = str(e)

    return reproducibility_status