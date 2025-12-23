#!/usr/bin/env python3
"""
Simple test script for batch processing functionality in ParallelBountyAnalyzer.
"""

import sys
import os
import logging
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.bounty.bounty_performance_optimizer import ParallelBountyAnalyzer, BountyAnalysisBatch

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_sample_bounty_data():
    """Create sample bounty data for testing."""
    return [
        {
            "id": "bounty-001",
            "title": "Add TypeScript support to CLI",
            "repository_url": "https://github.com/example/repo",
            "description": "Implement TypeScript compilation and type checking for the CLI tool",
            "reward": 500,
            "tags": ["typescript", "cli", "build-tools"]
        },
        {
            "id": "bounty-002",
            "title": "Improve error handling in API client",
            "repository_url": "https://github.com/example/repo",
            "description": "Add comprehensive error handling and retry logic to the API client",
            "reward": 300,
            "tags": ["api", "error-handling", "reliability"]
        },
        {
            "id": "bounty-003",
            "title": "Add unit tests for core modules",
            "repository_url": "https://github.com/example/repo",
            "description": "Create comprehensive unit test suite for core business logic",
            "reward": 400,
            "tags": ["testing", "unit-tests", "quality"]
        }
    ]

def create_sample_analysis_results():
    """Create sample analysis results for testing."""
    return {
        "intent_posture": {
            "maintainer_intent": "open_to_contributions",
            "response_time_days": 2.5,
            "acceptance_rate": 0.75
        },
        "governance": {
            "has_contributing_guide": True,
            "has_code_of_conduct": True,
            "has_issue_templates": True,
            "branch_protection": True
        },
        "risk_synthesis": {
            "overall_risk_score": 0.3,
            "security_concerns": ["minor"],
            "code_quality_score": 0.8
        },
        "test_signals": {
            "has_tests": True,
            "test_coverage": 0.75,
            "ci_status": "passing"
        },
        "api_analysis": {
            "has_api": True,
            "api_endpoints": ["/api/v1/users", "/api/v1/repos"],
            "webhooks_configured": True
        }
    }

def main():
    """Main test function."""
    logger.info("Starting batch processing test...")

    try:
        # Create analyzer
        analyzer = ParallelBountyAnalyzer(max_workers=2)
        logger.info("ParallelBountyAnalyzer initialized successfully")

        # Create sample data
        bounty_items = create_sample_bounty_data()
        analysis_results = create_sample_analysis_results()

        # Create batch
        batch = BountyAnalysisBatch(
            bounty_items=bounty_items,
            repository_url="https://github.com/example/repo",
            analysis_results=analysis_results,
            batch_id="test-batch-001",
            priority=1
        )

        logger.info(f"Created batch with {len(bounty_items)} bounty items")

        # Run batch processing
        logger.info("Starting parallel batch processing...")
        results = analyzer.analyze_bounty_batch_parallel(batch)

        # Print results
        logger.info(f"Batch processing completed. Got {len(results)} results:")

        for i, result in enumerate(results, 1):
            print(f"\n--- Result {i} ---")
            print(f"Bounty ID: {result.get('bounty_id')}")
            print(f"Title: {result.get('bounty_title')}")
            print(f"Recommendation: {result.get('recommendation')}")
            print(f"Confidence: {result.get('overall_confidence', 0.0):.2f}")

            if 'error' in result:
                print(f"Error: {result['error']}")
            else:
                triage = result.get('profitability_triage', {})
                decision = triage.get('triage_decision', {})
                print(f"Triage Decision: {decision.get('decision', 'unknown')}")

        # Get performance stats
        stats = analyzer.get_performance_stats()
        print("\n--- Performance Stats ---")
        print(f"Max Workers: {stats['max_workers']}")
        print(f"Cache Size: {stats['cache_size_mb']:.2f} MB")
        print(f"Cache Entries: {stats['cache_entries']}")

        logger.info("Test completed successfully!")

    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())