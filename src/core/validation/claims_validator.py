"""
Claims Validation Framework

Validates public claims made about the Repository Intelligence Scanner,
including determinism guarantees, accuracy metrics, and safety boundaries.
"""

import hashlib
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from ..exceptions import ValidationError


@dataclass
class ClaimValidationResult:
    """Result of validating a specific claim."""
    claim: str
    is_valid: bool
    confidence: float
    evidence: Dict[str, Any]
    violations: List[str]


class ClaimsValidator:
    """
    Validates all public claims made about the system.

    Claims validated:
    - Deterministic analysis (same input -> same output)
    - 99.999% SME accuracy (subject matter expert agreement)
    - Offline operation (no external network calls)
    - Safety boundaries (no code execution, no business logic analysis)
    """

    def __init__(self, validation_data_path: Optional[Path] = None):
        self.validation_data_path = validation_data_path or Path("validation_data")
        self.validation_data_path.mkdir(exist_ok=True)

    def validate_all_claims(self, analysis_results: Dict[str, Any]) -> List[ClaimValidationResult]:
        """Validate all claims against the analysis results."""
        results = []

        results.append(self.validate_determinism(analysis_results))
        results.append(self.validate_accuracy(analysis_results))
        results.append(self.validate_offline_operation(analysis_results))
        results.append(self.validate_safety_boundaries(analysis_results))

        return results

    def validate_determinism(self, analysis_results: Dict[str, Any]) -> ClaimValidationResult:
        """Validate that analysis is deterministic."""
        claim = "Deterministic analysis (same input produces same output)"

        # Generate hash of inputs and outputs
        input_hash = self._hash_analysis_inputs(analysis_results)
        output_hash = self._hash_analysis_outputs(analysis_results)

        # Check against stored hashes for this input
        stored_hashes = self._load_stored_hashes(input_hash)

        is_deterministic = all(h == output_hash for h in stored_hashes)
        confidence = 1.0 if len(stored_hashes) >= 3 else 0.5  # Need multiple runs

        evidence = {
            "input_hash": input_hash,
            "output_hash": output_hash,
            "previous_runs": len(stored_hashes),
            "consistent_outputs": len(set(stored_hashes + [output_hash])) == 1
        }

        violations = [] if is_deterministic else ["Analysis output not deterministic"]

        # Store this run
        self._store_hash(input_hash, output_hash)

        return ClaimValidationResult(
            claim=claim,
            is_valid=is_deterministic,
            confidence=confidence,
            evidence=evidence,
            violations=violations
        )

    def validate_accuracy(self, analysis_results: Dict[str, Any]) -> ClaimValidationResult:
        """Validate 99.999% SME accuracy claim."""
        claim = "99.999% SME accuracy (subject matter expert agreement)"

        # This would require SME validation data
        # For now, placeholder - would need real SME feedback data
        sme_validations = self._load_sme_validations()

        if not sme_validations:
            return ClaimValidationResult(
                claim=claim,
                is_valid=False,
                confidence=0.0,
                evidence={"sme_validations_count": 0},
                violations=["No SME validation data available"]
            )

        total_validations = len(sme_validations)
        agreements = sum(1 for v in sme_validations if v["agreement"])
        accuracy = agreements / total_validations

        is_valid = accuracy >= 0.99999  # 99.999%
        confidence = min(1.0, total_validations / 1000)  # Higher confidence with more data

        evidence = {
            "total_validations": total_validations,
            "agreements": agreements,
            "accuracy": accuracy,
            "target_accuracy": 0.99999
        }

        violations = [] if is_valid else [f"Accuracy {accuracy:.6f} below 99.999% threshold"]

        return ClaimValidationResult(
            claim=claim,
            is_valid=is_valid,
            confidence=confidence,
            evidence=evidence,
            violations=violations
        )

    def validate_offline_operation(self, analysis_results: Dict[str, Any]) -> ClaimValidationResult:
        """Validate that analysis operates offline."""
        claim = "Offline operation (no external network calls)"

        # Check for network-related evidence in analysis
        network_indicators = [
            "external_api_calls" in str(analysis_results),
            "network_requests" in analysis_results,
            any("http" in str(v).lower() for v in analysis_results.values())
        ]

        has_network_activity = any(network_indicators)
        is_valid = not has_network_activity

        evidence = {
            "network_indicators_found": has_network_activity,
            "checked_fields": ["external_api_calls", "network_requests", "http_references"]
        }

        violations = [] if is_valid else ["Potential network activity detected"]

        return ClaimValidationResult(
            claim=claim,
            is_valid=is_valid,
            confidence=0.9,  # High confidence in detection
            evidence=evidence,
            violations=violations
        )

    def validate_safety_boundaries(self, analysis_results: Dict[str, Any]) -> ClaimValidationResult:
        """Validate safety boundaries are maintained."""
        claim = "Safety boundaries (no code execution, no business logic analysis)"

        # Check for forbidden analysis types
        forbidden_indicators = [
            "code_execution" in analysis_results,
            "business_logic" in analysis_results,
            "runtime_behavior" in analysis_results
        ]

        violates_boundaries = any(forbidden_indicators)
        is_valid = not violates_boundaries

        evidence = {
            "forbidden_indicators": forbidden_indicators,
            "checked_fields": ["code_execution", "business_logic", "runtime_behavior"]
        }

        violations = [] if is_valid else ["Safety boundaries violated"]

        return ClaimValidationResult(
            claim=claim,
            is_valid=is_valid,
            confidence=0.95,
            evidence=evidence,
            violations=violations
        )

    def _hash_analysis_inputs(self, results: Dict[str, Any]) -> str:
        """Generate hash of analysis inputs."""
        # Extract repository path and analysis config
        repo_path = results.get("repository_path", "")
        config = results.get("analysis_config", {})

        input_data = {
            "repo_path": repo_path,
            "config": json.dumps(config, sort_keys=True)
        }

        return hashlib.sha256(json.dumps(input_data, sort_keys=True).encode()).hexdigest()

    def _hash_analysis_outputs(self, results: Dict[str, Any]) -> str:
        """Generate hash of analysis outputs."""
        # Hash the key outputs, excluding timestamps
        outputs = {k: v for k, v in results.items() if k not in ["timestamp", "run_id"]}
        return hashlib.sha256(json.dumps(outputs, sort_keys=True).encode()).hexdigest()

    def _load_stored_hashes(self, input_hash: str) -> List[str]:
        """Load previously stored output hashes for this input."""
        hash_file = self.validation_data_path / f"{input_hash}.json"
        if not hash_file.exists():
            return []

        try:
            with open(hash_file) as f:
                data = json.load(f)
                return data.get("output_hashes", [])
        except (json.JSONDecodeError, KeyError):
            return []

    def _store_hash(self, input_hash: str, output_hash: str):
        """Store output hash for determinism validation."""
        hash_file = self.validation_data_path / f"{input_hash}.json"

        data = {"output_hashes": []}
        if hash_file.exists():
            try:
                with open(hash_file) as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                pass

        if output_hash not in data["output_hashes"]:
            data["output_hashes"].append(output_hash)

        with open(hash_file, "w") as f:
            json.dump(data, f, indent=2)

    def _load_sme_validations(self) -> List[Dict[str, Any]]:
        """Load SME validation data."""
        # Placeholder - would load from validation_data/sme_validations.json
        sme_file = self.validation_data_path / "sme_validations.json"
        if not sme_file.exists():
            return []

        try:
            with open(sme_file) as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []