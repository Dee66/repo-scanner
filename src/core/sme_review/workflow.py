"""
SME Review Workflow Integration
Automatically identifies and submits edge cases for SME review
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from .manager import SMEReviewManager, EdgeCaseCategory, ReviewPriority


class ReviewWorkflowIntegration:
    """
    Integrates SME review process with validation pipeline

    Automatically identifies edge cases that require expert review
    and submits them through the SME review workflow.
    """

    def __init__(self, reviews_dir: str = "sme_reviews"):
        self.review_manager = SMEReviewManager(reviews_dir)
        self.logger = logging.getLogger(__name__)

    def process_validation_results(self, validation_results: Dict[str, Any]) -> List[str]:
        """
        Process validation results and submit edge cases for review

        Args:
            validation_results: Results from validation pipeline

        Returns:
            List of submitted case IDs
        """
        submitted_cases = []

        # Process each repository result
        for repo_result in validation_results.get('repositories', []):
            cases = self._identify_edge_cases(repo_result)
            for case in cases:
                try:
                    case_id = self.review_manager.submit_edge_case(**case)
                    submitted_cases.append(case_id)
                    self.logger.info(f"Submitted edge case for review: {case_id}")
                except Exception as e:
                    self.logger.error(f"Failed to submit edge case: {e}")

        return submitted_cases

    def _identify_edge_cases(self, repo_result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Identify edge cases that require SME review

        Args:
            repo_result: Individual repository validation result

        Returns:
            List of edge case submissions
        """
        cases = []
        repo_url = repo_result.get('repository_url', 'unknown')
        analysis_result = repo_result.get('analysis_result', {})

        # Check for analysis failures
        if not analysis_result.get('success', True):
            cases.append({
                'title': f"Analysis Failure: {repo_url}",
                'description': f"Repository analysis failed with error: {analysis_result.get('error', 'Unknown error')}",
                'category': EdgeCaseCategory.ANALYSIS_ACCURACY,
                'repository_url': repo_url,
                'analysis_result': analysis_result,
                'expected_behavior': "Analysis should complete successfully",
                'actual_behavior': f"Analysis failed: {analysis_result.get('error', 'Unknown error')}",
                'error_details': analysis_result.get('error_details'),
                'priority': ReviewPriority.HIGH
            })

        # Check for misleading signals with high risk
        misleading_signals = analysis_result.get('misleading_signals', [])
        high_risk_signals = [s for s in misleading_signals if s.get('risk_score', 0) >= 0.8]

        if high_risk_signals:
            cases.append({
                'title': f"High-Risk Misleading Signals: {repo_url}",
                'description': f"Detected {len(high_risk_signals)} high-risk misleading signals that may indicate analysis issues",
                'category': EdgeCaseCategory.MISLEADING_SIGNALS,
                'repository_url': repo_url,
                'analysis_result': analysis_result,
                'expected_behavior': "Low-risk or no misleading signals",
                'actual_behavior': f"High-risk signals detected: {[s.get('type', 'unknown') for s in high_risk_signals]}",
                'priority': ReviewPriority.HIGH
            })

        # Check for enterprise complexity issues
        if self._is_enterprise_complexity_case(analysis_result):
            cases.append({
                'title': f"Enterprise Complexity: {repo_url}",
                'description': "Repository exhibits complex enterprise patterns that may challenge analysis accuracy",
                'category': EdgeCaseCategory.ENTERPRISE_COMPLEXITY,
                'repository_url': repo_url,
                'analysis_result': analysis_result,
                'expected_behavior': "Analysis should handle enterprise complexity gracefully",
                'actual_behavior': "Complex enterprise patterns detected requiring specialized handling",
                'priority': ReviewPriority.MEDIUM
            })

        # Check for performance issues
        analysis_time = analysis_result.get('analysis_time', 0)
        if analysis_time > 300:  # 5 minutes
            cases.append({
                'title': f"Performance Issue: {repo_url}",
                'description': f"Analysis took {analysis_time:.1f}s which exceeds performance targets",
                'category': EdgeCaseCategory.PERFORMANCE_ISSUE,
                'repository_url': repo_url,
                'analysis_result': analysis_result,
                'expected_behavior': "Analysis should complete within performance targets (< 30s)",
                'actual_behavior': f"Analysis took {analysis_time:.1f}s",
                'priority': ReviewPriority.MEDIUM
            })

        # Check for language-specific edge cases
        language_issues = self._identify_language_edge_cases(analysis_result)
        for issue in language_issues:
            cases.append({
                'title': f"Language Edge Case: {repo_url}",
                'description': issue['description'],
                'category': EdgeCaseCategory.LANGUAGE_EDGE_CASE,
                'repository_url': repo_url,
                'analysis_result': analysis_result,
                'expected_behavior': issue['expected'],
                'actual_behavior': issue['actual'],
                'priority': ReviewPriority.MEDIUM
            })

        # Check for security concerns
        security_concerns = analysis_result.get('security_concerns', [])
        if security_concerns:
            cases.append({
                'title': f"Security Concerns: {repo_url}",
                'description': f"Analysis detected {len(security_concerns)} potential security issues",
                'category': EdgeCaseCategory.SECURITY_CONCERN,
                'repository_url': repo_url,
                'analysis_result': analysis_result,
                'expected_behavior': "No security concerns or proper handling",
                'actual_behavior': f"Security concerns detected: {[c.get('type', 'unknown') for c in security_concerns]}",
                'priority': ReviewPriority.CRITICAL
            })

        return cases

    def _is_enterprise_complexity_case(self, analysis_result: Dict[str, Any]) -> bool:
        """Determine if this is an enterprise complexity case"""
        # Check for large repository size
        file_count = analysis_result.get('file_count', 0)
        if file_count > 10000:
            return True

        # Check for complex directory structure
        max_depth = analysis_result.get('max_directory_depth', 0)
        if max_depth > 10:
            return True

        # Check for multiple programming languages
        languages = analysis_result.get('languages_detected', [])
        if len(languages) > 3:
            return True

        # Check for enterprise patterns
        has_enterprise_patterns = analysis_result.get('enterprise_patterns', {}).get('detected', False)
        if has_enterprise_patterns:
            return True

        return False

    def _identify_language_edge_cases(self, analysis_result: Dict[str, Any]) -> List[Dict[str, str]]:
        """Identify language-specific edge cases"""
        issues = []

        # Check for mixed language repositories
        languages = analysis_result.get('languages_detected', [])
        if len(languages) > 1:
            primary_lang = languages[0] if languages else 'unknown'
            other_langs = languages[1:]

            issues.append({
                'description': f"Mixed language repository: {primary_lang} with {other_langs}",
                'expected': f"Primary language {primary_lang} should dominate analysis",
                'actual': f"Multiple languages detected: {languages}"
            })

        # Check for unusual file extensions
        unusual_extensions = analysis_result.get('unusual_extensions', [])
        if unusual_extensions:
            issues.append({
                'description': f"Unusual file extensions detected: {unusual_extensions}",
                'expected': "All files should have recognized extensions",
                'actual': f"Unusual extensions: {unusual_extensions}"
            })

        # Check for language adapter issues
        adapter_issues = analysis_result.get('adapter_issues', [])
        if adapter_issues:
            issues.append({
                'description': f"Language adapter issues: {adapter_issues}",
                'expected': "Language adapters should handle all supported languages",
                'actual': f"Adapter issues: {adapter_issues}"
            })

        return issues

    def get_review_queue_summary(self) -> Dict[str, Any]:
        """Get summary of current review queue"""
        metrics = self.review_manager.get_review_metrics()
        overdue = self.review_manager.get_overdue_reviews()

        return {
            'total_cases': metrics.total_cases,
            'pending_reviews': metrics.pending_reviews,
            'overdue_reviews': len(overdue),
            'completed_reviews': metrics.completed_reviews,
            'cases_by_priority': metrics.cases_by_priority,
            'cases_by_category': metrics.cases_by_category,
            'overdue_cases': [case.id for case in overdue]
        }

    def auto_assign_reviews(self, available_reviewers: List[str]) -> Dict[str, List[str]]:
        """
        Automatically assign pending reviews to available reviewers

        Args:
            available_reviewers: List of available reviewer names

        Returns:
            Dictionary mapping reviewer to list of assigned case IDs
        """
        assignments = {reviewer: [] for reviewer in available_reviewers}

        # Get pending cases ordered by priority
        pending_cases = self._get_pending_cases_by_priority()

        reviewer_index = 0
        for case in pending_cases:
            reviewer = available_reviewers[reviewer_index % len(available_reviewers)]

            if self.review_manager.assign_reviewer(case.id, reviewer):
                assignments[reviewer].append(case.id)

            reviewer_index += 1

        return assignments

    def _get_pending_cases_by_priority(self) -> List:
        """Get pending cases ordered by priority"""
        cases = self.review_manager._load_all_cases()
        pending_cases = [c for c in cases if c.status == self.review_manager.ReviewStatus.PENDING]

        # Sort by priority (CRITICAL > HIGH > MEDIUM > LOW)
        priority_order = {
            self.review_manager.ReviewPriority.CRITICAL: 4,
            self.review_manager.ReviewPriority.HIGH: 3,
            self.review_manager.ReviewPriority.MEDIUM: 2,
            self.review_manager.ReviewPriority.LOW: 1
        }

        return sorted(pending_cases,
                     key=lambda c: priority_order.get(c.priority, 0),
                     reverse=True)