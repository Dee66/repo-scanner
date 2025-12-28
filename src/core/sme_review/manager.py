"""
SME Review Process for Edge Case Validation
Manages subject matter expert reviews of complex edge cases
"""

import json
import os
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import re


class ReviewStatus(Enum):
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    REQUIRES_CHANGES = "requires_changes"


class ReviewPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EdgeCaseCategory(Enum):
    ENTERPRISE_COMPLEXITY = "enterprise_complexity"
    LANGUAGE_EDGE_CASE = "language_edge_case"
    MISLEADING_SIGNALS = "misleading_signals"
    PERFORMANCE_ISSUE = "performance_issue"
    ANALYSIS_ACCURACY = "analysis_accuracy"
    SECURITY_CONCERN = "security_concern"


@dataclass
class ReviewCase:
    """An edge case submitted for SME review"""
    id: str
    title: str
    description: str
    category: EdgeCaseCategory
    priority: ReviewPriority
    repository_url: str
    repository_path: Optional[str]
    analysis_result: Dict[str, Any]
    expected_behavior: str
    actual_behavior: str
    error_details: Optional[str] = None
    submitted_by: str = "system"
    submitted_at: Optional[datetime] = None
    assigned_to: Optional[str] = None
    status: ReviewStatus = ReviewStatus.PENDING
    review_deadline: Optional[datetime] = None

    def to_dict(self) -> Dict:
        data = asdict(self)
        data["category"] = self.category.value
        data["priority"] = self.priority.value
        data["status"] = self.status.value
        if self.submitted_at:
            data["submitted_at"] = self.submitted_at.isoformat()
        if self.review_deadline:
            data["review_deadline"] = self.review_deadline.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> 'ReviewCase':
        # Convert string enums back to enum values
        data["category"] = EdgeCaseCategory(data["category"])
        data["priority"] = ReviewPriority(data["priority"])
        data["status"] = ReviewStatus(data["status"])

        # Convert ISO strings back to datetime
        if data.get("submitted_at"):
            data["submitted_at"] = datetime.fromisoformat(data["submitted_at"])
        if data.get("review_deadline"):
            data["review_deadline"] = datetime.fromisoformat(data["review_deadline"])

        return cls(**data)


@dataclass
class ReviewFeedback:
    """Feedback provided by SME reviewer"""
    case_id: str
    reviewer: str
    review_date: datetime
    decision: ReviewStatus
    confidence_level: int  # 1-5 scale
    findings: str
    recommendations: str
    requires_code_changes: bool
    requires_config_changes: bool
    requires_documentation_changes: bool
    follow_up_actions: List[str]
    evidence_links: List[str] = None

    def to_dict(self) -> Dict:
        data = asdict(self)
        data["decision"] = self.decision.value
        data["review_date"] = self.review_date.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> 'ReviewFeedback':
        data["decision"] = ReviewStatus(data["decision"])
        data["review_date"] = datetime.fromisoformat(data["review_date"])
        return cls(**data)


@dataclass
class ReviewMetrics:
    """Metrics for the SME review process"""
    total_cases: int
    pending_reviews: int
    completed_reviews: int
    average_review_time_days: float
    approval_rate: float
    rejection_rate: float
    requires_changes_rate: float
    average_confidence: float
    cases_by_category: Dict[str, int]
    cases_by_priority: Dict[str, int]


class SMEReviewManager:
    """
    Manages the SME review process for edge case validation

    Provides systematic review workflows, tracking, and integration
    with the validation pipeline.
    """

    def __init__(self, reviews_dir: str = "sme_reviews"):
        self.reviews_dir = Path(reviews_dir)
        self.reviews_dir.mkdir(exist_ok=True)

        # Create subdirectories
        (self.reviews_dir / "cases").mkdir(exist_ok=True)
        (self.reviews_dir / "feedback").mkdir(exist_ok=True)
        (self.reviews_dir / "reports").mkdir(exist_ok=True)

    def submit_edge_case(self,
                        title: str,
                        description: str,
                        category: EdgeCaseCategory,
                        repository_url: str,
                        analysis_result: Dict[str, Any],
                        expected_behavior: str,
                        actual_behavior: str,
                        error_details: Optional[str] = None,
                        priority: ReviewPriority = ReviewPriority.MEDIUM,
                        submitted_by: str = "system") -> str:
        """
        Submit an edge case for SME review

        Args:
            title: Brief title for the case
            description: Detailed description
            category: Category of edge case
            repository_url: URL of the repository
            analysis_result: Full analysis result data
            expected_behavior: What should have happened
            actual_behavior: What actually happened
            error_details: Any error messages or details
            priority: Review priority level
            submitted_by: Who submitted the case

        Returns:
            Case ID for tracking
        """
        case_id = f"case_{uuid.uuid4().hex[:8]}"

        # Determine priority based on analysis result
        if self._requires_urgent_review(analysis_result):
            priority = ReviewPriority.CRITICAL

        case = ReviewCase(
            id=case_id,
            title=title,
            description=description,
            category=category,
            priority=priority,
            repository_url=repository_url,
            repository_path=None,  # Will be set if local analysis
            analysis_result=analysis_result,
            expected_behavior=expected_behavior,
            actual_behavior=actual_behavior,
            error_details=error_details,
            submitted_by=submitted_by,
            submitted_at=datetime.now(),
            status=ReviewStatus.PENDING
        )

        # Save case
        case_file = self.reviews_dir / "cases" / f"{case_id}.json"
        with open(case_file, 'w') as f:
            json.dump(case.to_dict(), f, indent=2)

        return case_id

    def _requires_urgent_review(self, analysis_result: Dict[str, Any]) -> bool:
        """Determine if a case requires urgent review"""
        # Check for critical analysis failures
        if not analysis_result.get('success', False):
            return True

        # Check for security-related issues
        if analysis_result.get('security_concerns', []):
            return True

        # Check for high-risk misleading signals
        signals = analysis_result.get('misleading_signals', [])
        high_risk_signals = [s for s in signals if s.get('risk_level', 0) >= 8]
        if high_risk_signals:
            return True

        return False

    def assign_reviewer(self, case_id: str, reviewer: str, deadline_days: int = 7) -> bool:
        """
        Assign a reviewer to a case

        Args:
            case_id: Case ID to assign
            reviewer: Reviewer name/email
            deadline_days: Days to complete review

        Returns:
            True if assignment successful
        """
        case_file = self.reviews_dir / "cases" / f"{case_id}.json"
        if not case_file.exists():
            return False

        with open(case_file, 'r') as f:
            case_data = json.load(f)

        case = ReviewCase.from_dict(case_data)
        case.assigned_to = reviewer
        case.status = ReviewStatus.IN_REVIEW
        case.review_deadline = datetime.now().replace(hour=23, minute=59, second=59)  # End of day

        # Add deadline days
        if case.review_deadline:
            case.review_deadline = case.review_deadline.replace(
                day=min(case.review_deadline.day + deadline_days, 28)  # Avoid invalid dates
            )

        with open(case_file, 'w') as f:
            json.dump(case.to_dict(), f, indent=2)

        return True

    def submit_review_feedback(self,
                              case_id: str,
                              reviewer: str,
                              decision: ReviewStatus,
                              confidence_level: int,
                              findings: str,
                              recommendations: str,
                              requires_code_changes: bool = False,
                              requires_config_changes: bool = False,
                              requires_documentation_changes: bool = False,
                              follow_up_actions: List[str] = None,
                              evidence_links: List[str] = None) -> bool:
        """
        Submit review feedback for a case

        Args:
            case_id: Case ID being reviewed
            reviewer: Reviewer name
            decision: Review decision
            confidence_level: Confidence in decision (1-5)
            findings: Detailed findings
            recommendations: Specific recommendations
            requires_code_changes: Whether code changes are needed
            requires_config_changes: Whether config changes are needed
            requires_documentation_changes: Whether documentation changes are needed
            follow_up_actions: List of follow-up actions
            evidence_links: Links to evidence or references

        Returns:
            True if feedback submitted successfully
        """
        if follow_up_actions is None:
            follow_up_actions = []
        if evidence_links is None:
            evidence_links = []

        feedback = ReviewFeedback(
            case_id=case_id,
            reviewer=reviewer,
            review_date=datetime.now(),
            decision=decision,
            confidence_level=max(1, min(5, confidence_level)),  # Clamp to 1-5
            findings=findings,
            recommendations=recommendations,
            requires_code_changes=requires_code_changes,
            requires_config_changes=requires_config_changes,
            requires_documentation_changes=requires_documentation_changes,
            follow_up_actions=follow_up_actions,
            evidence_links=evidence_links
        )

        # Save feedback
        feedback_file = self.reviews_dir / "feedback" / f"{case_id}_feedback.json"
        with open(feedback_file, 'w') as f:
            json.dump(feedback.to_dict(), f, indent=2)

        # Update case status
        case_file = self.reviews_dir / "cases" / f"{case_id}.json"
        if case_file.exists():
            with open(case_file, 'r') as f:
                case_data = json.load(f)

            case_data["status"] = decision.value
            with open(case_file, 'w') as f:
                json.dump(case_data, f, indent=2)

        return True

    def get_review_metrics(self) -> ReviewMetrics:
        """Get comprehensive metrics for the review process"""
        cases = self._load_all_cases()
        feedback = self._load_all_feedback()

        total_cases = len(cases)
        pending_reviews = len([c for c in cases if c.status == ReviewStatus.PENDING])
        completed_reviews = len([c for c in cases if c.status in [ReviewStatus.APPROVED, ReviewStatus.REJECTED, ReviewStatus.REQUIRES_CHANGES]])

        # Calculate review times
        review_times = []
        for fb in feedback:
            case = next((c for c in cases if c.id == fb.case_id), None)
            if case and case.submitted_at:
                review_time = (fb.review_date - case.submitted_at).days
                review_times.append(review_time)

        average_review_time = sum(review_times) / len(review_times) if review_times else 0

        # Calculate rates
        if completed_reviews > 0:
            approval_rate = len([fb for fb in feedback if fb.decision == ReviewStatus.APPROVED]) / completed_reviews
            rejection_rate = len([fb for fb in feedback if fb.decision == ReviewStatus.REJECTED]) / completed_reviews
            requires_changes_rate = len([fb for fb in feedback if fb.decision == ReviewStatus.REQUIRES_CHANGES]) / completed_reviews
        else:
            approval_rate = rejection_rate = requires_changes_rate = 0

        # Average confidence
        if feedback:
            average_confidence = sum(fb.confidence_level for fb in feedback) / len(feedback)
        else:
            average_confidence = 0

        # Cases by category and priority
        cases_by_category = {}
        cases_by_priority = {}

        for case in cases:
            cat = case.category.value
            pri = case.priority.value
            cases_by_category[cat] = cases_by_category.get(cat, 0) + 1
            cases_by_priority[pri] = cases_by_priority.get(pri, 0) + 1

        return ReviewMetrics(
            total_cases=total_cases,
            pending_reviews=pending_reviews,
            completed_reviews=completed_reviews,
            average_review_time_days=average_review_time,
            approval_rate=approval_rate,
            rejection_rate=rejection_rate,
            requires_changes_rate=requires_changes_rate,
            average_confidence=average_confidence,
            cases_by_category=cases_by_category,
            cases_by_priority=cases_by_priority
        )

    def _load_all_cases(self) -> List[ReviewCase]:
        """Load all review cases"""
        cases = []
        for case_file in (self.reviews_dir / "cases").glob("*.json"):
            try:
                with open(case_file, 'r') as f:
                    case_data = json.load(f)
                cases.append(ReviewCase.from_dict(case_data))
            except Exception:
                continue  # Skip malformed files
        return cases

    def _load_all_feedback(self) -> List[ReviewFeedback]:
        """Load all review feedback"""
        feedback = []
        for fb_file in (self.reviews_dir / "feedback").glob("*_feedback.json"):
            try:
                with open(fb_file, 'r') as f:
                    fb_data = json.load(f)
                feedback.append(ReviewFeedback.from_dict(fb_data))
            except Exception:
                continue  # Skip malformed files
        return feedback

    def generate_review_report(self, output_file: Optional[str] = None) -> str:
        """Generate a comprehensive review report"""
        metrics = self.get_review_metrics()
        cases = self._load_all_cases()
        feedback = self._load_all_feedback()

        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = self.reviews_dir / "reports" / f"sme_review_report_{timestamp}.md"

        report_path = Path(output_file)
        report_path.parent.mkdir(exist_ok=True)

        with open(report_path, 'w') as f:
            f.write("# SME Review Process Report\n")
            f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")

            f.write("## Executive Summary\n")
            f.write(f"- **Total Cases:** {metrics.total_cases}\n")
            f.write(f"- **Pending Reviews:** {metrics.pending_reviews}\n")
            f.write(f"- **Completed Reviews:** {metrics.completed_reviews}\n")
            f.write(".1f")
            f.write(".1f")
            f.write(".1f")
            f.write(".1f")
            f.write(".1f")
            f.write("\n")

            f.write("## Cases by Category\n")
            for category, count in metrics.cases_by_category.items():
                f.write(f"- **{category.replace('_', ' ').title()}:** {count}\n")
            f.write("\n")

            f.write("## Cases by Priority\n")
            for priority, count in metrics.cases_by_priority.items():
                f.write(f"- **{priority.title()}:** {count}\n")
            f.write("\n")

            f.write("## Recent Cases\n")
            recent_cases = sorted(cases, key=lambda c: c.submitted_at or datetime.min, reverse=True)[:10]
            for case in recent_cases:
                status_emoji = {
                    ReviewStatus.PENDING: "⏳",
                    ReviewStatus.IN_REVIEW: "🔄",
                    ReviewStatus.APPROVED: "✅",
                    ReviewStatus.REJECTED: "❌",
                    ReviewStatus.REQUIRES_CHANGES: "🔧"
                }.get(case.status, "❓")

                f.write(f"### {status_emoji} {case.title}\n")
                f.write(f"- **ID:** {case.id}\n")
                f.write(f"- **Category:** {case.category.value.replace('_', ' ').title()}\n")
                f.write(f"- **Priority:** {case.priority.value.title()}\n")
                f.write(f"- **Status:** {case.status.value.replace('_', ' ').title()}\n")
                if case.assigned_to:
                    f.write(f"- **Assigned to:** {case.assigned_to}\n")
                f.write(f"- **Submitted:** {case.submitted_at.isoformat() if case.submitted_at else 'Unknown'}\n")
                f.write(f"- **Description:** {case.description[:200]}...\n\n")

        return str(report_path)

    def get_overdue_reviews(self) -> List[ReviewCase]:
        """Get cases that are overdue for review"""
        cases = self._load_all_cases()
        now = datetime.now()

        overdue = []
        for case in cases:
            if (case.status == ReviewStatus.IN_REVIEW and
                case.review_deadline and
                case.review_deadline < now):
                overdue.append(case)

        return overdue