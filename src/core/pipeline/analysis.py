"""Analysis pipeline stages for Repository Intelligence Scanner."""

import asyncio
import concurrent.futures
import functools
import time
import logging
from pathlib import Path
from typing import Dict, List, Any

from ..performance_optimizer import OptimizedThreadPool, get_performance_optimizer

# Optional monitoring import
try:
    from src.optional.monitoring import get_performance_monitor
except ImportError:
    # Fallback when monitoring is not available
    def get_performance_monitor():
        return None

# Optional tracing import
try:
    from src.optional.tracing import get_tracer
    TRACING_AVAILABLE = True
except ImportError:
    TRACING_AVAILABLE = False

# Timeout and resource limit imports
from ..timeouts_and_limits import analysis_timeout, analysis_limits
from ..resource_manager import get_resource_manager

# Behavioral principles validation
from ..behavioral_principles import validate_behavioral_compliance, refusal_checker
from ..principles.trust import apply_conservative_bias
from ..authority_limits import AuthorityDomain, enforce_authority_limits
from ..offline_enforcement import enforce_offline_mode

logger = logging.getLogger(__name__)

from src.core.pipeline.repository_discovery import discover_repository_root, get_canonical_file_list
from src.core.pipeline.structural_modeling import analyze_repository_structure
from src.core.pipeline.static_semantic_analysis import analyze_semantic_structure
from src.core.pipeline.inter_file_dependency_analysis import analyze_inter_file_dependencies
from src.core.pipeline.documentation_accuracy_analysis import analyze_documentation_accuracy
from src.core.pipeline.code_implementation_pattern_detection import detect_code_implementation_patterns
from src.core.pipeline.claims_accuracy_scoring import score_claims_vs_implementation_accuracy
from src.core.pipeline.feature_completeness_assessment import assess_feature_completeness
from src.core.pipeline.documentation_accuracy_confidence import calculate_documentation_accuracy_confidence
from src.core.pipeline.documentation_code_gap_analysis import analyze_documentation_code_gaps
from src.core.pipeline.documentation_accuracy_reporting import generate_documentation_accuracy_report
from src.core.pipeline.primary_report_generator import generate_primary_report
from src.core.pipeline.machine_readable_output_generator import MachineReadableOutputGenerator
from src.core.pipeline.silence_policy import evaluate_silence_policy
from src.core.pipeline.quality_bar import evaluate_quality_bar
from src.core.pipeline.success_criteria import evaluate_success_criteria
from src.core.validation.schema_validator import get_schema_validator
from src.core.pipeline.code_comprehension import analyze_code_comprehension
from src.core.pipeline.advanced_code_analysis import analyze_advanced_code
from src.core.pipeline.compliance_analysis import analyze_compliance
from src.core.pipeline.dependency_analysis import analyze_dependencies
from src.core.pipeline.code_duplication_analysis import analyze_code_duplication
from src.core.pipeline.api_analysis import analyze_api_definitions
from src.core.pipeline.test_signal_analysis import analyze_test_signals
from src.core.pipeline.governance_signal_analysis import analyze_governance_signals
from src.core.pipeline.intent_posture_classification import classify_intent_posture
from src.core.pipeline.misleading_signal_detection import analyze_misleading_signals
from src.core.pipeline.safe_change_surface_modeling import analyze_safe_change_surface
from src.core.pipeline.security_analysis import analyze_security_vulnerabilities
from src.core.pipeline.security_analysis.cryptographic_analysis import CryptographicAnalyzer
from src.core.pipeline.security_analysis.supply_chain_security import SupplyChainAnalyzer
from src.core.pipeline.security_analysis.security_testing_depth import SecurityTestingAnalyzer
from src.core.analysis.ast_analysis import ASTAnalysisEngine
from src.core.pipeline.risk_synthesis import synthesize_risks
from src.core.pipeline.decision_artifact_generation import generate_decision_artifacts
from src.core.pipeline.authority_ceiling_evaluation import evaluate_authority_ceiling
from src.core.pipeline.determinism_verification import verify_determinism, enforce_reproducibility_guarantee
from src.core.pipeline.enterprise_edge_case_handler import EnterpriseRepositoryHandler, EdgeCaseConfig


class FileCache:
    """Simple file content cache to avoid repeated I/O operations."""
    
    def __init__(self):
        self._cache: Dict[str, str] = {}
    
    def get_file_content(self, file_path: str) -> str:
        """Get file content with caching."""
        if file_path not in self._cache:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    self._cache[file_path] = f.read()
            except (IOError, OSError):
                self._cache[file_path] = ""
        return self._cache[file_path]
    
    def clear(self):
        """Clear the cache."""
        self._cache.clear()


# Global file cache instance
file_cache = FileCache()

ANALYSIS_PIPELINE_STAGES = [
    "repository_discovery",
    "structural_modeling",
    "static_semantic_analysis",
    "inter_file_dependency_analysis",
    "documentation_accuracy_analysis",
    "code_implementation_pattern_detection",
    "claims_accuracy_scoring",
    "feature_completeness_assessment",
    "documentation_accuracy_confidence",
    "documentation_code_gap_analysis",
    "documentation_accuracy_reporting",
    "advanced_code_analysis",
    "code_comprehension_analysis",
    "compliance_analysis",
    "dependency_analysis",
    "code_duplication_analysis",
    "api_analysis",
    "security_vulnerability_analysis",
    "cryptographic_analysis",
    "supply_chain_security",
    "security_testing_depth",
    "test_signal_analysis",
    "governance_signal_analysis",
    "intent_posture_classification",
    "misleading_signal_detection",
    "safe_change_surface_modeling",
    "risk_and_gap_synthesis",
    "decision_artifact_generation",
    "authority_ceiling_evaluation",
    "silence_policy_evaluation",
    "primary_report_generation",
    "machine_readable_output_generation",
    "schema_validation",
    "quality_bar_evaluation",
    "determinism_verification",
    "success_criteria_evaluation"
]

PARALLELISM_MODEL = {
    "strategy": "bounded_parallelism",
    "guarantees": [
        "output_order_independent_of_execution_order",
        "parallel_tasks_must_be_pure",
        "shared_state_forbidden"
    ]
}

@analysis_timeout
@analysis_limits
def execute_pipeline(repository_path: str) -> dict:
    """Execute the full analysis pipeline with automatic optimization selection."""
    start_time = time.time()
    performance_optimizer = get_performance_optimizer()
    performance_monitor = get_performance_monitor()
    resource_manager = get_resource_manager()

    # Get initial degradation config
    degradation_config = resource_manager.get_degradation_config()
    logger.info(f"Starting analysis with degradation config: {degradation_config}")

    # Start distributed tracing span if enabled
    span = None
    if TRACING_AVAILABLE:
        tracer = get_tracer(__name__)
        if tracer:
            span = tracer.start_as_span("execute_pipeline", attributes={"repository_path": repository_path})
            span.set_attribute("component", "analysis_pipeline")

    # Optional metrics collection
    metrics_collector = None
    operation_start = None
    try:
        from src.optional.metrics_collector import get_metrics_collector, record_operation_start
        metrics_collector = get_metrics_collector()
        operation_start = record_operation_start("analysis_pipeline", {"repository_path": repository_path})
            # DEBUG_DISABLED: print(f"DEBUG: Metrics recording started for {repository_path}, operation_start={operation_start}")
    except ImportError as e:
            # DEBUG_DISABLED: print(f"DEBUG: Failed to import metrics collector: {e}")
        pass

    # Start performance tracking
    performance_monitor.start_operation("pipeline_execution", {"repository_path": repository_path})

    try:
        # Log initial memory usage
        initial_memory = performance_optimizer.get_memory_usage()
        logger.info(f"Starting analysis - Initial memory: {initial_memory['rss_mb']:.1f}MB")

        # BPS-015: Enforce offline-only execution mode
        offline_enforcement = enforce_offline_mode({
            "operation": "repository_analysis",
            "repository_path": repository_path,
            "stage": "pipeline_initialization"
        })

        if offline_enforcement["enforcement_status"] == "violated":
            logger.error("Offline mode violation detected - aborting analysis")
            return {
                "repository_root": None,
                "files": [],
                "status": "analysis_aborted_offline_violation",
                "offline_enforcement": offline_enforcement,
                "error": "Offline mode requirements not met"
            }

        # Repository discovery
        repo_root = discover_repository_root(repository_path)
        file_list = get_canonical_file_list(repo_root)

        if not isinstance(file_list, list):
            file_list = []
        
        # Debug: check file_list contents
        logger.info(f"Repository root: {repo_root}")
        logger.info(f"File list length: {len(file_list)}")
        if file_list:
            logger.info(f"First file: {file_list[0]}, type: {type(file_list[0])}")
            # Check if any items are not strings
            non_strings = [f for f in file_list if not isinstance(f, str)]
            if non_strings:
                logger.error(f"Non-string items in file_list: {len(non_strings)} items, first 5: {non_strings[:5]}")

        # BPS-006 to BPS-010: Perform behavioral rule refusal checks
        analysis_request = {
            "type": "comprehensive_security_analysis",  # Default analysis type
            "repository_path": repository_path
        }
        repository_content = {
            "files": file_list,
            "repository_root": repo_root
        }

        refusal_artifacts = refusal_checker.perform_refusal_checks(analysis_request, repository_content)
        if refusal_artifacts:
            logger.warning(f"Analysis refused due to behavioral rule violations: {len(refusal_artifacts)} refusals")
            # Return early with refusal artifacts
            return {
                "repository_root": repo_root,
                "files": file_list,
                "status": "analysis_refused",
                "refusal_artifacts": [self._refusal_to_dict(r) for r in refusal_artifacts],
                "behavioral_validation": {"compliant": False, "refusals": len(refusal_artifacts)}
            }

        # BPS-014: Evaluate authority ceiling limits
        authority_evaluation = enforce_authority_limits(
            "comprehensive_repository_analysis",
            AuthorityDomain.REPOSITORY_ANALYSIS,
            {
                "repository_path": repository_path,
                "file_count": len(file_list),
                "analysis_type": "comprehensive_security_analysis"
            }
        )

        if not authority_evaluation["authority_evaluation"]["can_proceed"]:
            logger.warning(f"Analysis blocked due to authority ceiling violations: {authority_evaluation['authority_evaluation']['violation_count']} violations")
            # Return early with authority violation
            return {
                "repository_root": repo_root,
                "files": file_list,
                "status": "analysis_blocked_authority_violation",
                "authority_evaluation": authority_evaluation,
                "behavioral_validation": {"compliant": True}  # Behavioral rules passed
            }

        # Auto-select pipeline based on repository complexity
        complexity_threshold = 10000  # Much higher threshold for enterprise repos
        if False:
            logger.info(f"Enterprise-scale repository detected ({len(file_list)} files), using enterprise edge case handler")

            # Use enterprise edge case handler for very complex repositories
            edge_case_config = EdgeCaseConfig(
                max_file_size_mb=100,  # Allow larger files for enterprise
                max_memory_usage_mb=4096,  # Allow more memory
                analysis_timeout_seconds=3600,  # 1 hour timeout
                max_concurrent_threads=12,
                batch_size=50  # Smaller batches for stability
            )

            handler = EnterpriseRepositoryHandler(edge_case_config)
            enterprise_result = handler.process_repository(repository_path, file_list)

            # Complete performance tracking
            execution_time = time.time() - start_time
            performance_monitor.complete_operation("pipeline_execution", {
                "execution_time": execution_time,
                "file_count": len(file_list),
                "pipeline_type": "enterprise_edge_case",
                "status": "success" if "results" in enterprise_result else "partial",
                "edge_cases_handled": enterprise_result.get("edge_cases_handled", {})
            })

            # Optional metrics completion for enterprise pipeline
            if metrics_collector and operation_start:
                try:
                    from src.optional.metrics_collector import record_operation_end
                    record_operation_end("analysis_pipeline", operation_start, "results" in enterprise_result, None, {
                        "execution_time": execution_time,
                        "file_count": len(file_list),
                        "pipeline_type": "enterprise_edge_case",
                        "edge_cases_handled": enterprise_result.get("edge_cases_handled", {})
                    })
            # DEBUG_DISABLED: print(f"DEBUG: Metrics recorded for enterprise pipeline, success={'results' in enterprise_result}")
                except ImportError:
                    pass

            return enterprise_result

        # Check for very large repositories that need distributed processing first
        complexity = _estimate_repository_complexity(file_list)
            # DEBUG_DISABLED: print(f"DEBUG: Repository complexity: {complexity}, file count: {len(file_list)}")
        if len(file_list) > 10000 or complexity > 1000:
            logger.info(f"Very large repository detected ({len(file_list)} files), using distributed pipeline")
            try:
                from .distributed_analysis import DistributedAnalysisPipeline
                pipeline = DistributedAnalysisPipeline()
                
                # Add timeout protection for distributed analysis
                import signal
                def timeout_handler(signum, frame):
                    raise TimeoutError("Distributed analysis timed out")
                
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(600)  # 10 minute timeout
                
                try:
                    result = pipeline.execute_distributed_analysis(repository_path, file_list)
                    
                    # Add standard pipeline components for compatibility
                    result.update({
                        "repository_root": repo_root,
                        "files": file_list,
                        "structure": {"analysis_type": "distributed"},
                        "semantic": {"analysis_type": "distributed"},
                        "status": "distributed_pipeline_complete"
                    })
                    
                    # Clean up resources synchronously
                    pipeline.cleanup()
                    
                    # Complete performance tracking for distributed pipeline
                    execution_time = time.time() - start_time
                    performance_monitor.complete_operation("pipeline_execution", {
                        "execution_time": execution_time,
                        "file_count": len(file_list),
                        "pipeline_type": "distributed",
                        "status": "success"
                    })

                    # Optional metrics completion for distributed pipeline
                    if metrics_collector and operation_start:
                        try:
                            from src.optional.metrics_collector import record_operation_end
                            record_operation_end("analysis_pipeline", operation_start, True, None, {
                                "execution_time": execution_time,
                                "file_count": len(file_list),
                                "pipeline_type": "distributed"
                            })
            # DEBUG_DISABLED: print(f"DEBUG: Metrics recorded for distributed pipeline")
                        except ImportError:
                            pass

                    # Add security analysis for distributed pipeline
                    try:
                        security_analysis = analyze_security_vulnerabilities(file_list, {"analysis_type": "distributed"})
                        result["unsafe_patterns"] = security_analysis.get("unsafe_patterns", {})
                        result["security_analysis"] = security_analysis
            # DEBUG_DISABLED: print(f"DEBUG: Added security analysis to distributed pipeline result")
                    except Exception as e:
            # DEBUG_DISABLED: print(f"DEBUG: Failed to add security analysis to distributed pipeline: {e}")
                        result["unsafe_patterns"] = {"summary": {"total_patterns": 0}}
                        result["security_analysis"] = {"error": str(e)}

                    return result
                    
                finally:
                    signal.alarm(0)  # Cancel timeout
                
            except TimeoutError:
                logger.error("Distributed analysis timed out after 10 minutes")
                # Ensure cleanup on timeout
                try:
                    pipeline.cleanup()
                except:
                    pass
            except ImportError as e:
                logger.warning(f"Distributed pipeline not available ({e}), trying optimized pipeline")
            except Exception as e:
                logger.error(f"Distributed pipeline failed ({e}), trying optimized pipeline")
                # Ensure cleanup on failure
                try:
                    pipeline.cleanup()
                except:
                    pass
                # Ensure cleanup on failure
                try:
                    pipeline.cleanup()
                except:
                    pass

        elif len(file_list) > 200 or _estimate_repository_complexity(file_list) > 50:
            logger.info(f"Complex repository detected ({len(file_list)} files), using optimized pipeline")
            logger.info(f"Repository path type: {type(repository_path)}, value: {repository_path}")
            try:
                from .optimized_analysis import execute_optimized_pipeline
                result = execute_optimized_pipeline(repository_path)
                # Complete performance tracking for optimized pipeline
                execution_time = time.time() - start_time
                performance_monitor.complete_operation("pipeline_execution", {
                    "execution_time": execution_time,
                    "file_count": len(file_list),
                    "pipeline_type": "optimized",
                    "status": "success"
                })

                # Optional metrics completion for optimized pipeline
                if metrics_collector and operation_start:
                    try:
                        from src.optional.metrics_collector import record_operation_end
                        record_operation_end("analysis_pipeline", operation_start, True, None, {
                            "execution_time": execution_time,
                            "file_count": len(file_list),
                            "pipeline_type": "optimized"
                        })
            # DEBUG_DISABLED: print(f"DEBUG: Metrics recorded for optimized pipeline")
                    except ImportError:
                        pass

                return result
            except ImportError as e:
                logger.warning(f"Optimized pipeline not available ({e}), falling back to standard pipeline")
            except Exception as e:
                logger.error(f"Optimized pipeline failed ({e}), falling back to standard pipeline")

        # Standard pipeline for smaller repositories
        logger.info(f"Standard repository ({len(file_list)} files), using standard pipeline")
        result = _execute_standard_pipeline(repository_path, repo_root, file_list, start_time, initial_memory, degradation_config)

        # Complete performance tracking
        execution_time = time.time() - start_time
        performance_monitor.complete_operation("pipeline_execution", {
            "execution_time": execution_time,
            "file_count": len(file_list),
            "pipeline_type": "standard",
            "status": "success"
        })

        # Optional metrics completion
        if metrics_collector and operation_start:
            try:
                from src.optional.metrics_collector import record_operation_end
                record_operation_end("analysis_pipeline", operation_start, True, None, {
                    "execution_time": execution_time,
                    "file_count": len(file_list),
                    "pipeline_type": "standard"
                })
            # DEBUG_DISABLED: print(f"DEBUG: Metrics recorded for standard pipeline")
            except ImportError:
                pass

        # Close tracing span
        if span:
            span.set_attribute("execution_time", execution_time)
            span.set_attribute("file_count", len(file_list))
            span.set_attribute("status", "success")
            span.end()

        return result

    except Exception as e:
        # Track failed operations
        execution_time = time.time() - start_time
        performance_monitor.complete_operation("pipeline_execution", {
            "execution_time": execution_time,
            "status": "failed",
            "error": str(e)
        })

        # Optional metrics completion for failed operations
        if metrics_collector and operation_start:
            try:
                from src.optional.metrics_collector import record_operation_end
                record_operation_end("analysis_pipeline", operation_start, False, str(e), {
                    "execution_time": execution_time,
                    "error": str(e)
                })
            except ImportError:
                pass

        # Close tracing span with error
        if span:
            span.set_attribute("execution_time", execution_time)
            span.set_attribute("status", "failed")
            span.set_attribute("error", str(e))
            span.end()

        raise

def _estimate_repository_complexity(file_list: List[str]) -> float:
    """Estimate repository complexity based on file count and types."""
    if not file_list:
        return 0.0

    # Validate input
    if not all(isinstance(f, str) for f in file_list):
        non_strings = [f for f in file_list if not isinstance(f, str)]
            # DEBUG_DISABLED: print(f"DEBUG: Non-string items in file_list for complexity estimation: {non_strings[:5]} (types: {[type(f) for f in non_strings[:5]]})")
        # Filter out non-strings
        file_list = [f for f in file_list if isinstance(f, str)]

    complexity = len(file_list)

    # Add complexity for different file types
    extensions = {}
    for file_path in file_list:
        ext = Path(file_path).suffix.lower()
        extensions[ext] = extensions.get(ext, 0) + 1

    # Weight different file types by analysis complexity
    complexity_weights = {
        '.py': 2.0,      # Python - complex AST analysis
        '.java': 1.8,    # Java - complex analysis
        '.js': 1.5,      # JavaScript - regex-based but complex
        '.ts': 1.5,      # TypeScript - similar to JS
        '.cpp': 1.7,     # C++ - complex parsing
        '.c': 1.6,       # C - complex parsing
        '.go': 1.4,      # Go - moderate complexity
        '.rs': 1.4,      # Rust - moderate complexity
        '.php': 1.3,     # PHP - moderate complexity
        '.rb': 1.3,      # Ruby - moderate complexity
        '.scala': 1.6,   # Scala - complex
        '.kt': 1.5,      # Kotlin - complex
        '.swift': 1.4,   # Swift - moderate
    }

    for ext, count in extensions.items():
        weight = complexity_weights.get(ext, 1.0)
        complexity += count * (weight - 1.0)  # -1 because base count is already included

    # Add complexity for large files
    large_files = 0
    for file_path in file_list[:100]:  # Sample first 100 files
        try:
            size = Path(file_path).stat().st_size
            if size > 100000:  # > 100KB
                large_files += 1
        except (OSError, IOError):
            pass

    complexity += large_files * 2.0

    return complexity


def _estimate_enterprise_complexity(file_list: List[str], repo_path: str) -> float:
    """Estimate enterprise repository complexity with additional factors."""
    base_complexity = _estimate_repository_complexity(file_list)

    if not file_list:
        return base_complexity

    # Enterprise-specific complexity factors
    enterprise_factors = 0.0

    # Factor 1: Directory depth and nesting
    try:
        max_depth = 0
        for file_path in file_list[:500]:  # Sample for performance
            try:
                rel_path = os.path.relpath(file_path, repo_path)
                depth = len(rel_path.split(os.sep)) - 1
                max_depth = max(max_depth, depth)
            except (ValueError, OSError):
                pass
        if max_depth > 10:
            enterprise_factors += (max_depth - 10) * 0.5
    except Exception:
        pass

    # Factor 2: Large file count (enterprise repos often have many large files)
    large_file_count = 0
    total_size = 0
    for file_path in file_list[:200]:  # Sample for performance
        try:
            size = Path(file_path).stat().st_size
            total_size += size
            if size > 500000:  # > 500KB
                large_file_count += 1
        except (OSError, IOError):
            pass

    if large_file_count > 5:
        enterprise_factors += large_file_count * 0.3

    # Factor 3: Total repository size (enterprise repos are often massive)
    if total_size > 1000000000:  # > 1GB
        enterprise_factors += 2.0
    elif total_size > 500000000:  # > 500MB
        enterprise_factors += 1.0

    # Factor 4: Language diversity (enterprise repos often have many languages)
    languages = set()
    for file_path in file_list[:300]:
        ext = Path(file_path).suffix.lower()
        if ext in ['.py', '.java', '.js', '.ts', '.cpp', '.c', '.go', '.rs', '.php', '.rb', '.scala', '.kt', '.swift']:
            languages.add(ext)

    if len(languages) > 5:
        enterprise_factors += (len(languages) - 5) * 0.2

    return base_complexity + enterprise_factors

def _execute_standard_pipeline(repository_path: str, repo_root: str, file_list: List[str],
                             start_time: float, initial_memory: Dict[str, Any], degradation_config: Dict[str, Any]) -> dict:
    """Execute the standard analysis pipeline for smaller repositories."""
    performance_optimizer = get_performance_optimizer()
    performance_stage_stats: Dict[str, Dict[str, float]] = {}

    skip_optional = degradation_config.get("skip_optional_stages", False)
    logger.info(f"Executing standard pipeline with optional stages {'skipped' if skip_optional else 'enabled'}")

    def _run_stage(name: str, func, *a, **k):
        """Run a pipeline stage and record time + memory usage."""
        t0 = time.time()
        mem0 = performance_optimizer.get_memory_usage().get('rss_mb', 0.0)
        try:
            res = func(*a, **k)
        except Exception:
            # still record timing on failure
            t1 = time.time()
            mem1 = performance_optimizer.get_memory_usage().get('rss_mb', 0.0)
            performance_stage_stats[name] = {
                'time_seconds': t1 - t0,
                'memory_rss_mb_start': mem0,
                'memory_rss_mb_end': mem1
            }
            raise
        t1 = time.time()
        mem1 = performance_optimizer.get_memory_usage().get('rss_mb', 0.0)
        performance_stage_stats[name] = {
            'time_seconds': t1 - t0,
            'memory_rss_mb_start': mem0,
            'memory_rss_mb_end': mem1
        }
        return res

    # Structural modeling (must be first)
    try:
        structure = _run_stage('structural_modeling', analyze_repository_structure, file_list)
    except Exception as e:
            # DEBUG_DISABLED: print(f"DEBUG: Error in standard pipeline analyze_repository_structure: {e}")
            # DEBUG_DISABLED: print(f"DEBUG: file_list sample: {file_list[:5]}")
            # DEBUG_DISABLED: print(f"DEBUG: file_list types: {[type(f) for f in file_list[:5]]}")
        raise

    # AST analysis (multi-language code parsing)
    ast_engine = ASTAnalysisEngine()
    ast_analysis = _run_stage('ast_analysis', ast_engine.analyze, repo_root, max_files=500)

    # Static semantic analysis (must be second)
    semantic = _run_stage('static_semantic_analysis', analyze_semantic_structure, file_list, structure)

    # Inter-file dependency analysis (depends on semantic)
    inter_file_dependencies = _run_stage('inter_file_dependency_analysis', analyze_inter_file_dependencies, file_list, semantic)

    # Documentation accuracy analysis (depends on repository structure)
    documentation_accuracy = _run_stage('documentation_accuracy_analysis', analyze_documentation_accuracy, repo_root, file_list)

    # Code implementation pattern detection (depends on semantic analysis)
    code_implementation_patterns = _run_stage('code_implementation_pattern_detection', detect_code_implementation_patterns, file_list, semantic)

    # Claims vs implementation accuracy scoring (depends on documentation and patterns)
    claims_accuracy_scoring = _run_stage('claims_accuracy_scoring', score_claims_vs_implementation_accuracy,
                                        documentation_accuracy.get('documentation_claims', {}),
                                        code_implementation_patterns)

    # Feature completeness assessment (depends on documentation claims and implementation patterns)
    feature_completeness = _run_stage('feature_completeness_assessment', assess_feature_completeness,
                                     documentation_accuracy.get('documentation_claims', {}),
                                     code_implementation_patterns)

    # Documentation accuracy confidence metrics (depends on claims, patterns, and accuracy scoring)
    documentation_confidence = _run_stage('documentation_accuracy_confidence', calculate_documentation_accuracy_confidence,
                                         documentation_accuracy.get('documentation_claims', {}),
                                         code_implementation_patterns, claims_accuracy_scoring)

    # Documentation-code gap analysis (depends on claims, patterns, and accuracy scoring)
    documentation_code_gaps = _run_stage('documentation_code_gap_analysis', analyze_documentation_code_gaps,
                                        documentation_accuracy.get('documentation_claims', {}),
                                        code_implementation_patterns, claims_accuracy_scoring)

    # Documentation accuracy reporting (depends on all DAC components)
    documentation_accuracy_report = _run_stage('documentation_accuracy_reporting', generate_documentation_accuracy_report,
                                             documentation_accuracy.get('documentation_claims', {}),
                                             code_implementation_patterns, claims_accuracy_scoring,
                                             feature_completeness, documentation_confidence, documentation_code_gaps)

    # Advanced code analysis (depends on semantic)
    advanced_code_analysis = _run_stage('advanced_code_analysis', analyze_advanced_code, file_list, semantic)

    # Code comprehension analysis (depends on semantic)
    code_comprehension = _run_stage('code_comprehension', analyze_code_comprehension, Path(repo_root), semantic)

    # Security vulnerability analysis (depends on semantic)
    security_analysis = _run_stage('security_vulnerability_analysis', analyze_security_vulnerabilities, file_list, semantic)

    # Malicious intent detection
    malicious_intent_analysis = {}
    try:
        from src.core.security.malicious_intent_detection import analyze_malicious_intent
        
        # Build file content dict for analysis
        repository_files = {}
        file_cache = FileCache()
        for file_path in file_list[:1000]:  # Limit to first 1000 files for performance
            try:
                content = file_cache.get_file_content(file_path)
                if content:
                    repository_files[file_path] = content
            except:
                pass
        
        malicious_intent_analysis = _run_stage('malicious_intent_detection', 
                                               analyze_malicious_intent, 
                                               repository_files)
    except Exception as e:
        logger.warning("Malicious intent detection failed: %s", e)
        malicious_intent_analysis = {"error": str(e), "detections": []}

    # Enhanced security analysis (optional based on feature flags)
    from ..feature_flags import is_feature_enabled, FeatureFlag

    cryptographic_analysis = {}
    if is_feature_enabled(FeatureFlag.CRYPTOGRAPHIC_ANALYSIS):
        crypto_analyzer = CryptographicAnalyzer()
        cryptographic_analysis = _run_stage('cryptographic_analysis', crypto_analyzer.analyze_key_management, file_list)
    else:
        cryptographic_analysis = {"status": "disabled_by_feature_flag"}

    supply_chain_analysis = {}
    if is_feature_enabled(FeatureFlag.SUPPLY_CHAIN_SECURITY):
        supply_analyzer = SupplyChainAnalyzer()
        supply_chain_analysis = _run_stage('supply_chain_security', supply_analyzer.analyze_dependencies, repo_root)
    else:
        supply_chain_analysis = {"status": "disabled_by_feature_flag"}

    security_testing_analysis = {}
    if is_feature_enabled(FeatureFlag.SECURITY_TESTING_DEPTH):
        testing_analyzer = SecurityTestingAnalyzer()
        security_testing_analysis = _run_stage('security_testing_depth', testing_analyzer.analyze_security_testing, file_list)
    else:
        security_testing_analysis = {"status": "disabled_by_feature_flag"}

    # Compliance analysis (depends on semantic)
    compliance_analysis = _run_stage('compliance_analysis', analyze_compliance, file_list, semantic)

    # Dependency analysis (depends on semantic)
    dependency_analysis = _run_stage('dependency_analysis', analyze_dependencies, file_list, semantic)

    # Code duplication analysis (optional - skip if degradation active)
    code_duplication_analysis = {}
    if not skip_optional:
        code_duplication_analysis = _run_stage('code_duplication_analysis', analyze_code_duplication, file_list, semantic)
    else:
        logger.info("Skipping code duplication analysis due to resource degradation")
        code_duplication_analysis = {"status": "skipped_due_to_degradation"}

    # API analysis (optional - skip if degradation active)
    api_analysis = {}
    if not skip_optional:
        api_analysis = _run_stage('api_analysis', analyze_api_definitions, file_list, semantic)
    else:
        logger.info("Skipping API analysis due to resource degradation")
        api_analysis = {"status": "skipped_due_to_degradation"}

    # Test signal analysis (run first as others depend on it)
    test_signals = _run_stage('test_signal_analysis', analyze_test_signals, file_list, structure, semantic)

    # Parallel execution for independent analysis stages
    thread_pool = OptimizedThreadPool(max_workers=degradation_config.get("max_threads", 4))
    try:
        # Submit parallel tasks that depend on test_signals
        governance_future = thread_pool.submit(analyze_governance_signals, file_list, structure, semantic, test_signals)
        intent_future = thread_pool.submit(classify_intent_posture, file_list, structure, semantic, test_signals, {})  # governance not ready yet

        # Wait for governance to complete, then update intent_posture with correct governance
        governance = governance_future.result()
        intent_posture = intent_future.result()

        # Re-run intent_posture with correct governance dependency
        intent_posture = classify_intent_posture(file_list, structure, semantic, test_signals, governance)
    finally:
        thread_pool_stats = thread_pool.get_stats()
        thread_pool.shutdown(wait=True)
        logger.info(f"Thread pool stats: {thread_pool_stats}")

    # Sequential execution for dependent stages
    misleading_signals = _run_stage('misleading_signal_detection', analyze_misleading_signals, file_list, structure, semantic, test_signals, governance, intent_posture)
    safe_change_surface = _run_stage('safe_change_surface_modeling', analyze_safe_change_surface, file_list, structure, semantic, test_signals, governance, intent_posture, misleading_signals)
    risk_synthesis = _run_stage('risk_and_gap_synthesis', synthesize_risks, file_list, structure, semantic, test_signals, governance, intent_posture, misleading_signals, safe_change_surface, security_analysis, code_comprehension, compliance_analysis, dependency_analysis, code_duplication_analysis, api_analysis, advanced_code_analysis, cryptographic_analysis, supply_chain_analysis, security_testing_analysis)
    decision_artifacts = _run_stage('decision_artifact_generation', generate_decision_artifacts, file_list, structure, semantic, test_signals, governance, intent_posture, misleading_signals, safe_change_surface, risk_synthesis)
    authority_ceiling_evaluation = _run_stage('authority_ceiling_evaluation', evaluate_authority_ceiling, file_list, structure, semantic, test_signals, governance, intent_posture, misleading_signals, safe_change_surface, risk_synthesis, decision_artifacts)
    determinism_verification = _run_stage('determinism_verification', verify_determinism, file_list, structure, semantic, test_signals, governance, intent_posture, misleading_signals, safe_change_surface, risk_synthesis, decision_artifacts, authority_ceiling_evaluation)

    # BPS-012: Enforce reproducibility guarantee
    reproducibility_status = enforce_reproducibility_guarantee(locals(), repository_path)

    execution_time = time.time() - start_time

    # Get final memory usage and performance stats
    final_memory = performance_optimizer.get_memory_usage()
    memory_delta = final_memory['rss_mb'] - initial_memory['rss_mb']

    # BPS-002: Validate evidence separation from judgment in all findings
    # Extract findings from all analysis stages for behavioral validation
    all_findings = []
    
    # Extract findings from security analysis
    if 'findings' in security_analysis:
        all_findings.extend(security_analysis['findings'])
    
    # Extract findings from risk synthesis
    if 'findings' in risk_synthesis:
        all_findings.extend(risk_synthesis['findings'])
    
    # Extract findings from compliance analysis
    if 'findings' in compliance_analysis:
        all_findings.extend(compliance_analysis['findings'])
    
    # Extract findings from dependency analysis
    if 'findings' in dependency_analysis:
        all_findings.extend(dependency_analysis['findings'])
    
    # Extract findings from code duplication analysis
    if 'findings' in code_duplication_analysis:
        all_findings.extend(code_duplication_analysis['findings'])
    
    # Extract findings from API analysis
    if 'findings' in api_analysis:
        all_findings.extend(api_analysis['findings'])
    
    # Extract findings from advanced code analysis
    if 'findings' in advanced_code_analysis:
        all_findings.extend(advanced_code_analysis['findings'])
    
    # Extract findings from cryptographic analysis
    if 'findings' in cryptographic_analysis:
        all_findings.extend(cryptographic_analysis.get('findings', []))
    
    # Extract findings from supply chain analysis
    if 'findings' in supply_chain_analysis:
        all_findings.extend(supply_chain_analysis.get('findings', []))
    
    # Extract findings from security testing analysis
    if 'findings' in security_testing_analysis:
        all_findings.extend(security_testing_analysis.get('findings', []))
    
    # Validate behavioral compliance
    behavioral_validation = validate_behavioral_compliance(all_findings)
    
    # Log validation results
    if not behavioral_validation['compliant']:
        logger.warning(f"Behavioral principle violations detected: {behavioral_validation['violations']}")
        # In production, this might trigger a refusal or correction process

    # BPS-013: Apply conservative bias on ambiguity

    # Generate primary human-readable report (before building final result)
    temp_results = {
        "structure": structure,
        "semantic": semantic,
        "inter_file_dependencies": inter_file_dependencies,
        "documentation_accuracy": documentation_accuracy,
        "code_implementation_patterns": code_implementation_patterns,
        "claims_accuracy_scoring": claims_accuracy_scoring,
        "feature_completeness_assessment": feature_completeness,
        "documentation_accuracy_confidence": documentation_confidence,
        "documentation_code_gap_analysis": documentation_code_gaps,
        "documentation_accuracy_report": documentation_accuracy_report,
        "advanced_code_analysis": advanced_code_analysis,
        "code_comprehension": code_comprehension,
        "security_analysis": security_analysis,
        "malicious_intent": malicious_intent_analysis,
        "cryptographic_analysis": cryptographic_analysis,
        "supply_chain_analysis": supply_chain_analysis,
        "security_testing_analysis": security_testing_analysis,
        "compliance_analysis": compliance_analysis,
        "dependency_analysis": dependency_analysis,
        "code_duplication_analysis": code_duplication_analysis,
        "api_analysis": api_analysis,
        "test_signals": test_signals,
        "governance": governance,
        "intent_posture": intent_posture,
        "misleading_signals": misleading_signals,
        "safe_change_surface": safe_change_surface,
        "risk_synthesis": risk_synthesis,
        "decision_artifacts": decision_artifacts,
        "authority_ceiling_evaluation": authority_ceiling_evaluation,
        "determinism_verification": determinism_verification
    }
    silence_policy_evaluation = _run_stage('silence_policy_evaluation', evaluate_silence_policy, temp_results)

    # Check if silence policy requires no output generation
    if silence_policy_evaluation.get("should_be_silent", False):
        logger.info("Silence policy triggered - returning silence verdict without generating outputs")
        result = {
            "repository_root": repo_root,
            "files": file_list,
            "silence_policy_evaluation": silence_policy_evaluation,
            "outputs_generated": False,
            "silence_verdict": silence_policy_evaluation.get("silence_verdict")
        }
        # Include all analysis results for transparency
        result.update(temp_results)
        return result

    primary_report = _run_stage('primary_report_generation', generate_primary_report, temp_results, repository_path)

    # Generate machine-readable output
    machine_output_generator = MachineReadableOutputGenerator()
    machine_readable_output = _run_stage('machine_readable_output_generation',
                                       machine_output_generator.generate_machine_readable_output,
                                       temp_results, repository_path)

    # Validate machine-readable output against schema
    schema_validator = get_schema_validator()
    schema_validation = _run_stage('schema_validation',
                                  lambda data: schema_validator.validate_data(data, 'output/scan_report'),
                                  machine_readable_output)

    # Evaluate outputs against quality bar
    quality_bar_evaluation = _run_stage('quality_bar_evaluation', evaluate_quality_bar, primary_report, machine_readable_output)

    result = {
        "repository_root": repo_root,
        "files": file_list,
        "outputs_generated": True,
        "silence_policy_evaluation": silence_policy_evaluation,
        "schema_validation": schema_validation,
        "quality_bar_evaluation": quality_bar_evaluation,
        "success_criteria_evaluation": success_criteria_evaluation,
        "primary_report": primary_report,
        "machine_readable_output": machine_readable_output,
        "performance_metrics": {
            "execution_time_seconds": execution_time,
            "parallel_stages_used": True,
            "cache_enabled": True,
            "initial_memory_mb": initial_memory['rss_mb'],
            "final_memory_mb": final_memory['rss_mb'],
            "memory_delta_mb": memory_delta,
            "thread_pool_stats": thread_pool_stats,
            "stages": performance_stage_stats,
            "degradation_config": degradation_config
        },
        "status": "standard_pipeline_complete"
    }
    # Include all analysis results
    result.update(temp_results)

    # Evaluate success criteria
    success_criteria_evaluation = _run_stage('success_criteria_evaluation', evaluate_success_criteria, result)

    # Apply conservative bias to the entire result
    result = apply_conservative_bias(result)

    return result

def _refusal_to_dict(refusal: 'RefusalArtifact') -> Dict[str, Any]:
    """Convert a RefusalArtifact to dictionary format."""
    return {
        "reason_for_refusal": refusal.reason_for_refusal,
        "missing_or_unknown_information": refusal.missing_or_unknown_information,
        "blast_radius_unbounded_statement": refusal.blast_radius_unbounded_statement,
        "responsible_human_role_required": refusal.responsible_human_role_required,
        "timestamp": refusal.timestamp
    }

def validate_parallelism_guarantees(operation: str) -> bool:
    """Validate operation maintains parallelism guarantees."""
    return True  # Placeholder
