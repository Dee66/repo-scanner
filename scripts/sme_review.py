#!/usr/bin/env python3
"""
SME Review Management CLI
Command-line interface for managing SME reviews
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from core.sme_review.manager import SMEReviewManager, ReviewStatus, ReviewPriority, EdgeCaseCategory
from core.sme_review.workflow import ReviewWorkflowIntegration


def submit_case(args):
    """Submit a new edge case for review"""
    manager = SMEReviewManager()

    # Load analysis result if provided
    analysis_result = {}
    if args.analysis_result_file:
        with open(args.analysis_result_file, 'r') as f:
            analysis_result = json.load(f)

    case_id = manager.submit_edge_case(
        title=args.title,
        description=args.description,
        category=EdgeCaseCategory(args.category),
        repository_url=args.repository_url,
        analysis_result=analysis_result,
        expected_behavior=args.expected,
        actual_behavior=args.actual,
        error_details=args.error_details,
        priority=ReviewPriority(args.priority) if args.priority else ReviewPriority.MEDIUM,
        submitted_by=args.submitter
    )

    print(f"✅ Submitted edge case: {case_id}")
    return case_id


def assign_reviewer(args):
    """Assign a reviewer to a case"""
    manager = SMEReviewManager()

    success = manager.assign_reviewer(args.case_id, args.reviewer, args.deadline_days)

    if success:
        print(f"✅ Assigned {args.reviewer} to case {args.case_id}")
        print(f"   Deadline: {args.deadline_days} days from now")
    else:
        print(f"❌ Failed to assign reviewer to case {args.case_id}")
        sys.exit(1)


def submit_feedback(args):
    """Submit review feedback"""
    manager = SMEReviewManager()

    success = manager.submit_review_feedback(
        case_id=args.case_id,
        reviewer=args.reviewer,
        decision=ReviewStatus(args.decision),
        confidence_level=args.confidence,
        findings=args.findings,
        recommendations=args.recommendations,
        requires_code_changes=args.code_changes,
        requires_config_changes=args.config_changes,
        requires_documentation_changes=args.doc_changes,
        follow_up_actions=args.follow_up if args.follow_up else [],
        evidence_links=args.evidence if args.evidence else []
    )

    if success:
        print(f"✅ Submitted feedback for case {args.case_id}")
    else:
        print(f"❌ Failed to submit feedback for case {args.case_id}")
        sys.exit(1)


def generate_report(args):
    """Generate SME review report"""
    manager = SMEReviewManager()

    report_file = manager.generate_review_report(args.output_file)
    print(f"📋 Generated review report: {report_file}")


def process_validation_results(args):
    """Process validation results and submit edge cases"""
    workflow = ReviewWorkflowIntegration()

    with open(args.validation_results_file, 'r') as f:
        validation_results = json.load(f)

    submitted_cases = workflow.process_validation_results(validation_results)

    print(f"✅ Processed validation results")
    print(f"   Submitted {len(submitted_cases)} edge cases for review:")
    for case_id in submitted_cases:
        print(f"   - {case_id}")


def show_queue_summary(args):
    """Show review queue summary"""
    workflow = ReviewWorkflowIntegration()
    summary = workflow.get_review_queue_summary()

    print("📊 SME Review Queue Summary")
    print(f"   Total Cases: {summary['total_cases']}")
    print(f"   Pending Reviews: {summary['pending_reviews']}")
    print(f"   Overdue Reviews: {summary['overdue_reviews']}")
    print(f"   Completed Reviews: {summary['completed_reviews']}")

    if summary['overdue_cases']:
        print(f"\n⚠️  Overdue Cases: {len(summary['overdue_cases'])}")
        for case_id in summary['overdue_cases'][:5]:  # Show first 5
            print(f"   - {case_id}")

    print("\n📈 Cases by Priority:")
    for priority, count in summary['cases_by_priority'].items():
        print(f"   - {priority.title()}: {count}")

    print("\n🏷️  Cases by Category:")
    for category, count in summary['cases_by_category'].items():
        print(f"   - {category.replace('_', ' ').title()}: {count}")


def auto_assign_reviews(args):
    """Automatically assign pending reviews"""
    workflow = ReviewWorkflowIntegration()

    assignments = workflow.auto_assign_reviews(args.reviewers)

    print("✅ Auto-assigned reviews:")
    total_assigned = 0
    for reviewer, cases in assignments.items():
        if cases:
            print(f"   {reviewer}: {len(cases)} cases")
            total_assigned += len(cases)
            for case_id in cases[:3]:  # Show first 3 per reviewer
                print(f"     - {case_id}")
            if len(cases) > 3:
                print(f"     ... and {len(cases) - 3} more")

    print(f"\n📊 Total assignments: {total_assigned}")


def main():
    parser = argparse.ArgumentParser(description="SME Review Management CLI")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Submit case
    submit_parser = subparsers.add_parser('submit', help='Submit a new edge case')
    submit_parser.add_argument('--title', required=True, help='Case title')
    submit_parser.add_argument('--description', required=True, help='Case description')
    submit_parser.add_argument('--category', required=True,
                              choices=[e.value for e in EdgeCaseCategory],
                              help='Edge case category')
    submit_parser.add_argument('--repository-url', required=True, help='Repository URL')
    submit_parser.add_argument('--analysis-result-file', help='JSON file with analysis result')
    submit_parser.add_argument('--expected', required=True, help='Expected behavior')
    submit_parser.add_argument('--actual', required=True, help='Actual behavior')
    submit_parser.add_argument('--error-details', help='Error details')
    submit_parser.add_argument('--priority', choices=[e.value for e in ReviewPriority],
                              help='Review priority')
    submit_parser.add_argument('--submitter', default='cli', help='Who is submitting')

    # Assign reviewer
    assign_parser = subparsers.add_parser('assign', help='Assign reviewer to case')
    assign_parser.add_argument('case_id', help='Case ID to assign')
    assign_parser.add_argument('--reviewer', required=True, help='Reviewer name')
    assign_parser.add_argument('--deadline-days', type=int, default=7, help='Review deadline in days')

    # Submit feedback
    feedback_parser = subparsers.add_parser('feedback', help='Submit review feedback')
    feedback_parser.add_argument('case_id', help='Case ID to review')
    feedback_parser.add_argument('--reviewer', required=True, help='Reviewer name')
    feedback_parser.add_argument('--decision', required=True,
                                choices=[e.value for e in ReviewStatus],
                                help='Review decision')
    feedback_parser.add_argument('--confidence', type=int, required=True,
                                choices=range(1, 6), help='Confidence level (1-5)')
    feedback_parser.add_argument('--findings', required=True, help='Review findings')
    feedback_parser.add_argument('--recommendations', required=True, help='Review recommendations')
    feedback_parser.add_argument('--code-changes', action='store_true', help='Requires code changes')
    feedback_parser.add_argument('--config-changes', action='store_true', help='Requires config changes')
    feedback_parser.add_argument('--doc-changes', action='store_true', help='Requires documentation changes')
    feedback_parser.add_argument('--follow-up', nargs='+', help='Follow-up actions')
    feedback_parser.add_argument('--evidence', nargs='+', help='Evidence links')

    # Generate report
    report_parser = subparsers.add_parser('report', help='Generate review report')
    report_parser.add_argument('--output-file', help='Output file path')

    # Process validation results
    process_parser = subparsers.add_parser('process', help='Process validation results')
    process_parser.add_argument('validation_results_file', help='Validation results JSON file')

    # Show queue summary
    queue_parser = subparsers.add_parser('queue', help='Show review queue summary')

    # Auto assign reviews
    auto_assign_parser = subparsers.add_parser('auto-assign', help='Auto-assign pending reviews')
    auto_assign_parser.add_argument('--reviewers', nargs='+', required=True,
                                   help='List of available reviewers')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == 'submit':
        submit_case(args)
    elif args.command == 'assign':
        assign_reviewer(args)
    elif args.command == 'feedback':
        submit_feedback(args)
    elif args.command == 'report':
        generate_report(args)
    elif args.command == 'process':
        process_validation_results(args)
    elif args.command == 'queue':
        show_queue_summary(args)
    elif args.command == 'auto-assign':
        auto_assign_reviews(args)


if __name__ == '__main__':
    main()