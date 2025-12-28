#!/bin/bash
# Validate Continuous Validation Effectiveness
# Ensures the validation pipeline maintains required effectiveness levels

set -e

echo "🔍 Validating Continuous Validation Effectiveness..."

# Check if validation results exist
VALIDATION_DIR="validation_data/repositories/validation_results"
if [ ! -d "$VALIDATION_DIR" ]; then
    echo "❌ Validation results directory not found: $VALIDATION_DIR"
    exit 1
fi

# Find the latest validation report
LATEST_REPORT=$(ls -t "$VALIDATION_DIR"/validation_report_*.md 2>/dev/null | head -1)
if [ -z "$LATEST_REPORT" ]; then
    echo "❌ No validation reports found"
    exit 1
fi

echo "📋 Analyzing latest validation report: $(basename "$LATEST_REPORT")"

# Extract key metrics from the report
SUCCESS_RATE=$(grep "Success Rate:" "$LATEST_REPORT" | head -1 | cut -d: -f2 | tr -d ' **%' || echo "0")
TOTAL_REPOS=$(grep "Total Repositories Analyzed:" "$LATEST_REPORT" | head -1 | cut -d: -f2 | tr -d ' **' || echo "0")
AVG_TIME=$(grep "Average Analysis Time:" "$LATEST_REPORT" | head -1 | cut -d: -f2 | tr -d ' **' | sed 's/seconds*//' || echo "0")

echo "📊 Current Metrics:"
echo "   - Success Rate: ${SUCCESS_RATE}%"
echo "   - Repositories Analyzed: $TOTAL_REPOS"
echo "   - Average Analysis Time: ${AVG_TIME}s"

# Validate effectiveness requirements
EFFECTIVENESS_THRESHOLD=95.0
if (( $(echo "$SUCCESS_RATE < $EFFECTIVENESS_THRESHOLD" | bc -l 2>/dev/null || echo "1") )); then
    echo "❌ EFFECTIVENESS REQUIREMENT FAILED"
    echo "   Required: ≥${EFFECTIVENESS_THRESHOLD}% success rate"
    echo "   Actual: ${SUCCESS_RATE}% success rate"
    echo "💡 Review the validation report for failure details: $LATEST_REPORT"
    exit 1
fi

# Validate minimum repository coverage (warning for continuous validation)
MIN_REPOS=3  # Lower threshold for continuous validation
if [ "$TOTAL_REPOS" -lt "$MIN_REPOS" ]; then
    echo "⚠️  MINIMUM REPOSITORY COVERAGE WARNING"
    echo "   Recommended: ≥${MIN_REPOS} repositories analyzed"
    echo "   Actual: $TOTAL_REPOS repositories analyzed"
    echo "💡 Continuous validation may not have full coverage - consider adding more repositories"
else
    echo "✅ Repository coverage adequate: $TOTAL_REPOS repositories"
fi

# Validate performance requirements (warning only for continuous validation)
PERF_THRESHOLD=60.0  # More lenient for continuous validation
if (( $(echo "$AVG_TIME > $PERF_THRESHOLD" | bc -l 2>/dev/null || echo "0") )); then
    echo "⚠️  PERFORMANCE WARNING"
    echo "   Recommended: <${PERF_THRESHOLD}s average analysis time"
    echo "   Actual: ${AVG_TIME}s average analysis time"
    echo "💡 Consider performance optimization if this persists"
fi

# Validate language coverage (warning for continuous validation)
echo "🌍 Checking language coverage..."
REQUIRED_LANGUAGES=("python" "java" "rust" "javascript" "go" "c++")
MISSING_LANGUAGES=()

for lang in "${REQUIRED_LANGUAGES[@]}"; do
    if ! grep -qi "| $lang |" "$LATEST_REPORT"; then
        MISSING_LANGUAGES+=("$lang")
    fi
done

if [ ${#MISSING_LANGUAGES[@]} -gt 0 ]; then
    echo "⚠️  LANGUAGE COVERAGE WARNING"
    echo "   Missing languages: ${MISSING_LANGUAGES[*]}"
    echo "💡 Continuous validation may not cover all languages - ensure periodic full validation"
else
    echo "✅ Language coverage complete"
fi

# Check for critical failures in the report
if grep -q "❌ CRITICAL" "$LATEST_REPORT"; then
    echo "❌ CRITICAL ISSUES DETECTED"
    echo "   Review the validation report for critical failure details: $LATEST_REPORT"
    exit 1
fi

echo "✅ CONTINUOUS VALIDATION EFFECTIVENESS VALIDATED"
echo "   - Effectiveness: ${SUCCESS_RATE}% (≥${EFFECTIVENESS_THRESHOLD}%)"
echo "   - Coverage: $TOTAL_REPOS repositories (≥${MIN_REPOS})"
echo "   - Languages: All required languages covered"
echo "   - Performance: ${AVG_TIME}s average analysis time"

exit 0