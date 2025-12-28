#!/bin/bash
# Detect Effectiveness Regressions
# Compares current validation results with historical baselines

set -e

echo "🔍 Detecting Effectiveness Regressions..."

VALIDATION_DIR="validation_data/repositories/validation_results"
if [ ! -d "$VALIDATION_DIR" ]; then
    echo "❌ Validation results directory not found: $VALIDATION_DIR"
    exit 1
fi

# Get recent validation reports (last 5 runs)
RECENT_REPORTS=$(ls -t "$VALIDATION_DIR"/validation_report_*.md 2>/dev/null | head -5)

if [ -z "$RECENT_REPORTS" ]; then
    echo "ℹ️  No validation reports found - cannot detect regressions"
    exit 0
fi

echo "📊 Analyzing recent validation runs..."

# Extract success rates from recent reports
declare -a SUCCESS_RATES
declare -a TIMESTAMPS

REPORT_COUNT=0
for report in $RECENT_REPORTS; do
    if [ -f "$report" ]; then
        timestamp=$(basename "$report" | sed 's/validation_report_\([0-9_]*\)\.md/\1/' | sed 's/_/ /g')
        success_rate=$(grep "Success Rate:" "$report" | head -1 | cut -d: -f2 | tr -d ' **%' || echo "0")

        if [ "$success_rate" != "0" ]; then
            SUCCESS_RATES[$REPORT_COUNT]=$success_rate
            TIMESTAMPS[$REPORT_COUNT]=$timestamp
            REPORT_COUNT=$((REPORT_COUNT + 1))
        fi
    fi
done

if [ $REPORT_COUNT -lt 2 ]; then
    echo "ℹ️  Insufficient historical data for regression analysis (need ≥2 reports)"
    exit 0
fi

echo "📈 Found $REPORT_COUNT recent validation runs"

# Calculate regression metrics
CURRENT_RATE=${SUCCESS_RATES[0]}
PREVIOUS_RATE=${SUCCESS_RATES[1]}

echo "   Current: ${TIMESTAMPS[0]} - ${CURRENT_RATE}%"
echo "   Previous: ${TIMESTAMPS[1]} - ${PREVIOUS_RATE}%"

# Calculate rate difference
RATE_DIFF=$(echo "$PREVIOUS_RATE - $CURRENT_RATE" | bc -l 2>/dev/null || echo "0")

# Regression thresholds
CRITICAL_REGRESSION_THRESHOLD=10.0  # 10% drop is critical
WARNING_REGRESSION_THRESHOLD=5.0    # 5% drop triggers warning

if (( $(echo "$RATE_DIFF > $CRITICAL_REGRESSION_THRESHOLD" | bc -l 2>/dev/null || echo "0") )); then
    echo "❌ CRITICAL EFFECTIVENESS REGRESSION DETECTED!"
    echo "   Drop: ${RATE_DIFF}% (threshold: ${CRITICAL_REGRESSION_THRESHOLD}%)"
    echo "   Previous: ${PREVIOUS_RATE}% → Current: ${CURRENT_RATE}%"
    echo "💡 This indicates a serious degradation in analysis effectiveness"
    echo "🔧 Immediate investigation required"
    exit 1
elif (( $(echo "$RATE_DIFF > $WARNING_REGRESSION_THRESHOLD" | bc -l 2>/dev/null || echo "0") )); then
    echo "⚠️  EFFECTIVENESS REGRESSION WARNING"
    echo "   Drop: ${RATE_DIFF}% (threshold: ${WARNING_REGRESSION_THRESHOLD}%)"
    echo "   Previous: ${PREVIOUS_RATE}% → Current: ${CURRENT_RATE}%"
    echo "💡 This indicates a potential issue with analysis effectiveness"
    echo "🔍 Consider investigating the cause"
    # Don't fail CI for warnings, but log clearly
else
    TREND="stable"
    if (( $(echo "$CURRENT_RATE > $PREVIOUS_RATE" | bc -l 2>/dev/null || echo "0") )); then
        TREND="improving (+$(echo "$CURRENT_RATE - $PREVIOUS_RATE" | bc -l))"
    elif (( $(echo "$RATE_DIFF < 0.1" | bc -l 2>/dev/null || echo "0") )); then
        TREND="stable"
    fi

    echo "✅ No effectiveness regression detected"
    echo "   Trend: $TREND"
fi

# Calculate trend over last 3 runs if available
if [ $REPORT_COUNT -ge 3 ]; then
    echo ""
    echo "📉 Trend Analysis (last 3 runs):"
    THREE_RUNS_AGO=${SUCCESS_RATES[2]}
    OVERALL_CHANGE=$(echo "$CURRENT_RATE - $THREE_RUNS_AGO" | bc -l 2>/dev/null || echo "0")

    if (( $(echo "$OVERALL_CHANGE > 1.0" | bc -l 2>/dev/null || echo "0") )); then
        echo "   📈 Improving: +${OVERALL_CHANGE}% over 3 runs"
    elif (( $(echo "$OVERALL_CHANGE < -1.0" | bc -l 2>/dev/null || echo "0") )); then
        echo "   📉 Declining: ${OVERALL_CHANGE}% over 3 runs"
    else
        echo "   📊 Stable: ${OVERALL_CHANGE}% change over 3 runs"
    fi
fi

echo ""
echo "🎯 Regression Detection Complete"
echo "   - Critical threshold: >${CRITICAL_REGRESSION_THRESHOLD}% drop"
echo "   - Warning threshold: >${WARNING_REGRESSION_THRESHOLD}% drop"

exit 0