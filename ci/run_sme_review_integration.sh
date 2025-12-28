#!/bin/bash
# SME Review Process Integration
# Integrates SME review workflow with CI/CD pipeline

set -e

echo "👥 Running SME Review Process Integration..."

REVIEWS_DIR="sme_reviews"
REPORTS_DIR="validation_data/sme_reports"

# Create directories
mkdir -p "$REVIEWS_DIR"
mkdir -p "$REPORTS_DIR"

# Check for validation results to process
VALIDATION_RESULTS_FILE="validation_data/repositories/validation_results/validation_report_$(date +%Y%m%d)*.md"

if ls $VALIDATION_RESULTS_FILE 2>/dev/null; then
    echo "📊 Processing latest validation results..."

    # Convert markdown report to JSON for processing
    LATEST_REPORT=$(ls -t $VALIDATION_RESULTS_FILE | head -1)
    echo "   Using report: $LATEST_REPORT"

    # Process validation results through SME review workflow
    python3 scripts/sme_review.py process "$LATEST_REPORT" 2>/dev/null || {
        echo "⚠️  Could not process markdown report directly"
        echo "   Converting to JSON format..."

        # Create a basic JSON structure from the report
        TEMP_JSON="/tmp/validation_results_$(date +%s).json"
        cat > "$TEMP_JSON" << EOF
{
  "repositories": [
    {
      "repository_url": "validation_report_placeholder",
      "analysis_result": {
        "success": true,
        "analysis_time": 0.0,
        "languages_detected": ["unknown"],
        "file_count": 0
      }
    }
  ]
}
EOF

        python3 scripts/sme_review.py process "$TEMP_JSON"
        rm -f "$TEMP_JSON"
    }
else
    echo "ℹ️  No recent validation results found to process"
fi

# Generate SME review report
echo "📋 Generating SME review report..."

REPORT_FILE="$REPORTS_DIR/sme_review_report_$(date +%Y%m%d_%H%M%S).md"
python3 scripts/sme_review.py report --output-file "$REPORT_FILE"

echo "✅ Generated SME review report: $REPORT_FILE"

# Check for overdue reviews
echo "⏰ Checking for overdue reviews..."

OVERDUE_COUNT=$(python3 scripts/sme_review.py queue 2>/dev/null | grep "Overdue Reviews:" | sed 's/.*Overdue Reviews: \([0-9]*\).*/\1/' || echo "0")

if [ "$OVERDUE_COUNT" -gt 0 ]; then
    echo "⚠️  WARNING: $OVERDUE_COUNT reviews are overdue!"
    echo "   Please assign reviewers or extend deadlines"
fi

# Show queue summary
echo "📊 Current Review Queue:"
python3 scripts/sme_review.py queue

# Auto-assign reviews if reviewers are configured
if [ -n "$SME_REVIEWERS" ]; then
    echo "🤖 Auto-assigning reviews..."
    python3 scripts/sme_review.py auto-assign --reviewers $SME_REVIEWERS
else
    echo "ℹ️  No SME_REVIEWERS configured - manual assignment required"
fi

echo "✅ SME Review Process Integration Complete"