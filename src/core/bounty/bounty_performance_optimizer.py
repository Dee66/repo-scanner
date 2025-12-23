"""Bounty Performance Optimizer for Large-Scale Operations.

Provides performance optimizations specifically for bounty hunting operations:
- Parallel bounty analysis pipeline
- Memory-efficient batch processing for large repositories
- Caching for repeated bounty evaluations
- Streaming processing for maintainer profiling
"""

import asyncio
import concurrent.futures
import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..performance_optimizer import OptimizedThreadPool, get_performance_optimizer
from .maintainer_profile_engine import MaintainerProfileEngine
from .profitability_triage import triage_bounty_profitability
from .api_integration_engine import analyze_api_integration_points

logger = logging.getLogger(__name__)

@dataclass
class BountyAnalysisBatch:
    """Batch of bounty analyses for parallel processing."""
    bounty_items: List[Dict[str, Any]]
    repository_url: str
    analysis_results: Dict[str, Any]
    batch_id: str
    priority: int = 0

@dataclass
class BountyCache:
    """Cache for bounty analysis results."""
    cache_dir: Path
    max_age_hours: int = 24

    def __post_init__(self):
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_bounty_cache_key(self, repository_url: str, bounty_data: Dict,
                           analysis_results: Dict) -> str:
        """Generate cache key for bounty analysis."""
        content = f"{repository_url}:{json.dumps(bounty_data, sort_keys=True)}:{json.dumps(analysis_results, sort_keys=True)}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def get_cached_bounty_analysis(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached bounty analysis."""
        cache_file = self.cache_dir / f"{cache_key}.json"
        if not cache_file.exists():
            return None

        # Check if cache is still valid
        if time.time() - cache_file.stat().st_mtime > self.max_age_hours * 3600:
            cache_file.unlink()  # Remove expired cache
            return None

        try:
            with open(cache_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def cache_bounty_analysis(self, cache_key: str, analysis_result: Dict[str, Any]):
        """Cache bounty analysis result."""
        cache_file = self.cache_dir / f"{cache_key}.json"
        try:
            with open(cache_file, 'w') as f:
                json.dump(analysis_result, f, indent=2)
        except IOError:
            logger.warning(f"Failed to cache bounty analysis: {cache_key}")

class ParallelBountyAnalyzer:
    """Parallel analyzer for bounty operations on large repositories."""

    def __init__(self, max_workers: int = 4, cache_dir: Path = None):
        self.max_workers = max_workers
        self.thread_pool = OptimizedThreadPool(max_workers=max_workers)
        self.cache = BountyCache(cache_dir or Path.home() / ".cache" / "repo-scanner" / "bounty")
        self.profile_engine = MaintainerProfileEngine()

    def analyze_bounty_batch_parallel(self, batch: BountyAnalysisBatch) -> List[Dict[str, Any]]:
        """Analyze multiple bounties in parallel for the same repository."""
        logger.info(f"Processing bounty batch {batch.batch_id} with {len(batch.bounty_items)} items")

        results = []

        # Submit all bounty analyses to thread pool
        futures = {}
        for bounty_data in batch.bounty_items:
            cache_key = self.cache.get_bounty_cache_key(
                batch.repository_url, bounty_data, batch.analysis_results
            )

            # Check cache first
            cached_result = self.cache.get_cached_bounty_analysis(cache_key)
            if cached_result:
                logger.debug(f"Using cached result for bounty {bounty_data.get('id')}")
                results.append(cached_result)
                continue

            # Submit for parallel processing
            future = self.thread_pool.submit(
                self._analyze_single_bounty,
                batch.repository_url,
                bounty_data,
                batch.analysis_results
            )
            futures[future] = (bounty_data, cache_key)

        # Collect results
        for future in as_completed(futures):
            bounty_data, cache_key = futures[future]
            try:
                result = future.result(timeout=300)  # 5 minute timeout
                results.append(result)
                # Cache the result
                self.cache.cache_bounty_analysis(cache_key, result)
            except concurrent.futures.TimeoutError:
                logger.error(f"Timeout analyzing bounty {bounty_data.get('id')}")
                results.append(self._create_error_result(bounty_data, "Analysis timeout"))
            except Exception as e:
                logger.error(f"Error analyzing bounty {bounty_data.get('id')}: {e}")
                results.append(self._create_error_result(bounty_data, str(e)))

        return results

    def _analyze_single_bounty(self, repository_url: str, bounty_data: Dict,
                              analysis_results: Dict) -> Dict[str, Any]:
        """Analyze a single bounty opportunity."""
        start_time = time.time()

        try:
            # Extract analysis results
            intent_posture = analysis_results.get('intent_posture', {})
            governance = analysis_results.get('governance', {})
            risk_synthesis = analysis_results.get('risk_synthesis', {})
            test_signals = analysis_results.get('test_signals', {})
            api_analysis = analysis_results.get('api_analysis', {})

            # Parallel execution of independent analysis steps
            with ThreadPoolExecutor(max_workers=3) as executor:
                # Submit independent tasks
                profile_future = executor.submit(
                    self._generate_maintainer_profile,
                    repository_url, intent_posture, governance
                )

                triage_future = executor.submit(
                    self._perform_profitability_triage,
                    repository_url, bounty_data, risk_synthesis, test_signals, {}  # Empty profile initially
                )

                integration_future = executor.submit(
                    self._analyze_integration_points,
                    [], api_analysis, governance
                )

                # Wait for results
                maintainer_profile = profile_future.result(timeout=120)
                triage_result = triage_future.result(timeout=120)
                integration_analysis = integration_future.result(timeout=120)

                # Update triage with actual maintainer profile
                if maintainer_profile:
                    triage_result = self._perform_profitability_triage(
                        repository_url, bounty_data, risk_synthesis, test_signals, maintainer_profile
                    )

            # Generate final assessment
            bounty_assessment = self._generate_bounty_assessment(
                bounty_data, maintainer_profile, triage_result, integration_analysis
            )

            processing_time = time.time() - start_time
            logger.info(f"Bounty {bounty_data.get('id')} analyzed in {processing_time:.2f}s")

            return bounty_assessment

        except Exception as e:
            logger.error(f"Failed to analyze bounty {bounty_data.get('id')}: {e}")
            return self._create_error_result(bounty_data, str(e))

    def _generate_maintainer_profile(self, repository_url: str, intent_posture: Dict,
                                   governance: Dict) -> Dict[str, Any]:
        """Generate maintainer profile (extracted for parallel execution)."""
        try:
            return self.profile_engine.generate_maintainer_profile(
                repository_url, intent_posture, governance
            )
        except Exception as e:
            logger.warning(f"Maintainer profile generation failed: {e}")
            return {}

    def _perform_profitability_triage(self, repository_url: str, bounty_data: Dict,
                                    risk_synthesis: Dict, test_signals: Dict,
                                    maintainer_profile: Dict) -> Dict[str, Any]:
        """Perform profitability triage (extracted for parallel execution)."""
        try:
            return triage_bounty_profitability(
                repository_url, bounty_data, risk_synthesis, test_signals, maintainer_profile
            )
        except Exception as e:
            logger.warning(f"Profitability triage failed: {e}")
            return {"triage_decision": {"decision": "unable_to_assess", "confidence": 0.0}}

    def _analyze_integration_points(self, file_list: List[str], api_analysis: Dict,
                                  governance: Dict) -> Dict[str, Any]:
        """Analyze integration points (extracted for parallel execution)."""
        try:
            return analyze_api_integration_points(
                file_list, api_analysis, governance
            )
        except Exception as e:
            logger.warning(f"Integration analysis failed: {e}")
            return {}

    def _generate_bounty_assessment(self, bounty_data: Dict, maintainer_profile: Dict,
                                  triage_result: Dict, integration_analysis: Dict) -> Dict[str, Any]:
        """Generate comprehensive bounty assessment."""
        return {
            "bounty_id": bounty_data.get("id"),
            "bounty_title": bounty_data.get("title"),
            "repository_url": bounty_data.get("repository_url"),
            "maintainer_profile": maintainer_profile,
            "profitability_triage": triage_result,
            "integration_analysis": integration_analysis,
            "overall_confidence": triage_result.get("triage_decision", {}).get("confidence", 0.0),
            "recommendation": triage_result.get("triage_decision", {}).get("decision", "unable_to_assess"),
            "analyzed_at": time.time()
        }

    def _create_error_result(self, bounty_data: Dict, error_message: str) -> Dict[str, Any]:
        """Create error result for failed analysis."""
        return {
            "bounty_id": bounty_data.get("id"),
            "error": error_message,
            "recommendation": "unable_to_assess",
            "overall_confidence": 0.0,
            "analyzed_at": time.time()
        }

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        return {
            "max_workers": self.max_workers,
            "cache_size_mb": sum(f.stat().st_size for f in self.cache.cache_dir.glob("*.json")) / 1024 / 1024,
            "cache_entries": len(list(self.cache.cache_dir.glob("*.json")))
        }