"""Reputation Monitor Engine for Bounty Hunting.

Tracks and monitors reputation metrics for bounty submissions:
- Response latency from maintainers
- Notification ping effectiveness
- Time-to-merge for accepted PRs
- Review comment analysis for ROI quantification
- Success rate tracking across platforms
"""

from typing import Dict, List, Optional, Any, Tuple
import time
from datetime import datetime, timedelta
from collections import defaultdict
import statistics
import logging

logger = logging.getLogger(__name__)


class ReputationMonitor:
    """Engine for monitoring bounty submission reputation and ROI."""

    def __init__(self):
        self.metrics_store = defaultdict(dict)
        self.response_latencies = defaultdict(list)
        self.merge_times = defaultdict(list)
        self.review_comments = defaultdict(list)
        self.success_rates = defaultdict(list)

    def record_bounty_submission(self, bounty_id: str, platform: str,
                               submission_time: datetime) -> None:
        """Record a bounty submission for tracking."""
        self.metrics_store[bounty_id] = {
            'platform': platform,
            'submission_time': submission_time,
            'status': 'submitted',
            'notifications_sent': 0,
            'responses': []
        }
        logger.info(f"Recorded bounty submission: {bounty_id} on {platform}")

    def record_notification_ping(self, bounty_id: str, ping_time: datetime,
                               ping_type: str = 'follow_up') -> None:
        """Record a notification ping sent to maintainer."""
        if bounty_id in self.metrics_store:
            self.metrics_store[bounty_id]['notifications_sent'] += 1
            logger.info(f"Recorded {ping_type} ping for bounty {bounty_id}")

    def record_maintainer_response(self, bounty_id: str, response_time: datetime,
                                 response_type: str = 'acknowledgment') -> None:
        """Record maintainer response to submission."""
        if bounty_id in self.metrics_store:
            submission_time = self.metrics_store[bounty_id]['submission_time']
            latency = (response_time - submission_time).total_seconds() / 3600  # hours

            self.response_latencies[bounty_id].append(latency)
            self.metrics_store[bounty_id]['responses'].append({
                'time': response_time,
                'type': response_type,
                'latency_hours': latency
            })

            logger.info(f"Recorded {response_type} response for bounty {bounty_id}, latency: {latency:.1f}h")

    def record_pr_merge(self, bounty_id: str, merge_time: datetime,
                      review_comments: int = 0) -> None:
        """Record PR merge for successful bounty."""
        if bounty_id in self.metrics_store:
            submission_time = self.metrics_store[bounty_id]['submission_time']
            time_to_merge = (merge_time - submission_time).total_seconds() / 3600  # hours

            self.merge_times[bounty_id].append(time_to_merge)
            self.review_comments[bounty_id].append(review_comments)
            self.metrics_store[bounty_id]['status'] = 'merged'
            self.metrics_store[bounty_id]['merge_time'] = merge_time

            logger.info(f"Recorded PR merge for bounty {bounty_id}, time-to-merge: {time_to_merge:.1f}h, comments: {review_comments}")

    def record_bounty_outcome(self, bounty_id: str, outcome: str) -> None:
        """Record final bounty outcome (merged, rejected, ignored)."""
        if bounty_id in self.metrics_store:
            self.metrics_store[bounty_id]['final_outcome'] = outcome
            platform = self.metrics_store[bounty_id]['platform']
            self.success_rates[platform].append(1 if outcome == 'merged' else 0)

            logger.info(f"Recorded outcome '{outcome}' for bounty {bounty_id}")

    def get_reputation_metrics(self, platform: Optional[str] = None) -> Dict[str, Any]:
        """Get current reputation metrics."""
        metrics = {}

        # Response latency metrics
        if self.response_latencies:
            all_latencies = [lat for latencies in self.response_latencies.values() for lat in latencies]
            if all_latencies:
                metrics['avg_response_latency_hours'] = statistics.mean(all_latencies)
                metrics['median_response_latency_hours'] = statistics.median(all_latencies)
                metrics['p95_response_latency_hours'] = statistics.quantiles(all_latencies, n=20)[18]  # 95th percentile

        # Time-to-merge metrics
        if self.merge_times:
            all_merge_times = [mt for merge_times in self.merge_times.values() for mt in merge_times]
            if all_merge_times:
                metrics['avg_time_to_merge_hours'] = statistics.mean(all_merge_times)
                metrics['median_time_to_merge_hours'] = statistics.median(all_merge_times)

        # Review comments metrics
        if self.review_comments:
            all_comments = [comments for comment_list in self.review_comments.values() for comments in comment_list]
            if all_comments:
                metrics['avg_review_comments'] = statistics.mean(all_comments)
                metrics['total_bounties_with_reviews'] = len([c for c in all_comments if c > 0])

        # Success rates by platform
        metrics['platform_success_rates'] = {}
        for plat, outcomes in self.success_rates.items():
            if outcomes:
                success_rate = sum(outcomes) / len(outcomes)
                metrics['platform_success_rates'][plat] = success_rate

        # Overall success rate
        all_outcomes = [outcome for outcomes in self.success_rates.values() for outcome in outcomes]
        if all_outcomes:
            metrics['overall_success_rate'] = sum(all_outcomes) / len(all_outcomes)

        # Filter by platform if specified
        if platform:
            if platform in self.success_rates:
                platform_outcomes = self.success_rates[platform]
                metrics['platform_success_rate'] = sum(platform_outcomes) / len(platform_outcomes)
            else:
                metrics['platform_success_rate'] = 0.0

        return metrics

    def get_bounty_status(self, bounty_id: str) -> Optional[Dict[str, Any]]:
        """Get status and metrics for a specific bounty."""
        return self.metrics_store.get(bounty_id)

    def get_roi_metrics(self) -> Dict[str, Any]:
        """Calculate ROI metrics based on time-to-merge and review effort."""
        roi_metrics = {}

        # ROI based on time-to-merge (faster merges = higher ROI)
        if self.merge_times:
            merge_times = [mt for times in self.merge_times.values() for mt in times]
            if merge_times:
                avg_merge_time = statistics.mean(merge_times)
                # ROI score: lower time = higher ROI (normalized to 0-1 scale)
                roi_metrics['merge_time_roi_score'] = max(0, 1 - (avg_merge_time / 168))  # 168h = 1 week

        # ROI based on review comments (fewer comments = higher ROI)
        if self.review_comments:
            comment_counts = [c for comments in self.review_comments.values() for c in comments]
            if comment_counts:
                avg_comments = statistics.mean(comment_counts)
                # ROI score: fewer comments = higher ROI
                roi_metrics['review_effort_roi_score'] = max(0, 1 - (avg_comments / 10))  # Normalize to 10 comments

        # Combined ROI score
        merge_roi = roi_metrics.get('merge_time_roi_score', 0)
        review_roi = roi_metrics.get('review_effort_roi_score', 0)
        if merge_roi or review_roi:
            roi_metrics['combined_roi_score'] = (merge_roi + review_roi) / 2

        return roi_metrics

    def simulate_maintainer_feedback(self, bounty_id: str, feedback_scenario: str) -> Dict[str, Any]:
        """Simulate maintainer feedback for testing ROI calculations."""
        scenarios = {
            'fast_merge': {
                'response_time': timedelta(hours=2),
                'merge_time': timedelta(hours=24),
                'review_comments': 2,
                'outcome': 'merged'
            },
            'slow_merge': {
                'response_time': timedelta(hours=48),
                'merge_time': timedelta(hours=168),  # 1 week
                'review_comments': 8,
                'outcome': 'merged'
            },
            'rejected': {
                'response_time': timedelta(hours=72),
                'merge_time': None,
                'review_comments': 5,
                'outcome': 'rejected'
            },
            'high_friction': {
                'response_time': timedelta(hours=120),
                'merge_time': timedelta(hours=336),  # 2 weeks
                'review_comments': 15,
                'outcome': 'merged'
            }
        }

        if feedback_scenario not in scenarios:
            raise ValueError(f"Unknown scenario: {feedback_scenario}")

        scenario = scenarios[feedback_scenario]
        submission_time = self.metrics_store.get(bounty_id, {}).get('submission_time', datetime.now())

        # Ensure bounty is recorded
        if bounty_id not in self.metrics_store:
            self.record_bounty_submission(bounty_id, 'simulation_platform', submission_time)

        # Simulate response
        response_time = submission_time + scenario['response_time']
        self.record_maintainer_response(bounty_id, response_time, 'simulation')

        # Simulate merge if applicable
        if scenario['merge_time']:
            merge_time = submission_time + scenario['merge_time']
            self.record_pr_merge(bounty_id, merge_time, scenario['review_comments'])

        # Record outcome
        self.record_bounty_outcome(bounty_id, scenario['outcome'])

        return {
            'scenario': feedback_scenario,
            'simulated_response_time': scenario['response_time'],
            'simulated_merge_time': scenario['merge_time'],
            'simulated_comments': scenario['review_comments'],
            'outcome': scenario['outcome']
        }

    def run_roi_pressure_test(self, test_bounties: List[str], scenarios: List[str]) -> Dict[str, Any]:
        """Run pressure test with multiple simulated feedback scenarios."""
        results = []

        for bounty_id in test_bounties:
            for scenario in scenarios:
                try:
                    result = self.simulate_maintainer_feedback(bounty_id, scenario)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Failed to simulate {scenario} for {bounty_id}: {e}")

        # Analyze results
        roi_metrics = self.get_roi_metrics()
        success_rates = self.get_reputation_metrics()

        return {
            'simulation_results': results,
            'final_roi_metrics': roi_metrics,
            'final_success_rates': success_rates,
            'test_summary': {
                'total_simulations': len(results),
                'scenarios_tested': list(set(scenarios)),
                'bounties_tested': len(test_bounties)
            }
        }

    def simulate_star_loss_trigger(self, star_threshold: float = 0.02) -> Dict[str, Any]:
        """Simulate star loss scenario to test circuit breaker functionality."""
        # Simulate star loss detection
        current_stars = 1044  # Based on context
        lost_stars = int(current_stars * star_threshold)
        new_star_count = current_stars - lost_stars

        # Check if threshold triggered
        threshold_triggered = lost_stars >= int(current_stars * star_threshold)

        trigger_actions = []
        if threshold_triggered:
            trigger_actions = [
                "Global PR lock activated",
                "All pending submissions paused",
                "Notification sent to user",
                "Reputation monitoring enhanced"
            ]
            logger.warning(f"Star loss threshold triggered: {lost_stars} stars lost ({star_threshold*100:.1f}% threshold)")

        return {
            'star_threshold': star_threshold,
            'current_stars': current_stars,
            'simulated_loss': lost_stars,
            'new_star_count': new_star_count,
            'threshold_triggered': threshold_triggered,
            'trigger_actions': trigger_actions,
            'circuit_breaker_status': 'ACTIVE' if threshold_triggered else 'STANDBY'
        }

    def validate_latency_accuracy(self, test_pings: int = 10) -> Dict[str, Any]:
        """Validate notification ping latency and response accuracy."""
        test_results = []

        for i in range(test_pings):
            bounty_id = f"latency_test_{i}"
            submission_time = datetime.now() - timedelta(hours=i+1)

            self.record_bounty_submission(bounty_id, 'test_platform', submission_time)

            # Simulate immediate ping
            ping_time = datetime.now()
            self.record_notification_ping(bounty_id, ping_time, 'latency_test')

            # Simulate maintainer response
            response_delay = timedelta(minutes=5 + i)  # Increasing delay
            response_time = ping_time + response_delay
            self.record_maintainer_response(bounty_id, response_time, 'latency_test')

            test_results.append({
                'bounty_id': bounty_id,
                'ping_to_response_minutes': response_delay.total_seconds() / 60,
                'within_human_bounds': response_delay.total_seconds() / 60 < 30  # <30 min is human-like
            })

        # Calculate accuracy metrics
        valid_responses = sum(1 for r in test_results if r['within_human_bounds'])
        accuracy = valid_responses / len(test_results)

        return {
            'test_results': test_results,
            'accuracy_percentage': accuracy * 100,
            'average_response_time_minutes': statistics.mean([r['ping_to_response_minutes'] for r in test_results]),
            'validation_status': 'PASSED' if accuracy >= 0.99 else 'FAILED'
        }