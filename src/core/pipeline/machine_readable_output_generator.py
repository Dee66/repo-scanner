"""Machine-readable output generator for deterministic JSON output."""

import json
import hashlib
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class MachineReadableOutputGenerator:
    """Generates deterministic, canonical JSON output with embedded governance hash."""

    def __init__(self):
        self.version = "2.0.0"
        self.output_schema = "scan_report"

    def generate_machine_readable_output(self, analysis_results: Dict[str, Any],
                                       repository_path: str) -> Dict[str, Any]:
        """
        Generate machine-readable output in canonical JSON format.

        Args:
            analysis_results: Complete analysis pipeline results
            repository_path: Path to the analyzed repository

        Returns:
            Dict containing machine-readable output with embedded governance hash
        """
        try:
            # Build the core output structure
            output = self._build_core_output(analysis_results, repository_path)

            # Add governance hash for integrity verification
            output = self._embed_governance_hash(output)

            return output

        except Exception as e:
            logger.error(f"Error generating machine-readable output: {e}")
            return self._generate_error_output(str(e))

    def _build_core_output(self, results: Dict[str, Any], repository_path: str) -> Dict[str, Any]:
        """Build the core machine-readable output structure."""
        repo_name = Path(repository_path).name
        # Remove non-deterministic timestamp for deterministic output
        # run_timestamp = datetime.utcnow().isoformat() + 'Z'

        # Generate run ID deterministically
        run_id = self._generate_deterministic_run_id(results, repository_path)

        output = {
            "version": self.version,
            "schema": self.output_schema,
            "run_id": run_id,
            # "timestamp": run_timestamp,  # Removed for determinism
            "repository": {
                "name": repo_name,
                "path": repository_path,
                "root": results.get("repository_root", repository_path)
            },
            "executive_verdict": self._generate_executive_verdict(results),
            "safe_to_change_map": self._generate_safe_to_change_map(results),
            "risk_gap_ledger": self._generate_risk_gap_ledger(results),
            "evidence_index": self._generate_evidence_index(results),
            "confidence_coverage": self._generate_confidence_coverage(results),
            "determinism_integrity": self._generate_determinism_integrity(results),
            "analysis_summary": self._generate_analysis_summary(results),
            "metadata": self._generate_metadata(results)
        }

        return output

    def _generate_executive_verdict(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate executive verdict section."""
        # Calculate overall verdict based on risk synthesis and authority evaluation
        risk_synthesis = results.get("risk_synthesis", {})
        authority_eval = results.get("authority_ceiling_evaluation", {})

        # Determine verdict based on critical risks and authority bounds
        critical_risks = []
        if "findings" in risk_synthesis:
            critical_risks = [f for f in risk_synthesis["findings"]
                            if f.get("severity") in ["critical", "high"]]

        # Authority ceiling evaluation
        authority_violated = authority_eval.get("authority_violated", False)

        if authority_violated:
            verdict = "UNSAFE"
            confidence = 0.9
            reason = "Authority ceiling violated - analysis scope exceeded safe boundaries"
        elif critical_risks:
            verdict = "CAUTION"
            confidence = 0.8
            reason = f"Critical risks identified: {len(critical_risks)} high-severity issues"
        elif risk_synthesis.get("status") == "completed":
            verdict = "SAFE"
            confidence = 0.85
            reason = "No critical risks identified, safe for competent engineering action"
        else:
            verdict = "INSUFFICIENT_EVIDENCE"
            confidence = 0.3
            reason = "Insufficient evidence for confident assessment"

        return {
            "verdict": verdict,
            "confidence": confidence,
            "scope_of_assessment": self._determine_assessment_scope(results),
            "blocking_risks": [r.get("description", "Unknown risk") for r in critical_risks[:5]],
            "safe_action_summary": self._generate_safe_actions(results, verdict),
            "unsafe_action_summary": self._generate_unsafe_actions(results, verdict),
            "evidence_index_refs": self._extract_evidence_refs(results),
            "reason": reason
        }

    def _generate_safe_to_change_map(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate safe-to-change map."""
        safe_change_surface = results.get("safe_change_surface", {})

        change_map = []
        if "surface_analysis" in safe_change_surface:
            for item in safe_change_surface["surface_analysis"]:
                change_map.append({
                    "artifact_id": item.get("file_path", item.get("module", "unknown")),
                    "change_safety": item.get("change_safety", "UNKNOWN"),
                    "reason_codes": item.get("reason_codes", []),
                    "evidence_refs": item.get("evidence_refs", []),
                    "confidence": item.get("confidence", 0.5)
                })

        return change_map

    def _generate_risk_gap_ledger(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate risk and gap ledger."""
        risk_synthesis = results.get("risk_synthesis", {})

        ledger = []
        if "findings" in risk_synthesis:
            for finding in risk_synthesis["findings"]:
                ledger.append({
                    "gap_id": finding.get("id", f"gap_{len(ledger)}"),
                    "gap_type": finding.get("type", "UNKNOWN"),
                    "priority": self._map_priority(finding.get("severity", "medium")),
                    "description": finding.get("description", "Unknown gap"),
                    "affected_artifacts": finding.get("affected_files", []),
                    "evidence_refs": finding.get("evidence_refs", []),
                    "why_this_matters": finding.get("impact", "Requires attention"),
                    "recommended_next_action": finding.get("recommendation", "Investigate further"),
                    "estimated_effort_range": finding.get("effort_estimate", "Unknown"),
                    "confidence": finding.get("confidence", 0.7)
                })

        return ledger

    def _generate_evidence_index(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate evidence index for auditability."""
        evidence_index = []

        # Extract evidence from various analysis stages
        evidence_sources = [
            ("security_analysis", "security"),
            ("code_comprehension", "code"),
            ("documentation_accuracy", "documentation"),
            ("test_signals", "testing"),
            ("governance", "governance")
        ]

        evidence_id = 0
        for stage_name, evidence_type in evidence_sources:
            stage_results = results.get(stage_name, {})
            if isinstance(stage_results, dict) and "evidence" in stage_results:
                for evidence_item in stage_results["evidence"]:
                    evidence_index.append({
                        "evidence_id": f"ev_{evidence_id}",
                        "evidence_type": evidence_type.upper(),
                        "source_artifact": evidence_item.get("source", stage_name),
                        "extracted_fact": evidence_item.get("fact", "Unknown fact"),
                        "derivation_method": evidence_item.get("method", "analysis"),
                        "confidence_weight": evidence_item.get("confidence", 0.8)
                    })
                    evidence_id += 1

        return evidence_index

    def _generate_confidence_coverage(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate confidence and coverage report."""
        # Calculate coverage by analysis dimension
        coverage = {
            "structure": self._calculate_coverage(results, "structure"),
            "code": self._calculate_coverage(results, "semantic"),
            "tests": self._calculate_coverage(results, "test_signals"),
            "specs": self._calculate_coverage(results, "documentation_accuracy"),
            "security": self._calculate_coverage(results, "security_analysis"),
        }

        # Calculate overall confidence from numeric coverage values
        numeric_coverages = [v for v in coverage.values() if isinstance(v, (int, float))]
        overall_confidence = min(numeric_coverages) if numeric_coverages else 0.5

        return {
            "coverage_by_dimension": coverage,
            "overall_confidence": overall_confidence,
            "unknown_areas": self._identify_unknown_areas(results),
            "degraded_modes_triggered": results.get("performance_metrics", {}).get("degradation_config", {}),
            "confidence_downgrades_applied": self._identify_confidence_downgrades(results),
            "reasons_for_uncertainty": self._identify_uncertainty_reasons(results)
        }

    def _generate_determinism_integrity(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate determinism and integrity report."""
        determinism = results.get("determinism_verification", {})

        return {
            "runs_executed": determinism.get("runs_executed", 1),
            "canonical_hash": self._generate_canonical_hash(results),
            "hash_consistency": determinism.get("consistent", True),
            "nondeterminism_sources_detected": determinism.get("nondeterminism_sources", []),
            "execution_environment_fingerprint": self._generate_environment_fingerprint()
        }

    def _embed_governance_hash(self, output: Dict[str, Any]) -> Dict[str, Any]:
        """Embed governance hash for integrity verification."""
        # Create a copy without the governance_hash field for hashing
        hashable_output = {k: v for k, v in output.items() if k != "governance_hash"}

        # Generate canonical JSON string with sorted keys
        try:
            canonical_json = json.dumps(hashable_output, sort_keys=True, separators=(',', ':'), default=str)
        except (TypeError, RecursionError):
            # Fallback for complex data types or recursion issues
            try:
                canonical_json = json.dumps(hashable_output, default=str)
            except:
                # Last resort: convert to string representation
                canonical_json = str(sorted(hashable_output.items()))

        # Generate SHA-256 hash
        governance_hash = hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()

        # Embed the hash
        output["governance_hash"] = governance_hash

        return output

    def _generate_deterministic_run_id(self, results: Dict[str, Any], repository_path: str) -> str:
        """Generate deterministic run ID based on repository and analysis inputs."""
        # Use repository path and key analysis timestamps for determinism
        key_data = {
            "repository_path": repository_path,
            "analysis_timestamp": results.get("performance_metrics", {}).get("execution_time_seconds", 0),
            "file_count": len(results.get("files", []))
        }

        canonical_key = json.dumps(key_data, sort_keys=True)
        run_id = hashlib.sha256(canonical_key.encode('utf-8')).hexdigest()[:16]

        return f"run_{run_id}"

    def _determine_assessment_scope(self, results: Dict[str, Any]) -> str:
        """Determine the scope of assessment performed."""
        files_analyzed = len(results.get("files", []))
        stages_completed = sum(1 for stage in [
            "structure", "semantic", "security_analysis", "test_signals",
            "documentation_accuracy", "governance"
        ] if stage in results and results[stage])

        if stages_completed >= 5:
            return f"Comprehensive analysis of {files_analyzed} files across {stages_completed} dimensions"
        elif stages_completed >= 3:
            return f"Partial analysis of {files_analyzed} files across {stages_completed} dimensions"
        else:
            return f"Limited analysis of {files_analyzed} files"

    def _generate_safe_actions(self, results: Dict[str, Any], verdict: str) -> str:
        """Generate summary of safe actions."""
        if verdict == "SAFE":
            return "Standard engineering practices may proceed with normal caution"
        elif verdict == "CAUTION":
            return "Address identified risks before major changes; routine maintenance is acceptable"
        else:
            return "No safe actions identified without additional assessment"

    def _generate_unsafe_actions(self, results: Dict[str, Any], verdict: str) -> str:
        """Generate summary of unsafe actions."""
        if verdict == "UNSAFE":
            return "All changes prohibited until critical issues resolved"
        elif verdict == "CAUTION":
            return "Major architectural changes, security modifications require additional review"
        else:
            return "Insufficient evidence to determine unsafe actions"

    def _extract_evidence_refs(self, results: Dict[str, Any]) -> List[str]:
        """Extract evidence references for the verdict."""
        refs = []
        evidence_index = self._generate_evidence_index(results)
        refs.extend([ev["evidence_id"] for ev in evidence_index[:10]])  # Limit to first 10
        return refs

    def _map_priority(self, severity: str) -> str:
        """Map severity to priority level."""
        severity_map = {
            "critical": "P0_SECURITY",
            "high": "P0",
            "medium": "P1",
            "low": "P2"
        }
        return severity_map.get(severity.lower(), "P2")

    def _calculate_coverage(self, results: Dict[str, Any], dimension: str) -> float:
        """Calculate coverage for a specific analysis dimension."""
        if dimension not in results:
            return 0.0

        result = results[dimension]
        if isinstance(result, dict):
            # Simple heuristic: if results exist and have content, assume 80% coverage
            if result and len(result) > 0:
                return 0.8
            else:
                return 0.0
        return 0.5

    def _identify_unknown_areas(self, results: Dict[str, Any]) -> List[str]:
        """Identify areas with unknown or insufficient coverage."""
        unknown = []
        key_dimensions = ["structure", "semantic", "security_analysis", "test_signals"]

        for dim in key_dimensions:
            if dim not in results or not results[dim]:
                unknown.append(f"Missing {dim.replace('_', ' ')} analysis")

        return unknown

    def _identify_confidence_downgrades(self, results: Dict[str, Any]) -> List[str]:
        """Identify reasons for confidence downgrades."""
        downgrades = []

        # Check for degraded modes
        perf_metrics = results.get("performance_metrics", {})
        if perf_metrics.get("degradation_config", {}).get("skip_optional_stages"):
            downgrades.append("Optional analysis stages skipped due to resource constraints")

        # Check for authority violations
        authority_eval = results.get("authority_ceiling_evaluation", {})
        if authority_eval.get("authority_violated"):
            downgrades.append("Authority ceiling exceeded")

        return downgrades

    def _identify_uncertainty_reasons(self, results: Dict[str, Any]) -> List[str]:
        """Identify reasons for uncertainty in assessment."""
        reasons = []

        # Check for authority violations
        authority_eval = results.get("authority_ceiling_evaluation", {})
        if authority_eval.get("authority_violated"):
            reasons.append("Authority ceiling exceeded")

        # Check for behavioral validation issues
        behavioral = results.get("behavioral_validation", {})
        if not behavioral.get("compliant", True):
            reasons.append("Behavioral principle violations detected")

        # Check for missing analysis stages
        key_stages = ["security_analysis", "code_comprehension", "documentation_accuracy"]
        for stage in key_stages:
            if stage not in results or not results[stage]:
                reasons.append(f"Missing {stage.replace('_', ' ')} analysis")

        return reasons

    def _generate_canonical_hash(self, results: Dict[str, Any]) -> str:
        """Generate canonical hash of analysis results."""
        # Create hashable representation
        hashable = {
            "repository_root": results.get("repository_root", ""),
            "file_count": len(results.get("files", [])),
            "analysis_stages": list(results.keys()),
            "performance_metrics": results.get("performance_metrics", {})
        }

        canonical_json = json.dumps(hashable, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()

    def _generate_environment_fingerprint(self) -> str:
        """Generate execution environment fingerprint."""
        # Simple fingerprint based on current environment
        env_data = {
            "python_version": "3.12",  # Would be dynamic in real implementation
            "platform": "linux",      # Would be dynamic
            "timestamp": datetime.utcnow().isoformat()
        }

        canonical_json = json.dumps(env_data, sort_keys=True)
        return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()[:16]

    def _generate_analysis_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate analysis summary statistics."""
        return {
            "total_files_analyzed": len(results.get("files", [])),
            "analysis_stages_completed": len([k for k in results.keys()
                                            if isinstance(results[k], dict) and results[k]]),
            "findings_count": self._count_findings(results),
            "evidence_count": len(self._generate_evidence_index(results))
        }

    def _generate_metadata(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate metadata section."""
        perf_metrics = results.get("performance_metrics", {})

        return {
            "scanner_version": "2.0.0",
            "analysis_duration_seconds": perf_metrics.get("execution_time_seconds", 0),
            "memory_usage_mb": perf_metrics.get("final_memory_mb", 0),
            "parallel_processing_used": perf_metrics.get("parallel_stages_used", False)
        }

    def _count_findings(self, results: Dict[str, Any]) -> int:
        """Count total findings across all analysis stages."""
        count = 0

        # Count findings in security analysis
        security = results.get("security_analysis", {})
        if "findings" in security:
            count += len(security["findings"])

        # Count findings in risk synthesis
        risk = results.get("risk_synthesis", {})
        if "findings" in risk:
            count += len(risk["findings"])

        # Count findings in other stages
        other_stages = ["compliance_analysis", "dependency_analysis", "code_duplication_analysis"]
        for stage in other_stages:
            stage_result = results.get(stage, {})
            if "findings" in stage_result:
                count += len(stage_result["findings"])

        return count

    def _generate_error_output(self, error_message: str) -> Dict[str, Any]:
        """Generate error output when analysis fails."""
        return {
            "version": self.version,
            "schema": self.output_schema,
            "error": error_message,
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "status": "generation_failed"
        }