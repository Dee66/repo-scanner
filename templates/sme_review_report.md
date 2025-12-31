# SME Review Process Report
**Generated:** {{ generation_time }}
**SME Confidence Assessment:** {{ sme_confidence_assessment.confidence_level|title }} ({{ "%.1f"|format(sme_confidence_assessment.confidence_score * 100) }}%)

## Executive Summary
- **Total Cases:** {{ metrics.total_cases }}
- **Pending Reviews:** {{ metrics.pending_reviews }}
- **Completed Reviews:** {{ metrics.completed_reviews }}
- **Average Review Time:** {{ "%.1f"|format(metrics.average_review_time_days) }} days
- **Approval Rate:** {{ "%.1f"|format(metrics.approval_rate * 100) }}%
- **Average Confidence:** {{ "%.1f"|format(metrics.average_confidence) }}/5
{% if metrics.effectiveness_metrics %}
- **Overall Effectiveness:** {{ "%.1f"|format(metrics.effectiveness_metrics.weighted_accuracy * 100) }}%
- **Precision:** {{ "%.1f"|format(metrics.effectiveness_metrics.precision * 100) }}%
- **Recall:** {{ "%.1f"|format(metrics.effectiveness_metrics.recall * 100) }}%
- **F1 Score:** {{ "%.1f"|format(metrics.effectiveness_metrics.f1_score * 100) }}%
{% endif %}

## SME Confidence Assessment
**Assessment By:** {{ sme_confidence_assessment.assessment_by }}
**Date:** {{ sme_confidence_assessment.assessment_date }}
**Rationale:** {{ sme_confidence_assessment.rationale }}

{% if metrics.effectiveness_metrics %}
## Effectiveness Metrics
**Overall Weighted Accuracy:** {{ "%.1f"|format(metrics.effectiveness_metrics.weighted_accuracy * 100) }}%

### Precision/Recall Analysis
- **Precision:** {{ "%.1f"|format(metrics.effectiveness_metrics.precision * 100) }}% (correct positive predictions)
- **Recall:** {{ "%.1f"|format(metrics.effectiveness_metrics.recall * 100) }}% (found all actual issues)
- **F1 Score:** {{ "%.1f"|format(metrics.effectiveness_metrics.f1_score * 100) }}% (balanced precision/recall)

### Performance Metrics
- **True Positive Rate:** {{ "%.1f"|format(metrics.effectiveness_metrics.true_positive_rate * 100) }}%
- **False Positive Rate:** {{ "%.1f"|format(metrics.effectiveness_metrics.false_positive_rate * 100) }}%
- **False Negative Rate:** {{ "%.1f"|format(metrics.effectiveness_metrics.false_negative_rate * 100) }}%

### Confidence Analysis
- **Confidence-Accuracy Correlation:** {{ "%.2f"|format(metrics.effectiveness_metrics.confidence_accuracy_correlation) }}
- **High Confidence Accuracy:** {{ "%.1f"|format(metrics.effectiveness_metrics.high_confidence_accuracy * 100) }}%
- **Low Confidence Accuracy:** {{ "%.1f"|format(metrics.effectiveness_metrics.low_confidence_accuracy * 100) }}%

### Category Effectiveness
{% for category, effectiveness in metrics.category_effectiveness.items() %}
- **{{ category|replace('_', ' ')|title }}:** {{ "%.1f"|format(effectiveness * 100) }}%
{% endfor %}

### Quality Indicators
- **Weighted Review Score:** {{ "%.1f"|format(metrics.weighted_review_score * 100) }}%
- **Review Consistency:** {{ "%.1f"|format(metrics.review_consistency_score * 100) }}%
- **Inter-Reviewer Agreement:** {{ "%.1f"|format(metrics.inter_reviewer_agreement * 100) }}%

{% if metrics.effectiveness_metrics.rolling_accuracy_7d > 0 %}
### Trends (7-day Rolling Average)
- **Accuracy Trend:** {{ "%.1f"|format(metrics.effectiveness_metrics.rolling_accuracy_7d * 100) }}%
{% endif %}
{% endif %}

## Cases by Category
{% for category, count in metrics.cases_by_category.items() %}
- **{{ category|replace('_', ' ')|title }}:** {{ count }}
{% endfor %}

## Cases by Priority
{% for priority, count in metrics.cases_by_priority.items() %}
- **{{ priority|title }}:** {{ count }}
{% endfor %}

## Recent Cases
{% for case in recent_cases %}
### {{ case.status_emoji }} {{ case.title }}
- **ID:** {{ case.id }}
- **Category:** {{ case.category|replace('_', ' ')|title }}
- **Priority:** {{ case.priority|title }}
- **Status:** {{ case.status|replace('_', ' ')|title }}
{% if case.assigned_to %}
- **Assigned SME:** {{ case.assigned_to }}
{% if case.reviewer_backup %}
- **Backup SMEs:** {{ case.reviewer_backup|join(', ') }}
{% endif %}
- **Estimated Completion:** {{ case.estimated_completion_days }} days
{% endif %}
- **Submitted:** {{ case.submitted_at if case.submitted_at else 'Unknown' }}
- **Description:** {{ case.description[:200] }}...
{% endfor %}

## SME Validation Status
{% for validation in sme_validations %}
### {{ validation.claim }}
- **Verified:** {{ "✅ Yes" if validation.verified else "❌ No" }}
- **Confidence:** {{ "%.1f"|format(validation.get('confidence', 0.5) * 100) }}%
- **Verified By:** {{ validation.verified_by }}
- **Notes:** {{ validation.notes }}
{% if validation.get('evidence_links') %}
- **Evidence:** {{ validation.evidence_links|join(', ') }}
{% endif %}
{% endfor %}

---
*Report generated automatically with SME data integration*